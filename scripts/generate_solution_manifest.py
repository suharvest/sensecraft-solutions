#!/usr/bin/env python3
"""Generate solution manifest, zip archives, and bundled_hashes.json.

Scans the solutions/ directory, creates reproducible zip archives for each
solution, and writes manifest.json + bundled_hashes.json.  Optionally uploads
everything to Alibaba Cloud OSS via ossutil.

Usage:
    uv run python scripts/generate_solution_manifest.py                 # generate + upload to OSS
    uv run python scripts/generate_solution_manifest.py --no-upload     # generate only, no upload
    uv run python scripts/generate_solution_manifest.py --output-dir ./dist
"""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return 'sha256:<hex>' digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# Names/suffixes that must never ship in an OTA zip even if git can't be
# consulted (fallback denylist; the primary filter is git-ignore below).
_JUNK_NAMES = {".DS_Store", "__pycache__", ".pytest_cache", ".venv", "Thumbs.db"}
_JUNK_SUFFIXES = {".pyc", ".pyo"}


def _filter_gitignored(files: list[Path], solution_dir: Path) -> list[Path]:
    """Drop files git would ignore (single batched ``git check-ignore`` call).

    The OTA zip must mirror what git tracks — committed ``bundled_hashes.json``
    is the source of truth, so anything git-ignored (build context, dev caches,
    OS junk) has no business in the published package. Falls back to the static
    denylist when git is unavailable (e.g. building from a source tarball).
    """
    # Paths must be relative to *solution_dir* (= git's cwd) so anchored
    # ignore rules like ``solutions/x/assets/docker/agent/`` resolve correctly;
    # git echoes each ignored path back verbatim.
    rel = {p: p.relative_to(solution_dir).as_posix() for p in files}
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            input="\n".join(rel.values()),
            cwd=solution_dir,
            capture_output=True,
            text=True,
        )
        # rc 0 = some ignored, 1 = none ignored; anything else = git error.
        if proc.returncode in (0, 1):
            ignored = {line for line in proc.stdout.splitlines() if line}
            return [p for p in files if rel[p] not in ignored]
    except (OSError, ValueError):
        pass
    # Fallback: no git — drop obvious junk by name/suffix.
    return [
        p
        for p in files
        if not (set(p.parts) & _JUNK_NAMES or p.suffix in _JUNK_SUFFIXES)
    ]


def create_solution_zip(solution_dir: Path, output_path: Path) -> None:
    """Create a content-reproducible zip of *solution_dir* at *output_path*.

    Files inside the zip are stored relative to the solution directory
    (e.g. ``solution.yaml``, ``intro/description.md``).  Entries are sorted
    alphabetically for reproducibility. Git-ignored paths are excluded so the
    published package never carries build context, dev caches, or OS junk.

    The archive must hash identically across machines and checkouts so an
    unchanged solution keeps a stable ``bundled_hashes`` entry (no spurious
    OTA churn). ``zipfile.write`` would bake in each file's filesystem mtime
    and permission bits — neither of which git preserves — so we build the
    entries by hand with a fixed timestamp, fixed permissions, and a pinned
    compression level. The hash then depends only on path + content.
    """
    # Symlinks are rejected outright (not just excluded from the zip): a
    # committed solution symlinking to something like /proc/self/environ
    # would otherwise have is_file()/read_bytes() follow it and bake the
    # publishing process's environment (incl. any injected secrets) into
    # the uploaded zip. Solutions have no legitimate reason to contain one.
    symlinks = [p for p in solution_dir.rglob("*") if p.is_symlink()]
    if symlinks:
        raise ValueError(
            f"{solution_dir.name}: refusing to publish — contains symlink(s): "
            + ", ".join(str(p.relative_to(solution_dir)) for p in symlinks)
        )

    all_files = sorted(
        p for p in solution_dir.rglob("*") if p.is_file() and not p.is_symlink()
    )
    all_files = _filter_gitignored(all_files, solution_dir)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file_path in all_files:
            arcname = file_path.relative_to(solution_dir).as_posix()
            # Fixed (1980-01-01 = zip epoch floor) mtime + fixed 0644 perms,
            # so checkout-dependent stat metadata can't perturb the hash.
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, file_path.read_bytes())


def _dirty_paths(solutions_dir: Path) -> list[str]:
    """Return uncommitted paths under ``solutions_dir``, worktree or index.

    Zips are built from files on disk, not from a git revision, so whatever is
    sitting in the working tree is what gets published — including a
    colleague's half-finished edit or an untracked image that has not been
    reviewed. Returns an empty list when git is unavailable, since a source
    tarball has nothing to compare against.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", str(solutions_dir)],
            cwd=solutions_dir,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    # Porcelain v1: two status columns, a space, then the path.
    return [line[3:] for line in proc.stdout.splitlines() if line.strip()]


def discover_solutions(solutions_dir: Path) -> list[Path]:
    """Return sorted list of solution directories that contain solution.yaml."""
    results = []
    for child in sorted(solutions_dir.iterdir()):
        if child.is_dir() and (child / "solution.yaml").exists():
            results.append(child)
    return results


def upload_to_oss(local_path: Path, oss_path: str) -> None:
    """Upload a local file to OSS using ossutil."""
    cmd = ["ossutil", "cp", str(local_path), oss_path, "--force"]
    print(f"  uploading {local_path.name} -> {oss_path}")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate solution manifest and zip archives."
    )
    parser.add_argument(
        "--solutions-dir",
        type=Path,
        default=None,
        help="Path to solutions directory (default: ../solutions relative to script)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to write zips, manifest.json, and bundled_hashes.json (default: cwd)",
    )
    parser.add_argument(
        "--base-url",
        default="https://sensecraft-statics.seeed.cc/solution-app/solutions",
        help="Base URL used in manifest.json",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=True,
        help="Upload zips and manifest to OSS using ossutil (default: True)",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to OSS",
    )
    parser.add_argument(
        "--min-app-version",
        default="0.2.0",
        help="Minimum app version recorded in manifest (default: 0.2.0)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "Package the working tree even when it has uncommitted changes. "
            "Off by default: zips are built from files on disk, so a dirty "
            "tree publishes work in progress"
        ),
    )
    args = parser.parse_args()

    # Resolve solutions directory
    if args.solutions_dir is not None:
        solutions_dir = args.solutions_dir.resolve()
    else:
        solutions_dir = Path(__file__).resolve().parent.parent / "solutions"

    if not solutions_dir.is_dir():
        print(f"Error: solutions directory not found: {solutions_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir: Path = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Solutions dir : {solutions_dir}")
    print(f"Output dir    : {output_dir}")
    print()

    dirty = _dirty_paths(solutions_dir)
    if dirty and not args.allow_dirty:
        print(
            f"Error: {len(dirty)} uncommitted path(s) under {solutions_dir}.",
            file=sys.stderr,
        )
        for path in dirty[:10]:
            print(f"  {path}", file=sys.stderr)
        if len(dirty) > 10:
            print(f"  ... and {len(dirty) - 10} more", file=sys.stderr)
        print(
            "\nZips are built from the working tree, so these would ship as-is. "
            "Commit or stash them, or pass --allow-dirty if that is intended.",
            file=sys.stderr,
        )
        sys.exit(1)
    if dirty:
        print(f"WARNING: packaging {len(dirty)} uncommitted path(s) (--allow-dirty)\n")

    solutions = discover_solutions(solutions_dir)
    if not solutions:
        print("No solutions found (no directories with solution.yaml).")
        sys.exit(0)

    # Load optional deprecation list — IDs of solutions that should be removed
    # from clients that previously had them installed (e.g. merged/retired).
    deprecated_file = solutions_dir / ".deprecated.json"
    deprecated_ids: list = []
    if deprecated_file.exists():
        try:
            loaded = json.loads(deprecated_file.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                deprecated_ids = [str(x) for x in loaded]
            else:
                print(
                    f"Warning: {deprecated_file} is not a JSON array; ignoring.",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"Warning: failed to parse {deprecated_file}: {e}", file=sys.stderr)
    if deprecated_ids:
        print(f"Deprecated solutions: {deprecated_ids}")
    else:
        print("No deprecated solutions.")
    print()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest_solutions: dict = {}
    bundled_hashes: dict = {}

    for sol_dir in solutions:
        solution_id = sol_dir.name
        zip_path = output_dir / f"{solution_id}.zip"

        print(f"[{solution_id}] creating zip ...")
        create_solution_zip(sol_dir, zip_path)

        file_hash = sha256_file(zip_path)
        file_size = zip_path.stat().st_size

        print(f"  hash: {file_hash}")
        print(f"  size: {file_size} bytes")

        manifest_solutions[solution_id] = {
            "hash": file_hash,
            "size": file_size,
            "updated_at": now,
            "min_app_version": args.min_app_version,
        }
        bundled_hashes[solution_id] = file_hash

    # Write manifest.json
    manifest = {
        "version": 1,
        "generated_at": now,
        "base_url": args.base_url,
        "deprecated": deprecated_ids,
        "solutions": manifest_solutions,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    publishing = args.upload and not args.no_upload

    print(f"\nWrote {manifest_path}")

    # Write bundled_hashes.json (to output_dir AND solutions_dir so runtime can find it)
    hashes_content = json.dumps(bundled_hashes, indent=2, ensure_ascii=False) + "\n"
    hashes_path = output_dir / "bundled_hashes.json"
    hashes_path.write_text(hashes_content, encoding="utf-8")
    print(f"Wrote {hashes_path}")

    # The in-repo copy is the runtime source of truth and gets committed, so it
    # is only refreshed on a real publish. A --no-upload run is a dry run and
    # must leave the checkout untouched: it used to rewrite this file anyway,
    # which on a dirty tree silently staged someone else's work for release.
    solutions_hashes_path = solutions_dir / "bundled_hashes.json"
    if publishing and solutions_hashes_path != hashes_path:
        solutions_hashes_path.write_text(hashes_content, encoding="utf-8")
        print(f"Wrote {solutions_hashes_path}")
    elif not publishing:
        print(f"Dry run: left {solutions_hashes_path} untouched")

    # Upload unless --no-upload
    if publishing:
        oss_prefix = "oss://sensecraft-statics/solution-app/solutions"
        print("\nUploading to OSS ...")

        for solution_id in manifest_solutions:
            zip_path = output_dir / f"{solution_id}.zip"
            upload_to_oss(zip_path, f"{oss_prefix}/{solution_id}.zip")

        upload_to_oss(manifest_path, f"{oss_prefix}/manifest.json")
        upload_to_oss(hashes_path, f"{oss_prefix}/bundled_hashes.json")

        print("\nUpload complete.")

    print("\nDone.")


if __name__ == "__main__":
    main()

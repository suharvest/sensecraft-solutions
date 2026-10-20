#!/usr/bin/env python3
"""Generate solution manifest, zip archives, and bundled_hashes.json.

Scans the solutions/ directory, creates reproducible zip archives for each
solution, and writes manifest.json + bundled_hashes.json for dry runs. CDN
publication consumes the signed content-cdn artifact produced by the App
Engine Build and verifies it before uploading via ossutil.

Usage:
    uv run python scripts/generate_solution_manifest.py --no-upload     # generate only, no upload
    uv run python scripts/generate_solution_manifest.py --output-dir ./dist --no-upload
    uv run python scripts/generate_solution_manifest.py --publish-artifact-dir ./content-cdn --no-upload
    uv run python scripts/generate_solution_manifest.py --publish-artifact-dir ./content-cdn --upload-signed
"""

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

APP_MINISIGN_PUBLIC_KEY = "RWTg282IuJHsoMOFZC0DP1q0LrS384gJsCLrXyX3CIzIKLPUHm3GGmBv"
_SAFE_SOLUTION_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_CONTENT_PIN = re.compile(r"^[0-9a-f]{40}$")
_SIGNED_BASE_URL = re.compile(
    r"^https://sensecraft-statics\.seeed\.cc/solution-app/solutions/releases/"
    r"([0-9a-f]{40})$"
)
_OSS_VERSIONING_XMLNS = "http://doc.oss-cn-hangzhou.aliyuncs.com"


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

# git can fail transiently (index.lock held by a concurrent command). Retry
# before giving up; never degrade silently.
_CHECK_IGNORE_ATTEMPTS = 3
_CHECK_IGNORE_BACKOFF = 0.15
# "not a git repository" is a permanent, expected state — not a transient fault.
_NOT_A_REPO_RE = re.compile(r"not a git repository", re.I)


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
    last_error: str | None = None
    for attempt in range(_CHECK_IGNORE_ATTEMPTS):
        try:
            proc = subprocess.run(
                ["git", "check-ignore", "--stdin"],
                input="\n".join(rel.values()),
                cwd=solution_dir,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            # git genuinely absent (source tarball, minimal image): the static
            # denylist is the documented degraded mode.
            return _denylist_only(files)
        except (OSError, ValueError) as exc:  # transient: pipe/exec hiccup
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            # rc 0 = some ignored, 1 = none ignored; anything else = git error.
            if proc.returncode in (0, 1):
                ignored = {line for line in proc.stdout.splitlines() if line}
                return [p for p in files if rel[p] not in ignored]
            if _NOT_A_REPO_RE.search(proc.stderr or ""):
                # git works, this tree just isn't under version control
                # (source tarball, vendored copy). Same documented degraded
                # mode as git being absent — retrying cannot change it.
                return _denylist_only(files)
            last_error = (
                f"exit {proc.returncode}: {proc.stderr.strip() or '(no stderr)'}"
            )
        if attempt + 1 < _CHECK_IGNORE_ATTEMPTS:
            time.sleep(_CHECK_IGNORE_BACKOFF * (attempt + 1))

    # git is present but keeps failing (index.lock contention, a broken repo,
    # resource exhaustion). Degrading to the denylist here would silently ship
    # git-ignored build context into a published OTA zip, so refuse instead.
    raise RuntimeError(
        f"git check-ignore failed {_CHECK_IGNORE_ATTEMPTS}x in {solution_dir} "
        f"({last_error}). Refusing to fall back to the static denylist: it does "
        "not know this repository's .gitignore and would package build context."
    )


def _denylist_only(files: list[Path]) -> list[Path]:
    """Name/suffix denylist — only for when git is not installed at all."""
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
    if "/solutions/releases/" in oss_path and oss_path.endswith(".zip"):
        bucket, key = oss_path.removeprefix("oss://").split("/", 1)
        cmd = [
            "ossutil",
            "api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            f"file://{local_path.resolve()}",
            "--forbid-overwrite",
        ]
        print(f"  uploading immutable {local_path.name} -> {oss_path}")
        try:
            subprocess.run(cmd, check=True)
            return
        except (subprocess.CalledProcessError, OSError) as exc:
            public_url = f"https://sensecraft-statics.seeed.cc/{key}"
            try:
                with urlopen(public_url, timeout=20) as response:
                    existing = response.read()
            except (HTTPError, URLError, OSError) as read_exc:
                raise RuntimeError(
                    f"immutable upload failed for {local_path.name}; existing object "
                    f"could not be verified at {public_url}: {read_exc}"
                ) from exc
            local_size = local_path.stat().st_size
            local_hash = sha256_file(local_path)
            existing_hash = "sha256:" + hashlib.sha256(existing).hexdigest()
            if len(existing) == local_size and existing_hash == local_hash:
                print(
                    "  immutable object already exists with matching hash: "
                    f"{public_url}"
                )
                return
            raise RuntimeError(
                f"immutable upload failed for {local_path.name}; existing object at "
                f"{public_url} differs in size or hash"
            ) from exc
    cmd = ["ossutil", "cp", str(local_path), oss_path, "--force"]
    print(f"  uploading {local_path.name} -> {oss_path}")
    subprocess.run(cmd, check=True)


def preflight_oss_versioning() -> None:
    """Require an OSS bucket state where immutable object creation is valid."""
    cmd = [
        "ossutil",
        "api",
        "get-bucket-versioning",
        "--bucket",
        "sensecraft-statics",
        "--output-format",
        "json",
        "--quiet",
        "--retry-times",
        "1",
    ]
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        raise RuntimeError("OSS bucket versioning preflight failed") from exc
    try:
        state = json.loads(proc.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "OSS bucket versioning preflight returned invalid JSON"
        ) from exc
    if not isinstance(state, dict) or state.get("+@xmlns") != _OSS_VERSIONING_XMLNS:
        raise RuntimeError(
            "OSS bucket versioning preflight returned an unexpected JSON object"
        )
    if "Status" in state:
        raise RuntimeError(
            "OSS bucket versioning must be absent; refusing signed publication"
        )
    if set(state) != {"+@xmlns"}:
        raise RuntimeError("OSS bucket versioning preflight returned unknown fields")


def _verify_minisign(
    path: Path, signature: Path, public_key: str | None = None
) -> None:
    """Verify a mature minisign signature with the App's fixed public key."""
    if public_key is None:
        public_key = APP_MINISIGN_PUBLIC_KEY
    minisign = shutil.which("minisign")
    if not minisign:
        raise RuntimeError("minisign is required to verify signed content artifacts")
    proc = subprocess.run(
        [minisign, "-Vm", str(path), "-x", str(signature), "-P", public_key],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"signature verification failed for {path.name}: {detail}")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON in {path.name}: {exc}") from exc


def _require_regular_file(path: Path, description: str) -> None:
    """Reject links and special files before reading an artifact."""
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise RuntimeError(f"{description} is missing: {path.name}") from exc
    if not stat.S_ISREG(mode):
        raise RuntimeError(f"{description} must be a regular file: {path.name}")


def validate_signed_artifact(artifact_dir: Path) -> list[tuple[Path, str]]:
    """Validate an App Engine Build content-cdn artifact.

    Returns the exact upload inventory in the required order.  RELEASE_STATUS
    and INVENTORY are accepted as CI metadata but are deliberately excluded
    from the upload set.
    """
    artifact_dir = artifact_dir.resolve()
    if not artifact_dir.is_dir():
        raise RuntimeError(f"signed artifact directory not found: {artifact_dir}")
    manifest_path = artifact_dir / "manifest.json"
    manifest_sig = artifact_dir / "manifest.json.minisig"
    hashes_path = artifact_dir / "bundled_hashes.json"
    hashes_sig = artifact_dir / "bundled_hashes.json.minisig"
    required = (manifest_path, manifest_sig, hashes_path, hashes_sig)
    for path in required:
        _require_regular_file(path, "signed artifact file")

    _verify_minisign(manifest_path, manifest_sig)
    _verify_minisign(hashes_path, hashes_sig)
    manifest = _read_json(manifest_path)
    bundled_hashes = _read_json(hashes_path)
    if not isinstance(manifest, dict) or not isinstance(
        manifest.get("solutions"), dict
    ):
        raise RuntimeError("manifest.json has no solutions object")
    if not isinstance(bundled_hashes, dict):
        raise RuntimeError("bundled_hashes.json must be an object")
    solutions = manifest["solutions"]
    if set(solutions) != set(bundled_hashes):
        raise RuntimeError("manifest and bundled_hashes solution IDs differ")

    base_url = manifest.get("base_url")
    base_match = (
        _SIGNED_BASE_URL.fullmatch(base_url) if isinstance(base_url, str) else None
    )
    if not base_match:
        raise RuntimeError(
            "signed artifact base_url must be exactly "
            "https://sensecraft-statics.seeed.cc/solution-app/solutions/"
            "releases/<40-hex-pin>"
        )
    content_pin = base_match.group(1)

    upload: list[tuple[Path, str]] = []
    for solution_id in sorted(solutions):
        if not isinstance(solution_id, str) or not _SAFE_SOLUTION_ID.fullmatch(
            solution_id
        ):
            raise RuntimeError(f"unsafe solution ID: {solution_id!r}")
        entry = solutions[solution_id]
        digest = bundled_hashes[solution_id]
        entry_hash = entry.get("hash") if isinstance(entry, dict) else None
        if not isinstance(entry_hash, str) or not _SHA256.fullmatch(entry_hash):
            raise RuntimeError(f"invalid manifest hash for {solution_id}")
        if (
            not isinstance(digest, str)
            or entry_hash != digest
            or not _SHA256.fullmatch(digest)
        ):
            raise RuntimeError(f"manifest/hash mismatch for {solution_id}")
        size = entry.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise RuntimeError(f"invalid manifest size for {solution_id}")
        zip_path = artifact_dir / f"{solution_id}.zip"
        _require_regular_file(zip_path, "solution archive")
        actual_size = zip_path.stat().st_size
        actual_hash = sha256_file(zip_path)
        if actual_size != size or actual_hash != digest:
            raise RuntimeError(f"zip hash/size mismatch for {solution_id}")
        upload.append(
            (
                zip_path,
                f"oss://sensecraft-statics/solution-app/solutions/releases/"
                f"{content_pin}/{solution_id}.zip",
            )
        )

    status_path = artifact_dir / "RELEASE_STATUS.json"
    _require_regular_file(status_path, "signed artifact file")
    status = _read_json(status_path)
    if (
        not isinstance(status, dict)
        or status.get("signed") is not True
        or status.get("publishable") is not True
    ):
        raise RuntimeError(
            "RELEASE_STATUS.json must set signed=true and publishable=true"
        )
    if status.get("channel") != "stable":
        raise RuntimeError("content publication requires a stable signed artifact")
    if (
        not isinstance(status.get("content_pin"), str)
        or not _CONTENT_PIN.fullmatch(status["content_pin"])
        or status["content_pin"] != content_pin
    ):
        raise RuntimeError(
            "RELEASE_STATUS.json content_pin does not match manifest base_url"
        )

    allowed = {
        "manifest.json",
        "manifest.json.minisig",
        "bundled_hashes.json",
        "bundled_hashes.json.minisig",
        "RELEASE_STATUS.json",
        "INVENTORY",
    } | {f"{solution_id}.zip" for solution_id in solutions}
    unexpected = sorted(
        path.name for path in artifact_dir.iterdir() if path.name not in allowed
    )
    if unexpected:
        raise RuntimeError(
            "signed artifact contains unrelated files: " + ", ".join(unexpected)
        )

    upload.extend(
        [
            (
                hashes_path,
                "oss://sensecraft-statics/solution-app/solutions/bundled_hashes.json",
            ),
            (
                hashes_sig,
                "oss://sensecraft-statics/solution-app/solutions/bundled_hashes.json.minisig",
            ),
            (
                manifest_path,
                "oss://sensecraft-statics/solution-app/solutions/manifest.json",
            ),
            (
                manifest_sig,
                "oss://sensecraft-statics/solution-app/solutions/manifest.json.minisig",
            ),
        ]
    )
    return upload


def print_upload_inventory(upload: list[tuple[Path, str]]) -> None:
    print(f"SIGNED_ARTIFACT_INVENTORY count={len(upload)}")
    for path, destination in upload:
        print(
            f"  {path.resolve()} size={path.stat().st_size} {sha256_file(path)} -> {destination}"
        )


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
        help=(
            "Legacy unsigned upload mode (refused); use --upload-signed with a "
            "verified --publish-artifact-dir"
        ),
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to OSS",
    )
    parser.add_argument(
        "--publish-artifact-dir",
        type=Path,
        help=(
            "Consume and validate a signed App Engine Build content-cdn artifact; "
            "does not regenerate source content"
        ),
    )
    parser.add_argument(
        "--upload-signed",
        action="store_true",
        help="Upload a validated --publish-artifact-dir (requires explicit opt-in)",
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

    publishing = not args.publish_artifact_dir and args.upload and not args.no_upload
    if args.upload_signed and not args.publish_artifact_dir:
        parser.error("--upload-signed requires --publish-artifact-dir")
    if args.publish_artifact_dir:
        upload_inventory = validate_signed_artifact(args.publish_artifact_dir)
        print(f"Signed artifact : {args.publish_artifact_dir.resolve()}")
        print_upload_inventory(upload_inventory)
        if args.upload_signed and not args.no_upload:
            preflight_oss_versioning()
            print("\nUploading validated signed artifact to OSS ...")
            for local_path, oss_path in upload_inventory:
                upload_to_oss(local_path, oss_path)
            print("\nUpload complete.")
        else:
            print("Dry run: no source files or CDN objects were modified")
        return

    if publishing:
        parser.error(
            "refusing unsigned real upload: use the signed App Engine Build "
            "content-cdn artifact with --publish-artifact-dir and --upload-signed"
        )

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
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
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

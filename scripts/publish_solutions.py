#!/usr/bin/env python3
"""publish_solutions.py

Unified solution content packaging, indexing, signing, and CDN publishing script.
Implements the Content Publish Migration Specification.

Usage:
    python3 scripts/publish_solutions.py \
        --solutions-dir ./solutions \
        --output-dir ./content-cdn \
        --content-pin <40-hex-commit> \
        --sequence 1 \
        --sign \
        --offline
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import json
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required. Please install it via 'pip install pyyaml' or 'uv add pyyaml'.",
        file=sys.stderr,
    )
    sys.exit(1)

JSON_SAFE_INTEGER_MAX = 9007199254740991

JUNK_NAMES = {
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    ".git",
    ".gitignore",
    ".env",
    ".env.local",
    ".env.production",
    "DEPLOY_LOG.md",
}

SENSITIVE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.(pem|key|p12|pfx|p8|keystore|jks|der|crt)$", re.IGNORECASE),
    re.compile(r"^(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\..*)?$", re.IGNORECASE),
    re.compile(r"^\.(npmrc|netrc|dockercfg)$", re.IGNORECASE),
    re.compile(r"^credentials(\..+)?$", re.IGNORECASE),
    re.compile(r"^secrets?(\..+)?\.json$", re.IGNORECASE),
]

LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def is_sensitive_file(name: str) -> bool:
    if name.lower() == ".env.example":
        return False
    return any(p.match(name) for p in SENSITIVE_PATTERNS)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package, index, sign and publish solution content to CDN."
    )
    parser.add_argument(
        "--solutions-dir",
        type=Path,
        required=True,
        help="Directory containing solution source directories (with solution.yaml).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory where packaged ZIPs and manifests will be written.",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="",
        help="Base URL for solution zip archives (e.g. https://.../releases/<pin>).",
    )
    parser.add_argument(
        "--content-pin",
        type=str,
        default="",
        help="40-hex commit hash of the solution content revision.",
    )
    parser.add_argument(
        "--sequence",
        type=int,
        default=None,
        help="Monotonically increasing sequence number for manifest anti-rollback.",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign manifest, bundled hashes, and solutions index using minisign.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload generated artifacts to OSS via ossutil.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preflight mode: validate, package, preflight OSS checks, test-sign, no write to OSS.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Offline mode: package and sign locally with zero network or OSS interaction.",
    )
    parser.add_argument(
        "--minisign-key-file",
        type=Path,
        default=None,
        help="Path to minisign secret key file (or set via CONTENT_SIGNING_PRIVATE_KEY env).",
    )
    parser.add_argument(
        "--minisign-pubkey",
        type=str,
        default=None,
        help="Minisign base64 public key for signature verification.",
    )
    parser.add_argument(
        "--min-app-version",
        type=str,
        default="0.5.0",
        help="Minimum client app version recorded in manifest entries.",
    )
    parser.add_argument(
        "--min-engine-version",
        type=str,
        default="0.0.11",
        help="Minimum engine version recorded in manifest entries.",
    )
    parser.add_argument(
        "--oss-bucket",
        type=str,
        default="sensecraft-statics",
        help="Target OSS bucket name.",
    )
    parser.add_argument(
        "--oss-prefix",
        type=str,
        default="solution-app/solutions",
        help="Target OSS path prefix.",
    )
    parser.add_argument(
        "--generate-test-keys",
        action="store_true",
        help="Allow generating ephemeral test keypair for signing (strictly disallowed with --upload).",
    )
    parser.add_argument(
        "--allow-local-branch",
        action="store_true",
        help="Allow publishing from a local branch without verifying origin/main reachability (testing only).",
    )
    return parser.parse_args(argv)


def check_repo_boundaries(solutions_dir: Path, repo_root: Path | None = None) -> Path:
    """Ensure solutions_dir is within the repository checkout and return repo root."""
    if solutions_dir.is_symlink():
        raise ValueError("solutions_dir must not be a symlink")

    resolved_solutions_dir = solutions_dir.resolve()
    res = subprocess.run(
        ["git", "-C", str(resolved_solutions_dir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise ValueError(
            f"solutions-dir ({resolved_solutions_dir}) must be inside repository checkout: directory is not inside a git repository"
        )

    detected_root = Path(res.stdout.strip()).resolve()
    target_root = repo_root.resolve() if repo_root is not None else detected_root

    try:
        resolved_solutions_dir.relative_to(target_root)
    except ValueError:
        raise ValueError(
            f"solutions-dir ({resolved_solutions_dir}) must be inside repository checkout ({target_root})"
        )
    return target_root


def check_head_and_pin(
    repo_root: Path,
    requested_pin: str,
    offline: bool = False,
    allow_local_branch: bool = False,
    upload: bool = False,
) -> str:
    """Bind HEAD to content-pin and verify ancestry."""
    if upload and allow_local_branch:
        raise ValueError("--allow-local-branch is forbidden in --upload mode")

    res = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    head_commit = res.stdout.strip().lower()

    if requested_pin:
        pin = requested_pin.strip().lower()
        if not re.fullmatch(r"^[0-9a-f]{40}$", pin):
            raise ValueError(f"content-pin must be a 40-character hex string (got '{pin}')")
        if pin != head_commit:
            raise ValueError(
                f"Mismatched HEAD vs content_pin: HEAD is {head_commit}, but --content-pin is {pin}"
            )
    else:
        pin = head_commit

    # Reachability check: git merge-base --is-ancestor "$CONTENT_PIN" origin/main
    if upload or (not offline and not allow_local_branch):
        verify_origin = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "origin/main"],
            capture_output=True,
            text=True,
        )
        if verify_origin.returncode != 0:
            raise ValueError(
                f"Authoritative ancestry check failed: cannot resolve origin/main in {repo_root}. "
                "In online mode, origin/main reachability is required. "
                "Use --allow-local-branch or --offline to bypass for local testing."
            )

        check_ancestor = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", pin, "origin/main"],
            capture_output=True,
            text=True,
        )
        if check_ancestor.returncode != 0:
            raise ValueError(
                f"Authoritative ancestry check failed: content-pin {pin} is not an ancestor of origin/main"
            )
    else:
        # Fallback to verifying against HEAD when offline or --allow-local-branch is specified
        fb = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", pin, "HEAD"],
            capture_output=True,
            text=True,
        )
        if fb.returncode != 0:
            raise ValueError(f"content-pin {pin} is not reachable from HEAD")

    return pin


def check_clean_tree(repo_root: Path) -> None:
    """Assert that the git working tree is clean."""
    res = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    dirty = res.stdout.strip()
    if dirty:
        raise ValueError(
            f"Working tree is dirty (uncommitted changes or untracked files detected):\n{dirty}\nClean checkout required."
        )


def get_git_tracked_files(repo_root: Path, content_pin: str, rel_path: str) -> list[str]:
    """Retrieve list of git-tracked files under rel_path at content_pin."""
    res = subprocess.run(
        ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only", content_pin, "--", rel_path],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    return sorted(lines)


def check_lfs_pointers(repo_root: Path, tracked_files: list[str]) -> None:
    """Ensure no tracked file is an unmaterialized Git LFS pointer."""
    for rel_file in tracked_files:
        full_path = repo_root / rel_file
        if full_path.is_file():
            header = full_path.read_bytes()[: len(LFS_POINTER_PREFIX)]
            if header.startswith(LFS_POINTER_PREFIX):
                raise ValueError(
                    f"Git LFS pointer detected in {rel_file}: must materialize full file content before publishing"
                )


def resolve_commit_time(repo_root: Path, content_pin: str) -> int:
    """Return commit timestamp as integer unix epoch from authoritative git log."""
    res = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%ct", content_pin],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0 and res.stdout.strip():
        try:
            return int(res.stdout.strip())
        except ValueError:
            pass
    raise ValueError(f"Could not determine git commit timestamp for pin '{content_pin}' in {repo_root}")


def resolve_iso_time(repo_root: Path, content_pin: str) -> str:
    """Return deterministic ISO timestamp from git commit time."""
    timestamp = resolve_commit_time(repo_root, content_pin)
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_sequence(seq: int | None, dry_run: bool, offline: bool) -> int:
    if seq is not None:
        if seq < 1:
            raise ValueError(f"sequence must be >= 1 (floor is 1), got {seq}")
        if seq > JSON_SAFE_INTEGER_MAX:
            raise ValueError(f"sequence must be between 1 and {JSON_SAFE_INTEGER_MAX} (got {seq})")
        return seq

    if dry_run or offline:
        return 1

    raise ValueError("Missing required --sequence (must be an integer >= 1 and <= 9007199254740991)")


def simple_yaml_load(path: Path) -> dict[str, Any]:
    """Parse YAML file safely."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}


def create_solution_zip(
    repo_root: Path,
    solution_dir: Path,
    tracked_repo_files: list[str],
    zip_out: Path,
) -> tuple[str, int]:
    """Pack ONLY git-tracked files for this solution into a deterministic zip file; return (sha256_hex, file_size)."""
    canonical_sol_dir = solution_dir.resolve()
    junk_lower = {j.lower() for j in JUNK_NAMES}
    sol_rel_prefix = canonical_sol_dir.relative_to(repo_root).as_posix() + "/"

    valid_files: list[tuple[str, Path]] = []
    for rel_repo_path in tracked_repo_files:
        if not rel_repo_path.startswith(sol_rel_prefix):
            continue
        full_path = repo_root / rel_repo_path
        if not full_path.is_file() or full_path.is_symlink():
            continue

        rel_in_solution = rel_repo_path[len(sol_rel_prefix):]
        parts = rel_in_solution.split("/")
        skip = False
        for part in parts:
            part_lower = part.lower()
            if is_sensitive_file(part):
                print(f"Notice: Excluded sensitive file: {rel_in_solution}", file=sys.stderr)
                skip = True
                break
            if (
                part in JUNK_NAMES
                or part_lower in junk_lower
                or part_lower.endswith("~")
                or part_lower.endswith(".tmp")
            ):
                skip = True
                break
        if not skip:
            valid_files.append((rel_in_solution, full_path))

    valid_files.sort(key=lambda x: x[0])

    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_in_sol, full_path in valid_files:
            zinfo = zipfile.ZipInfo(rel_in_sol, date_time=(2026, 1, 1, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, full_path.read_bytes())

    zip_bytes = zip_out.read_bytes()
    digest = hashlib.sha256(zip_bytes).hexdigest()
    size = len(zip_bytes)
    return digest, size


def run_minisign_sign(
    file_to_sign: Path,
    sec_key: Path,
    commit_time: int,
    version: int,
    password: str | None = None,
) -> Path:
    """Generate deterministic minisign signature with commit timestamp trusted comment."""
    sig_file = file_to_sign.with_name(f"{file_to_sign.name}.minisig")
    if sig_file.exists():
        sig_file.unlink()

    trusted_comment = f"timestamp:{commit_time} file:{file_to_sign.name} version:{version}"
    cmd = [
        "minisign",
        "-Sm",
        str(file_to_sign),
        "-s",
        str(sec_key),
        "-t",
        trusted_comment,
    ]
    if password is not None:
        if not password:
            cmd.append("-W")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"minisign failed: {res.stderr}")
        else:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = proc.communicate(input=f"{password}\n".encode("utf-8"))
            if proc.returncode != 0:
                raise RuntimeError(f"minisign failed: {err.decode('utf-8')}")
    else:
        cmd.append("-W")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"minisign failed: {res.stderr}")

    if not sig_file.is_file() or sig_file.stat().st_size == 0:
        raise RuntimeError(f"Failed to generate signature file at {sig_file}")
    return sig_file


def run_minisign_verify(file_to_verify: Path, sig_file: Path, pubkey_str: str) -> None:
    cmd = ["minisign", "-Vm", str(file_to_verify), "-x", str(sig_file), "-P", pubkey_str]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"minisign verification failed for {file_to_verify}: {res.stderr}")


def _to_bytes(val: str | bytes | None) -> bytes:
    if val is None:
        return b""
    if isinstance(val, bytes):
        return val
    return val.encode("utf-8")


def _to_str(val: str | bytes | None) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return val.decode("utf-8", errors="replace")


def is_oss_not_found(error_text: str) -> bool:
    """Return True only if error explicitly indicates object absence (NoSuchKey)."""
    if "AccessDenied" in error_text:
        return False
    if re.search(r'(?:<Code>|ErrorCode[=:]\s*|Code:\s*)NoSuchKey\b', error_text):
        return True
    if "The specified key does not exist" in error_text:
        return True
    return False


def cat_remote_manifest(
    bucket: str,
    prefix: str,
    ossutil_bin: str = "ossutil",
) -> tuple[dict[str, Any] | None, bytes | None]:
    """Retrieve remote manifest from OSS; return (manifest_dict, raw_bytes) or (None, None) if NoSuchKey.

    Fails closed on any error other than NoSuchKey.
    """
    remote_target = f"oss://{bucket}/{prefix}/v2/manifest.json"
    res = subprocess.run([ossutil_bin, "cat", remote_target], capture_output=True)
    if res.returncode == 0:
        raw_bytes = _to_bytes(res.stdout)
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to parse remote v2 manifest as JSON: {e}")
        return data, raw_bytes

    err = _to_str(res.stderr) + _to_str(res.stdout)
    if is_oss_not_found(err):
        return None, None

    raise RuntimeError(f"Failed to query remote authoritative manifest from OSS ({remote_target}):\n{err}")


def oss_object_exists(
    oss_target: str,
    ossutil_bin: str = "ossutil",
) -> tuple[bool, bytes | None]:
    """Check if an object exists on OSS; return (exists, raw_bytes).

    If object is absent with NoSuchKey, returns (False, None).
    Fails closed on any error other than NoSuchKey.
    """
    res = subprocess.run([ossutil_bin, "cat", oss_target], capture_output=True)
    if res.returncode == 0:
        return True, _to_bytes(res.stdout)

    err = _to_str(res.stderr) + _to_str(res.stdout)
    if is_oss_not_found(err):
        return False, None

    raise RuntimeError(f"Failed to check object status on OSS ({oss_target}):\n{err}")


def check_remote_sequence(
    bucket: str,
    prefix: str,
    sequence: int,
    output_dir: Path,
    ossutil_bin: str = "ossutil",
) -> None:
    """Retrieve remote manifest via cat_remote_manifest and enforce sequence monotonicity."""
    remote_target = f"oss://{bucket}/{prefix}/v2/manifest.json"
    remote_data, remote_bytes = cat_remote_manifest(bucket, prefix, ossutil_bin=ossutil_bin)
    if remote_data is None:
        print(f"[*] Remote v2 manifest not found ({remote_target}); initial publishing at sequence {sequence}.")
        return

    remote_seq = remote_data.get("sequence", 0)

    if sequence < remote_seq:
        raise ValueError(
            f"Publishing rejected: sequence {sequence} is lower than published sequence {remote_seq} (anti-rollback)"
        )
    elif sequence == remote_seq:
        local_bytes = (output_dir / "manifest.json").read_bytes()
        local_sha = hashlib.sha256(local_bytes).hexdigest()
        remote_sha = hashlib.sha256(remote_bytes or b"").hexdigest()
        if local_sha != remote_sha:
            raise ValueError(
                f"Publishing rejected: sequence {sequence} already exists on OSS with different manifest SHA-256 "
                f"({remote_sha} remote vs {local_sha} local). Incremented sequence required."
            )
        print(f"[*] Note: Sequence {sequence} and manifest SHA-256 match remote v2 entry; proceeding with idempotent resume...")
    else:
        print(f"[*] Monotonic sequence check passed: sequence {sequence} > remote sequence {remote_seq}.")


def check_immutable_release_conflicts(
    bucket: str,
    prefix: str,
    content_pin: str,
    artifacts: list[Path] | Path,
    ossutil_bin: str = "ossutil",
    is_test_keys: bool = False,
    prod_pubkey: str | None = None,
    output_dir: Path | None = None,
) -> set[str]:
    """Check release objects against oss://{bucket}/{prefix}/releases/{content_pin}/.

    Returns set of relative paths that already exist identically on OSS (to skip uploading).
    Raises ValueError if an object exists with different sha256 (conflict).
    Raises RuntimeError if OSS query fails unexpectedly (fail-closed).
    """
    already_identical: set[str] = set()
    if isinstance(artifacts, Path):
        out_d = artifacts.resolve()
        files_to_check = sorted(p for p in artifacts.rglob("*") if p.is_file())
    else:
        files_to_check = sorted(p for p in artifacts if p.is_file())
        out_d = _infer_output_dir(files_to_check, output_dir)

    for local_p in files_to_check:
        try:
            rel_path = local_p.resolve().relative_to(out_d.resolve()).as_posix()
        except ValueError:
            target_out = output_dir if output_dir is not None else out_d
            raise ValueError(f"Security Error: Artifact {local_p} is outside output directory {target_out}")
        fname = rel_path
        oss_target = f"oss://{bucket}/{prefix}/releases/{content_pin}/{rel_path}"
        exists, remote_bytes = oss_object_exists(oss_target, ossutil_bin=ossutil_bin)
        if exists and remote_bytes is not None:
            local_bytes = local_p.read_bytes()
            remote_sha = hashlib.sha256(remote_bytes).hexdigest()
            local_sha = hashlib.sha256(local_bytes).hexdigest()
            if is_test_keys and fname.endswith(".minisig"):
                if not prod_pubkey:
                    raise ValueError(
                        "Production public key (--minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY) is required to verify remote signatures during dry-run"
                    )
                target_payload = local_p.with_suffix("")
                if not target_payload.is_file():
                    raise ValueError(
                        f"Cannot verify remote signature {fname}: local payload {target_payload.name} does not exist"
                    )
                with tempfile.NamedTemporaryFile(suffix=".minisig", delete=False) as tmp_sig:
                    tmp_sig.write(remote_bytes)
                    tmp_sig_path = Path(tmp_sig.name)
                try:
                    run_minisign_verify(target_payload, tmp_sig_path, prod_pubkey)
                    print(f"  [*] Remote signature {fname} verified with production public key.")
                except Exception as e:
                    raise ValueError(
                        f"Immutable release conflict: remote {oss_target} signature is invalid: {e}"
                    ) from e
                finally:
                    tmp_sig_path.unlink(missing_ok=True)
                already_identical.add(fname)
            elif remote_sha == local_sha:
                already_identical.add(fname)
            else:
                raise ValueError(
                    f"Immutable release conflict: object {oss_target} already exists on OSS with differing sha256 "
                    f"({remote_sha} remote vs {local_sha} local). Overwriting immutable release objects is forbidden!"
                )

    return already_identical


check_immutable_release_conflict = check_immutable_release_conflicts


def upload_release_artifacts(
    bucket: str,
    prefix: str,
    content_pin: str,
    artifacts: list[Path],
    already_identical: set[str],
    output_dir: Path,
    ossutil_bin: str = "ossutil",
) -> None:
    """Upload immutable release objects to OSS preserving subdirectories."""
    frozen_root_manifest = f"oss://{bucket}/solution-app/solutions/manifest.json"
    pin_dest = f"oss://{bucket}/{prefix}/releases/{content_pin}/"
    valid_artifacts = [p for p in sorted(artifacts) if p.is_file()]

    for local_p in valid_artifacts:
        try:
            rel_path = local_p.resolve().relative_to(output_dir.resolve()).as_posix()
        except ValueError:
            raise ValueError(f"Security Error: Artifact {local_p} is outside output directory {output_dir}")

        if rel_path in already_identical:
            print(f"  [skip] {rel_path} (already identical on OSS)")
            continue

        dest_obj = f"{pin_dest}{rel_path}"
        if dest_obj == frozen_root_manifest:
            raise ValueError("Security Error: direct overwrite of frozen v1 root manifest is forbidden!")

        print(f"  [upload] {rel_path} -> {dest_obj}")
        rel_key = f"{prefix}/releases/{content_pin}/{rel_path}" if prefix else f"releases/{content_pin}/{rel_path}"
        res = subprocess.run(
            [
                ossutil_bin,
                "api",
                "put-object",
                "--bucket",
                bucket,
                "--key",
                rel_key,
                "--body",
                f"file://{local_p.resolve()}",
                "--forbid-overwrite",
                "true",
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Error uploading {rel_path} to {dest_obj}: {res.stderr}")


def verify_tar_stream_strictly(stream: Any) -> None:
    state = "EXPECT_HEADER"
    while True:
        try:
            block = stream.read(512)
        except Exception as e:
            raise ValueError(f"Stream decompression error: {e}")
        if not block:
            if state != "IN_TRAILER":
                raise ValueError(f"Unexpected EOF in state {state}: missing two 512-byte zero blocks")
            break
        if len(block) != 512:
            raise ValueError("Corrupted tar archive: truncated block")

        if block == b"\0" * 512:
            if state == "EXPECT_HEADER":
                state = "SEEN_FIRST_ZERO"
            elif state == "SEEN_FIRST_ZERO":
                state = "IN_TRAILER"
            elif state == "IN_TRAILER":
                pass
        else:
            if state in ("SEEN_FIRST_ZERO", "IN_TRAILER"):
                raise ValueError(f"Non-zero block encountered in state {state}")
            try:
                tarinfo = tarfile.TarInfo.frombuf(block, encoding="utf-8", errors="surrogateescape")
            except Exception as e:
                raise ValueError(f"Corrupted tar archive: invalid tar header: {e}")

            if tarinfo.size < 0:
                raise ValueError(f"Invalid tar member size: {tarinfo.size} cannot be negative")

            data_bytes_needed = ((tarinfo.size + 511) // 512) * 512
            data_read = 0
            while data_read < data_bytes_needed:
                try:
                    chunk = stream.read(min(65536, data_bytes_needed - data_read))
                except Exception as e:
                    raise ValueError(f"Stream decompression error during data read: {e}")
                if not chunk:
                    raise ValueError("Corrupted tar archive: truncated member data")
                data_read += len(chunk)

    if state != "IN_TRAILER":
        raise ValueError(f"Unexpected EOF: tar state was {state}, expected IN_TRAILER")


def parse_ar_members(raw_bytes: bytes) -> list[tuple[str, bytes]]:
    if not raw_bytes.startswith(b"!<arch>\n"):
        raise ValueError("Invalid ar archive: missing !<arch>\\n magic header")
    offset = 8
    members: list[tuple[str, bytes]] = []
    total_len = len(raw_bytes)
    while offset < total_len:
        if offset + 60 > total_len:
            raise ValueError("Invalid ar archive: truncated ar member header")
        header = raw_bytes[offset : offset + 60]
        offset += 60
        magic = header[58:60]
        if magic != b"`\n":
            raise ValueError(f"Invalid ar header magic: {magic!r}")
        raw_name = header[:16].decode("ascii", errors="replace").strip()
        clean_name = raw_name.rstrip("/")
        raw_size = header[48:58].decode("ascii", errors="replace").strip()
        try:
            member_size = int(raw_size)
        except ValueError:
            raise ValueError(f"Invalid ar member size: {raw_size}")
        if member_size < 0:
            raise ValueError(f"Invalid ar member size: {member_size}")
        if offset + member_size > total_len:
            raise ValueError("Invalid ar archive: truncated ar member data")
        member_data = raw_bytes[offset : offset + member_size]
        offset += member_size
        if member_size % 2 != 0:
            if offset >= total_len:
                raise ValueError("Invalid ar archive: missing padding byte after odd-sized member")
            pad_byte = raw_bytes[offset : offset + 1]
            if pad_byte != b"\n":
                raise ValueError(f"Invalid ar archive: expected b'\\n' padding byte, got {pad_byte!r}")
            offset += 1
        members.append((clean_name, member_data))
    return members


def verify_deb_archive_strictly(deb_data: bytes, expected_sha256: str | None = None) -> None:
    if expected_sha256:
        actual_sha = hashlib.sha256(deb_data).hexdigest()
        clean_exp = expected_sha256.strip().lower()
        if actual_sha != clean_exp:
            raise ValueError(f"SHA256 checksum mismatch: expected {clean_exp}, got {actual_sha}")

    members = parse_ar_members(deb_data)
    debian_binary_count = 0
    control_count = 0
    data_count = 0

    for name, content in members:
        if name == "debian-binary":
            debian_binary_count += 1
            if content != b"2.0\n":
                raise ValueError(f"Invalid debian-binary content: expected '2.0\\n', got {content!r}")
        elif name.startswith("control.tar"):
            control_count += 1
            if ".zst" in name or name.endswith(".zst"):
                raise ValueError(f"Incompatible deb package: reCamera does not support zstd compression ({name})")
            if name in ("control.tar.gz",) or name.endswith(".tar.gz"):
                try:
                    gz_stream = gzip.GzipFile(fileobj=io.BytesIO(content))
                    verify_tar_stream_strictly(gz_stream)
                except Exception as e:
                    raise ValueError(f"Corrupted control.tar.gz: {e}")
            elif name in ("control.tar.xz",) or name.endswith(".tar.xz"):
                try:
                    xz_stream = lzma.LZMAFile(io.BytesIO(content))
                    verify_tar_stream_strictly(xz_stream)
                except Exception as e:
                    raise ValueError(f"Corrupted control.tar.xz: {e}")
            else:
                raise ValueError(f"Unsupported compression for control tar: {name} (only .tar.gz and .tar.xz allowed)")
        elif name.startswith("data.tar"):
            data_count += 1
            if ".zst" in name or name.endswith(".zst"):
                raise ValueError(f"Incompatible deb package: reCamera does not support zstd compression ({name})")
            if name in ("data.tar.gz",) or name.endswith(".tar.gz"):
                try:
                    gz_stream = gzip.GzipFile(fileobj=io.BytesIO(content))
                    verify_tar_stream_strictly(gz_stream)
                except Exception as e:
                    raise ValueError(f"Corrupted data.tar.gz: {e}")
            elif name in ("data.tar.xz",) or name.endswith(".tar.xz"):
                try:
                    xz_stream = lzma.LZMAFile(io.BytesIO(content))
                    verify_tar_stream_strictly(xz_stream)
                except Exception as e:
                    raise ValueError(f"Corrupted data.tar.xz: {e}")
            else:
                raise ValueError(f"Unsupported compression for data tar: {name} (only .tar.gz and .tar.xz allowed)")
        else:
            if ".zst" in name:
                raise ValueError(f"Incompatible deb package: reCamera does not support zstd compression ({name})")
            raise ValueError(f"Unexpected member in deb archive: {name}")

    if debian_binary_count != 1:
        raise ValueError(f"Deb archive must contain exactly one debian-binary member (found {debian_binary_count})")
    if control_count != 1:
        raise ValueError(f"Deb archive must contain exactly one control.tar.* member (found {control_count})")
    if data_count != 1:
        raise ValueError(f"Deb archive must contain exactly one data.tar.* member (found {data_count})")


def discover_solutions_from_git(
    repo_root: Path,
    solutions_dir: Path,
    content_pin: str,
    tracked_files: list[str],
) -> list[tuple[str, Path, dict[str, Any]]]:
    """Discover solution entries exclusively from git-tracked files.

    Identifies solution directories by finding tracked solution.yaml files.
    Ignores untracked/ignored folders and rejects duplicate solution IDs.
    """
    canonical_solutions_dir = solutions_dir.resolve()
    rel_solutions_dir = canonical_solutions_dir.relative_to(repo_root.resolve()).as_posix()
    if not rel_solutions_dir.endswith("/"):
        prefix = rel_solutions_dir + "/"
    else:
        prefix = rel_solutions_dir

    tracked_sol_yamls = [
        f for f in tracked_files
        if f.startswith(prefix) and f.endswith("/solution.yaml")
    ]

    solution_entries: list[tuple[str, Path, dict[str, Any]]] = []
    seen_ids: dict[str, Path] = {}

    for rel_yaml_path in sorted(tracked_sol_yamls):
        full_yaml_path = repo_root / rel_yaml_path
        if not full_yaml_path.is_file():
            continue
        sol_dir = full_yaml_path.parent
        if sol_dir.is_symlink():
            continue

        # Check if directory or file is ignored by git
        res_ignore = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-q", "--", rel_yaml_path],
            capture_output=True,
        )
        if res_ignore.returncode == 0:
            # Explicitly ignored by gitignore
            continue

        meta = simple_yaml_load(full_yaml_path)
        sol_id = str(meta.get("id") or sol_dir.name).strip()
        if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", sol_id):
            raise ValueError(f"Invalid solution id '{sol_id}' in {rel_yaml_path}: must match ^[a-zA-Z0-9_-]+$")

        if sol_id in seen_ids:
            raise ValueError(
                f"Duplicate solution id detected: '{sol_id}' in {sol_dir} (already defined in {seen_ids[sol_id]})"
            )
        seen_ids[sol_id] = sol_dir
        solution_entries.append((sol_id, sol_dir, meta))

    return solution_entries


def verify_solution_packages(
    solutions: Path | list[tuple[str, Path, dict[str, Any]]],
    offline: bool = False,
) -> None:
    """Verify deb packages referenced by solutions targeting reCamera/SG2002/riscv64."""
    cache_dir = Path(os.environ.get("SC_DEB_CACHE_DIR", Path.home() / ".cache" / "sensecraft_debs"))

    if isinstance(solutions, Path):
        if not solutions.is_dir():
            return
        solution_items: list[tuple[Path, dict[str, Any]]] = []
        for sol_dir in sorted(solutions.iterdir()):
            if sol_dir.is_symlink() or not sol_dir.is_dir():
                continue
            sol_yaml_file = sol_dir / "solution.yaml"
            if not sol_yaml_file.is_file():
                continue
            sol_meta = simple_yaml_load(sol_yaml_file)
            solution_items.append((sol_dir, sol_meta))
    else:
        solution_items = [(entry[1], entry[2]) for entry in solutions]

    for sol_dir, sol_meta in solution_items:
        devices_dir = sol_dir / "devices"
        if not devices_dir.is_dir():
            continue

        yaml_candidates: list[Path] = []
        for dev_yaml in sorted(devices_dir.glob("*.yaml")):
            if dev_yaml.is_file():
                yaml_candidates.append(dev_yaml)
        apps_dir = devices_dir / "apps"
        if apps_dir.is_dir():
            for app_yaml in sorted(apps_dir.glob("*.yaml")):
                if app_yaml.is_file():
                    yaml_candidates.append(app_yaml)

        for dev_yaml in yaml_candidates:
            dev_data = simple_yaml_load(dev_yaml)
            if not isinstance(dev_data, dict):
                continue

            deb_pkg = (dev_data.get("binary") or {}).get("deb_package")
            if deb_pkg is None:
                deb_pkg = dev_data.get("deb_package")
            if not deb_pkg:
                continue

            if isinstance(deb_pkg, dict):
                deb_path = str(deb_pkg.get("path") or "")
                checksum_info = deb_pkg.get("checksum") or {}
                expected_sha256 = (checksum_info.get("sha256") if isinstance(checksum_info, dict) else None) or deb_pkg.get("sha256")
            elif isinstance(deb_pkg, str):
                deb_path = deb_pkg
                expected_sha256 = None
            else:
                continue

            if not deb_path:
                continue

            dev_type = str(dev_data.get("type") or "").lower()
            dev_class = str(dev_data.get("device_class") or "").lower()
            dev_target = str(dev_data.get("target_platform") or "").lower()
            sol_target = str(sol_meta.get("target_platform") or "").lower()
            path_lower = deb_path.lower()

            is_recamera = (
                "recamera" in dev_type
                or "recamera" in dev_class
                or "recamera" in dev_target
                or "sg2002" in dev_target
                or "recamera" in sol_target
                or "sg2002" in sol_target
                or "riscv64" in path_lower
                or ".zst" in path_lower
            )

            if not is_recamera:
                continue

            if ".zst" in path_lower:
                raise ValueError(
                    f"Incompatible deb package in {dev_yaml}: reCamera does not support zstd compression ({deb_path})"
                )

            deb_bytes: bytes | None = None
            local_candidate = Path(deb_path)
            if local_candidate.is_file():
                deb_bytes = local_candidate.read_bytes()
            elif (dev_yaml.parent / deb_path).is_file():
                deb_bytes = (dev_yaml.parent / deb_path).read_bytes()
            elif (sol_dir / deb_path).is_file():
                deb_bytes = (sol_dir / deb_path).read_bytes()
            elif deb_path.startswith(("http://", "https://")):
                filename = Path(urllib.parse.urlsplit(deb_path).path).name
                if (sol_dir / "packages" / filename).is_file():
                    deb_bytes = (sol_dir / "packages" / filename).read_bytes()
                elif (sol_dir / filename).is_file():
                    deb_bytes = (sol_dir / filename).read_bytes()
                elif (dev_yaml.parent / filename).is_file():
                    deb_bytes = (dev_yaml.parent / filename).read_bytes()
                else:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    cached_file = cache_dir / filename
                    if cached_file.is_file():
                        cached_bytes = cached_file.read_bytes()
                        if not expected_sha256 or hashlib.sha256(cached_bytes).hexdigest() == str(expected_sha256).strip().lower():
                            deb_bytes = cached_bytes
                    if deb_bytes is None:
                        if offline:
                            print(f"Notice: Skipping deb download for {deb_path} in offline mode", file=sys.stderr)
                            continue
                        try:
                            req = urllib.request.Request(deb_path, headers={"User-Agent": "SenseCraft-Publisher/1.0"})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                downloaded = resp.read()
                            cached_file.write_bytes(downloaded)
                            deb_bytes = downloaded
                        except Exception as e:
                            raise ValueError(f"Failed to fetch deb package from {deb_path} for {dev_yaml}: {e}")
            else:
                if offline:
                    print(f"Notice: Deb package {deb_path} not found locally in offline mode", file=sys.stderr)
                    continue
                raise ValueError(f"Deb package not found for {dev_yaml}: {deb_path}")

            if deb_bytes is not None:
                verify_deb_archive_strictly(deb_bytes, expected_sha256=expected_sha256)


V2_AUXILIARY_FILES = [
    "bundled_hashes.json",
    "bundled_hashes.json.minisig",
    "solutions_index.json",
    "solutions_index.json.minisig",
]

V2_ENTRY_FILES = [
    "manifest.json",
    "manifest.json.minisig",
]

V2_PROMOTED_FILES = V2_AUXILIARY_FILES + V2_ENTRY_FILES


def validate_base_url(base_url: str, content_pin: str) -> str:
    """Validate base_url against immutable releases endpoint schema for content_pin.

    If empty, defaults to canonical releases endpoint:
        f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{content_pin}"
    If non-empty, must strictly equal:
        f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{content_pin}"
    Any forbidden, mismatched, or altered base-url is rejected (fail-closed).
    """
    expected = f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{content_pin}"
    cleaned = (base_url or "").strip().rstrip("/")
    if not cleaned:
        return expected
    if cleaned != expected:
        raise ValueError(
            f"Forbidden or mismatched base-url: '{base_url}'. "
            f"Base URL must equal '{expected}'"
        )
    return cleaned


def generate_manifest_dict(
    sequence: int,
    content_pin: str,
    generated_at: str,
    base_url: str,
    manifest_solutions: dict[str, Any],
    solutions_index_sha256: str | None = None,
    solutions_index_size: int | None = None,
    bundled_hashes_sha256: str | None = None,
    bundled_hashes_size: int | None = None,
) -> dict[str, Any]:
    """Generate manifest dictionary binding solutions and auxiliary files."""
    canonical_base_url = validate_base_url(base_url, content_pin)
    manifest_payload: dict[str, Any] = {
        "version": 2,
        "sequence": sequence,
        "content_pin": content_pin,
        "generated_at": generated_at,
        "base_url": canonical_base_url,
        "deprecated": [],
        "solutions": manifest_solutions,
    }
    auxiliary_files: dict[str, Any] = {}
    if solutions_index_sha256 is not None:
        idx_info = {
            "sha256": solutions_index_sha256,
            "size": solutions_index_size,
        }
        manifest_payload["solutions_index"] = idx_info
        auxiliary_files["solutions_index.json"] = idx_info

    if bundled_hashes_sha256 is not None:
        hashes_info = {
            "sha256": bundled_hashes_sha256,
            "size": bundled_hashes_size,
        }
        manifest_payload["bundled_hashes"] = hashes_info
        auxiliary_files["bundled_hashes.json"] = hashes_info

    if auxiliary_files:
        manifest_payload["auxiliary_files"] = auxiliary_files

    return manifest_payload


def _infer_output_dir(artifacts: list[Path], output_dir: Path | None = None) -> Path:
    if output_dir is not None:
        return output_dir.resolve()
    valid = [p.resolve() for p in artifacts if p.is_file() or p.exists()]
    if not valid:
        raise ValueError("Cannot infer output_dir: artifacts list is empty")
    for p in valid:
        if p.name == "manifest.json":
            return p.parent
    try:
        common = Path(os.path.commonpath([p.as_posix() for p in valid]))
        if common.is_file():
            return common.parent
        return common
    except Exception as e:
        raise ValueError(f"Cannot infer output_dir from artifacts: {e}")


def process_solution_cover(
    sol_id: str,
    sol_dir: Path,
    cover_image: str | None,
    repo_root: Path,
    tracked_files_set: set[str],
    output_dir: Path,
    generated_artifacts: list[Path],
) -> str:
    """Safely validate, extract, and rewrite cover image for a solution."""
    if not cover_image or not isinstance(cover_image, str) or not cover_image.strip():
        return ""
    cover_image = cover_image.strip()

    # Absolute URL: keep unchanged
    if cover_image.startswith(("http://", "https://", "data:")):
        return cover_image

    # Path traversal validation
    p = Path(cover_image)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Security Error: Path traversal in cover_image for {sol_id}: {cover_image}")

    # Symlink validation on path components and target file
    cur = sol_dir
    for part in p.parts:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"Security Error: Symlink detected in cover_image for {sol_id}: {cover_image}")

    raw_cover_path = sol_dir / cover_image
    try:
        resolved_sol_dir = sol_dir.resolve()
        resolved_cover_path = raw_cover_path.resolve()
        resolved_cover_path.relative_to(resolved_sol_dir)
    except ValueError:
        raise ValueError(f"Security Error: Path traversal in cover_image for {sol_id}: {cover_image}")

    # Sensitive and junk file check
    junk_lower = {j.lower() for j in JUNK_NAMES}
    for part in p.parts:
        part_lower = part.lower()
        if (
            is_sensitive_file(part)
            or part in JUNK_NAMES
            or part_lower in junk_lower
            or part_lower.endswith("~")
            or part_lower.endswith(".tmp")
        ):
            raise ValueError(
                f"Security Error: Sensitive or junk file referenced as cover_image for {sol_id}: {cover_image}"
            )
    name_lower = raw_cover_path.name.lower()
    if (
        is_sensitive_file(raw_cover_path.name)
        or raw_cover_path.name in JUNK_NAMES
        or name_lower in junk_lower
        or name_lower.endswith("~")
        or name_lower.endswith(".tmp")
    ):
        raise ValueError(
            f"Security Error: Sensitive or junk file referenced as cover_image for {sol_id}: {cover_image}"
        )

    # Missing file downgrade
    if not raw_cover_path.is_file():
        print(f"[WARNING] Solution {sol_id} cover_image {cover_image} not found, setting to empty")
        return ""

    # Git-tracked check
    try:
        rel_repo_path = raw_cover_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"Security Error: cover_image for {sol_id} escapes repository: {cover_image}")

    if rel_repo_path not in tracked_files_set:
        raise ValueError(f"Security Error: cover_image for {sol_id} is not tracked by git: {cover_image}")

    # Sanitize filename and prepare isolated output directory covers/{sol_id}/{clean_filename}
    clean_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", p.name)
    if not clean_filename:
        clean_filename = "cover.png"

    covers_dir = output_dir / "covers"
    if covers_dir.is_symlink():
        raise ValueError(f"Security Error: Output covers directory is a symlink: {covers_dir}")
    covers_dir.mkdir(parents=True, exist_ok=True)
    if covers_dir.is_symlink():
        raise ValueError(f"Security Error: Output covers directory is a symlink: {covers_dir}")
    if not covers_dir.resolve().is_relative_to(output_dir.resolve()):
        raise ValueError(f"Security Error: Output covers directory escapes output directory: {covers_dir}")

    dest_dir = covers_dir / sol_id
    if dest_dir.is_symlink():
        raise ValueError(f"Security Error: Target cover directory is a symlink: {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    if dest_dir.is_symlink():
        raise ValueError(f"Security Error: Target cover directory is a symlink: {dest_dir}")
    if not dest_dir.resolve().is_relative_to(covers_dir.resolve()):
        raise ValueError(f"Security Error: Target cover directory escapes covers directory: {dest_dir}")

    dest_cover = dest_dir / clean_filename
    if dest_cover.is_symlink():
        raise ValueError(f"Security Error: Target cover file is a symlink: {dest_cover}")
    if not dest_cover.resolve().is_relative_to(dest_dir.resolve()):
        raise ValueError(f"Security Error: Target cover path escapes covers directory: {dest_cover}")
    if dest_cover.parent != dest_dir:
        raise ValueError(f"Security Error: Target cover path escapes covers directory: {dest_cover}")

    # Copy to destination
    dest_cover.write_bytes(raw_cover_path.read_bytes())
    generated_artifacts.append(dest_cover)

    return f"covers/{sol_id}/{clean_filename}"


def format_artifact_inventory(
    artifacts: list[Path],
    bucket: str,
    prefix: str,
    content_pin: str,
    output_dir: Path | None = None,
) -> str:
    """Format complete artifact inventory with un-truncated sha256, size, dest, and count.

    Enumerates ALL destinations that will be written:
    - Immutable release objects (releases/<pin>/...) for all generated artifacts.
    - Mutable v2 objects (v2/...) for auxiliary and entry manifest files.
    """
    valid_artifacts = [p for p in sorted(artifacts) if p.is_file()]
    out_d = _infer_output_dir(valid_artifacts, output_dir)
    target_out = output_dir if output_dir is not None else out_d

    for p in valid_artifacts:
        try:
            p.resolve().relative_to(out_d.resolve())
        except ValueError:
            raise ValueError(f"Security Error: Artifact {p} is outside output directory {target_out}")

    artifact_map = {p.resolve().relative_to(out_d.resolve()).as_posix(): p for p in valid_artifacts}

    destinations: list[dict[str, Any]] = []

    # 1. Immutable release destinations for all generated artifacts
    for p in valid_artifacts:
        raw = p.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        size = len(raw)
        try:
            rel_key = p.resolve().relative_to(out_d.resolve()).as_posix()
        except ValueError:
            target_out = output_dir if output_dir is not None else out_d
            raise ValueError(f"Security Error: Artifact {p} is outside output directory {target_out}")
        dest_path = f"oss://{bucket}/{prefix}/releases/{content_pin}/{rel_key}"
        destinations.append({
            "name": rel_key,
            "dest": rel_key,
            "destination": dest_path,
            "size": size,
            "sha256": sha,
        })

    # 2. Mutable v2 auxiliary and entry manifest destinations
    for fname in V2_PROMOTED_FILES:
        if fname in artifact_map:
            p = artifact_map[fname]
            raw = p.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            size = len(raw)
            dest_path = f"oss://{bucket}/{prefix}/v2/{fname}"
            destinations.append({
                "name": fname,
                "dest": fname,
                "destination": dest_path,
                "size": size,
                "sha256": sha,
            })

    lines = [
        "=" * 80,
        f"COMPLETE ARTIFACT INVENTORY (Total: {len(destinations)})",
        "=" * 80,
    ]
    for d in destinations:
        lines.append(f"Artifact: {d['name']}")
        lines.append(f"  Destination: {d['destination']}")
        lines.append(f"  Size:        {d['size']} bytes")
        lines.append(f"  SHA-256:     {d['sha256']}")
    lines.append("=" * 80)
    lines.append(f"Total count: {len(destinations)}")
    lines.append("=" * 80)
    return "\n".join(lines)


def package_and_publish(args: argparse.Namespace) -> int:
    if args.sequence is not None and args.sequence < 1:
        raise ValueError(f"sequence must be >= 1 (floor is 1), got {args.sequence}")

    if args.dry_run:
        args.generate_test_keys = True
        # Unconditionally clear private key variable so dry-run never touches production private key
        args.minisign_key_file = None
        if "CONTENT_SIGNING_PRIVATE_KEY" in os.environ:
            del os.environ["CONTENT_SIGNING_PRIVATE_KEY"]

    if args.upload and getattr(args, "generate_test_keys", False):
        raise ValueError("Security Error: --generate-test-keys is strictly forbidden in production/upload mode (--upload)")

    if args.upload and getattr(args, "allow_local_branch", False):
        raise ValueError("--allow-local-branch is forbidden in --upload mode")

    if args.upload and not args.dry_run and not args.sign:
        raise ValueError("--upload requires --sign")

    # Enforce repo boundaries
    repo_root = check_repo_boundaries(args.solutions_dir)
    solutions_dir = args.solutions_dir.resolve()
    output_dir = args.output_dir.resolve()

    if solutions_dir == output_dir or solutions_dir in output_dir.parents or output_dir in solutions_dir.parents:
        raise ValueError(
            f"output_dir ({output_dir}) and solutions_dir ({solutions_dir}) must not overlap or be nested within each other"
        )

    # Working tree clean check
    check_clean_tree(repo_root)

    # HEAD and Pin binding
    content_pin = check_head_and_pin(
        repo_root,
        args.content_pin,
        offline=args.offline,
        allow_local_branch=getattr(args, "allow_local_branch", False),
        upload=getattr(args, "upload", False),
    )
    sequence = resolve_sequence(args.sequence, args.dry_run, args.offline)

    bucket = args.oss_bucket.strip()
    prefix = args.oss_prefix.strip().strip("/")

    base_url = validate_base_url(args.base_url, content_pin)

    # Get git tracked files under solutions_dir at content_pin
    rel_solutions_dir = solutions_dir.relative_to(repo_root).as_posix()
    tracked_files = get_git_tracked_files(repo_root, content_pin, rel_solutions_dir)

    # Check for Git LFS pointers among tracked files
    check_lfs_pointers(repo_root, tracked_files)

    # Discover valid solution folders from git-tracked files
    solution_entries = discover_solutions_from_git(
        repo_root, solutions_dir, content_pin, tracked_files
    )
    if not solution_entries:
        print(f"Error: no valid solutions containing solution.yaml found in {solutions_dir}", file=sys.stderr)
        return 1

    # Verify deb packages
    verify_solution_packages(solution_entries, offline=args.offline)

    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.zip", "manifest.json*", "bundled_hashes.json*", "solutions_index.json*"):
        for f in output_dir.glob(pattern):
            if f.is_file():
                f.unlink()
    covers_dir = output_dir / "covers"
    if covers_dir.is_symlink():
        raise ValueError(f"Security Error: Output covers directory is a symlink: {covers_dir}")
    if covers_dir.exists():
        if not covers_dir.resolve().is_relative_to(output_dir.resolve()):
            raise ValueError(f"Security Error: Output covers directory escapes output directory: {covers_dir}")
        if covers_dir.is_dir():
            shutil.rmtree(covers_dir, ignore_errors=True)

    print(f"[*] Packaging solutions from: {solutions_dir}")
    print(f"[*] Target content pin:       {content_pin}")
    print(f"[*] Target sequence:          {sequence}")
    print(f"[*] Output directory:         {output_dir}")
    print(f"[*] Base URL:                 {base_url}")
    print(f"[*] Mode:                     {'offline' if args.offline else ('dry-run' if args.dry_run else 'publish')}")

    commit_time = resolve_commit_time(repo_root, content_pin)
    now_iso = resolve_iso_time(repo_root, content_pin)

    tracked_files_set = set(tracked_files)
    generated_artifacts: list[Path] = []
    manifest_solutions: dict[str, Any] = {}
    bundled_hashes: dict[str, str] = {}
    index_solutions: list[dict[str, Any]] = []

    for sol_id, sol_dir, meta in solution_entries:
        zip_path = (output_dir / f"{sol_id}.zip").resolve()
        if zip_path.parent != output_dir or not zip_path.is_relative_to(output_dir):
            raise ValueError(f"Path traversal detected: {zip_path} escapes output directory {output_dir}")

        digest, size = create_solution_zip(repo_root, sol_dir, tracked_files, zip_path)
        generated_artifacts.append(zip_path)
        sha_str = f"sha256:{digest}"
        bundled_hashes[sol_id] = sha_str

        name_zh = (
            (meta.get("name_i18n") or {}).get("zh")
            if isinstance(meta.get("name_i18n"), dict)
            else None
        ) or meta.get("name_zh") or meta.get("name") or sol_id

        intro = meta.get("intro") if isinstance(meta.get("intro"), dict) else {}
        summary = intro.get("summary") or meta.get("summary") or ""
        summary_zh = (
            (intro.get("summary_i18n") or {}).get("zh")
            if isinstance(intro.get("summary_i18n"), dict)
            else None
        ) or intro.get("summary_zh") or meta.get("summary_zh") or summary

        cover_image_raw = intro.get("cover_image") or meta.get("cover_image") or ""
        category = intro.get("category") or meta.get("category") or "general"
        tags_val = intro.get("tags") or meta.get("tags") or []
        tags = tags_val if isinstance(tags_val, list) else [tags_val]
        difficulty = meta.get("difficulty") or "intermediate"
        estimated_time = meta.get("estimated_time") or "30min"

        final_cover = process_solution_cover(
            sol_id=sol_id,
            sol_dir=sol_dir,
            cover_image=cover_image_raw,
            repo_root=repo_root,
            tracked_files_set=tracked_files_set,
            output_dir=output_dir,
            generated_artifacts=generated_artifacts,
        )

        manifest_entry = {
            "hash": sha_str,
            "size": size,
            "updated_at": now_iso,
            "min_app_version": args.min_app_version,
            "min_engine_version": args.min_engine_version,
            "name": meta.get("name") or sol_id,
            "name_zh": name_zh,
            "summary": summary,
            "summary_zh": summary_zh,
            "cover_image": final_cover,
            "category": category,
            "tags": tags,
            "difficulty": difficulty,
            "estimated_time": estimated_time,
        }
        manifest_solutions[sol_id] = manifest_entry

        idx_entry = {
            "id": sol_id,
            "name": meta.get("name") or sol_id,
            "name_zh": name_zh,
            "summary": summary,
            "summary_zh": summary_zh,
            "cover_image": final_cover,
            "category": category,
            "tags": tags,
            "solution_type": meta.get("solution_type") or "solution",
            "difficulty": difficulty,
            "estimated_time": estimated_time,
            "deployed_count": 0,
            "device_refs": meta.get("device_refs") if isinstance(meta.get("device_refs"), list) else [],
            "size": size,
            "hash": sha_str,
            "updated_at": now_iso,
        }
        index_solutions.append(idx_entry)
        print(f"  + [{sol_id}] -> {zip_path.name} ({size} bytes, {sha_str})")

    # Generate bundled_hashes.json
    bundled_hashes_path = output_dir / "bundled_hashes.json"
    bundled_hashes_path.write_text(json.dumps(bundled_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated_artifacts.append(bundled_hashes_path)
    bundled_bytes = bundled_hashes_path.read_bytes()
    bundled_sha = hashlib.sha256(bundled_bytes).hexdigest()
    bundled_size = len(bundled_bytes)

    # Generate solutions_index.json
    solutions_index_path = output_dir / "solutions_index.json"
    index_payload = {
        "version": 1,
        "generated_at": now_iso,
        "solutions": index_solutions,
    }
    solutions_index_path.write_text(json.dumps(index_payload, indent=2) + "\n", encoding="utf-8")
    generated_artifacts.append(solutions_index_path)
    index_bytes = solutions_index_path.read_bytes()
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    index_size = len(index_bytes)

    # Generate manifest.json (v2 format with sequence, bound solutions_index and auxiliary_files)
    manifest_path = output_dir / "manifest.json"
    manifest_payload = generate_manifest_dict(
        sequence=sequence,
        content_pin=content_pin,
        generated_at=now_iso,
        base_url=base_url,
        manifest_solutions=manifest_solutions,
        solutions_index_sha256=index_sha,
        solutions_index_size=index_size,
        bundled_hashes_sha256=bundled_sha,
        bundled_hashes_size=bundled_size,
    )
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    generated_artifacts.append(manifest_path)
    print("[*] Generated core manifest files successfully.")

    # Signing phase
    targets_to_sign = [
        (manifest_path, 2),
        (bundled_hashes_path, 1),
        (solutions_index_path, 1),
    ]

    use_ephemeral = False
    if args.sign or args.dry_run:
        sec_file = getattr(args, "minisign_key_file", None)
        password = os.environ.get("CONTENT_SIGNING_PRIVATE_KEY_PASSWORD")
        temp_key_dir: str | None = None

        has_env_key = bool(os.environ.get("CONTENT_SIGNING_PRIVATE_KEY"))
        has_file_key = bool(sec_file and Path(sec_file).is_file())

        if args.upload:
            if not (has_env_key or has_file_key):
                raise ValueError(
                    "In upload mode, CONTENT_SIGNING_PRIVATE_KEY (env or --minisign-key-file) is strictly required. "
                    "Ephemeral test keys are forbidden in production/upload mode."
                )

        use_ephemeral = False
        if not (has_env_key or has_file_key):
            if args.offline or getattr(args, "generate_test_keys", False):
                use_ephemeral = True
            else:
                raise ValueError(
                    "Signing key missing: CONTENT_SIGNING_PRIVATE_KEY env var or --minisign-key-file is required. "
                    "Ephemeral test keys are only permitted if --offline or --generate-test-keys is passed."
                )

        if use_ephemeral:
            temp_key_dir = tempfile.mkdtemp(prefix="minisign-ephemeral-")
            sec_file = Path(temp_key_dir) / "test.key"
            pub_file = Path(temp_key_dir) / "test.pub"
            subprocess.run(
                ["minisign", "-G", "-f", "-p", str(pub_file), "-s", str(sec_file), "-W"],
                check=True,
                capture_output=True,
            )
            pub_lines = pub_file.read_text(encoding="utf-8").strip().splitlines()
            pubkey = pub_lines[1]
            password = None
            mode_name = "Offline" if args.offline else "Test-keys"
            print(f"[*] {mode_name} mode: generated ephemeral test keypair (pubkey: {pubkey})")
        else:
            pubkey = getattr(args, "minisign_pubkey", None) or os.environ.get("CONTENT_MINISIGN_PUBLIC_KEY")
            if not pubkey:
                raise ValueError(
                    "--minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY environment variable is required when signing with a private key"
                )

            if not sec_file and has_env_key:
                temp_key_dir = tempfile.mkdtemp(prefix="minisign-env-")
                sec_file = Path(temp_key_dir) / "content.key"
                sec_file.write_text(os.environ["CONTENT_SIGNING_PRIVATE_KEY"], encoding="utf-8")
                sec_file.chmod(0o600)

        if not sec_file or not Path(sec_file).is_file():
            raise ValueError("Error: --sign specified but no secret key provided")

        try:
            for target_path, target_version in targets_to_sign:
                sig = run_minisign_sign(
                    target_path,
                    Path(sec_file),
                    commit_time=commit_time,
                    version=target_version,
                    password=password,
                )
                run_minisign_verify(target_path, sig, pubkey)
                generated_artifacts.append(sig)
                print(f"  ✔ Signed & verified: {sig.name}")
        finally:
            if temp_key_dir and os.path.exists(temp_key_dir):
                shutil.rmtree(temp_key_dir, ignore_errors=True)

    # Emit complete artifact inventory BEFORE performing any upload, write, or preflight
    inventory_output = format_artifact_inventory(
        generated_artifacts, bucket, prefix, content_pin, output_dir=output_dir
    )
    print(f"\n{inventory_output}\n")

    # OSS Preflight and Upload Phase
    if not args.offline and (args.upload or args.dry_run):
        # Freeze Guard check
        frozen_root_manifest = f"oss://{bucket}/solution-app/solutions/manifest.json"
        pin_dest = f"oss://{bucket}/{prefix}/releases/{content_pin}/"
        v2_dest = f"oss://{bucket}/{prefix}/v2/"

        if pin_dest.rstrip("/") == f"oss://{bucket}/solution-app/solutions":
            raise ValueError(f"Security Error: direct upload to frozen v1 root ({pin_dest}) is forbidden!")
        if v2_dest.rstrip("/") == f"oss://{bucket}/solution-app/solutions":
            raise ValueError(f"Security Error: direct upload to frozen v1 root ({v2_dest}) is forbidden!")

        # 1. Authoritative sequence retrieval & monotonic check
        check_remote_sequence(bucket, prefix, sequence, output_dir)

        # 2. Immutable release conflict check
        use_test_keys = getattr(args, "generate_test_keys", False) or args.dry_run or use_ephemeral
        prod_pubkey = getattr(args, "minisign_pubkey", None) or os.environ.get("CONTENT_MINISIGN_PUBLIC_KEY")
        already_identical = check_immutable_release_conflicts(
            bucket,
            prefix,
            content_pin,
            generated_artifacts,
            is_test_keys=use_test_keys,
            prod_pubkey=prod_pubkey,
            output_dir=output_dir,
        )

        if args.dry_run:
            print("[*] Dry-run preflight complete. Zero changes written to OSS.")
            return 0

        # Upload phase
        print("[*] Uploading immutable release objects to OSS...")
        upload_release_artifacts(
            bucket=bucket,
            prefix=prefix,
            content_pin=content_pin,
            artifacts=generated_artifacts,
            already_identical=already_identical,
            output_dir=output_dir,
        )

        # Promotion order to v2/: auxiliary files first, entry manifest last
        print("[*] Promoting to mutable v2 entry...")
        gen_names = {
            p.resolve().relative_to(output_dir.resolve()).as_posix()
            for p in generated_artifacts
        }
        for fname in V2_AUXILIARY_FILES:
            if fname in gen_names:
                local_p = output_dir / fname
                if local_p.is_file():
                    dest_obj = f"{v2_dest}{fname}"
                    print(f"  [v2 aux] {fname} -> {dest_obj}")
                    res = subprocess.run(["ossutil", "cp", "-f", str(local_p), dest_obj], capture_output=True, text=True)
                    if res.returncode != 0:
                        raise RuntimeError(f"Error promoting {fname} to {v2_dest}: {res.stderr}")

        for fname in V2_ENTRY_FILES:
            if fname in gen_names:
                local_p = output_dir / fname
                if local_p.is_file():
                    dest_obj = f"{v2_dest}{fname}"
                    print(f"  [v2 entry] {fname} -> {dest_obj}")
                    res = subprocess.run(["ossutil", "cp", "-f", str(local_p), dest_obj], capture_output=True, text=True)
                    if res.returncode != 0:
                        raise RuntimeError(f"Error promoting {fname} to {v2_dest}: {res.stderr}")

        print("✔ CDN publishing completed successfully!")

    print("\n" + "=" * 60)
    print("PUBLISH INVENTORY SUMMARY")
    print("=" * 60)
    for p in sorted(generated_artifacts):
        if p.is_file():
            try:
                rel_name = p.resolve().relative_to(output_dir.resolve()).as_posix()
            except ValueError:
                rel_name = p.name
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            print(f"{rel_name:<32} {p.stat().st_size:>9} bytes  sha256:{h[:16]}...")
    print("=" * 60)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return package_and_publish(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

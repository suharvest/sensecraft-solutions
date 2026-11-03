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


def check_head_and_pin(repo_root: Path, requested_pin: str, offline: bool = False) -> str:
    """Bind HEAD to content-pin and verify ancestry."""
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
    # If origin/main is not present (offline/test checkout), fallback to HEAD
    has_origin_main = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "origin/main"],
        capture_output=True,
        text=True,
    ).returncode == 0

    if has_origin_main and not offline:
        check_ancestor = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", pin, "origin/main"],
            capture_output=True,
            text=True,
        )
        if check_ancestor.returncode != 0:
            raise ValueError(f"content-pin {pin} is not an ancestor of origin/main")
    else:
        # Fallback to verifying against HEAD
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
    """Return commit timestamp as integer unix epoch."""
    if "SOURCE_DATE_EPOCH" in os.environ:
        try:
            return int(os.environ["SOURCE_DATE_EPOCH"])
        except ValueError:
            pass
    res = subprocess.run(
        ["git", "-C", str(repo_root), "show", "-s", "--format=%ct", content_pin],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0 and res.stdout.strip():
        return int(res.stdout.strip())
    raise ValueError(f"Could not determine git commit timestamp for pin '{content_pin}' in {repo_root}")


def resolve_iso_time(repo_root: Path, content_pin: str) -> str:
    """Return deterministic ISO timestamp from git commit time."""
    timestamp = resolve_commit_time(repo_root, content_pin)
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_sequence(seq: int | None, dry_run: bool, offline: bool) -> int:
    if seq is not None:
        if seq < 0 or seq > JSON_SAFE_INTEGER_MAX:
            raise ValueError(f"sequence must be between 0 and {JSON_SAFE_INTEGER_MAX} (got {seq})")
        return seq

    if dry_run or offline:
        return 1

    raise ValueError("Missing required --sequence (must be non-negative integer <= 9007199254740991)")


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


def check_remote_sequence(
    bucket: str,
    prefix: str,
    sequence: int,
    output_dir: Path,
    ossutil_bin: str = "ossutil",
) -> None:
    """Retrieve remote manifest via ossutil cat and enforce sequence monotonicity."""
    remote_target = f"oss://{bucket}/{prefix}/v2/manifest.json"
    res = subprocess.run([ossutil_bin, "cat", remote_target], capture_output=True, text=True)
    if res.returncode != 0:
        err = res.stderr + res.stdout
        # Genuine 404 / NoSuchKey
        if "NoSuchKey" in err or "404" in err or "The specified key does not exist" in err:
            print(f"[*] Remote v2 manifest not found ({remote_target}); initial publishing at sequence {sequence}.")
            return
        # Fail closed on any network, auth, or bucket error
        raise RuntimeError(f"Failed to query remote authoritative manifest from OSS ({remote_target}):\n{err}")

    try:
        remote_data = json.loads(res.stdout)
    except Exception as e:
        raise RuntimeError(f"Failed to parse remote v2 manifest as JSON: {e}")

    remote_seq = remote_data.get("sequence", 0)

    if sequence < remote_seq:
        raise ValueError(
            f"Publishing rejected: sequence {sequence} is lower than published sequence {remote_seq} (anti-rollback)"
        )
    elif sequence == remote_seq:
        local_bytes = (output_dir / "manifest.json").read_bytes()
        local_sha = hashlib.sha256(local_bytes).hexdigest()
        remote_bytes = res.stdout.encode("utf-8")
        remote_sha = hashlib.sha256(remote_bytes).hexdigest()
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
    output_dir: Path,
    ossutil_bin: str = "ossutil",
) -> set[str]:
    """Check all release objects against oss://{bucket}/{prefix}/releases/{content_pin}/.

    Returns set of filenames that already exist identically on OSS (to skip uploading).
    Raises ValueError if an object exists with different sha256 (conflict).
    Raises RuntimeError if OSS query fails unexpectedly (fail-closed).
    """
    already_identical: set[str] = set()
    files_to_check = sorted(p for p in output_dir.iterdir() if p.is_file())

    for local_p in files_to_check:
        fname = local_p.name
        oss_target = f"oss://{bucket}/{prefix}/releases/{content_pin}/{fname}"
        res = subprocess.run([ossutil_bin, "cat", oss_target], capture_output=True)
        if res.returncode == 0:
            remote_bytes = res.stdout
            local_bytes = local_p.read_bytes()
            remote_sha = hashlib.sha256(remote_bytes).hexdigest()
            local_sha = hashlib.sha256(local_bytes).hexdigest()
            if remote_sha == local_sha:
                already_identical.add(fname)
            else:
                raise ValueError(
                    f"Immutable release conflict: object {oss_target} already exists on OSS with differing sha256 "
                    f"({remote_sha} remote vs {local_sha} local). Overwriting immutable release objects is forbidden!"
                )
        else:
            err = res.stderr.decode("utf-8", errors="replace") + res.stdout.decode("utf-8", errors="replace")
            if "NoSuchKey" in err or "404" in err or "The specified key does not exist" in err:
                # Missing object on OSS: allowed (breakpoint resume)
                pass
            else:
                raise RuntimeError(f"Failed to check object status on OSS ({oss_target}):\n{err}")

    return already_identical


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


def verify_solution_packages(solutions_dir: Path, offline: bool = False) -> None:
    """Verify deb packages referenced by solutions targeting reCamera/SG2002/riscv64."""
    if not solutions_dir.is_dir():
        return

    cache_dir = Path(os.environ.get("SC_DEB_CACHE_DIR", Path.home() / ".cache" / "sensecraft_debs"))

    for sol_dir in sorted(solutions_dir.iterdir()):
        if sol_dir.is_symlink() or not sol_dir.is_dir():
            continue
        sol_yaml_file = sol_dir / "solution.yaml"
        if not sol_yaml_file.is_file():
            continue
        sol_meta = simple_yaml_load(sol_yaml_file)

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


def package_and_publish(args: argparse.Namespace) -> int:
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
    content_pin = check_head_and_pin(repo_root, args.content_pin, offline=args.offline)
    sequence = resolve_sequence(args.sequence, args.dry_run, args.offline)

    base_url = args.base_url.strip().rstrip("/")
    if not base_url:
        base_url = f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{content_pin}"

    # Get git tracked files under solutions_dir at content_pin
    rel_solutions_dir = solutions_dir.relative_to(repo_root).as_posix()
    tracked_files = get_git_tracked_files(repo_root, content_pin, rel_solutions_dir)

    # Check for Git LFS pointers among tracked files
    check_lfs_pointers(repo_root, tracked_files)

    # Verify deb packages
    verify_solution_packages(solutions_dir, offline=args.offline)

    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.zip", "manifest.json*", "bundled_hashes.json*", "solutions_index.json*"):
        for f in output_dir.glob(pattern):
            if f.is_file():
                f.unlink()

    print(f"[*] Packaging solutions from: {solutions_dir}")
    print(f"[*] Target content pin:       {content_pin}")
    print(f"[*] Target sequence:          {sequence}")
    print(f"[*] Output directory:         {output_dir}")
    print(f"[*] Base URL:                 {base_url}")
    print(f"[*] Mode:                     {'offline' if args.offline else ('dry-run' if args.dry_run else 'publish')}")

    commit_time = resolve_commit_time(repo_root, content_pin)
    now_iso = resolve_iso_time(repo_root, content_pin)

    # Discover valid solution folders
    solution_entries: list[tuple[str, Path, dict[str, Any]]] = []
    for child in sorted(solutions_dir.iterdir()):
        if child.is_symlink() or not child.is_dir():
            continue
        yaml_path = child / "solution.yaml"
        if yaml_path.is_file():
            meta = simple_yaml_load(yaml_path)
            sol_id = meta.get("id") or child.name
            if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", sol_id):
                raise ValueError(f"Invalid solution id '{sol_id}': must match ^[a-zA-Z0-9_-]+$")
            solution_entries.append((sol_id, child, meta))

    if not solution_entries:
        print(f"Error: no valid solutions containing solution.yaml found in {solutions_dir}", file=sys.stderr)
        return 1

    manifest_solutions: dict[str, Any] = {}
    bundled_hashes: dict[str, str] = {}
    index_solutions: list[dict[str, Any]] = []

    for sol_id, sol_dir, meta in solution_entries:
        zip_path = (output_dir / f"{sol_id}.zip").resolve()
        if zip_path.parent != output_dir or not zip_path.is_relative_to(output_dir):
            raise ValueError(f"Path traversal detected: {zip_path} escapes output directory {output_dir}")

        digest, size = create_solution_zip(repo_root, sol_dir, tracked_files, zip_path)
        sha_str = f"sha256:{digest}"
        bundled_hashes[sol_id] = sha_str

        manifest_entry = {
            "hash": sha_str,
            "size": size,
            "updated_at": now_iso,
            "min_app_version": args.min_app_version,
            "min_engine_version": args.min_engine_version,
        }
        manifest_solutions[sol_id] = manifest_entry

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

        cover_image = intro.get("cover_image") or meta.get("cover_image") or ""
        category = intro.get("category") or meta.get("category") or "general"
        tags_val = intro.get("tags") or meta.get("tags") or []
        tags = tags_val if isinstance(tags_val, list) else [tags_val]

        idx_entry = {
            "id": sol_id,
            "name": meta.get("name") or sol_id,
            "name_zh": name_zh,
            "summary": summary,
            "summary_zh": summary_zh,
            "cover_image": cover_image,
            "category": category,
            "tags": tags,
            "solution_type": meta.get("solution_type") or "solution",
            "difficulty": meta.get("difficulty") or "intermediate",
            "estimated_time": meta.get("estimated_time") or "30min",
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

    # Generate solutions_index.json
    solutions_index_path = output_dir / "solutions_index.json"
    index_payload = {
        "version": 1,
        "generated_at": now_iso,
        "solutions": index_solutions,
    }
    solutions_index_path.write_text(json.dumps(index_payload, indent=2) + "\n", encoding="utf-8")

    # Generate manifest.json (v2 format with sequence)
    manifest_path = output_dir / "manifest.json"
    manifest_payload = {
        "version": 2,
        "sequence": sequence,
        "content_pin": content_pin,
        "generated_at": now_iso,
        "base_url": base_url,
        "deprecated": [],
        "solutions": manifest_solutions,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    print("[*] Generated core manifest files successfully.")

    # Signing phase
    targets_to_sign = [
        (manifest_path, 2),
        (bundled_hashes_path, 1),
        (solutions_index_path, 1),
    ]

    if args.sign or args.dry_run:
        sec_file = getattr(args, "minisign_key_file", None)
        password = os.environ.get("CONTENT_SIGNING_PRIVATE_KEY_PASSWORD")
        temp_key_dir: str | None = None

        has_env_key = "CONTENT_SIGNING_PRIVATE_KEY" in os.environ
        has_file_key = sec_file and Path(sec_file).is_file()

        if args.dry_run or ((args.offline or not (has_env_key or has_file_key)) and not has_file_key and not has_env_key):
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
            mode_name = "Dry-run" if args.dry_run else "Offline"
            print(f"[*] {mode_name} mode: generated ephemeral test keypair (pubkey: {pubkey})")
        else:
            pubkey = getattr(args, "minisign_pubkey", None) or os.environ.get("CONTENT_MINISIGN_PUBLIC_KEY")
            if not pubkey:
                print(
                    "Error: --minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY environment variable is required when signing",
                    file=sys.stderr,
                )
                return 1

            if not sec_file and has_env_key:
                temp_key_dir = tempfile.mkdtemp(prefix="minisign-env-")
                sec_file = Path(temp_key_dir) / "content.key"
                sec_file.write_text(os.environ["CONTENT_SIGNING_PRIVATE_KEY"], encoding="utf-8")
                sec_file.chmod(0o600)

        if not sec_file or not Path(sec_file).is_file():
            print("Error: --sign specified but no secret key provided", file=sys.stderr)
            return 1

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
                print(f"  ✔ Signed & verified: {sig.name}")
        finally:
            if temp_key_dir and os.path.exists(temp_key_dir):
                shutil.rmtree(temp_key_dir, ignore_errors=True)

    # OSS Preflight and Upload Phase
    if not args.offline and (args.upload or args.dry_run):
        bucket = args.oss_bucket.strip()
        prefix = args.oss_prefix.strip().strip("/")

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
        already_identical = check_immutable_release_conflicts(bucket, prefix, content_pin, output_dir)

        if args.dry_run:
            print("[*] Dry-run preflight complete. Zero changes written to OSS.")
            return 0

        # Upload phase
        print("[*] Uploading immutable release objects to OSS...")
        files_to_upload = sorted(p for p in output_dir.iterdir() if p.is_file())
        for local_p in files_to_upload:
            fname = local_p.name
            if fname in already_identical:
                print(f"  [skip] {fname} (already identical on OSS)")
                continue
            dest_obj = f"{pin_dest}{fname}"
            if dest_obj == frozen_root_manifest:
                raise ValueError("Security Error: direct overwrite of frozen v1 root manifest is forbidden!")
            print(f"  [upload] {fname} -> {dest_obj}")
            res = subprocess.run(["ossutil", "cp", "-f", str(local_p), dest_obj], capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Error uploading {fname} to {dest_obj}: {res.stderr}")

        # Promotion order to v2/: auxiliary files first, entry manifest last
        print("[*] Promoting to mutable v2 entry...")
        aux_files = [
            "bundled_hashes.json",
            "bundled_hashes.json.minisig",
            "solutions_index.json",
            "solutions_index.json.minisig",
        ]
        for fname in aux_files:
            local_p = output_dir / fname
            if local_p.is_file():
                dest_obj = f"{v2_dest}{fname}"
                print(f"  [v2 aux] {fname} -> {dest_obj}")
                res = subprocess.run(["ossutil", "cp", "-f", str(local_p), dest_obj], capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Error promoting {fname} to {v2_dest}: {res.stderr}")

        entry_files = [
            "manifest.json",
            "manifest.json.minisig",
        ]
        for fname in entry_files:
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
    for p in sorted(output_dir.iterdir()):
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            print(f"{p.name:<32} {p.stat().st_size:>9} bytes  sha256:{h[:16]}...")
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

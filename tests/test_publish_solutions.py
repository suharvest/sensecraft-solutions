"""Unit tests for scripts/publish_solutions.py

Covers all 14 safety and recovery contracts from the Content Publish Migration Specification:
- Low sequence rejected
- Fail-closed on OSS read failure
- Identical sequence + byte-identical manifest succeeds idempotently
- Identical sequence + altered content rejected
- Immutable release object conflict rejected
- Mismatched HEAD vs content_pin rejected
- External solutions_dir rejected
- Dirty working tree rejected
- Git LFS pointer rejected
- Ignored-file injection isolation
- Deterministic signature reproducibility
- Partial promotion / breakpoint missing object recovery
- Two fresh checkouts produce byte-identical packages and manifests
- Offline mode produces valid local minisign signatures
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import publish_solutions


def init_test_git_repo(repo_dir: Path) -> str:
    """Initialize a git repository with sample solutions and return HEAD commit hash."""
    subprocess.run(["git", "init", "-b", "main", str(repo_dir)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "commit.gpgsign", "false"], check=True)

    # .gitignore
    (repo_dir / ".gitignore").write_text("*.zip\n*.tmp\n", encoding="utf-8")

    # solutions/sol_alpha
    sol_a = repo_dir / "solutions" / "sol_alpha"
    sol_a.mkdir(parents=True)
    (sol_a / "solution.yaml").write_text(
        "id: sol_alpha\nname: Solution Alpha\nversion: 1.0.0\n",
        encoding="utf-8",
    )
    (sol_a / "guide.md").write_text("# Guide Alpha\n", encoding="utf-8")

    # solutions/sol_beta
    sol_b = repo_dir / "solutions" / "sol_beta"
    sol_b.mkdir(parents=True)
    (sol_b / "solution.yaml").write_text(
        "id: sol_beta\nname: Solution Beta\nversion: 1.0.0\n",
        encoding="utf-8",
    )
    (sol_b / "guide.md").write_text("# Guide Beta\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "Initial commit"], check=True, capture_output=True)

    head = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().lower()
    return head


def generate_test_minisign_keypair(target_dir: Path) -> tuple[Path, str]:
    sec_key = target_dir / "test.key"
    pub_key = target_dir / "test.pub"
    subprocess.run(
        ["minisign", "-G", "-f", "-p", str(pub_key), "-s", str(sec_key), "-W"],
        check=True,
        capture_output=True,
    )
    pubkey_str = pub_key.read_text(encoding="utf-8").strip().splitlines()[1]
    return sec_key, pubkey_str


def test_mismatched_head_vs_content_pin_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    bogus_pin = "0123456789abcdef0123456789abcdef01234567"

    with pytest.raises(ValueError, match="Mismatched HEAD vs content_pin"):
        publish_solutions.check_head_and_pin(repo, bogus_pin, offline=True)


def test_external_solutions_dir_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)
    external_dir = tmp_path / "external_solutions"
    external_dir.mkdir()

    with pytest.raises(ValueError, match="must be inside repository checkout"):
        publish_solutions.check_repo_boundaries(external_dir)

    # Also test external dir from another repo
    other_repo = tmp_path / "other_repo"
    init_test_git_repo(other_repo)
    with pytest.raises(ValueError, match="must be inside repository checkout"):
        publish_solutions.check_repo_boundaries(other_repo / "solutions", repo_root=repo)


def test_dirty_working_tree_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    # Modify a tracked file without committing
    guide = repo / "solutions" / "sol_alpha" / "guide.md"
    guide.write_text("# Altered Guide\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Working tree is dirty"):
        publish_solutions.check_clean_tree(repo)


def test_git_lfs_pointer_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    # Write a simulated Git LFS pointer file and track it
    lfs_file = repo / "solutions" / "sol_alpha" / "model.bin"
    lfs_file.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
        b"oid sha256:4d7a282a16da4d0134438c8cce218f7b49430e10161fb926a1455a80a1adc70e\n"
        b"size 12345\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add LFS pointer"], check=True, capture_output=True)

    tracked = publish_solutions.get_git_tracked_files(
        repo, "HEAD", "solutions/sol_alpha"
    )
    with pytest.raises(ValueError, match="Git LFS pointer detected"):
        publish_solutions.check_lfs_pointers(repo, tracked)


def test_ignored_file_injection_isolation(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_clean = tmp_path / "out_clean"

    # 1. Clean packaging
    rc1 = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_clean),
        "--content-pin", head,
        "--sequence", "1",
        "--offline",
    ])
    assert rc1 == 0
    clean_zip_bytes = (out_clean / "sol_alpha.zip").read_bytes()
    clean_zip_sha = hashlib.sha256(clean_zip_bytes).hexdigest()

    # 2. Inject ignored files (*.zip, *.tmp) into the solution directory
    ignored_zip = repo / "solutions" / "sol_alpha" / "temp_injected.zip"
    ignored_zip.write_bytes(b"MALICIOUS_INJECTED_DATA")
    ignored_tmp = repo / "solutions" / "sol_alpha" / "scratch.tmp"
    ignored_tmp.write_bytes(b"TEMPORARY_SCRATCH_DATA")

    # Working tree should still be clean according to git status --porcelain because files are ignored
    publish_solutions.check_clean_tree(repo)

    out_injected = tmp_path / "out_injected"
    rc2 = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_injected),
        "--content-pin", head,
        "--sequence", "1",
        "--offline",
    ])
    assert rc2 == 0
    injected_zip_bytes = (out_injected / "sol_alpha.zip").read_bytes()
    injected_zip_sha = hashlib.sha256(injected_zip_bytes).hexdigest()

    # The packaged zip must be 100% byte-identical; ignored files must NOT be included
    assert clean_zip_sha == injected_zip_sha


def test_deterministic_signature_reproducibility(tmp_path: Path):
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    test_file = tmp_path / "manifest.json"
    test_file.write_text('{"version": 2, "sequence": 1}\n', encoding="utf-8")

    commit_time = 1730000000
    version = 2

    # Sign first time
    sig1_path = publish_solutions.run_minisign_sign(
        test_file, sec_key, commit_time=commit_time, version=version
    )
    sig1_bytes = sig1_path.read_bytes()

    # Verify first signature
    publish_solutions.run_minisign_verify(test_file, sig1_path, pubkey)

    # Re-sign with exact same parameters
    sig1_path.unlink()
    sig2_path = publish_solutions.run_minisign_sign(
        test_file, sec_key, commit_time=commit_time, version=version
    )
    sig2_bytes = sig2_path.read_bytes()

    # Signatures must be byte-for-byte identical
    assert sig1_bytes == sig2_bytes
    publish_solutions.run_minisign_verify(test_file, sig2_path, pubkey)


def test_offline_mode_produces_valid_local_minisign_signatures(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir = tmp_path / "cdn_out"

    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--offline",
    ])
    assert rc == 0

    manifest_sig = out_dir / "manifest.json.minisig"
    bundled_sig = out_dir / "bundled_hashes.json.minisig"
    index_sig = out_dir / "solutions_index.json.minisig"

    assert manifest_sig.is_file() and manifest_sig.stat().st_size > 0
    assert bundled_sig.is_file() and bundled_sig.stat().st_size > 0
    assert index_sig.is_file() and index_sig.stat().st_size > 0

    # Ensure trusted comment contains expected timestamp and file fields
    sig_text = manifest_sig.read_text(encoding="utf-8")
    assert "trusted comment: timestamp:" in sig_text
    assert "file:manifest.json" in sig_text
    assert "version:2" in sig_text


def test_two_fresh_checkouts_produce_byte_identical_packages_and_manifests(tmp_path: Path):
    origin = tmp_path / "origin"
    head = init_test_git_repo(origin)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)

    checkout_a = tmp_path / "checkout_a"
    checkout_b = tmp_path / "checkout_b"
    subprocess.run(["git", "clone", str(origin), str(checkout_a)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(origin), str(checkout_b)], check=True, capture_output=True)

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"

    args_a = [
        "--solutions-dir", str(checkout_a / "solutions"),
        "--output-dir", str(out_a),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--minisign-key-file", str(sec_key),
        "--minisign-pubkey", pubkey,
        "--offline",
    ]
    args_b = [
        "--solutions-dir", str(checkout_b / "solutions"),
        "--output-dir", str(out_b),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--minisign-key-file", str(sec_key),
        "--minisign-pubkey", pubkey,
        "--offline",
    ]

    assert publish_solutions.main(args_a) == 0
    assert publish_solutions.main(args_b) == 0

    files_a = sorted(p.name for p in out_a.iterdir() if p.is_file())
    files_b = sorted(p.name for p in out_b.iterdir() if p.is_file())
    assert files_a == files_b

    for fname in files_a:
        bytes_a = (out_a / fname).read_bytes()
        bytes_b = (out_b / fname).read_bytes()
        sha_a = hashlib.sha256(bytes_a).hexdigest()
        sha_b = hashlib.sha256(bytes_b).hexdigest()
        assert sha_a == sha_b, f"File {fname} differs between two fresh checkouts"


def test_low_sequence_rejected(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "manifest.json").write_text('{"sequence": 5}', encoding="utf-8")

    remote_manifest_json = json.dumps({"sequence": 10})
    mock_res = mock.Mock(returncode=0, stdout=remote_manifest_json, stderr="")

    with mock.patch("subprocess.run", return_value=mock_res):
        with pytest.raises(ValueError, match="is lower than published sequence 10"):
            publish_solutions.check_remote_sequence("bucket", "prefix", 5, out_dir)


def test_fail_closed_on_oss_read_failure(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "manifest.json").write_text('{"sequence": 10}', encoding="utf-8")

    mock_res = mock.Mock(returncode=1, stdout="", stderr="AccessDenied: The bucket requires STS token")

    with mock.patch("subprocess.run", return_value=mock_res):
        with pytest.raises(RuntimeError, match="Failed to query remote authoritative manifest from OSS"):
            publish_solutions.check_remote_sequence("bucket", "prefix", 10, out_dir)


def test_identical_sequence_with_byte_identical_manifest_succeeds_idempotently(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    manifest_bytes = b'{\n  "version": 2,\n  "sequence": 10\n}\n'
    (out_dir / "manifest.json").write_bytes(manifest_bytes)

    mock_res = mock.Mock(returncode=0, stdout=manifest_bytes.decode("utf-8"), stderr="")

    with mock.patch("subprocess.run", return_value=mock_res):
        # Should succeed without raising
        publish_solutions.check_remote_sequence("bucket", "prefix", 10, out_dir)


def test_identical_sequence_with_altered_content_rejected(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "manifest.json").write_text('{"sequence": 10, "content_pin": "pin_local"}', encoding="utf-8")

    remote_content = '{"sequence": 10, "content_pin": "pin_remote"}'
    mock_res = mock.Mock(returncode=0, stdout=remote_content, stderr="")

    with mock.patch("subprocess.run", return_value=mock_res):
        with pytest.raises(ValueError, match="already exists on OSS with different manifest SHA-256"):
            publish_solutions.check_remote_sequence("bucket", "prefix", 10, out_dir)


def test_immutable_release_conflict_rejected(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    local_zip = out_dir / "sol_alpha.zip"
    local_zip.write_bytes(b"LOCAL_NEW_ZIP_CONTENT")

    # Remote returns different content for sol_alpha.zip
    mock_res = mock.Mock(returncode=0, stdout=b"REMOTE_OLD_DIFFERING_CONTENT", stderr=b"")

    with mock.patch("subprocess.run", return_value=mock_res):
        with pytest.raises(ValueError, match="Immutable release conflict"):
            publish_solutions.check_immutable_release_conflicts(
                "bucket", "prefix", "pin12345", out_dir
            )


def test_partial_promotion_breakpoint_missing_object_recovery(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "sol_alpha.zip").write_bytes(b"CONTENT_ALPHA")
    (out_dir / "sol_beta.zip").write_bytes(b"CONTENT_BETA")

    def mock_subprocess(cmd, **kwargs):
        target = cmd[2]
        if "sol_alpha.zip" in target:
            # sol_alpha exists identically on OSS
            return mock.Mock(returncode=0, stdout=b"CONTENT_ALPHA", stderr=b"")
        else:
            # sol_beta is missing (NoSuchKey)
            return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: object does not exist")

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        already_identical = publish_solutions.check_immutable_release_conflicts(
            "bucket", "prefix", "pin12345", out_dir
        )
        assert already_identical == {"sol_alpha.zip"}


def test_ephemeral_key_rejected_in_upload_mode_when_private_key_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    subprocess.run(["git", "-C", str(repo), "branch", "origin/main"], check=True, capture_output=True)
    out_dir = tmp_path / "cdn_out"

    with mock.patch.dict(os.environ, {}, clear=True):
        # 1. --upload with missing private key must fail closed (raise ValueError)
        with pytest.raises(ValueError, match="In upload mode, CONTENT_SIGNING_PRIVATE_KEY"):
            publish_solutions.package_and_publish(
                publish_solutions.parse_args([
                    "--solutions-dir", str(repo / "solutions"),
                    "--output-dir", str(out_dir),
                    "--content-pin", head,
                    "--sequence", "1",
                    "--sign",
                    "--upload",
                ])
            )

        # 2. --upload with --generate-test-keys must also be strictly rejected
        with pytest.raises(ValueError, match="--generate-test-keys is strictly forbidden in production/upload mode"):
            publish_solutions.package_and_publish(
                publish_solutions.parse_args([
                    "--solutions-dir", str(repo / "solutions"),
                    "--output-dir", str(out_dir),
                    "--content-pin", head,
                    "--sequence", "1",
                    "--sign",
                    "--upload",
                    "--generate-test-keys",
                ])
            )


def test_solution_discovery_ignores_untracked_ignored_folders(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)

    # Add an untracked directory with a solution.yaml
    untracked_sol = repo / "solutions" / "sol_untracked"
    untracked_sol.mkdir()
    (untracked_sol / "solution.yaml").write_text("id: sol_untracked\nname: Untracked\n", encoding="utf-8")

    # Add an ignored directory with a solution.yaml
    with open(repo / ".gitignore", "a", encoding="utf-8") as f:
        f.write("solutions/sol_ignored/\n")
    ignored_sol = repo / "solutions" / "sol_ignored"
    ignored_sol.mkdir()
    (ignored_sol / "solution.yaml").write_text("id: sol_ignored\nname: Ignored\n", encoding="utf-8")

    tracked_files = publish_solutions.get_git_tracked_files(repo, head, "solutions")
    entries = publish_solutions.discover_solutions_from_git(repo, repo / "solutions", head, tracked_files)

    discovered_ids = {entry[0] for entry in entries}
    assert discovered_ids == {"sol_alpha", "sol_beta"}
    assert "sol_untracked" not in discovered_ids
    assert "sol_ignored" not in discovered_ids


def test_solution_discovery_rejects_duplicate_solution_ids(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    # Add sol_gamma that duplicates sol_alpha id
    sol_gamma = repo / "solutions" / "sol_gamma"
    sol_gamma.mkdir()
    (sol_gamma / "solution.yaml").write_text("id: sol_alpha\nname: Duplicate Alpha\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add duplicate id"], check=True, capture_output=True)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()

    tracked_files = publish_solutions.get_git_tracked_files(repo, head, "solutions")
    with pytest.raises(ValueError, match="Duplicate solution id detected"):
        publish_solutions.discover_solutions_from_git(repo, repo / "solutions", head, tracked_files)


def test_upload_inventory_restricts_upload_to_explicitly_generated_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    subprocess.run(["git", "-C", str(repo), "branch", "origin/main"], check=True, capture_output=True)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    out_dir = tmp_path / "cdn_out"

    # Put a rogue file in output directory
    out_dir.mkdir(parents=True)
    rogue_file = out_dir / "rogue_unrelated_file.txt"
    rogue_file.write_text("should not be checked or uploaded", encoding="utf-8")

    checked_targets: list[str] = []
    uploaded_sources: list[str] = []
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                checked_targets.append(target)
                return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
            elif "ossutil cp" in cmd_str:
                src = cmd_list[-2]
                uploaded_sources.append(src)
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc = publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--sign",
                "--upload",
                "--minisign-key-file", str(sec_key),
                "--minisign-pubkey", pubkey,
            ])
        )
        assert rc == 0

    # Ensure rogue_unrelated_file was NEVER checked on OSS or uploaded
    for target in checked_targets:
        assert "rogue_unrelated_file" not in target
    for src in uploaded_sources:
        assert "rogue_unrelated_file" not in src


def test_non_nosuchkey_oss_errors_fail_closed(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "manifest.json").write_text('{"sequence": 1}', encoding="utf-8")

    for err_msg in [
        "HTTP 403 Forbidden: Access denied",
        "404 Not Found (reverse proxy gateway error)",
        "Connection reset by peer",
        "Request timeout",
    ]:
        mock_res = mock.Mock(returncode=1, stdout=b"", stderr=err_msg.encode("utf-8"))
        with mock.patch("subprocess.run", return_value=mock_res):
            with pytest.raises(RuntimeError, match="Failed to query remote authoritative manifest from OSS"):
                publish_solutions.check_remote_sequence("bucket", "prefix", 1, out_dir)

            with pytest.raises(RuntimeError, match="Failed to check object status on OSS"):
                publish_solutions.oss_object_exists("oss://bucket/prefix/file.zip")


def test_promotion_interruption_simulation_and_resume(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    subprocess.run(["git", "-C", str(repo), "branch", "origin/main"], check=True, capture_output=True)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    out_dir = tmp_path / "cdn_out"

    promoted_v2_files: list[str] = []
    should_interrupt = True
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                if "v2/manifest.json" in target:
                    if promoted_v2_files and "manifest.json" in promoted_v2_files:
                        return mock.Mock(returncode=0, stdout=(out_dir / "manifest.json").read_bytes(), stderr=b"")
                    return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
                return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
            elif "ossutil cp" in cmd_str:
                dest = cmd_list[4] if len(cmd_list) > 4 else cmd_list[-1]
                if "/v2/" in dest:
                    filename = dest.split("/v2/")[-1]
                    if should_interrupt and filename == "manifest.json":
                        raise RuntimeError("Simulated network drop before manifest promotion")
                    promoted_v2_files.append(filename)
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    args = [
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--upload",
        "--minisign-key-file", str(sec_key),
        "--minisign-pubkey", pubkey,
    ]

    # Run 1: Fails during promotion right before manifest.json completes
    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        with pytest.raises(RuntimeError, match="Simulated network drop"):
            publish_solutions.package_and_publish(publish_solutions.parse_args(args))

    # Verify auxiliary files were promoted before manifest.json
    assert "bundled_hashes.json" in promoted_v2_files
    assert "solutions_index.json" in promoted_v2_files
    assert "manifest.json" not in promoted_v2_files

    # Run 2: Resume with identical sequence completes cleanly
    should_interrupt = False
    promoted_v2_files.clear()
    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc = publish_solutions.package_and_publish(publish_solutions.parse_args(args))
        assert rc == 0
        idx_aux = max(
            promoted_v2_files.index("bundled_hashes.json"),
            promoted_v2_files.index("solutions_index.json"),
        )
        idx_entry = promoted_v2_files.index("manifest.json")
        assert idx_aux < idx_entry


def test_authoritative_ancestry_failure_fails_closed_when_not_offline(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)

    # 1. In online mode (offline=False, allow_local_branch=False), missing origin/main must fail closed
    with pytest.raises(ValueError, match="Authoritative ancestry check failed: cannot resolve origin/main"):
        publish_solutions.check_head_and_pin(repo, head, offline=False, allow_local_branch=False)

    # 2. If origin/main exists but head is NOT an ancestor, must fail closed
    # Create origin/main pointing to an earlier orphan commit
    subprocess.run(["git", "-C", str(repo), "checkout", "--orphan", "other_branch"], check=True, capture_output=True)
    (repo / "dummy.txt").write_text("orphan", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "dummy.txt"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Orphan commit"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-f", "origin/main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "main"], check=True, capture_output=True)

    with pytest.raises(ValueError, match="is not an ancestor of origin/main"):
        publish_solutions.check_head_and_pin(repo, head, offline=False, allow_local_branch=False)

    # 3. With allow_local_branch=True, it succeeds by verifying against HEAD
    pin = publish_solutions.check_head_and_pin(repo, head, offline=False, allow_local_branch=True)
    assert pin == head

    # 4. With offline=True, it succeeds by verifying against HEAD
    pin_offline = publish_solutions.check_head_and_pin(repo, head, offline=True, allow_local_branch=False)
    assert pin_offline == head


def test_allow_local_branch_rejected_when_combined_with_upload(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir = tmp_path / "cdn_out"

    # In package_and_publish
    args = publish_solutions.parse_args([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--upload",
        "--allow-local-branch",
    ])
    with pytest.raises(ValueError, match="--allow-local-branch is forbidden in --upload mode"):
        publish_solutions.package_and_publish(args)

    # In check_head_and_pin directly with upload=True
    with pytest.raises(ValueError, match="--allow-local-branch is forbidden in --upload mode"):
        publish_solutions.check_head_and_pin(
            repo, head, offline=False, allow_local_branch=True, upload=True
        )

    # Also verify that upload mode strictly requires ancestry check from origin/main
    with pytest.raises(ValueError, match="Authoritative ancestry check failed: cannot resolve origin/main"):
        publish_solutions.check_head_and_pin(
            repo, head, offline=False, allow_local_branch=False, upload=True
        )


def test_solutions_index_bound_in_manifest(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir = tmp_path / "cdn_out"

    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--offline",
    ])
    assert rc == 0

    manifest_file = out_dir / "manifest.json"
    index_file = out_dir / "solutions_index.json"
    hashes_file = out_dir / "bundled_hashes.json"

    assert manifest_file.is_file()
    assert index_file.is_file()
    assert hashes_file.is_file()

    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    index_bytes = index_file.read_bytes()
    expected_index_sha = hashlib.sha256(index_bytes).hexdigest()
    expected_index_size = len(index_bytes)

    bundled_bytes = hashes_file.read_bytes()
    expected_bundled_sha = hashlib.sha256(bundled_bytes).hexdigest()
    expected_bundled_size = len(bundled_bytes)

    # Verify solutions_index is bound directly in manifest
    assert "solutions_index" in manifest_data
    assert manifest_data["solutions_index"]["sha256"] == expected_index_sha
    assert manifest_data["solutions_index"]["size"] == expected_index_size

    # Verify bundled_hashes is bound directly in manifest
    assert "bundled_hashes" in manifest_data
    assert manifest_data["bundled_hashes"]["sha256"] == expected_bundled_sha
    assert manifest_data["bundled_hashes"]["size"] == expected_bundled_size

    # Verify auxiliary_files binds both solutions_index.json and bundled_hashes.json
    assert "auxiliary_files" in manifest_data
    assert "solutions_index.json" in manifest_data["auxiliary_files"]
    assert manifest_data["auxiliary_files"]["solutions_index.json"]["sha256"] == expected_index_sha
    assert manifest_data["auxiliary_files"]["solutions_index.json"]["size"] == expected_index_size
    assert "bundled_hashes.json" in manifest_data["auxiliary_files"]
    assert manifest_data["auxiliary_files"]["bundled_hashes.json"]["sha256"] == expected_bundled_sha
    assert manifest_data["auxiliary_files"]["bundled_hashes.json"]["size"] == expected_bundled_size


def test_artifact_inventory_emitted_before_upload(tmp_path: Path, capsys: pytest.CaptureFixture):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    subprocess.run(["git", "-C", str(repo), "branch", "origin/main"], check=True, capture_output=True)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    out_dir = tmp_path / "cdn_out"

    events: list[str] = []
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                events.append("ossutil cat")
                return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
            elif "ossutil cp" in cmd_str:
                events.append(f"ossutil cp {cmd_list[-1]}")
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc = publish_solutions.main([
            "--solutions-dir", str(repo / "solutions"),
            "--output-dir", str(out_dir),
            "--content-pin", head,
            "--sequence", "1",
            "--sign",
            "--upload",
            "--minisign-key-file", str(sec_key),
            "--minisign-pubkey", pubkey,
        ])
        assert rc == 0

    captured = capsys.readouterr()
    stdout = captured.out

    # Verify complete inventory is present in stdout
    assert "COMPLETE ARTIFACT INVENTORY" in stdout
    assert "Total count: 14" in stdout
    assert "sol_alpha.zip" in stdout
    assert "sol_beta.zip" in stdout
    assert "manifest.json" in stdout
    assert "solutions_index.json" in stdout
    assert "bundled_hashes.json" in stdout

    # Verify un-truncated 64-hex sha256 is emitted for artifacts
    sol_alpha_sha = hashlib.sha256((out_dir / "sol_alpha.zip").read_bytes()).hexdigest()
    assert sol_alpha_sha in stdout

    # Verify immutable release destination path on OSS is printed
    assert f"oss://sensecraft-statics/solution-app/solutions/releases/{head}/sol_alpha.zip" in stdout
    assert f"oss://sensecraft-statics/solution-app/solutions/releases/{head}/manifest.json" in stdout

    # Verify mutable v2 destination paths on OSS are printed
    assert "oss://sensecraft-statics/solution-app/solutions/v2/manifest.json" in stdout
    assert "oss://sensecraft-statics/solution-app/solutions/v2/solutions_index.json" in stdout
    assert "oss://sensecraft-statics/solution-app/solutions/v2/bundled_hashes.json" in stdout

    # Verify inventory was printed strictly BEFORE upload began
    idx_inventory = stdout.find("COMPLETE ARTIFACT INVENTORY")
    idx_upload_start = stdout.find("Uploading immutable release objects to OSS...")
    assert idx_inventory != -1
    assert idx_upload_start != -1
    assert idx_inventory < idx_upload_start

    # Verify ossutil cp was executed
    assert any("ossutil cp" in ev for ev in events)


def test_inventory_emitted_in_offline_and_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir_offline = tmp_path / "cdn_offline"
    out_dir_dry_run = tmp_path / "cdn_dry_run"

    # 1. Offline mode
    rc_offline = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir_offline),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--offline",
    ])
    assert rc_offline == 0
    stdout_offline = capsys.readouterr().out
    assert "COMPLETE ARTIFACT INVENTORY" in stdout_offline
    assert "Total count: 14" in stdout_offline

    # 2. Dry-run mode
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc_dry_run = publish_solutions.main([
            "--solutions-dir", str(repo / "solutions"),
            "--output-dir", str(out_dir_dry_run),
            "--content-pin", head,
            "--sequence", "1",
            "--sign",
            "--generate-test-keys",
            "--dry-run",
            "--allow-local-branch",
        ])
        assert rc_dry_run == 0

    stdout_dry = capsys.readouterr().out
    assert "COMPLETE ARTIFACT INVENTORY" in stdout_dry
    assert "Total count: 14" in stdout_dry
    assert "Dry-run preflight complete. Zero changes written to OSS." in stdout_dry


def test_immutable_release_upload_does_not_use_force(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    subprocess.run(["git", "-C", str(repo), "branch", "origin/main"], check=True, capture_output=True)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    out_dir = tmp_path / "cdn_out"

    ossutil_calls: list[list[str]] = []
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            if cmd_list[1] in ("cp", "api"):
                ossutil_calls.append(cmd_list)
                return mock.Mock(returncode=0, stdout="", stderr="")
            elif cmd_list[1] == "cat":
                return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc = publish_solutions.main([
            "--solutions-dir", str(repo / "solutions"),
            "--output-dir", str(out_dir),
            "--content-pin", head,
            "--sequence", "1",
            "--sign",
            "--upload",
            "--minisign-key-file", str(sec_key),
            "--minisign-pubkey", pubkey,
        ])
        assert rc == 0

    # Separate immutable releases/<pin>/ uploads from mutable v2/ promotions
    immutable_calls = [c for c in ossutil_calls if "put-object" in c]
    v2_calls = [c for c in ossutil_calls if "cp" in c and "/v2/" in " ".join(c)]

    assert len(immutable_calls) > 0
    assert len(v2_calls) > 0

    # Immutable releases upload must use ossutil api put-object with --forbid-overwrite true
    for call in immutable_calls:
        assert "-f" not in call, f"Forbidden -f flag found in immutable release upload: {call}"
        assert "put-object" in call, f"Expected put-object in immutable upload: {call}"
        assert "--bucket" in call
        assert "--key" in call
        assert "--body" in call
        call_str = " ".join(call)
        assert "--forbid-overwrite true" in call_str or ("--forbid-overwrite" in call and "true" in call), f"Missing forbid-overwrite in immutable upload: {call}"
        key_idx = call.index("--key")
        assert f"solution-app/solutions/releases/{head}/" in call[key_idx + 1]

    # Mutable v2 promotion may contain -f and must NOT forbid overwrite
    for call in v2_calls:
        assert "-f" in call, f"Expected -f flag in v2 promotion: {call}"
        assert "--forbid-overwrite" not in call


def test_forbidden_or_mismatched_base_url_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    expected_url = f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{head}"

    # 1. Matching base URL succeeds
    validated = publish_solutions.validate_base_url(expected_url, head)
    assert validated == expected_url

    # 2. Matching base URL with trailing slash succeeds and normalizes
    validated_slash = publish_solutions.validate_base_url(expected_url + "/", head)
    assert validated_slash == expected_url

    # 3. Empty base URL defaults to canonical release URL
    default_url = publish_solutions.validate_base_url("", head)
    assert default_url == expected_url

    # 4. Mismatched pin in base URL rejected
    with pytest.raises(ValueError, match="Forbidden or mismatched base-url"):
        publish_solutions.validate_base_url(
            "https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/wrongpin00000000000000000000000000000000",
            head,
        )

    # 5. Untrusted domain rejected
    with pytest.raises(ValueError, match="Forbidden or mismatched base-url"):
        publish_solutions.validate_base_url(
            f"https://malicious.cdn.example.com/solutions/releases/{head}",
            head,
        )

    # 6. Rejection through main() CLI execution
    out_dir = tmp_path / "cdn_out"
    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--base-url", "https://unauthorized-domain.com/releases",
        "--sequence", "1",
        "--offline",
    ])
    assert rc != 0


def test_all_destinations_including_v2_enumerated_in_inventory(tmp_path: Path):
    files = [
        tmp_path / "sol_alpha.zip",
        tmp_path / "sol_beta.zip",
        tmp_path / "manifest.json",
        tmp_path / "manifest.json.minisig",
        tmp_path / "solutions_index.json",
        tmp_path / "solutions_index.json.minisig",
        tmp_path / "bundled_hashes.json",
        tmp_path / "bundled_hashes.json.minisig",
    ]
    for f in files:
        f.write_text(f"content of {f.name}", encoding="utf-8")

    pin = "abcdef1234567890abcdef1234567890abcdef12"
    inventory = publish_solutions.format_artifact_inventory(
        files,
        bucket="test-bucket",
        prefix="test-prefix",
        content_pin=pin,
    )

    # Total destinations = 8 release + 6 v2 = 14
    assert "Total: 14" in inventory
    assert "Total count: 14" in inventory

    # Check all 8 release destinations
    for f in files:
        assert f"oss://test-bucket/test-prefix/releases/{pin}/{f.name}" in inventory

    # Check all 6 v2 destinations
    for name in [
        "bundled_hashes.json",
        "bundled_hashes.json.minisig",
        "solutions_index.json",
        "solutions_index.json.minisig",
        "manifest.json",
        "manifest.json.minisig",
    ]:
        assert f"oss://test-bucket/test-prefix/v2/{name}" in inventory

    # Solution ZIPs must NOT be in v2/
    assert f"oss://test-bucket/test-prefix/v2/sol_alpha.zip" not in inventory
    assert f"oss://test-bucket/test-prefix/v2/sol_beta.zip" not in inventory


def test_is_oss_not_found_strict_parsing():
    """Ensure is_oss_not_found strictly detects NoSuchKey and rejects false positives."""
    # Negative assertions explicitly required
    assert publish_solutions.is_oss_not_found("ErrorCode=NotNoSuchKey") is False
    assert publish_solutions.is_oss_not_found("ErrorCode=AccessDenied; diagnostic=NoSuchKey") is False
    assert publish_solutions.is_oss_not_found("AccessDenied") is False
    assert publish_solutions.is_oss_not_found("HTTP 403 Forbidden") is False
    assert publish_solutions.is_oss_not_found("Some other error string") is False

    # Positive assertions
    assert publish_solutions.is_oss_not_found("ErrorCode=NoSuchKey") is True
    assert publish_solutions.is_oss_not_found("ErrorCode: NoSuchKey") is True
    assert publish_solutions.is_oss_not_found("<Code>NoSuchKey</Code>") is True
    assert publish_solutions.is_oss_not_found("Code: NoSuchKey") is True
    assert publish_solutions.is_oss_not_found("The specified key does not exist") is True
    assert publish_solutions.is_oss_not_found("Error: ErrorCode=NoSuchKey: not found") is True


def test_dry_run_unconditionally_uses_test_keys_even_with_env_private_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """Assert publish_solutions.py --dry-run uses test keys even when CONTENT_SIGNING_PRIVATE_KEY is present."""
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir = tmp_path / "cdn_dry_run"

    # Inject a non-empty (and non-minisign) private key into environment
    monkeypatch.setenv("CONTENT_SIGNING_PRIVATE_KEY", "untrusted-secret-private-key-material")
    assert "CONTENT_SIGNING_PRIVATE_KEY" in os.environ

    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc = publish_solutions.main([
            "--solutions-dir", str(repo / "solutions"),
            "--output-dir", str(out_dir),
            "--content-pin", head,
            "--sequence", "1",
            "--dry-run",
            "--allow-local-branch",
        ])
        assert rc == 0

    # Ensure private key was purged so it could never be touched or leaked
    assert "CONTENT_SIGNING_PRIVATE_KEY" not in os.environ

    stdout = capsys.readouterr().out
    # Confirm test-keys mode generated an ephemeral test keypair
    assert "Test-keys mode: generated ephemeral test keypair" in stdout
    assert "Dry-run preflight complete. Zero changes written to OSS." in stdout


def test_sequence_less_than_one_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    out_dir = tmp_path / "cdn_out"

    # Reject sequence = 0 in CLI / package_and_publish
    with pytest.raises(ValueError, match=r"sequence must be >= 1 \(floor is 1\), got 0"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "0",
                "--offline",
            ])
        )

    # Reject sequence = 0 directly in resolve_sequence
    with pytest.raises(ValueError, match=r"sequence must be >= 1 \(floor is 1\), got 0"):
        publish_solutions.resolve_sequence(0, dry_run=False, offline=False)

    # Reject negative sequence in resolve_sequence
    with pytest.raises(ValueError, match=r"sequence must be >= 1 \(floor is 1\), got -1"):
        publish_solutions.resolve_sequence(-1, dry_run=False, offline=False)


def test_dry_run_existing_release_with_test_keys_verifies_production_signature(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
    prod_sec_key, prod_pubkey = generate_test_minisign_keypair(tmp_path / "prod_keys")
    out_dir_prod = tmp_path / "cdn_prod"

    # Generate real production signed artifacts
    rc_prod = publish_solutions.package_and_publish(
        publish_solutions.parse_args([
            "--solutions-dir", str(repo / "solutions"),
            "--output-dir", str(out_dir_prod),
            "--content-pin", head,
            "--sequence", "1",
            "--sign",
            "--offline",
            "--minisign-key-file", str(prod_sec_key),
            "--minisign-pubkey", prod_pubkey,
        ])
    )
    assert rc_prod == 0

    # Read the production files into memory to mock remote OSS
    remote_oss_files: dict[str, bytes] = {
        p.name: p.read_bytes() for p in out_dir_prod.iterdir() if p.is_file()
    }

    out_dir_dry = tmp_path / "cdn_dry"
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                fname = target.split("/")[-1]
                if f"/releases/{head}/" in target and fname in remote_oss_files:
                    return mock.Mock(returncode=0, stdout=remote_oss_files[fname], stderr=b"")
                return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    # 1. With prod_pubkey provided: dry run verifies remote .minisig against prod_pubkey
    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        rc_dry = publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir_dry),
                "--content-pin", head,
                "--sequence", "1",
                "--sign",
                "--dry-run",
                "--allow-local-branch",
                "--minisign-pubkey", prod_pubkey,
            ])
        )
        assert rc_dry == 0

    # 2. Without pubkey: dry run fails closed when verifying remote signatures
    out_dir_dry_nopubkey = tmp_path / "cdn_dry_nopubkey"
    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        with pytest.raises(
            ValueError,
            match=r"Production public key \(--minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY\) is required to verify remote signatures during dry-run",
        ):
            publish_solutions.package_and_publish(
                publish_solutions.parse_args([
                    "--solutions-dir", str(repo / "solutions"),
                    "--output-dir", str(out_dir_dry_nopubkey),
                    "--content-pin", head,
                    "--sequence", "1",
                    "--sign",
                    "--dry-run",
                    "--allow-local-branch",
                ])
            )

    # 3. Altered payload content MUST still be rejected in dry-run
    remote_oss_files["sol_alpha.zip"] = b"tampered-zip-contents"
    out_dir_dry_tampered = tmp_path / "cdn_dry_tampered"
    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        with pytest.raises(ValueError, match="Immutable release conflict.*sol_alpha.zip"):
            publish_solutions.package_and_publish(
                publish_solutions.parse_args([
                    "--solutions-dir", str(repo / "solutions"),
                    "--output-dir", str(out_dir_dry_tampered),
                    "--content-pin", head,
                    "--sequence", "1",
                    "--sign",
                    "--dry-run",
                    "--allow-local-branch",
                    "--minisign-pubkey", prod_pubkey,
                ])
            )


def test_check_immutable_release_conflicts_unit(tmp_path: Path):
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    test_file = tmp_path / "manifest.json"
    test_file.write_text('{"version": 2}\n', encoding="utf-8")
    sig = publish_solutions.run_minisign_sign(test_file, sec_key, commit_time=1700000000, version=2)

    # Ephemeral key signs a copy in a separate directory so it doesn't overwrite sig
    eph_dir = tmp_path / "eph"
    eph_dir.mkdir(parents=True, exist_ok=True)
    eph_sec_key, _ = generate_test_minisign_keypair(eph_dir)
    test_file_eph = eph_dir / "manifest.json"
    test_file_eph.write_text('{"version": 2}\n', encoding="utf-8")
    eph_sig = publish_solutions.run_minisign_sign(test_file_eph, eph_sec_key, commit_time=1700000000, version=2)
    eph_sig_bytes = eph_sig.read_bytes()

    # If is_test_keys is False, signature mismatch raises conflict
    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                if target.endswith("manifest.json"):
                    return mock.Mock(returncode=0, stdout=test_file.read_bytes(), stderr=b"")
                elif target.endswith("manifest.json.minisig"):
                    return mock.Mock(returncode=0, stdout=eph_sig_bytes, stderr=b"")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        # In non-test-keys mode, signature mismatch is a conflict
        with pytest.raises(ValueError, match="Immutable release conflict.*manifest.json.minisig"):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[test_file, sig],
                is_test_keys=False,
            )

        # In test-keys mode with prod_pubkey, remote signature is verified against pubkey
        # Since eph_sig was signed by eph_sec_key (not pubkey), it correctly detects invalid remote sig
        with pytest.raises(ValueError, match="remote .* signature is invalid"):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[test_file, sig],
                is_test_keys=True,
                prod_pubkey=pubkey,
            )

        # In test-keys mode without pubkey, fail closed
        with pytest.raises(
            ValueError,
            match=r"Production public key \(--minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY\) is required to verify remote signatures during dry-run",
        ):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[test_file, sig],
                is_test_keys=True,
                prod_pubkey=None,
            )

        # In test-keys mode with pubkey but missing local payload, fails closed
        orphaned_sig = tmp_path / "orphan.minisig"
        orphaned_sig.write_bytes(sig.read_bytes())
        with pytest.raises(ValueError, match=r"Cannot verify remote signature .* local payload .* does not exist"):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[orphaned_sig],
                is_test_keys=True,
                prod_pubkey=pubkey,
            )


def test_check_immutable_release_conflicts_minisig_identical_sha_test_keys(tmp_path: Path):
    """Regression test: even if remote_sha == local_sha for a .minisig file,
    when is_test_keys=True, missing pubkey or missing payload or invalid signature
    raises ValueError (it does NOT bypass through the equality check)."""
    _prod_sec_key, prod_pubkey = generate_test_minisign_keypair(tmp_path / "prod")
    test_sec_key, _ = generate_test_minisign_keypair(tmp_path / "test")

    test_file = tmp_path / "manifest.json"
    test_file.write_text('{"version": 2}\n', encoding="utf-8")
    test_sig = publish_solutions.run_minisign_sign(test_file, test_sec_key, commit_time=1700000000, version=2)
    sig_bytes = test_sig.read_bytes()

    real_run = subprocess.run

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                if target.endswith("manifest.json"):
                    return mock.Mock(returncode=0, stdout=test_file.read_bytes(), stderr=b"")
                elif target.endswith("manifest.json.minisig") or target.endswith("orphan.minisig"):
                    # Remote has IDENTICAL sha / bytes to local test_sig
                    return mock.Mock(returncode=0, stdout=sig_bytes, stderr=b"")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        # 1. Missing pubkey: even if remote_sha == local_sha, must raise ValueError
        with pytest.raises(
            ValueError,
            match=r"Production public key \(--minisign-pubkey or CONTENT_MINISIGN_PUBLIC_KEY\) is required to verify remote signatures during dry-run",
        ):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[test_file, test_sig],
                is_test_keys=True,
                prod_pubkey=None,
            )

        # 2. Missing payload: even if remote_sha == local_sha, must raise ValueError
        orphaned_sig = tmp_path / "orphan.minisig"
        orphaned_sig.write_bytes(sig_bytes)
        with pytest.raises(
            ValueError,
            match=r"Cannot verify remote signature .* local payload .* does not exist",
        ):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[orphaned_sig],
                is_test_keys=True,
                prod_pubkey=prod_pubkey,
            )

        # 3. Invalid signature: remote_sha == local_sha, but signed with test key (not prod_pubkey)
        with pytest.raises(
            ValueError,
            match=r"remote .* signature is invalid",
        ):
            publish_solutions.check_immutable_release_conflicts(
                bucket="bucket",
                prefix="prefix",
                content_pin="pin",
                artifacts=[test_file, test_sig],
                is_test_keys=True,
                prod_pubkey=prod_pubkey,
            )

    # 4. Valid signature: remote_sha == local_sha, signed with prod_pubkey, verified successfully
    prod_sig = publish_solutions.run_minisign_sign(test_file, _prod_sec_key, commit_time=1700000000, version=2)
    prod_sig_bytes = prod_sig.read_bytes()

    def mock_subprocess_valid(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil":
            cmd_str = " ".join(cmd_list)
            if "ossutil cat" in cmd_str:
                target = cmd_list[2]
                if target.endswith("manifest.json"):
                    return mock.Mock(returncode=0, stdout=test_file.read_bytes(), stderr=b"")
                elif target.endswith("manifest.json.minisig"):
                    return mock.Mock(returncode=0, stdout=prod_sig_bytes, stderr=b"")
            return mock.Mock(returncode=0, stdout="", stderr="")
        return real_run(cmd, **kwargs)

    with mock.patch("subprocess.run", side_effect=mock_subprocess_valid):
        identical = publish_solutions.check_immutable_release_conflicts(
            bucket="bucket",
            prefix="prefix",
            content_pin="pin",
            artifacts=[test_file, prod_sig],
            is_test_keys=True,
            prod_pubkey=prod_pubkey,
        )
        assert "manifest.json" in identical
        assert "manifest.json.minisig" in identical


def init_test_repo_with_covers(repo_dir: Path) -> str:
    """Initialize a git repository with solutions containing relative, absolute, and missing covers."""
    subprocess.run(["git", "init", "-b", "main", str(repo_dir)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo_dir), "config", "commit.gpgsign", "false"], check=True)

    (repo_dir / ".gitignore").write_text("*.zip\n*.tmp\n", encoding="utf-8")

    # 1. sol_alpha with relative cover in gallery/
    sol_a = repo_dir / "solutions" / "sol_alpha"
    sol_a.mkdir(parents=True)
    (sol_a / "gallery").mkdir(parents=True)
    cover_png = sol_a / "gallery" / "cover.png"
    cover_png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRFAKEPNGDATA")
    (sol_a / "solution.yaml").write_text(
        "id: sol_alpha\n"
        "name: Solution Alpha\n"
        "name_zh: 方案 Alpha\n"
        "version: 1.0.0\n"
        "intro:\n"
        "  summary: Alpha Summary\n"
        "  summary_zh: Alpha 摘要\n"
        "  cover_image: gallery/cover.png\n"
        "  category: industrial\n"
        "  tags: [iot, edge]\n"
        "difficulty: beginner\n"
        "estimated_time: 15min\n",
        encoding="utf-8",
    )
    (sol_a / "guide.md").write_text("# Guide Alpha\n", encoding="utf-8")

    # 2. sol_url with absolute HTTP URL cover
    sol_u = repo_dir / "solutions" / "sol_url"
    sol_u.mkdir(parents=True)
    (sol_u / "solution.yaml").write_text(
        "id: sol_url\n"
        "name: Solution URL\n"
        "name_zh: 方案 URL\n"
        "intro:\n"
        "  summary: URL Summary\n"
        "  summary_zh: URL 摘要\n"
        "  cover_image: https://files.seeedstudio.com/wiki/cover.png\n"
        "  category: vision\n"
        "  tags: [ai]\n"
        "difficulty: advanced\n"
        "estimated_time: 45min\n",
        encoding="utf-8",
    )
    (sol_u / "guide.md").write_text("# Guide URL\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "Initial commit with covers"], check=True, capture_output=True)

    head = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().lower()
    return head


def test_manifest_inlined_metadata_and_relative_cover_extraction(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_repo_with_covers(repo)
    out_dir = tmp_path / "cdn_out"

    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--offline",
    ])
    assert rc == 0

    manifest_file = out_dir / "manifest.json"
    index_file = out_dir / "solutions_index.json"
    assert manifest_file.is_file()
    assert index_file.is_file()

    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    index_data = json.loads(index_file.read_text(encoding="utf-8"))

    m_sol = manifest_data["solutions"]
    assert "sol_alpha" in m_sol
    assert "sol_url" in m_sol

    # 1. Verify sol_alpha inlined display metadata in manifest.json
    alpha_m = m_sol["sol_alpha"]
    assert alpha_m["name"] == "Solution Alpha"
    assert alpha_m["name_zh"] == "方案 Alpha"
    assert alpha_m["summary"] == "Alpha Summary"
    assert alpha_m["summary_zh"] == "Alpha 摘要"
    expected_cover_url = f"https://sensecraft-statics.seeed.cc/solution-app/solutions/releases/{head}/covers/sol_alpha/cover.png"
    assert alpha_m["cover_image"] == expected_cover_url
    assert alpha_m["category"] == "industrial"
    assert alpha_m["tags"] == ["iot", "edge"]
    assert alpha_m["difficulty"] == "beginner"
    assert alpha_m["estimated_time"] == "15min"

    # Verify solutions_index.json has identical fields
    idx_map = {item["id"]: item for item in index_data["solutions"]}
    alpha_idx = idx_map["sol_alpha"]
    for field in ["name", "name_zh", "summary", "summary_zh", "cover_image", "category", "tags", "difficulty", "estimated_time"]:
        assert alpha_m[field] == alpha_idx[field]

    # 2. Verify extracted cover image file
    extracted_cover = out_dir / "covers" / "sol_alpha" / "cover.png"
    assert extracted_cover.is_file()
    assert extracted_cover.read_bytes() == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRFAKEPNGDATA"

    # 3. Verify sol_url kept its absolute URL unchanged
    url_m = m_sol["sol_url"]
    assert url_m["cover_image"] == "https://files.seeedstudio.com/wiki/cover.png"
    assert idx_map["sol_url"]["cover_image"] == "https://files.seeedstudio.com/wiki/cover.png"
    assert not (out_dir / "covers" / "sol_url").exists()


def test_cover_image_path_traversal_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)

    # 1. Traversal using ..
    bad_sol = repo / "solutions" / "sol_traversal"
    bad_sol.mkdir()
    (bad_sol / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (bad_sol / "solution.yaml").write_text(
        "id: sol_traversal\nname: Traversal\ncover_image: ../../secret.png\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add bad traversal solution"], check=True, capture_output=True)
    new_head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    out_dir = tmp_path / "cdn_out"
    with pytest.raises(ValueError, match=r"Security Error: Path traversal in cover_image for sol_traversal"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", new_head,
                "--sequence", "1",
                "--offline",
            ])
        )

    # 2. Absolute path traversal
    (bad_sol / "solution.yaml").write_text(
        "id: sol_traversal\nname: Traversal\ncover_image: /etc/passwd\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add absolute path cover solution"], check=True, capture_output=True)
    abs_head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    with pytest.raises(ValueError, match=r"Security Error: Path traversal in cover_image for sol_traversal"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", abs_head,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_cover_image_symlink_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    sol_sym = repo / "solutions" / "sol_sym"
    sol_sym.mkdir()
    (sol_sym / "guide.md").write_text("# Guide\n", encoding="utf-8")

    real_img = repo / "solutions" / "sol_alpha" / "guide.md"
    symlink_img = sol_sym / "symlink_cover.png"
    os.symlink(real_img, symlink_img)

    (sol_sym / "solution.yaml").write_text(
        "id: sol_sym\nname: Symlink Sol\ncover_image: symlink_cover.png\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add symlink cover solution"], check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    out_dir = tmp_path / "cdn_out"
    with pytest.raises(ValueError, match=r"Security Error: Symlink detected in cover_image for sol_sym"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_cover_image_missing_downgrades_gracefully(tmp_path: Path, capsys: pytest.CaptureFixture):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    sol_m = repo / "solutions" / "sol_missing"
    sol_m.mkdir()
    (sol_m / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (sol_m / "solution.yaml").write_text(
        "id: sol_missing\nname: Missing Cover Sol\ncover_image: gallery/absent.png\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add missing cover solution"], check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    out_dir = tmp_path / "cdn_out"
    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--offline",
    ])
    assert rc == 0

    captured = capsys.readouterr()
    assert "[WARNING] Solution sol_missing cover_image gallery/absent.png not found, setting to empty" in captured.out

    manifest_data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    index_data = json.loads((out_dir / "solutions_index.json").read_text(encoding="utf-8"))

    assert manifest_data["solutions"]["sol_missing"]["cover_image"] == ""
    idx_sol = next(s for s in index_data["solutions"] if s["id"] == "sol_missing")
    assert idx_sol["cover_image"] == ""


def test_cover_image_sensitive_file_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    sol_s = repo / "solutions" / "sol_sensitive"
    sol_s.mkdir()
    (sol_s / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (sol_s / "solution.yaml").write_text(
        "id: sol_sensitive\nname: Sensitive Sol\ncover_image: .env\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add sensitive cover solution"], check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    out_dir = tmp_path / "cdn_out"
    with pytest.raises(ValueError, match=r"Security Error: Sensitive or junk file referenced as cover_image"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_cover_image_junk_file_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    sol_j = repo / "solutions" / "sol_junk"
    sol_j.mkdir()
    (sol_j / "guide.md").write_text("# Guide\n", encoding="utf-8")

    # Case-insensitive DEPLOY_LOG.md
    (sol_j / "solution.yaml").write_text(
        "id: sol_junk\nname: Junk Sol\ncover_image: deploy_log.md\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add junk cover solution"], check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    out_dir = tmp_path / "cdn_out"
    with pytest.raises(ValueError, match=r"Security Error: Sensitive or junk file referenced as cover_image"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--offline",
            ])
        )

    # .DS_Store
    (sol_j / "solution.yaml").write_text(
        "id: sol_junk\nname: Junk Sol\ncover_image: .DS_Store\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Add ds_store cover solution"], check=True, capture_output=True)
    head2 = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()

    with pytest.raises(ValueError, match=r"Security Error: Sensitive or junk file referenced as cover_image"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head2,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_output_covers_dir_symlink_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_repo_with_covers(repo)
    out_dir = tmp_path / "cdn_out"
    out_dir.mkdir()

    # Create covers directory as a symlink pointing to an external directory
    external_dir = tmp_path / "external_target"
    external_dir.mkdir()
    os.symlink(external_dir, out_dir / "covers")

    with pytest.raises(ValueError, match=r"Security Error: Output covers directory is a symlink"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_target_sol_cover_dir_symlink_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_repo_with_covers(repo)
    out_dir = tmp_path / "cdn_out"
    out_dir.mkdir()
    covers_dir = out_dir / "covers"
    covers_dir.mkdir()

    # Create target solution cover directory as a symlink pointing to an external directory
    external_dir = tmp_path / "external_sol_target"
    external_dir.mkdir()
    os.symlink(external_dir, covers_dir / "sol_alpha")

    with pytest.raises(ValueError, match=r"Security Error: Target cover directory is a symlink"):
        publish_solutions.process_solution_cover(
            sol_id="sol_alpha",
            sol_dir=repo / "solutions" / "sol_alpha",
            cover_image="gallery/cover.png",
            repo_root=repo,
            tracked_files_set={"solutions/sol_alpha/gallery/cover.png"},
            output_dir=out_dir,
            generated_artifacts=[],
        )


def test_cover_image_untracked_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    init_test_git_repo(repo)

    sol_u = repo / "solutions" / "sol_untracked"
    sol_u.mkdir()
    (sol_u / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (sol_u / "solution.yaml").write_text(
        "id: sol_untracked\nname: Untracked Sol\ncover_image: cover.png\n",
        encoding="utf-8",
    )
    # Ignore cover.png in .gitignore so git working tree remains clean
    (repo / ".gitignore").write_text("*.zip\n*.tmp\ncover.png\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "Commit untracked cover solution"], check=True, capture_output=True)

    # Now create cover.png on disk (which is ignored, so working tree is clean)
    cover_file = sol_u / "cover.png"
    cover_file.write_bytes(b"UNTRACKED_PNG_DATA")

    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip().lower()
    out_dir = tmp_path / "cdn_out"

    with pytest.raises(ValueError, match=r"Security Error: cover_image for sol_untracked is not tracked by git"):
        publish_solutions.package_and_publish(
            publish_solutions.parse_args([
                "--solutions-dir", str(repo / "solutions"),
                "--output-dir", str(out_dir),
                "--content-pin", head,
                "--sequence", "1",
                "--offline",
            ])
        )


def test_minisign_digital_signature_verification_with_covers(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_repo_with_covers(repo)
    sec_key, pubkey = generate_test_minisign_keypair(tmp_path)
    out_dir = tmp_path / "cdn_out"

    rc = publish_solutions.main([
        "--solutions-dir", str(repo / "solutions"),
        "--output-dir", str(out_dir),
        "--content-pin", head,
        "--sequence", "1",
        "--sign",
        "--minisign-key-file", str(sec_key),
        "--minisign-pubkey", pubkey,
        "--offline",
    ])
    assert rc == 0

    manifest_file = out_dir / "manifest.json"
    manifest_sig = out_dir / "manifest.json.minisig"
    index_file = out_dir / "solutions_index.json"
    index_sig = out_dir / "solutions_index.json.minisig"
    hashes_file = out_dir / "bundled_hashes.json"
    hashes_sig = out_dir / "bundled_hashes.json.minisig"

    assert manifest_sig.is_file()
    assert index_sig.is_file()
    assert hashes_sig.is_file()

    # Real minisign verification
    publish_solutions.run_minisign_verify(manifest_file, manifest_sig, pubkey)
    publish_solutions.run_minisign_verify(index_file, index_sig, pubkey)
    publish_solutions.run_minisign_verify(hashes_file, hashes_sig, pubkey)


def test_artifact_inventory_and_oss_keys_preserve_subdirectories(tmp_path: Path):
    out_dir = tmp_path / "cdn_out"
    out_dir.mkdir()
    covers_sol_dir = out_dir / "covers" / "sol_alpha"
    covers_sol_dir.mkdir(parents=True)

    manifest = out_dir / "manifest.json"
    manifest.write_text('{"version": 2}\n', encoding="utf-8")
    zip_alpha = out_dir / "sol_alpha.zip"
    zip_alpha.write_bytes(b"ZIP_ALPHA")
    cover_file = covers_sol_dir / "cover.png"
    cover_file.write_bytes(b"COVER_BYTES")

    artifacts = [manifest, zip_alpha, cover_file]
    pin = "1234567890abcdef1234567890abcdef12345678"

    # 1. Verify format_artifact_inventory preserves subdirectories and d["dest"] is relative
    inventory = publish_solutions.format_artifact_inventory(
        artifacts,
        bucket="test-bucket",
        prefix="test-prefix",
        content_pin=pin,
        output_dir=out_dir,
    )

    assert f"oss://test-bucket/test-prefix/releases/{pin}/covers/sol_alpha/cover.png" in inventory
    assert f"oss://test-bucket/test-prefix/releases/{pin}/sol_alpha.zip" in inventory

    # 2. Verify check_immutable_release_conflicts preserves subdirectories
    queried_targets: list[str] = []

    def mock_subprocess(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil" and cmd_list[1] == "cat":
            queried_targets.append(cmd_list[2])
            if "covers/sol_alpha/cover.png" in cmd_list[2]:
                return mock.Mock(returncode=0, stdout=b"COVER_BYTES", stderr=b"")
            return mock.Mock(returncode=1, stdout=b"", stderr=b"ErrorCode=NoSuchKey: not found")
        return mock.Mock(returncode=0, stdout="", stderr="")

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        identical = publish_solutions.check_immutable_release_conflicts(
            bucket="test-bucket",
            prefix="test-prefix",
            content_pin=pin,
            artifacts=artifacts,
            output_dir=out_dir,
        )

    assert any(t.endswith("releases/1234567890abcdef1234567890abcdef12345678/covers/sol_alpha/cover.png") for t in queried_targets)
    assert "covers/sol_alpha/cover.png" in identical

    # 3. Verify upload_release_artifacts preserves subdirectories in key and dest_obj
    uploaded_keys: list[str] = []

    def mock_upload(cmd, **kwargs):
        cmd_list = [str(c) for c in cmd]
        if cmd_list and cmd_list[0] == "ossutil" and "put-object" in cmd_list:
            key_idx = cmd_list.index("--key") + 1
            uploaded_keys.append(cmd_list[key_idx])
            return mock.Mock(returncode=0, stdout="", stderr="")
        return mock.Mock(returncode=0, stdout="", stderr="")

    with mock.patch("subprocess.run", side_effect=mock_upload):
        publish_solutions.upload_release_artifacts(
            bucket="test-bucket",
            prefix="test-prefix",
            content_pin=pin,
            artifacts=artifacts,
            already_identical={"covers/sol_alpha/cover.png"},  # Should be skipped
            output_dir=out_dir,
        )

    # zip_alpha and manifest should be uploaded, cover should be skipped
    assert any(k.endswith("sol_alpha.zip") for k in uploaded_keys)
    assert not any(k.endswith("covers/sol_alpha/cover.png") for k in uploaded_keys)

    # Now test when cover is NOT identical: it MUST upload with key containing covers/
    with mock.patch("subprocess.run", side_effect=mock_upload):
        publish_solutions.upload_release_artifacts(
            bucket="test-bucket",
            prefix="test-prefix",
            content_pin=pin,
            artifacts=[cover_file],
            already_identical=set(),
            output_dir=out_dir,
        )
    assert any(k == f"test-prefix/releases/{pin}/covers/sol_alpha/cover.png" for k in uploaded_keys)


def test_artifact_outside_output_dir_rejected(tmp_path: Path):
    out_dir = tmp_path / "cdn_out"
    out_dir.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")

    # 1. format_artifact_inventory must raise ValueError
    with pytest.raises(ValueError, match=r"Security Error: Artifact .* is outside output directory"):
        publish_solutions.format_artifact_inventory(
            [outside_file],
            bucket="b",
            prefix="p",
            content_pin="1234567890abcdef1234567890abcdef12345678",
            output_dir=out_dir,
        )

    # 2. check_immutable_release_conflicts must raise ValueError
    with pytest.raises(ValueError, match=r"Security Error: Artifact .* is outside output directory"):
        publish_solutions.check_immutable_release_conflicts(
            bucket="b",
            prefix="p",
            content_pin="1234567890abcdef1234567890abcdef12345678",
            artifacts=[outside_file],
            output_dir=out_dir,
        )

    # 3. upload_release_artifacts must raise ValueError
    with pytest.raises(ValueError, match=r"Security Error: Artifact .* is outside output directory"):
        publish_solutions.upload_release_artifacts(
            bucket="b",
            prefix="p",
            content_pin="1234567890abcdef1234567890abcdef12345678",
            artifacts=[outside_file],
            already_identical=set(),
            output_dir=out_dir,
        )






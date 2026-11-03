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
            return mock.Mock(returncode=1, stdout=b"", stderr=b"Error: NoSuchKey: object does not exist")

    with mock.patch("subprocess.run", side_effect=mock_subprocess):
        already_identical = publish_solutions.check_immutable_release_conflicts(
            "bucket", "prefix", "pin12345", out_dir
        )
        assert already_identical == {"sol_alpha.zip"}


def test_ephemeral_key_rejected_in_upload_mode_when_private_key_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    head = init_test_git_repo(repo)
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
                    "--allow-local-branch",
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
                    "--allow-local-branch",
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
                return mock.Mock(returncode=1, stdout=b"", stderr=b"NoSuchKey: not found")
            elif "ossutil cp" in cmd_str:
                src = cmd_list[3]
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
                "--allow-local-branch",
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
                    return mock.Mock(returncode=1, stdout=b"", stderr=b"NoSuchKey: not found")
                return mock.Mock(returncode=1, stdout=b"", stderr=b"NoSuchKey: not found")
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
        "--allow-local-branch",
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

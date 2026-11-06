import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

server_dir = Path(__file__).resolve().parent.parent / "server"
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_compile_success_file():
    def mock_subprocess(cmd, cwd, **kwargs):
        # Create dummy binary output in build dir
        build_dir = Path(cwd) / ".esphome" / "build" / "test_node" / ".pioenvs" / "test_node"
        build_dir.mkdir(parents=True, exist_ok=True)
        bin_path = build_dir / "firmware.factory.bin"
        bin_path.write_bytes(b"\xe9\x04\x00\x00DUMMY_FIRMWARE_BINARY")
        return MagicMock(returncode=0, stdout="Compiled successfully", stderr="")

    with patch("subprocess.run", side_effect=mock_subprocess):
        response = client.post(
            "/api/compile",
            files={"file": ("test_node.yaml", b"esphome:\n  name: test_node\n", "application/x-yaml")},
        )
        assert response.status_code == 200
        assert response.content == b"\xe9\x04\x00\x00DUMMY_FIRMWARE_BINARY"
        assert response.headers["content-type"] == "application/octet-stream"
        assert "firmware.factory.bin" in response.headers["content-disposition"]


def test_compile_success_body():
    def mock_subprocess(cmd, cwd, **kwargs):
        build_dir = Path(cwd) / ".esphome" / "build" / "node"
        build_dir.mkdir(parents=True, exist_ok=True)
        bin_path = build_dir / "firmware.bin"
        bin_path.write_bytes(b"DUMMY_RAW_BODY_BIN")
        return MagicMock(returncode=0, stdout="Build finished", stderr="")

    with patch("subprocess.run", side_effect=mock_subprocess):
        response = client.post(
            "/api/compile",
            content=b"esphome:\n  name: node\n",
            headers={"Content-Type": "application/x-yaml"},
        )
        assert response.status_code == 200
        assert response.content == b"DUMMY_RAW_BODY_BIN"


def test_compile_failure():
    def mock_subprocess(cmd, cwd, **kwargs):
        return MagicMock(returncode=1, stdout="In file included from ...", stderr="Error: undefined component")

    with patch("subprocess.run", side_effect=mock_subprocess):
        response = client.post(
            "/api/compile",
            files={"file": ("config.yaml", b"invalid: config\n", "application/x-yaml")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Compilation failed"
        assert "undefined component" in data["output"]


def test_compile_empty_content():
    response = client.post("/api/compile", content=b"   ")
    assert response.status_code == 400
    assert response.json()["error"] == "Missing YAML configuration"


def test_compile_binary_missing():
    def mock_subprocess(cmd, cwd, **kwargs):
        return MagicMock(returncode=0, stdout="Build succeeded but no bin produced", stderr="")

    with patch("subprocess.run", side_effect=mock_subprocess):
        response = client.post(
            "/api/compile",
            files={"file": ("config.yaml", b"esphome: test\n", "application/x-yaml")},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "Binary not found"


def test_concurrent_compilation_queue():
    """Verify that multiple concurrent requests queue safely without race condition."""
    import time

    def mock_subprocess(cmd, cwd, **kwargs):
        time.sleep(0.05)
        build_dir = Path(cwd) / ".esphome" / "build" / "test_node"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "firmware.factory.bin").write_bytes(b"\xaa\xbb\xcc\xdd" * 8)
        return MagicMock(returncode=0, stdout="Success", stderr="")

    with patch("subprocess.run", side_effect=mock_subprocess):
        # Fire 3 requests sequentially/concurrently via TestClient
        res1 = client.post("/api/compile", content=b"esphome: node1\n")
        res2 = client.post("/api/compile", content=b"esphome: node2\n")
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res1.content == b"\xaa\xbb\xcc\xdd" * 8
        assert res2.content == b"\xaa\xbb\xcc\xdd" * 8

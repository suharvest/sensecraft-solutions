"""``solutionctl manage list-apps`` error handling (engine HTTP mocked)."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from solutionctl import _engine_http
from solutionctl.commands import manage


def _serve(status: int, body: dict):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def engine_returning(monkeypatch):
    servers = []

    def _make(status, body):
        srv = _serve(status, body)
        servers.append(srv)
        url = f"http://127.0.0.1:{srv.server_address[1]}"

        @contextmanager
        def fake():
            yield _engine_http.EngineConn(base_url=url)

        monkeypatch.setattr(manage, "engine_session", fake)

    yield _make
    for s in servers:
        s.shutdown()


def test_requires_desktop_app_is_a_clear_exit_4(engine_returning, capsys):
    engine_returning(
        501,
        {"success": False, "error": "requires_desktop_app",
         "detail": "needs python", "code": "REQUIRES_DESKTOP_APP", "group": "device_management"},
    )
    assert manage.run("list-apps") == 4
    err = capsys.readouterr().err
    assert "desktop App" in err
    assert "Traceback" not in err


def test_other_http_errors_exit_1(engine_returning, capsys):
    engine_returning(500, {"detail": "boom"})
    assert manage.run("list-apps") == 1
    assert "boom" in capsys.readouterr().err


def test_success_prints_json(engine_returning, capsys):
    engine_returning(200, {"apps": []})
    assert manage.run("list-apps") == 0
    assert json.loads(capsys.readouterr().out) == {"apps": []}


def test_error_id_is_parsed_by_the_http_layer(engine_returning):
    engine_returning(501, {"error": "requires_desktop_app", "detail": "x"})
    with manage.engine_session() as conn:
        with pytest.raises(_engine_http.EngineHttpError) as e:
            conn.get("/x")
    assert e.value.status == 501 and e.value.error == "requires_desktop_app"

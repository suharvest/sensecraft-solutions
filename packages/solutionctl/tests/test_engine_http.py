"""The engine runs as a subprocess; what it logs reaches the same terminal."""

from __future__ import annotations

import io
import subprocess
import time
from unittest.mock import patch

from solutionctl import _engine_http


def test_engine_log_lines_are_redacted_before_they_reach_stderr():
    proc = subprocess.Popen(
        [
            "python3",
            "-c",
            "import sys; sys.stderr.write('deploying with password=hunter2\\n')",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    captured = io.StringIO()
    with patch.object(_engine_http.sys, "stderr", captured):
        _engine_http._pump_stderr(proc)
    proc.wait(timeout=10)

    written = captured.getvalue()
    assert "hunter2" not in written
    assert "deploying with password=<REDACTED>" in written


class _SlowStderr(io.StringIO):
    """Stderr that lags, the way a busy terminal or a CI log collector does."""

    def write(self, text):  # noqa: D102
        time.sleep(0.4)
        return super().write(text)


def test_the_last_engine_lines_are_forwarded_before_the_cli_returns(tmp_path):
    """The engine logs why it is stopping as it stops; do not cut that off."""
    fake = tmp_path / "engine"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import signal, sys, time\n"
        "def bye(*a):\n"
        "    sys.stderr.write('shutting down, password=hunter2\\n')\n"
        "    sys.stderr.flush()\n"
        "    sys.exit(0)\n"
        "signal.signal(signal.SIGTERM, bye)\n"
        "print('{\"base_url\": \"http://127.0.0.1:1\", \"pid\": 1}', flush=True)\n"
        "time.sleep(30)\n"
    )
    fake.chmod(0o755)

    captured = _SlowStderr()
    with patch.object(_engine_http, "locate_engine", lambda: str(fake)), patch.object(
        _engine_http, "_wait_healthy", lambda *a, **kw: True
    ), patch.object(_engine_http.sys, "stderr", captured):
        with _engine_http.headless_engine():
            pass

    written = captured.getvalue()
    assert "shutting down" in written
    assert "hunter2" not in written

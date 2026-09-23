"""The engine runs as a subprocess; what it logs reaches the same terminal."""

from __future__ import annotations

import io
import subprocess
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

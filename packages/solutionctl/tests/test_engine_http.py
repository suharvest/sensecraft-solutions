"""The engine runs as a subprocess; what it logs reaches the same terminal."""

from __future__ import annotations

import io
import subprocess
import threading

import pytest
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


def _fake_engine(tmp_path, body):
    fake = tmp_path / "engine"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import signal, sys, time\n"
        "def bye(*a):\n"
        + body
        + "signal.signal(signal.SIGTERM, bye)\n"
        'print(\'{"base_url": "http://127.0.0.1:1", "pid": 1}\', flush=True)\n'
        "time.sleep(30)\n"
    )
    fake.chmod(0o755)
    return fake


class _StuckStderr(io.StringIO):
    """Stderr that wedges on the engine's log lines -- a full pipe, a stuck
    log collector. The CLI's own lines still go through, as they would."""

    def write(self, text):  # noqa: D102
        if "shutting down" in text:
            time.sleep(60)
        return super().write(text)


def test_a_wedged_log_pump_does_not_hold_the_cli_or_the_pipe(tmp_path):
    """Waiting for the pump is bounded: give up, and take the fd back."""
    fake = _fake_engine(
        tmp_path,
        "    sys.stderr.write('shutting down\\n')\n"
        "    sys.stderr.flush()\n"
        "    sys.exit(0)\n",
    )
    # Device discovery shells out (mdfind on macOS) before the engine is
    # spawned, so the engine is found by its argv, never by being first.
    spawned = []
    real_popen = subprocess.Popen

    def spy_popen(*a, **kw):
        proc = real_popen(*a, **kw)
        argv = a[0] if a else kw.get("args")
        if argv and str(fake) in [str(x) for x in argv]:
            spawned.append(proc)
        return proc

    with patch.object(_engine_http, "locate_engine", lambda: str(fake)), patch.object(
        _engine_http, "_wait_healthy", lambda *a, **kw: True
    ), patch.object(_engine_http.sys, "stderr", _StuckStderr()), patch.object(
        _engine_http, "PUMP_TIMEOUT", 0.3
    ), patch.object(_engine_http.subprocess, "Popen", spy_popen):
        started = time.monotonic()
        with _engine_http.headless_engine() as base_url:
            assert base_url
        elapsed = time.monotonic() - started

    assert elapsed < 10, f"teardown waited {elapsed:.1f}s on a wedged pump"
    assert len(spawned) == 1, f"expected one engine process, saw {len(spawned)}"
    assert spawned[0].poll() is not None, "the engine outlived the CLI"


def test_the_pump_is_joined_even_when_stopping_the_engine_raises(tmp_path):
    """A failed wait must not skip the pump: its lines are the diagnosis."""
    fake = _fake_engine(
        tmp_path,
        "    sys.stderr.write('shutting down, password=hunter2\\n')\n"
        "    sys.stderr.flush()\n"
        "    sys.exit(0)\n",
    )
    captured = _SlowStderr()
    joined = []
    real_join = threading.Thread.join

    def spy_join(self, *a, **kw):
        joined.append(self.name)
        return real_join(self, *a, **kw)

    with patch.object(_engine_http, "locate_engine", lambda: str(fake)), patch.object(
        _engine_http, "_wait_healthy", lambda *a, **kw: True
    ), patch.object(_engine_http.sys, "stderr", captured), patch.object(
        threading.Thread, "join", spy_join
    ):
        try:
            with _engine_http.headless_engine() as base_url:
                assert base_url
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            pass

    assert joined, "the log pump was never joined"
    written = captured.getvalue()
    assert "hunter2" not in written


def test_teardown_is_bounded_when_a_descendant_holds_the_log_pipe(tmp_path):
    """The engine's children inherit stderr; one can outlive it holding the
    write end, leaving the pump blocked on a read that will not return."""
    fake = tmp_path / "engine"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import subprocess, sys, time\n"
        # A grandchild keeps stderr open well past the engine's own exit.
        "subprocess.Popen(['python3', '-c', 'import time; time.sleep(5)'],\n"
        "                 stderr=sys.stderr)\n"
        'print(\'{"base_url": "http://127.0.0.1:1", "pid": 1}\', flush=True)\n'
        "time.sleep(30)\n"
    )
    fake.chmod(0o755)

    with patch.object(_engine_http, "locate_engine", lambda: str(fake)), patch.object(
        _engine_http, "_wait_healthy", lambda *a, **kw: True
    ), patch.object(_engine_http, "PUMP_TIMEOUT", 0.3):
        started = time.monotonic()
        with _engine_http.headless_engine():
            pass
        elapsed = time.monotonic() - started

    # Bounded by PUMP_TIMEOUT, not by whenever the grandchild lets go.
    assert elapsed < 3, f"teardown waited {elapsed:.1f}s on an inherited pipe"


def test_the_pump_is_joined_when_stopping_the_engine_itself_raises(tmp_path):
    """A wait() that blows up must not cost us the logs that explain it."""
    fake = _fake_engine(tmp_path, "    sys.exit(0)\n")
    joined = []
    real_join = threading.Thread.join
    boom = RuntimeError("wait failed")

    def spy_join(self, *a, **kw):
        joined.append(self.name)
        return real_join(self, *a, **kw)

    real_popen = subprocess.Popen

    def spy_popen(*a, **kw):
        # Only the engine's wait() explodes: device discovery shells out
        # through subprocess.run, which waits on its own processes.
        proc = real_popen(*a, **kw)
        argv = a[0] if a else kw.get("args")
        if argv and str(fake) in [str(x) for x in argv]:
            proc.wait = exploding_wait
        return proc

    def exploding_wait(*a, **kw):
        raise boom

    with patch.object(_engine_http, "locate_engine", lambda: str(fake)), patch.object(
        _engine_http, "_wait_healthy", lambda *a, **kw: True
    ), patch.object(_engine_http.sys, "stderr", io.StringIO()), patch.object(
        threading.Thread, "join", spy_join
    ), patch.object(_engine_http.subprocess, "Popen", spy_popen):
        with pytest.raises(RuntimeError, match="wait failed"):
            with _engine_http.headless_engine():
                pass

    assert any("_pump_stderr" in name for name in joined), "the log pump was not joined"

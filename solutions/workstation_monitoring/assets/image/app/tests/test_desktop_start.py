"""Desktop startup must open a ready service, not wait for the CLI to exit."""
import importlib.util
import os
from pathlib import Path
import shlex
import signal
import socket
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('desktop_start', Path(__file__).resolve().parents[1] / 'scripts/start_desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class DesktopStartTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'start.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.root / 'start.sh').chmod(0o755)

    def test_existing_service_does_not_launch_or_attach_a_second_launcher(self):
        with patch.object(desktop, 'camera_ready', return_value=True), patch.object(desktop.subprocess, 'Popen') as popen:
            self.assertFalse(desktop.ensure_service(self.root, 'http://localhost/'))
        popen.assert_not_called()

    def test_cold_start_returns_on_readiness_while_launcher_keeps_running(self):
        process = MagicMock(); process.poll.return_value = None
        with patch.object(desktop, 'camera_ready', side_effect=[False, False, True]), \
             patch.object(desktop, 'project_running', return_value=False), \
             patch.object(desktop.subprocess, 'Popen', return_value=process) as popen, \
             patch.object(desktop.time, 'sleep'):
            self.assertTrue(desktop.ensure_service(self.root, 'http://localhost/'))
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        process.wait.assert_not_called(); process.terminate.assert_not_called()

    def test_an_existing_booting_service_is_waited_for_without_starting_another(self):
        with patch.object(desktop, 'camera_ready', side_effect=[False, False, True]), \
             patch.object(desktop, 'project_running', return_value=True), \
             patch.object(desktop.subprocess, 'Popen') as popen, patch.object(desktop.time, 'sleep'):
            self.assertFalse(desktop.ensure_service(self.root, 'http://localhost/'))
        popen.assert_not_called()

    def test_failure_is_reported_instead_of_waiting_for_browser_forever(self):
        process = MagicMock(); process.poll.return_value = 1
        with patch.object(desktop, 'camera_ready', return_value=False), \
             patch.object(desktop, 'project_running', return_value=False), \
             patch.object(desktop.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(RuntimeError, 'desktop-service.log'):
                desktop.ensure_service(self.root, 'http://localhost/')

    def test_browser_handoff_success_and_launch_failure(self):
        (self.root / 'logs').mkdir()
        with patch.dict(desktop.os.environ, {'DISPLAY': ':0'}), \
             patch.object(desktop, 'browser_command', return_value=['firefox', '--new-tab', 'http://localhost/']), \
             patch.object(desktop.subprocess, 'Popen') as popen, patch.object(desktop.time, 'sleep'):
            popen.return_value.poll.return_value = 0
            desktop.open_browser(self.root, 'http://localhost/')
            popen.return_value.poll.return_value = 1
            with self.assertRaisesRegex(RuntimeError, '服务仍在运行'):
                desktop.open_browser(self.root, 'http://localhost/')

    def test_no_gui_has_clear_error(self):
        with patch.dict(desktop.os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, '桌面显示会话'):
                desktop.open_browser(self.root, 'http://localhost/')

    def test_real_background_service_opens_before_its_process_exits(self):
        # Exercise actual HTTP readiness with a tiny isolated service, not the GPU app.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        worker = self.root / 'fake_camera.py'
        pidfile = self.root / 'fake-camera.pid'
        worker.write_text('from http.server import BaseHTTPRequestHandler,HTTPServer\n'
            'from pathlib import Path\nimport os\n'
            f'Path({str(pidfile)!r}).write_text(str(os.getpid()))\n'
            'class Handler(BaseHTTPRequestHandler):\n'
            ' def do_GET(self):\n'
            '  self.send_response(200);self.end_headers();self.wfile.write(b\'{"schema_version":"1.0","decoder":"software"}\')\n'
            f'HTTPServer(("127.0.0.1",{port}),Handler).serve_forever()\n')
        (self.root / 'start.sh').write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(worker)) + '\n')
        launch = desktop.subprocess.Popen
        children = []
        def retain_child(*args, **kwargs):
            child = launch(*args, **kwargs)
            children.append(child)
            return child
        try:
            with patch.object(desktop.subprocess, 'Popen', side_effect=retain_child):
                self.assertTrue(desktop.ensure_service(self.root, f'http://127.0.0.1:{port}/', timeout=5))
            pid = int(pidfile.read_text())
            os.kill(pid, 0)  # Still running: readiness did not wait for launcher exit.
        finally:
            if pidfile.exists():
                pid = int(pidfile.read_text())
                try: os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError: pass
            for child in children:
                child.wait(timeout=5)

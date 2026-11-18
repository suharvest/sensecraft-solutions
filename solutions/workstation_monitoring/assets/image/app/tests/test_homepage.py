"""Exercise the production GET handler without starting camera/GPU workers."""
import ast
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class HomepageTests(unittest.TestCase):
    def test_production_http_root_matches_canonical_frontend(self):
        module = ast.parse((ROOT/'scripts/preview.py').read_text())
        handler = next(node for node in module.body if isinstance(node, ast.ClassDef) and any(
            isinstance(child, ast.FunctionDef) and child.name == 'do_GET' for child in node.body))
        method = next(node for node in handler.body if isinstance(node, ast.FunctionDef) and node.name == 'do_GET')
        metrics = dict(schema_version='1.0', gpu_percent=23.4)
        namespace = dict(ROOT=ROOT, urlsplit=urlsplit,
                         system_metrics=SimpleNamespace(snapshot=lambda: metrics))
        namespace['studio_http']=SimpleNamespace(handle=lambda *args:False)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(ROOT/'scripts/preview.py'), 'exec'), namespace)

        class Handler(BaseHTTPRequestHandler):
            do_GET = namespace['do_GET']

            def json(self, value):
                self.send_bytes(json.dumps(value).encode(), 'application/json')

            def send_bytes(self, body, content_type):
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            with urlopen(base + '/', timeout=3) as response:
                home = response.read()
            self.assertEqual(home, (ROOT/'frontend/public/index.html').read_bytes())
            self.assertIn(b'id="settingsToggle"', home)
            self.assertIn(b'id="settingsDialog"', home)
            self.assertIn(b'id="help"', home)
            with urlopen(base + '/settings?embedded=1', timeout=3) as response:
                settings = response.read()
                self.assertEqual(settings, (ROOT/'frontend/public/settings.html').read_bytes())
                self.assertIn(b'id="sourceType"', settings)
                self.assertIn(b'id="testSource"', settings)
            for asset in ('overlay-style.json', 'overlay.js'):
                with urlopen(base + '/' + asset, timeout=3) as response:
                    self.assertEqual(response.read(), (ROOT/'frontend/public'/asset).read_bytes())
            with urlopen(base + '/api/v1/system/metrics', timeout=3) as response:
                self.assertEqual(json.loads(response.read()), metrics)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

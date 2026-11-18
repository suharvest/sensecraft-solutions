import ast
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import struct
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import yaml
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.camera_sources import CameraSources, normalize_source, public_source, source_uri, usb_devices
from jetson_worktime.settings import SettingsConflict, SettingsStore

CONFIG = dict(image_size=[100, 100], roi_configured=True, regions={
    'station': [[0, 0], [99, 0], [99, 99], [0, 99]],
    'seat': [[50, 20], [90, 20], [90, 80], [50, 80]]})


class CameraSourceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root/'configs').mkdir()
        (self.root/'configs/behavior.yaml').write_text(yaml.safe_dump(CONFIG))
        self.service = BehaviorService(self.root, start_workers=False)
        self.addCleanup(self.service.close)
        self.fallback = normalize_source(dict(type='rtsp', url='rtsp://admin:secret@old/stream', codec='h265'))
        self.candidate = dict(type='rtsp', url='rtsp://new/stream', username='user', password='private', codec='h264')
        self.factory = MagicMock()
        self.factory.return_value.read.return_value = (np.zeros((100, 100, 3), np.uint8), 1, 2)
        self.sources = CameraSources(self.service, self.fallback, self.factory)

    def test_first_launch_camera_status_without_a_source(self):
        root=Path(__file__).resolve().parents[1]
        handler=next(n for n in ast.parse((root/'scripts/preview.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        camera=next(n for n in handler.body if isinstance(n,ast.FunctionDef) and n.name=='camera')
        self.sources.fallback=None
        namespace=dict(state_lock=threading.RLock(),state={'timestamp':0,'status':'connecting','width':None,'height':None},
                       behavior=self.service,cameras=self.sources,time=time)
        exec(compile(ast.Module(body=[camera],type_ignores=[]),'camera_handler','exec'),namespace)
        result=namespace['camera'](None)
        self.assertFalse(result['configured'])
        self.assertEqual(result['status'],'unconfigured')
        self.assertEqual(result['source_type'],'unconfigured')

    def test_credentials_and_retention(self):
        self.assertNotIn('secret', str(public_source(self.fallback)))
        source = normalize_source(dict(type='rtsp', url='rtsp://old/stream', username='admin', password='', codec='h265'), self.fallback)
        self.assertEqual(source['password'], 'secret')
        source['url'] = 'rtsp://new/stream'
        source['password'] = ''
        self.assertEqual(normalize_source(source, self.fallback)['password'], '')
        self.assertIn('admin:secret@', source_uri(self.fallback))
        for value in ('http://host', 'rtsp://host:wrong/a', 'rtsp://host/\nsecret'):
            with self.assertRaises(ValueError) as caught:
                normalize_source(dict(type='rtsp', url=value))
            self.assertNotIn('secret', str(caught.exception))

    def test_test_does_not_switch_and_token_is_bound(self):
        result = self.sources.test(dict(expected_revision=0, camera_source=self.candidate))
        self.assertEqual(result['width'], 100)
        self.assertEqual(self.sources.current(), self.fallback)
        request = dict(expected_revision=0, camera_source={**self.candidate, 'codec':'h265'}, test_token=result['test_token'])
        with self.assertRaises(ValueError):
            self.sources.switch(request, {})
        request['camera_source'] = self.candidate
        self.sources.tokens[result['test_token']] = (self.candidate, 0, time.monotonic()-1)
        with self.assertRaises(ValueError):
            self.sources.switch(request, {})
        self.assertEqual(self.service.config['revision'], 0)

    def test_switch_finishes_once_invalidates_and_persists(self):
        now = time.monotonic()
        self.service.engine.observe(now, 'SEATED')
        self.service.engine.manual('start', now)
        self.service.flush()
        self.service.observations.publish({'observation_id':'old'}, b'old')
        old_reader = MagicMock()
        self.sources.reader = old_reader
        result = self.sources.test(dict(expected_revision=0, camera_source=self.candidate))
        request = dict(expected_revision=0, camera_source=self.candidate, test_token=result['test_token'])
        saved = self.sources.switch(request, {})
        self.assertEqual(saved['revision'], 1)
        self.assertFalse(saved['roi_configured'])
        self.assertIsNone(self.service.engine.current)
        self.assertEqual(len(self.service.engine.completed), 1)
        self.assertIsNone(self.service.observation_frame('old'))
        old_reader.close.assert_called_once()
        self.assertNotIn('private', str(saved))
        self.assertEqual(SettingsStore(self.service.store.path).snapshot()['camera_source'], self.candidate)
        self.assertEqual(self.service.store.path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(SettingsConflict):
            self.sources.switch(request, {})
        self.assertEqual(len(self.service.engine.completed), 1)
        with self.assertRaises(ValueError):
            self.service.action('start')

    def test_adopting_legacy_source_persists_then_repeat_is_noop(self):
        candidate = {**self.fallback, 'password':''}
        tested = self.sources.test(dict(expected_revision=0, camera_source=candidate))
        saved = self.sources.switch(dict(expected_revision=0, camera_source=candidate, test_token=tested['test_token']), {})
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(self.service.config['camera_source'], self.fallback)
        tested = self.sources.test(dict(expected_revision=1, camera_source=candidate))
        saved = self.sources.switch(dict(expected_revision=1, camera_source=candidate, test_token=tested['test_token']), {})
        self.assertEqual(saved['revision'], 1)

    def test_failed_candidate_or_persist_keeps_old_reader(self):
        old_reader = MagicMock()
        self.sources.reader = old_reader
        test = self.sources.test(dict(expected_revision=0, camera_source=self.candidate))
        request = dict(expected_revision=0, camera_source=self.candidate, test_token=test['test_token'])
        with patch('jetson_worktime.settings.os.replace', side_effect=OSError('full')):
            with self.assertRaises(OSError):
                self.sources.switch(request, {})
        self.assertIs(self.sources.reader, old_reader)
        old_reader.close.assert_not_called()
        self.assertEqual(self.service.config['revision'], 0)
        self.factory.return_value.read.side_effect = RuntimeError('private credentials')
        with self.assertRaises(ValueError) as caught:
            self.sources.switch(request, {})
        self.assertNotIn('private', str(caught.exception))
        self.assertIs(self.sources.reader, old_reader)

    def test_production_http_test_and_switch_routes(self):
        root = Path(__file__).resolve().parents[1]
        module = ast.parse((root/'scripts/preview.py').read_text())
        handler = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'Handler')
        state = dict(status='online', timestamp=time.monotonic(), sequence=1, width=100, height=100,
                     jpeg_width=100, jpeg_height=100, source_fps=20, stream_session_id='old',
                     receive_sequence=1, pts_ns='1')
        namespace = dict(BaseHTTPRequestHandler=BaseHTTPRequestHandler, json=json, time=time,
                         urlsplit=urlsplit, parse_qs=parse_qs, behavior=self.service,
                         cameras=self.sources, state=state, state_lock=threading.Lock(), ROOT=root,
                         SettingsConflict=SettingsConflict)
        from types import SimpleNamespace
        from jetson_worktime.studio_store import StudioError
        namespace['maintenance']=__import__('jetson_worktime.deployment',fromlist=['maintenance']).maintenance
        namespace['studio_http']=SimpleNamespace(handle=lambda *args:False)
        namespace['StudioError']=StudioError
        exec(compile(ast.Module(body=[handler], type_ignores=[]), 'preview.py', 'exec'), namespace)
        server = ThreadingHTTPServer(('127.0.0.1', 0), namespace['Handler'])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        def request(path, method='GET', payload=None):
            data = json.dumps(payload).encode() if payload is not None else None
            req = Request(base+path, data=data, method=method, headers={'Content-Type':'application/json'})
            try:
                with urlopen(req, timeout=5) as response:
                    return response.status, json.load(response)
            except HTTPError as error:
                return error.code, json.load(error)
        try:
            status, config = request('/api/v1/settings')
            self.assertEqual(status, 200)
            self.assertNotIn('secret', json.dumps(config))
            payload = dict(expected_revision=0, camera_source=self.candidate)
            status, _ = request('/api/v1/settings', 'PUT', dict(**payload, test_token='bad'))
            self.assertEqual(status, 400)
            status, tested = request('/api/v1/camera/test', 'POST', payload)
            self.assertEqual(status, 200)
            status, saved = request('/api/v1/settings', 'PUT', dict(**payload, test_token=tested['test_token']))
            self.assertEqual(status, 200)
            self.assertEqual(saved['revision'], 1)
            self.assertFalse(saved['roi_configured'])
            self.assertEqual(saved['camera_source']['url'], self.candidate['url'])
            self.assertNotIn('private', json.dumps(saved))
            self.assertIsNone(saved['camera']['stream_session_id'])
            self.assertEqual(self.service.frame_ref, {})
            status, _ = request('/api/v1/camera/test', 'POST', payload)
            self.assertEqual(status, 409)
            self.assertEqual(saved['detection'], dict(person_confidence=.1, keypoint_confidence=.4))
            invalid = dict(expected_revision=1, detection=dict(person_confidence=.09, keypoint_confidence=.4))
            status, _ = request('/api/v1/settings', 'PUT', invalid)
            self.assertEqual(status, 400)
            thresholds = dict(person_confidence=.6, keypoint_confidence=.7)
            update = dict(expected_revision=1, detection=thresholds)
            status, saved = request('/api/v1/settings', 'PUT', update)
            self.assertEqual(status, 200)
            self.assertEqual(saved['revision'], 2)
            self.assertEqual(saved['detection'], thresholds)
            self.assertNotIn('privacy_keypoint_confidence', saved)
            status, _ = request('/api/v1/settings', 'PUT', update)
            self.assertEqual(status, 409)
            status, saved = request('/api/v1/settings', 'PUT', dict(update, expected_revision=2))
            self.assertEqual(status, 200)
            self.assertEqual(saved['revision'], 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_enumeration_filters_formats_and_uses_stable_identity(self):
        path = MagicMock()
        path.resolve.return_value = Path('/dev/video0')
        path.__str__.return_value = '/dev/video0'
        stable = MagicMock()
        stable.resolve.return_value = Path('/dev/video0')
        stable.__str__.return_value = '/dev/v4l/by-id/camera'
        def glob(root, pattern):
            return [stable] if str(root).endswith('by-id') else [path]
        def ioctl(fd, operation, buffer, mutate):
            if operation == 0x80685600:
                buffer[16:20] = b'Test'
                struct.pack_into('II', buffer, 84, 1, 0)
            else:
                index = struct.unpack_from('I', buffer)[0]
                if index == 2:
                    raise OSError()
                buffer[44:48] = [b'YUYV', b'MJPG'][index]
        with patch('pathlib.Path.glob', glob), patch('os.open', return_value=3), patch('os.close') as close, patch('fcntl.ioctl', side_effect=ioctl):
            result = usb_devices()['devices']
        self.assertEqual(result, [dict(device='/dev/v4l/by-id/camera', name='Test', formats=['yuyv','mjpeg'])])
        close.assert_called_once_with(3)

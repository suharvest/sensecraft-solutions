from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import yaml
from jetson_worktime.behavior import SessionEngine
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.runtime_quality import ObservationWriter, RuntimeQuality
from jetson_worktime.streaming import VideoTransport
from test_ownership import CONFIG, person


class StartPreviewTests(unittest.TestCase):
    def service(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root/'configs').mkdir()
        (root/'configs/behavior.yaml').write_text(yaml.safe_dump(CONFIG))
        service = BehaviorService(root, start_workers=False)
        self.addCleanup(service.close)
        service.connected = True
        service.source_session = 'stream'
        service.source_size = [200, 200]
        return service

    def packet(self, service):
        t = time.monotonic_ns()
        return dict(config={**deepcopy(service.config), 'regions_confirmed':True},
            protected=np.zeros((200,200,3), np.uint8), persons=[], accepted=True,
            pts=None, received=t, started=t, completed=t, width=200, height=200,
            meta=dict(session_id='stream',receive_sequence=1), label='MISSING',
            reason='test', ownership={}, camera_changed=False)

    def test_blocker_and_same_track_confirmation_are_explicit(self):
        service = self.service()
        service.config["roi_configured"] = True
        service.camera_changed = True
        result = service.snapshot()['start_confirmation']
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertEqual(result['blocker_code'], 'reason.moved')
        self.assertFalse(service.engine.current)
        e = SessionEngine(CONFIG)
        for t in range(6):
            e.observe_persons(t,[person(1)],200,200)
        self.assertEqual(e.snapshot(5)['start_confirmation']['elapsed_seconds'],5)
        e.observe_persons(6,[person(2)],200,200)
        self.assertEqual(e.snapshot(6)['start_confirmation']['last_reset']['reason_code'],'startup.trackChanged')
        for t in range(7,17):
            e.observe_persons(t,[person(2)],200,200)
        self.assertTrue(e.snapshot(16)['active'])

    def test_slow_encoding_does_not_hold_service_lock_and_old_policy_cannot_publish(self):
        service = self.service()
        entered, release = threading.Event(), threading.Event()
        errors = []
        def encode(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('test timed out')
            return {'zh-CN':b'zh','en':b'en'}
        def publish():
            try: service._publish_media(self.packet(service))
            except Exception as e: errors.append(e)
        with patch('jetson_worktime.behavior_service.encode_overlays',side_effect=encode):
            thread = threading.Thread(target=publish)
            thread.start()
            self.assertTrue(entered.wait(1))
            acquired = service.lock.acquire(timeout=.2)
            self.assertTrue(acquired)
            if acquired: service.lock.release()
            service.apply_settings(dict(expected_revision=0, privacy={'enabled':False}), {})
            release.set()
            thread.join(timeout=2)
        self.assertFalse(errors)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(service.media)
        self.assertFalse(service.observations.entries)

    def test_writer_drains_in_order_and_reports_disk_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'rows.jsonl'
            writer = ObservationWriter(p.open('w'), RuntimeQuality())
            for n in range(40): writer.submit({'n':n})
            self.assertTrue(writer.close())
            self.assertEqual([json.loads(l)['n'] for l in p.read_text().splitlines()],list(range(40)))
        class Broken:
            def write(self, data): raise OSError('disk full')
            def close(self): pass
        writer = ObservationWriter(Broken(), RuntimeQuality())
        writer.submit({})
        writer.queue.join()
        with self.assertRaises(OSError): writer.submit({})
        self.assertTrue(writer.close())

    def test_quality_is_bounded_but_total_stalls_remain_counted(self):
        q = RuntimeQuality(3)
        for n in range(6): q.sample('video_interval_ms',600 if n==0 else 100)
        s = q.snapshot()['video_interval_ms']
        self.assertEqual((s['count'],s['window_count'],s['over_500ms']),(6,3,1))

    def test_pacer_defers_a_new_frame_instead_of_dropping_it(self):
        value = VideoTransport.__new__(VideoTransport)
        value.condition = threading.Condition(threading.RLock())
        value.stop = threading.Event()
        value.epoch = 0
        value.latest = None
        value.sessions = {'viewer':dict(epoch=0,locale='en',profile='local',created=time.monotonic(),path='/viewer')}
        value.pending, value.socket_profiles, value.jpegs = {}, {}, {}
        value.process = SimpleNamespace(poll=lambda:None,terminate=lambda:None,wait=lambda timeout:None)
        value.quality = RuntimeQuality()
        value.delete_remote = lambda path:None
        sent, first = [], threading.Event()
        def write(image, received, *metadata):
            sent.append((received,time.monotonic()))
            first.set()
            if len(sent)==2: value.stop.set()
        value.publishers = {('en','local'):SimpleNamespace(write=write, close=lambda:None)}
        config = dict(max_observation_age=1.5,revision=0,privacy={'enabled':True})
        frame = np.zeros((100,100,3),np.uint8)
        received = time.monotonic_ns()
        value.submit(frame,[],config,True,True,received)
        with patch('jetson_worktime.overlay.draw_overlay'):
            thread = threading.Thread(target=value.run)
            thread.start()
            try:
                self.assertTrue(first.wait(1))
                value.submit(frame,[],config,True,True,received+1)
                thread.join(timeout=1)
            finally:
                value.stop.set()
                thread.join(timeout=1)
        self.assertEqual([n for n,t in sent],[received,received+1])
        self.assertGreaterEqual(sent[1][1]-sent[0][1],1/20-.005)


if __name__ == '__main__':
    unittest.main()

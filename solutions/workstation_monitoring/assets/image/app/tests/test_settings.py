from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import yaml

from jetson_worktime.settings import SettingsStore, SettingsConflict, validate_regions
from jetson_worktime.behavior_service import BehaviorService

CONFIG = dict(image_size=[100, 100], regions={
    'station': [[0, 0], [99, 0], [99, 99], [0, 99]],
    'seat': [[50, 20], [90, 20], [90, 80], [50, 80]]})


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root/'configs').mkdir()
        self.path = self.root/'configs/behavior.yaml'
        self.path.write_text(yaml.safe_dump(CONFIG))
        self.store = SettingsStore(self.path)

    def test_legacy_defaults_and_restart(self):
        config = self.store.snapshot()
        self.assertTrue(config['privacy']['enabled'])
        self.assertEqual(config['revision'], 0)
        self.assertFalse(config['display']['keypoints'])
        updated, changed, detection = self.store.commit(dict(expected_revision=0, privacy={'enabled': False}))
        self.assertTrue(changed)
        self.assertFalse(detection)
        self.assertEqual(SettingsStore(self.path).snapshot(), updated)

    def test_existing_display_choices_survive_new_visual_defaults(self):
        config = {**CONFIG, 'display':dict(boxes=True, regions=True, keypoints=True)}
        self.path.write_text(yaml.safe_dump(config))
        self.assertTrue(self.store.snapshot()['display']['keypoints'])

    def test_invalid_values_and_conflict(self):
        for change in ({'privacy': {'enabled': 1}}, {'display': {'boxes': True}},
                       {'timing': {}}, {'expected_revision': True}, {'unknown': 1}):
            with self.assertRaises(ValueError):
                self.store.commit(dict(expected_revision=0, **{k:v for k,v in change.items() if k!='expected_revision'}) if 'expected_revision' not in change else change)
        self.store.commit(dict(expected_revision=0, privacy={'enabled': False}))
        with self.assertRaises(SettingsConflict):
            self.store.commit(dict(expected_revision=0, privacy={'enabled': True}))

    def test_atomic_write_failure_preserves_file_and_cleans_temporary(self):
        before = self.path.read_bytes()
        with patch('jetson_worktime.settings.os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.store.commit(dict(expected_revision=0, privacy={'enabled': False}))
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse(list(self.path.parent.glob('.behavior-*.tmp')))

    def test_two_concurrent_writers_one_wins(self):
        results = []
        def save():
            try:
                SettingsStore(self.path).commit(dict(expected_revision=0, privacy={'enabled': False}))
                results.append('ok')
            except SettingsConflict:
                results.append('conflict')
        threads = [threading.Thread(target=save) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ['ok', 'conflict'])

    def test_noop_keeps_revision(self):
        result, changed, detection = self.store.commit(dict(expected_revision=0, privacy={'enabled': True}))
        self.assertEqual(result['revision'], 0)
        self.assertFalse(changed or detection)

    def test_region_validation(self):
        validate_regions(CONFIG['regions'], CONFIG['image_size'])
        for polygon in ([[0,0],[99,99],[0,99],[99,0]], [[0,0],[1,1],[2,2]], [[0,0],[101,0],[0,99]], [[0,0],[99,0],[0,0]]):
            regions = deepcopy(CONFIG['regions'])
            regions['seat'] = polygon
            with self.assertRaises(ValueError):
                validate_regions(regions, [100,100])
        regions = dict(station=[[0,0],[99,0],[99,99],[60,99],[60,30],[40,30],[40,99],[0,99]],
                       seat=[[20,60],[80,60],[80,80],[20,80]])
        with self.assertRaises(ValueError):
            validate_regions(regions, [100,100])

    def service(self):
        service = BehaviorService(self.root, start_workers=False)
        self.addCleanup(service.close)
        now = time.monotonic()
        service.engine.observe(now, 'SEATED')
        service.engine.manual('start', now)
        service.flush()
        return service

    def test_display_and_privacy_keep_session_and_invalidate_old_frames(self):
        service = self.service()
        session = service.engine.current['session_id']
        service.observations.publish({'observation_id':'old'}, b'old')
        service.apply_settings(dict(expected_revision=0, privacy={'enabled':False}), {})
        self.assertEqual(service.engine.current['session_id'], session)
        self.assertIsNone(service.observation_frame('old'))
        self.assertEqual(service.settings()['revision'], 1)

    def test_timing_ends_once_and_restarts_confirmation(self):
        service = self.service()
        timing = service.settings()['timing']
        timing['start_seconds'] = 5
        request = dict(expected_revision=0, timing=timing)
        service.apply_settings(request, {})
        self.assertIsNone(service.engine.current)
        self.assertEqual(len(service.engine.completed), 1)
        self.assertEqual(service.engine.completed[0]['end_reason'], 'configuration_changed')
        request['expected_revision'] = 1
        service.apply_settings(request, {})
        self.assertEqual(len(service.engine.completed), 1)
        service.engine.observe(time.monotonic(), 'SEATED')
        self.assertEqual(service.engine.snapshot(time.monotonic())['state'], 'START_PENDING')
        events = [json.loads(line) for line in (service.output/'events.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['event']=='session_end' for e in events), 1)

    def test_stale_roi_and_save_failure_keep_active_session(self):
        service = self.service()
        with self.assertRaises(SettingsConflict):
            service.apply_settings(dict(expected_revision=0, regions=CONFIG['regions'], image_size=[100,100]),
                                   dict(status='reconnecting'))
        self.assertIsNotNone(service.engine.current)
        with self.assertRaises(ValueError):
            service.apply_settings(dict(expected_revision=0, regions=CONFIG['regions'], reference_frame=[]), {})
        timing = service.settings()['timing']
        timing['start_seconds'] = 7
        with patch('jetson_worktime.settings.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                service.apply_settings(dict(expected_revision=0, timing=timing), {})
        self.assertIsNotNone(service.engine.current)
        self.assertEqual(service.config['revision'], 0)

    def test_media_publication_is_frame_matched_with_either_privacy_setting(self):
        import numpy as np
        from types import SimpleNamespace
        from jetson_worktime import runtime
        for enabled in (True, False):
            service = BehaviorService(self.root, start_workers=False)
            try:
                service.apply_settings(dict(expected_revision=service.config['revision'], privacy={'enabled':enabled}), {})
                frame = np.zeros((100,100,3),np.uint8)
                received = time.monotonic_ns()
                meta = dict(session_id='matched-stream',receive_sequence=7)
                service.submit(frame,123,received,meta)
                result = SimpleNamespace(boxes=SimpleNamespace(conf=SimpleNamespace(cpu=lambda:SimpleNamespace(tolist=lambda:[]))))
                model = SimpleNamespace(predict=lambda *a,**k:None,predictor=None, track=lambda *a,**k:[result],
                    model=SimpleNamespace(parameters=lambda:iter([SimpleNamespace(device=SimpleNamespace(type='cuda'))])))
                fake_torch = SimpleNamespace(set_num_threads=lambda n:None,cuda=SimpleNamespace(synchronize=lambda:None,empty_cache=lambda:None))
                fake_yolo = SimpleNamespace(YOLO=lambda *a:model)
                def encode(*args, **kwargs):
                    return {'zh-CN':b'zh','en':b'en'}
                with patch.dict('sys.modules',{'torch':fake_torch,'ultralytics':fake_yolo}), \
                        patch.object(runtime,'extract_persons',return_value=[]), \
                        patch.object(service,'guard'), patch.object(service.studio,'model',return_value={'path':'test-model.pt'}), \
                        patch('jetson_worktime.behavior_service.encode_overlays',side_effect=encode):
                    original_publish = service.observations.publish
                    def publish(*args):
                        original_publish(*args)
                        service.stop.set()
                    with patch.object(service.observations, 'publish', side_effect=publish):
                        media = threading.Thread(target=service.media_worker)
                        media.start()
                        service._inference_loop()
                        media.join(timeout=3)
                self.assertEqual(service.media['meta'],meta)
                self.assertEqual(service.media['received'],received)
                self.assertEqual(service.media['privacy_applied'],enabled)
                self.assertEqual(service.media['revision'],service.config['revision'])
                self.assertEqual(service.observation_snapshot()['observation']['frame']['receive_sequence'],7)
            finally:
                service.stop.clear()
                service.close()

    def test_roi_save_accepts_current_camera_and_marks_configured(self):
        service = self.service()
        service.connected = True
        service.source_session = 's'
        service.source_size = [100,100]
        camera = dict(status='online', age_ms=10, width=100, height=100, stream_session_id='s')
        request = dict(expected_revision=0, regions=CONFIG['regions'], image_size=[100,100],
                       reference_frame=dict(stream_session_id='s', image_size=[100,100]))
        result = service.apply_settings(request, camera)
        self.assertTrue(result['roi_configured'])
        self.assertIsNone(service.engine.current)
        service.camera_changed = True
        request['expected_revision'] = result['revision']
        with self.assertRaises(SettingsConflict):
            service.apply_settings(request, camera)
        request['reference_frame']['camera_changed'] = True
        reconfirmed = service.apply_settings(request, camera)
        self.assertFalse(service.camera_changed)
        self.assertEqual(reconfirmed['revision'], result['revision']+1)


if __name__ == '__main__':
    unittest.main()

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import yaml

from jetson_worktime.behavior import classify
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.detection import DETECTION_DEFAULTS, detection_settings, filter_persons
from jetson_worktime.media import protect_frame
from jetson_worktime.settings import SettingsStore, SettingsConflict

CONFIG = dict(image_size=[200,200], regions={
    'station':[[0,0],[199,0],[199,199],[0,199]],
    'seat':[[20,20],[110,20],[110,110],[20,110]]})


def person(score=.6, keypoint_score=.8):
    positions = [[60,35],[55,30],[65,30],[45,35],[75,35],[40,70],[100,70]]
    points = [dict(x=x,y=y,confidence=keypoint_score) for x,y in positions]
    points += [dict(x=None,y=None,confidence=0) for _ in range(10)]
    return dict(bbox_xyxy=[20,10,140,190],confidence=score,keypoints=points,person_track_id=1,valid=True)


class DetectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root/'configs').mkdir()
        self.path = self.root/'configs/behavior.yaml'
        self.path.write_text(yaml.safe_dump(CONFIG))
        self.store = SettingsStore(self.path)

    def service(self):
        service = BehaviorService(self.root, start_workers=False)
        self.addCleanup(service.close)
        return service

    def test_legacy_defaults_and_independent_privacy_threshold_survive_restart(self):
        self.path.write_text(yaml.safe_dump({**CONFIG,'keypoint_confidence':.6}))
        before = self.path.read_bytes()
        initial = self.store.snapshot()
        self.assertEqual(detection_settings(initial),dict(person_confidence=.1,keypoint_confidence=.6))
        self.assertEqual(initial['privacy_keypoint_confidence'],.6)
        self.assertEqual(self.path.read_bytes(),before)
        updated,changed,detection = self.store.commit(dict(expected_revision=0,detection=dict(person_confidence=.8,keypoint_confidence=.95)))
        self.assertTrue(changed and detection)
        self.assertEqual(updated['privacy_keypoint_confidence'],.6)
        self.assertEqual(SettingsStore(self.path).snapshot(),updated)
        self.assertEqual(SettingsStore.public(updated)['detection_defaults'],DETECTION_DEFAULTS)
        self.assertNotIn('privacy_keypoint_confidence',SettingsStore.public(updated))

    def test_legacy_subfloor_keypoints_preserve_effective_behavior(self):
        self.path.write_text(yaml.safe_dump({**CONFIG,'keypoint_confidence':.15}))
        config = self.store.snapshot()
        self.assertEqual(config['keypoint_confidence'],.25)
        self.assertEqual(config['privacy_keypoint_confidence'],.15)

    def test_validation_bounds_booleans_nonfinite_and_partial_payloads(self):
        invalid = [dict(person_confidence=.09,keypoint_confidence=.4),
                   dict(person_confidence=1.01,keypoint_confidence=.4),
                   dict(person_confidence=.1,keypoint_confidence=.24),
                   dict(person_confidence=.1,keypoint_confidence=1.01),
                   dict(person_confidence=True,keypoint_confidence=.4),
                   dict(person_confidence=float('nan'),keypoint_confidence=.4),
                   dict(person_confidence=.1,keypoint_confidence=float('inf')),
                   dict(person_confidence=.1),dict(person_confidence=.1,keypoint_confidence=.4,unknown=1),None]
        before = self.path.read_bytes()
        for detection in invalid:
            with self.subTest(detection=detection), self.assertRaises(ValueError):
                self.store.commit(dict(expected_revision=0,detection=detection))
            self.assertEqual(self.path.read_bytes(),before)
        config,changed,_ = self.store.commit(dict(expected_revision=0,detection=dict(person_confidence=1,keypoint_confidence=1)))
        self.assertTrue(changed)
        config,_,_ = self.store.commit(dict(expected_revision=config['revision'],detection=dict(person_confidence=.1,keypoint_confidence=.25)))
        self.assertEqual(detection_settings(config),dict(person_confidence=.1,keypoint_confidence=.25))

    def test_score_filter_is_inclusive_and_rejects_unknown_scores(self):
        people = [person(score) for score in (.49,.5,.51)]
        selected = filter_persons(people,dict(person_confidence=.5))
        self.assertEqual([p['confidence'] for p in selected],[.5,.51])
        self.assertEqual(filter_persons([person(None),person(True),person(float('nan'))],{}),[])

    def test_keypoint_threshold_affects_decisions_and_privacy_is_independent(self):
        self.path.write_text(yaml.safe_dump({**CONFIG,'keypoint_confidence':.6}))
        old = self.store.snapshot()
        frame = np.random.default_rng(8).integers(0,255,(200,200,3),dtype=np.uint8)
        people = [person()]
        protected = protect_frame(frame,people,old)
        self.assertEqual(classify(filter_persons(deepcopy(people),old),200,200,old)[0],'SEATED')
        new,_,_ = self.store.commit(dict(expected_revision=0,detection=dict(person_confidence=.9,keypoint_confidence=.95)))
        self.assertEqual(classify(filter_persons(deepcopy(people),new),200,200,new)[0],'MISSING')
        self.assertTrue(np.array_equal(protect_frame(frame,people,new),protected))
        self.assertFalse(np.array_equal(protected,frame))
        new['person_confidence']=.1
        self.assertEqual(classify(filter_persons(deepcopy(people),new),200,200,new)[0],'UNKNOWN')

    def test_save_ends_once_invalidates_and_keeps_event_thresholds(self):
        service = self.service()
        now = time.monotonic()
        service.engine.observe(now,'SEATED')
        service.engine.manual('start',now)
        service.flush()
        service.observations.publish({'observation_id':'old'},b'old')
        service.frame_ref={'receive_sequence':1}
        service.latest=('old',)
        request=dict(expected_revision=0,detection=dict(person_confidence=.55,keypoint_confidence=.7))
        result=service.apply_settings(request,{})
        self.assertEqual(result['revision'],1)
        self.assertIsNone(service.engine.current)
        self.assertEqual(len(service.engine.completed),1)
        self.assertEqual(service.engine.completed[0]['end_reason'],'configuration_changed')
        self.assertIsNone(service.observation_frame('old'))
        self.assertEqual(service.frame_ref,{})
        self.assertIsNone(service.latest)
        request['expected_revision']=1
        self.assertEqual(service.apply_settings(request,{})['revision'],1)
        with self.assertRaises(SettingsConflict):
            service.apply_settings({**request,'expected_revision':0},{})
        events=[json.loads(row) for row in (service.output/'events.jsonl').read_text().splitlines()]
        ended=[e for e in events if e['event']=='session_end']
        self.assertEqual(len(ended),1)
        self.assertEqual(ended[0]['detection'],DETECTION_DEFAULTS)
        changed=next(e for e in events if e['event']=='configuration_changed')
        self.assertEqual(changed['detection'],request['detection'])
        service.engine.observe(time.monotonic(),'SEATED')
        self.assertEqual(service.snapshot()['state'],'START_PENDING')

    def test_failed_persistence_keeps_active_session_and_settings(self):
        service = self.service()
        now=time.monotonic()
        service.engine.observe(now,'SEATED')
        service.engine.manual('start',now)
        original=service.engine.current['session_id']
        with patch('jetson_worktime.settings.os.replace',side_effect=OSError('full')):
            with self.assertRaises(OSError):
                service.apply_settings(dict(expected_revision=0,detection=dict(person_confidence=.8,keypoint_confidence=.9)),{})
        self.assertEqual(service.config['revision'],0)
        self.assertEqual(service.engine.current['session_id'],original)

    def test_worker_resets_tracker_filters_business_and_protects_all_candidates(self):
        from jetson_worktime import runtime
        service = self.service()
        tracker = MagicMock()
        track = MagicMock(return_value=[SimpleNamespace()])
        model = SimpleNamespace(predict=lambda *a,**k:None,predictor=SimpleNamespace(trackers=[tracker]),track=track,
            model=SimpleNamespace(predict=lambda *a,**k:None,parameters=lambda:iter([SimpleNamespace(device=SimpleNamespace(type='cuda'))])))
        fake_torch=SimpleNamespace(set_num_threads=lambda n:None,cuda=SimpleNamespace(synchronize=lambda:None,empty_cache=lambda:None))
        fake_yolo=SimpleNamespace(YOLO=lambda *args:model)
        first=threading.Event()
        errors=[]
        published=[]
        candidates=[]
        def encode(image,people,config,**kwargs):
            published.append((config['revision'],len(people)))
            if len(published)==1:
                first.set()
            return {'zh-CN':b'zh','en':b'en'}
        def protect(image,people,config):
            candidates.append(len(people))
            return protect_frame(image,people,config)
        frame=np.zeros((200,200,3),np.uint8)
        service.submit(frame,1,time.monotonic_ns(),dict(session_id='stream',receive_sequence=1))
        def configure():
            try:
                if not first.wait(5):
                    raise TimeoutError('first frame missing')
                service.apply_settings(dict(expected_revision=0,detection=dict(person_confidence=.9,keypoint_confidence=.95)),{})
                service.submit(frame,2,time.monotonic_ns(),dict(session_id='stream',receive_sequence=2))
            except Exception as error:
                errors.append(error)
                service.stop.set()
                with service.condition:
                    service.condition.notify_all()
        thread=threading.Thread(target=configure,daemon=True)
        with patch.dict('sys.modules',{'torch':fake_torch,'ultralytics':fake_yolo}), \
                patch.object(runtime,'extract_persons',side_effect=lambda result:[person()]), \
                patch.object(service,'guard'), patch.object(service.studio,'model',return_value={'path':'test-model.pt'}), \
                patch('jetson_worktime.behavior_service.protect_frame',side_effect=protect), \
                patch('jetson_worktime.behavior_service.encode_overlays',side_effect=encode):
            # Invalidation replaces the cache, so intercept the class method instead.
            from jetson_worktime.api import ObservationCache
            original_class_publish = ObservationCache.publish
            def class_publish(cache, *args):
                original_class_publish(cache, *args)
                if len(published) == 2:
                    service.stop.set()
            publisher_patch = patch.object(ObservationCache, 'publish', class_publish)
            publisher_patch.start()
            media = threading.Thread(target=service.media_worker)
            media.start()
            thread.start()
            try:
                service._inference_loop()
            finally:
                thread.join(timeout=6)
                media.join(timeout=3)
                publisher_patch.stop()
                service.stop.clear()
        self.assertFalse(errors)
        self.assertEqual(published,[(0,1),(1,0)])
        self.assertEqual(candidates,[1,1])
        self.assertEqual(tracker.reset.call_count,2)
        self.assertEqual([c.kwargs['conf'] for c in track.call_args_list],[.1,.1])
        observation=service.observation_snapshot()['observation']
        self.assertEqual(observation['detection'],dict(person_confidence=.9,keypoint_confidence=.95))
        self.assertEqual(observation['persons'],[])
        self.assertEqual(service.media['meta']['receive_sequence'],2)

    def test_extract_person_scores_and_coordinate_floor(self):
        from jetson_worktime.runtime import extract_persons
        def tensor(values):
            return SimpleNamespace(cpu=lambda:SimpleNamespace(tolist=lambda:values))
        result=SimpleNamespace(boxes=SimpleNamespace(xyxy=tensor([[1,2,30,40]]),conf=tensor([.65]),id=None),
                               keypoints=SimpleNamespace(data=tensor([[[1,2,.24],[3,4,.25]]])))
        extracted=extract_persons(result)
        self.assertEqual(extracted[0]['confidence'],.65)
        self.assertIsNone(extracted[0]['keypoints'][0]['x'])
        self.assertEqual(extracted[0]['keypoints'][1]['x'],3)


if __name__=='__main__':
    unittest.main()

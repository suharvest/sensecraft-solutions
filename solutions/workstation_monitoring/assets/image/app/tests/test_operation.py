"""Business controls must not stop protected video or erase historical records."""
from copy import deepcopy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
import yaml
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.settings import SettingsStore, SettingsConflict
from jetson_worktime.materials import validate_materials, material_behavior_changed
from jetson_worktime.overlay import draw_overlay, draw_material_objects

class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'configs').mkdir()
        self.path=self.root/'configs/behavior.yaml'
        self.path.write_text(yaml.safe_dump(dict(image_size=[200,200],regions={'station':[[0,0],[199,0],[199,199],[0,199]],'seat':[[20,20],[110,20],[110,110],[20,110]]})))
        self.service=BehaviorService(self.root,start_workers=False);self.addCleanup(self.service.close)
    def start(self):
        now=time.monotonic()-2
        self.service.engine.observe(now,'SEATED');self.service.engine.manual('start',now)
        return self.service.engine.current['session_id']
    def test_defaults_validation_and_restart(self):
        s=self.service
        self.assertTrue(s.settings()['operation']['detection_enabled'])
        self.assertTrue(s.settings()['materials']['show_confidence'])
        for value in [None,{}, {'detection_enabled':1},{'detection_enabled':False,'x':1}]:
            with self.assertRaises(ValueError):s.apply_settings(dict(expected_revision=0,operation=value),{})
        s.apply_settings(dict(expected_revision=0,operation={'detection_enabled':False}),{})
        self.assertFalse(SettingsStore(self.path).snapshot()['operation']['detection_enabled'])
        self.assertEqual(s.snapshot()['operating_mode'],'preview')
    def test_disable_settles_once_and_preserves_history(self):
        s=self.service;ident=self.start()
        s.apply_settings(dict(expected_revision=0,operation={'detection_enabled':False}),{})
        result=s.snapshot();self.assertFalse(result['active']);self.assertEqual(result['session_id'],ident)
        self.assertEqual(s.engine.completed[-1]['end_reason'],'detection_disabled')
        before=result['work_seconds'];s.snapshot();self.assertEqual(s.snapshot()['work_seconds'],before)
        s.apply_settings(dict(expected_revision=1,operation={'detection_enabled':False}),{})
        self.assertEqual(len(s.engine.completed),1)
        s.apply_settings(dict(expected_revision=1,operation={'detection_enabled':True}),{})
        self.assertIsNone(s.engine.seat_since);self.assertFalse(s.snapshot()['active'])
        self.assertEqual(sum(e['kind']=='session_end' for e in s.studio.store.events(ident)),1)
    def test_reset_keeps_history_and_receipts_ignore_new_sessions(self):
        s=self.service;ident=self.start();request={'expected_revision':0,'token':'reset-token-one'}
        old_epoch=s.runtime_epoch
        result=s.action('reset_display',request)
        self.assertEqual([result[k] for k in ['work_seconds','rest_seconds','pending_seconds','unknown_seconds']],[0,0,0,0])
        self.assertIsNone(result['session_id']);self.assertEqual(s.engine.completed[-1]['session_id'],ident)
        self.assertEqual(s.engine.completed[-1]['end_reason'],'manual_reset');self.assertGreater(s.runtime_epoch,old_epoch)
        next_id=self.start();s.action('reset_display',request);self.assertEqual(s.engine.current['session_id'],next_id)
        self.assertEqual(len([e for e in s.studio.store.events(ident) if e['kind']=='session_end']),1)
        self.assertEqual(s.studio.store.list('display_control')[0]['token'],request['token'])
    def test_failed_reset_leaves_live_session_and_display_intact(self):
        s=self.service;ident=self.start()
        with patch.object(s.studio.store,'put',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):s.action('reset_display',{'expected_revision':0,'token':'reset-fail-token'})
        self.assertEqual(s.engine.current['session_id'],ident);self.assertIsNone(s.display_reset)
        self.assertEqual(s.studio.store.events(ident),[])
        with self.assertRaises(SettingsConflict):s.action('reset_display',{'expected_revision':9,'token':'reset-conflict-token'})
    def test_reset_disabled_stays_disabled_and_reloads_marker(self):
        s=self.service;s.apply_settings({'expected_revision':0,'operation':{'detection_enabled':False}}, {})
        s.action('reset_display',{'expected_revision':1,'token':'reset-disabled-token'})
        second=BehaviorService(self.root,start_workers=False);self.addCleanup(second.close)
        self.assertEqual(second.snapshot()['operating_mode'],'preview');self.assertEqual(second.display_reset['token'],'reset-disabled-token')
    def test_training_rejects_controls(self):
        with patch.object(self.service.studio,'active_job',return_value={'id':'job'}):
            with self.assertRaises(ValueError):self.service.action('reset_display',{'expected_revision':0,'token':'training-reset-token'})
            with self.assertRaises(ValueError):self.service.apply_settings({'expected_revision':0,'operation':{'detection_enabled':False}}, {})
    def test_preview_publishes_no_business_observation_and_rejects_old_epoch(self):
        s=self.service;s.apply_settings({'expected_revision':0,'operation':{'detection_enabled':False}}, {})
        image=np.full((200,200,3),120,np.uint8);meta={'session_id':'camera','receive_sequence':1}
        s.submit(image,0,time.monotonic_ns(),meta);s.transport=Mock()
        with patch.object(s,'guard'):
            s._preview_frame(image,0,time.monotonic_ns(),meta,s.config,s.runtime_epoch)
        self.assertFalse(s.engine.current);self.assertIsNotNone(s.full_frame)
        self.assertFalse(s.media_latest['accepted']);self.assertEqual(s.media_latest['persons'],[])
        s.transport.submit.assert_called_once();s.transport.reset_mock();s.runtime_epoch+=1
        s._preview_frame(image,0,time.monotonic_ns(),meta,s.config,s.runtime_epoch-1)
        s.transport.submit.assert_not_called();s.transport=None
    def test_preview_without_privacy_does_not_load_any_model(self):
        s=self.service;s.apply_settings({'expected_revision':0,'operation':{'detection_enabled':False},'privacy':{'enabled':False}}, {})
        image=np.zeros((200,200,3),np.uint8);meta={'session_id':'camera','receive_sequence':1}
        s.submit(image,0,time.monotonic_ns(),meta)
        yolo=Mock(side_effect=AssertionError('model loading in raw preview'))
        with patch.object(s,'_preview_frame',side_effect=lambda *a:s.stop.set()):
            s._run_models(SimpleNamespace(),None,yolo,None,None)
        s.stop.clear();yolo.assert_not_called()
    def test_confidence_display_is_presentation_only(self):
        old=deepcopy(self.service.config['materials']);legacy=deepcopy(old);legacy.pop('show_confidence')
        self.assertTrue(validate_materials(legacy,[200,200])['show_confidence'])
        new={**old,'show_confidence':False};self.assertFalse(material_behavior_changed(old,new))
        ident=self.start()
        with patch.object(self.service.studio,'validate_selection'):
            self.service.apply_settings({'expected_revision':0,'materials':new},{})
        self.assertEqual(self.service.engine.current['session_id'],ident)
    def test_preview_overlay_never_draws_anything(self):
        config=deepcopy(self.service.config);config['operation']['detection_enabled']=False
        image=np.full((200,200,3),100,np.uint8);before=image.copy();draw_overlay(image,[],config)
        np.testing.assert_array_equal(before,image)
    def test_material_confidence_label_respects_setting(self):
        config=deepcopy(self.service.config);config['materials']['show_confidence']=False
        config['_material_status']={'available':True,'class_names':{'2':'packed'},'detections':[{'class_id':2,'role':'count','confidence':.876,'bbox_xyxy':[20,20,80,80]}]}
        with patch('jetson_worktime.overlay._material_sprite',return_value={'width':30,'height':15}) as sprite:
            draw_material_objects(np.zeros((200,200,3),np.uint8),config,'en');self.assertEqual(sprite.call_args.args[0],'packed')
            config['materials']['show_confidence']=True
            draw_material_objects(np.zeros((200,200,3),np.uint8),config,'en');self.assertEqual(sprite.call_args.args[0],'packed 0.88')

    def test_preview_keeps_privacy_detection_without_business_inference(self):
        import gc
        s=self.service;s.apply_settings({'expected_revision':0,'operation':{'detection_enabled':False}}, {})
        frame=np.full((200,200,3),100,np.uint8);protected=np.zeros_like(frame)
        s.submit(frame,0,time.monotonic_ns(),{'session_id':'camera','receive_sequence':1})
        model=SimpleNamespace(predict=Mock(),predictor=None,track=Mock(return_value=[object()]),
            model=SimpleNamespace(parameters=lambda:iter([SimpleNamespace(device=SimpleNamespace(type='cuda'))])))
        torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None,empty_cache=lambda:None))
        extract=Mock(return_value=[{'candidate':'privacy only'}])
        delivered=[]
        def publish(image,*args):delivered.append(image);s.stop.set()
        with patch.object(s.studio,'model',return_value={'path':'person.pt'}), \
             patch('jetson_worktime.behavior_service.protect_frame',return_value=protected) as protect, \
             patch.object(s,'_preview_frame',side_effect=publish):
            s._run_models(torch,None,lambda path:model,extract,gc)
        s.stop.clear();protect.assert_called_once();self.assertEqual(protect.call_args.args[1],[{'candidate':'privacy only'}])
        self.assertIs(delivered[0],protected);self.assertFalse(s.engine.current);self.assertEqual(s.material_counter.last_time,None)

    def test_reset_sequence_does_not_depend_on_wall_clock_order(self):
        s=self.service;self.start();s.action('reset_display',{'expected_revision':0,'token':'reset-clock-first'})
        self.start()
        with patch('jetson_worktime.behavior_service.time.time',return_value=1):
            s.action('reset_display',{'expected_revision':0,'token':'reset-clock-second'})
        self.assertIsNone(s.engine.current);self.assertEqual(s.display_reset['token'],'reset-clock-second')
        self.assertEqual(len(s.engine.completed),2)

    def test_live_capture_is_independent_of_business_worker(self):
        import threading
        s=self.service;s.config['privacy']['enabled']=False
        s.transport=Mock();s.error='inference_failed'
        frame=np.zeros((200,200,3),np.uint8);meta={'session_id':'live-camera','receive_sequence':1}
        worker=threading.Thread(target=s.live_worker);worker.start()
        try:
            s.submit(frame,0,time.monotonic_ns(),meta)
            deadline=time.monotonic()+1
            while not s.transport.submit.called and time.monotonic()<deadline: time.sleep(.005)
            self.assertTrue(s.transport.submit.called)
            self.assertEqual(s.transport.submit.call_args.args[1],[])
            self.assertFalse(s.engine.current);self.assertIsNone(s.material_counter.last_time)
        finally:
            s.stop.set()
            with s.live_condition:s.live_condition.notify_all()
            worker.join(1);s.stop.clear();s.transport=None
        self.assertFalse(worker.is_alive())

    def test_live_capture_never_bypasses_privacy_or_training(self):
        import threading
        s=self.service;s.transport=Mock();frame=np.zeros((200,200,3),np.uint8)
        for privacy,mode in [(True,'business'),(False,'training')]:
            s.config['privacy']['enabled']=privacy;s.operating_mode=mode
            worker=threading.Thread(target=s.live_worker);worker.start()
            s.submit(frame,0,time.monotonic_ns(),{'session_id':'camera','receive_sequence':1})
            time.sleep(.03);s.stop.set()
            with s.live_condition:s.live_condition.notify_all()
            worker.join(1);s.stop.clear();s.transport.submit.assert_not_called()
        s.transport=None

    def test_each_processed_frame_detects_products_and_updates_the_count_window(self):
        import gc
        s=self.service;s.config['privacy']['enabled']=False
        s.config['models']['material']='test-material'
        s.config['materials'].update(enabled=True,configured=True,sample_hz=2,
            regions={'pending':[[0,0],[90,0],[90,199],[0,199]],'completed':[[100,0],[199,0],[199,199],[100,199]]})
        frame=np.zeros((200,200,3),np.uint8)
        def values(value):return SimpleNamespace(cpu=lambda:SimpleNamespace(tolist=lambda:value))
        result=SimpleNamespace(boxes=SimpleNamespace(xyxy=values([[120,40,150,70]]),cls=values([0]),conf=values([.9])))
        model=SimpleNamespace(predict=Mock(),predictor=None,track=Mock(return_value=[object()]),
            model=SimpleNamespace(parameters=lambda:iter([SimpleNamespace(device=SimpleNamespace(type='cuda'))])))
        products=SimpleNamespace(predict=Mock(return_value=[result]),names={0:'product'})
        torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None,empty_cache=lambda:None))
        packets=[]
        def feed(packet):
            packets.append(packet)
            if len(packets)==5:s.stop.set();return
            s.submit(frame,0,time.monotonic_ns(),{'session_id':'camera','receive_sequence':len(packets)+1})
        observe=Mock(wraps=s.material_counter.observe)
        s.submit(frame,0,time.monotonic_ns(),{'session_id':'camera','receive_sequence':1})
        with patch.object(s.studio,'model',side_effect=lambda ident,role=None:{'path':ident,'sha256':'f'*64}), \
             patch.object(s,'guard'),patch.object(s,'model_hashes',return_value={}), \
             patch('jetson_worktime.behavior_service.protect_frame',side_effect=lambda image,*_:image), \
             patch.object(s.writer,'submit',side_effect=feed),patch.object(s.material_counter,'observe',observe):
            s._run_models(torch,None,lambda path:products if path=='test-material' else model,lambda result:[],gc)
        s.stop.clear()
        self.assertEqual(products.predict.call_count,6)  # One warm-up, five distinct frames.
        self.assertEqual(observe.call_count,5)
        self.assertEqual([p['receive_sequence'] for p in packets],[1,2,3,4,5])
        self.assertEqual(s.quality.snapshot()['material_inference_ms']['count'],5)
        self.assertTrue(s.live_observation['materials']['detections'])

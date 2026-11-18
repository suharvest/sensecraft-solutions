from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from jetson_worktime.activity import ActivityEstimator
from jetson_worktime.inference import workbench_crop,material_input,material_results,acceleration_path
from jetson_worktime.materials import MATERIAL_DEFAULTS,MaterialCounter,validate_materials,material_threshold
from jetson_worktime.studio_store import StudioStore


class ActivityTests(unittest.TestCase):
    def test_estimate_requires_temporal_evidence_and_does_not_tick_on_reads(self):
        a=ActivityEstimator()
        for t in (0,.5,1,1.5,2):a.settle(t,'active','handling','s',('camera',1))
        r=a.snapshot(2,True,'s');self.assertEqual(r['state'],'active')
        self.assertEqual(r['active_estimated_seconds'],.5)
        self.assertEqual(a.snapshot(20,True,'s')['active_estimated_seconds'],.5)
        self.assertFalse(a.snapshot(20,True,'s')['available'])
    def test_gap_is_unknown_and_new_session_does_not_inherit_time(self):
        a=ActivityEstimator()
        for t in (0,1,2,3):a.settle(t,'active','handling','s',1)
        old=a.totals['active'];a.settle(10,'active','handling','s',1)
        self.assertEqual(a.totals['active'],old);self.assertGreaterEqual(a.totals['unknown'],7)
        a.settle(11,'active','handling','next',1);self.assertEqual(sum(a.totals.values()),0)
    def test_absence_unknown_and_stale_observation_never_mean_active(self):
        a=ActivityEstimator();a.settle(1,'absent','missing','s',1);a.settle(2,'unknown','occluded','s',1)
        self.assertEqual(a.state,'unknown');self.assertEqual(a.totals['active'],0)
        a.settle(1,'active','out of order','s',1);self.assertEqual(a.state,'unknown')
    def test_reconnect_gap_is_retained_as_unknown(self):
        a=ActivityEstimator();a.settle(1,'active','handling','s',1)
        a.reset_context();a.settle(10,'active','handling','s',2)
        self.assertEqual(a.totals['unknown'],9)


class CropTests(unittest.TestCase):
    def test_class_thresholds_keep_global_floor_and_validate_values(self):
        from jetson_worktime.studio_store import StudioError
        cfg=deepcopy(MATERIAL_DEFAULTS);cfg['confidence']=.2;cfg['confidence_by_class']={'0':.55,'2':.1}
        self.assertEqual(material_threshold(cfg,0),.55);self.assertEqual(material_threshold(cfg,2),.2)
        self.assertEqual(validate_materials(cfg,[100,100])['confidence_by_class'],cfg['confidence_by_class'])
        for bad in ({'2':True},{'2':float('nan')},{'bad':.4},{2:.4}):
            cfg['confidence_by_class']=bad
            with self.assertRaises(StudioError):validate_materials(cfg,[100,100])
    def test_crop_preserves_both_regions_and_original_coordinates(self):
        cfg=dict(image_size=[2560,1440],materials=dict(configured=True,inference_region='workbench',regions={
            'pending':[[1000,900],[1700,900],[1700,1300],[1000,1300]],
            'completed':[[1000,400],[1500,400],[1500,700],[1000,700]]}))
        x,y,r,b=workbench_crop(cfg,2560,1440)
        self.assertLessEqual(x,1000);self.assertLessEqual(y,400);self.assertGreaterEqual(r,1700);self.assertGreaterEqual(b,1300)
        self.assertLess(r-x,2560)
        self.assertEqual(workbench_crop(cfg,1920,1080),(0,0,1920,1080))
    def test_unavailable_acceleration_retains_pt(self):
        self.assertEqual(acceleration_path('/tmp/nonexistent',{'path':'model.pt','sha256':'a'*64}),('model.pt','pytorch'))
    def test_engine_cache_requires_exact_runtime_and_integrity(self):
        import hashlib,json
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cache=root/'data/acceleration';cache.mkdir(parents=True)
            engine=cache/'model.engine';engine.write_bytes(b'validated-engine')
            metadata={'path':'authoritative.pt','sha256':'a'*64}
            value=dict(weights_sha256=metadata['sha256'],tensorrt='10.3.0',machine='aarch64',hardware='Test Jetson',
                       validated=True,engine=engine.name,engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest())
            manifest=cache/(metadata['sha256']+'.json');manifest.write_text(json.dumps(value));original=Path.read_text
            def read(path,*args,**kwargs):
                return 'Test Jetson\0' if str(path)=='/proc/device-tree/model' else original(path,*args,**kwargs)
            with patch.dict('sys.modules',tensorrt=SimpleNamespace(__version__='10.3.0')),patch('platform.machine',return_value='aarch64'),patch.object(Path,'read_text',autospec=True,side_effect=read):
                self.assertEqual(acceleration_path(root,metadata),(str(engine),'tensorrt-fp16'))
                engine.write_bytes(b'corrupt')
                self.assertEqual(acceleration_path(root,metadata),('authoritative.pt','pytorch'))
                engine.write_bytes(b'validated-engine');value['tensorrt']='other';manifest.write_text(json.dumps(value))
                self.assertEqual(acceleration_path(root,metadata),('authoritative.pt','pytorch'))


class VerifiedProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=StudioStore(Path(self.temp.name));self.counter=MaterialCounter(self.store)
        m=deepcopy(MATERIAL_DEFAULTS);m.update(enabled=True,configured=True,production_policy='verified',
            regions={'pending':[[0,0],[90,0],[90,99],[0,99]],'completed':[[100,0],[199,0],[199,99],[100,99]]},
            rules={'pending':{'count':[0],'alert':[]},'completed':{'count':[2],'alert':[1]}})
        self.cfg=dict(revision=1,image_size=[200,100],materials=m)
    def d(self,x=120,c=2):return dict(class_id=c,confidence=.95,bbox_xyxy=[x,20,x+10,40])
    def sample(self,t,ds):
        self.counter.observe(ds,t,self.cfg,'s',session_started=0)
        return self.counter.snapshot(t,self.cfg,True,'s')
    def test_initial_inventory_is_not_new_production(self):
        self.sample(0,[self.d()]);r=self.sample(1,[self.d()])
        self.assertEqual(r['completed'],1);self.assertEqual(r['cumulative'],1);self.assertEqual(r['production_total'],0)
    def test_class_conflicts_outside_counting_zones_do_not_create_review_spam(self):
        self.sample(0,[]);self.sample(1,[])
        for t in (2,3,6,7):r=self.sample(t,[self.d(92,0),self.d(92,1)])
        self.assertEqual(r['reviews'],[]);self.assertEqual(r['production_total'],0)
        for t in (8,9):r=self.sample(t,[self.d(120,0),self.d(120,1)])
        self.assertTrue(any(e['review_reason']=='label_conflict' for e in r['reviews']))
    def test_ambiguous_pending_identity_cannot_create_origin_proof(self):
        self.sample(0,[self.d(60,0),self.d(66,0)]);self.sample(1,[self.d(60,0),self.d(66,0)])
        r=self.sample(1.1,[self.d(63,0)])
        conflicted=[tr for tr in self.counter.tracks.values() if tr.get('conflict')]
        self.assertTrue(conflicted);self.assertTrue(all(not tr['pending_confirmed'] for tr in conflicted))
        self.assertEqual(r['reviews'],[])
    def test_unproven_arrival_needs_review_and_resolution_is_idempotent(self):
        self.sample(0,[]);self.sample(1,[]);self.sample(2,[self.d()]);r=self.sample(3,[self.d()])
        self.assertEqual(r['production_total'],0);self.assertEqual(r['reviews'][0]['review_reason'],'completion_unverified')
        request=dict(token='verified-test-token',delta=1,reason='Checked evidence',event_id=r['reviews'][0]['id'],expected_total=0)
        self.counter.adjust('s',request);self.counter.adjust('s',request)
        r=self.counter.snapshot(3,self.cfg,True,'s');self.assertEqual(r['production_total'],1)
    def test_removal_and_reappearance_do_not_add_production(self):
        self.sample(0,[self.d()]);self.sample(1,[self.d()]);self.sample(4,[])
        self.sample(5,[self.d()]);r=self.sample(6,[self.d()])
        self.assertEqual(r['production_total'],0);self.assertEqual(r['reviews'][0]['review_reason'],'return')
    def test_verified_origin_counts_once_across_zone_motion(self):
        self.sample(0,[self.d(70,0)]);self.sample(1,[self.d(70,0)])
        for t,x,c in [(1.1,80,0),(1.2,90,0),(1.3,100,2),(1.4,110,2),(1.5,120,2),(2,120,2),(2.5,120,2),(3,120,2)]:r=self.sample(t,[self.d(x,c)])
        self.assertEqual(r['production_total'],1)
        self.sample(4,[]);r=self.sample(4.5,[self.d()]);self.assertEqual(r['production_total'],1)
    def test_old_events_have_no_new_production_interpretation(self):
        self.store.event('legacy','initial','initial',4)
        r=self.counter.snapshot(0,self.cfg,True,'legacy');self.assertIsNone(r['production_total'])
    def test_identity_review_of_an_already_counted_item_cannot_add_again(self):
        from jetson_worktime.studio_store import StudioError
        self.sample(0,[self.d()]);self.sample(1,[self.d()])
        key,track=next(iter(self.counter.tracks.items()));self.counter._review(key,track,'identity_ambiguous')
        event=self.store.events('s')[-1]
        with self.assertRaises(StudioError):self.counter.adjust('s',dict(token='bad-duplicate-review',event_id=event['id'],delta=1,reason='Duplicate',expected_total=1))
    def test_reviewed_completion_can_be_corrected_if_it_becomes_abnormal(self):
        self.sample(0,[]);self.sample(1,[]);self.sample(2,[self.d()]);r=self.sample(3,[self.d()])
        approval=dict(token='approve-review-token',event_id=r['reviews'][0]['id'],delta=1,reason='Checked',expected_total=0)
        self.counter.adjust('s',approval)
        self.sample(4,[self.d(c=1)]);r=self.sample(5,[self.d(c=1)])
        abnormal=next(e for e in r['reviews'] if e['review_reason']=='counted_became_abnormal')
        self.assertTrue(abnormal['production_counted'])
        self.counter.adjust('s',dict(token='correct-review-token',event_id=abnormal['id'],delta=-1,reason='Incomplete',expected_total=1))
        self.assertEqual(self.counter.snapshot(5,self.cfg,True,'s')['production_total'],0)
        self.counter.adjust('s',approval)
        self.assertFalse(next(iter(self.counter.tracks.values()))['production_counted'])

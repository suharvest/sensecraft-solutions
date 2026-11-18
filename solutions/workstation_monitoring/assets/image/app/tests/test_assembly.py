from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from jetson_worktime.materials import MATERIAL_DEFAULTS,MaterialCounter,validate_materials,material_behavior_changed
from jetson_worktime.studio_store import StudioStore,StudioError

class AssemblyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.store=StudioStore(Path(self.temp.name));self.counter=MaterialCounter(self.store)
  m=deepcopy(MATERIAL_DEFAULTS);m.update(enabled=True,configured=True,regions={'pending':[[0,0],[90,0],[90,99],[0,99]],'completed':[[100,0],[199,0],[199,99],[100,99]]},rules={'pending':{'count':[0,3],'alert':[]},'completed':{'count':[2],'alert':[1]}})
  self.config=dict(revision=1,image_size=[200,100],materials=m)
 def d(self,c,x=120):return dict(class_id=c,confidence=.9,bbox_xyxy=[x,20,x+10,40])
 def sample(self,t,ds,session='s'):
  self.counter.observe(ds,t,self.config,session,session_started=0,model_id='m',model_sha256='a'*64,class_names={0:'box',1:'not_packed',2:'packed',3:'part'})
  return self.counter.snapshot(t,self.config,True,session)
 def test_per_class_initial_and_alert_is_not_completion(self):
  ds=[self.d(0,5),self.d(3,30),self.d(2,120),self.d(1,150)]
  self.sample(0,ds);r=self.sample(1,ds)
  self.assertEqual(r['by_class']['pending'],{'0':1,'3':1});self.assertEqual(r['completed'],1);self.assertEqual(r['cumulative'],1);self.assertEqual(r['initial'],1);self.assertEqual(len(r['alerts']),1)
  self.sample(2,ds);self.assertEqual(len(self.store.list('material_alert')),1)
 def test_class_transition_needs_stability_and_never_double_counts(self):
  self.sample(0,[self.d(2)]);r=self.sample(1,[self.d(2)]);self.assertEqual(r['cumulative'],1)
  r=self.sample(2,[self.d(1)]);self.assertFalse(r['alerts']);self.assertEqual(r['completed'],1)
  r=self.sample(3,[self.d(1)]);self.assertEqual(len(r['alerts']),1);self.assertEqual(r['cumulative'],1);self.assertEqual(r['reviews'][0]['review_reason'],'counted_became_abnormal')
  r=self.sample(4,[self.d(2)]);self.assertEqual(len(r['alerts']),1)
  r=self.sample(5,[self.d(2)]);self.assertFalse(r['alerts']);self.assertEqual(r['cumulative'],1);self.assertFalse(self.store.list('material_alert')[0]['active'])
 def test_anomaly_can_count_after_stable_recovery(self):
  self.sample(0,[self.d(1)]);r=self.sample(1,[self.d(1)]);self.assertEqual(r['cumulative'],0)
  self.sample(2,[self.d(2)]);r=self.sample(3,[self.d(2)]);self.assertEqual(r['cumulative'],1);self.assertEqual(r['added'],1)
 def test_alert_outside_completed_zone_does_not_fire(self):
  self.sample(0,[self.d(1,5)]);r=self.sample(1,[self.d(1,5)]);self.assertFalse(r['alerts']);self.assertEqual(r['pending'],0)
 def test_no_session_alert_is_durable_without_production(self):
  self.sample(0,[self.d(1)],None);r=self.sample(1,[self.d(1)],None);self.assertEqual(len(r['alerts']),1);self.assertEqual(r['cumulative'],0)
  r=self.sample(4,[],None);self.assertFalse(r['alerts']);self.assertFalse(self.store.list('material_alert')[0]['active'])
 def test_deduction_idempotency(self):
  self.sample(0,[self.d(2)]);self.sample(1,[self.d(2)]);self.sample(2,[self.d(1)]);r=self.sample(3,[self.d(1)])
  req=dict(token='deduction-123',delta=-1,reason='confirmed unfinished',event_id=r['reviews'][0]['id'],expected_total=1)
  self.assertEqual(self.counter.adjust('s',req)['cumulative'],0);self.assertEqual(self.counter.adjust('s',req)['cumulative'],0)
 def test_conflicting_labels_do_not_increment(self):
  ds=[self.d(2),self.d(1)];self.sample(0,ds);r=self.sample(1,ds);self.assertEqual(r['completed'],0);self.assertEqual(r['cumulative'],0);self.assertEqual(len(r['reviews']),1)
 def test_legacy_migration_display_and_invalid_rules(self):
  old={k:v for k,v in self.config['materials'].items() if k not in ('rules','names','masks','class_styles','binding')};old['class_id']=3
  m=validate_materials(old,[200,100]);self.assertEqual(m['rules']['completed']['count'],[3]);self.assertEqual(m['masks'],{'pending':True,'completed':True})
  new=deepcopy(m);new['masks']['completed']=False;self.assertFalse(material_behavior_changed(m,new))
  new['rules']['completed']['alert']=[3]
  with self.assertRaises(StudioError):validate_materials(new,[200,100])
 def test_arbitrary_model_classes(self):
  self.config['materials']['rules']={'pending':{'count':[11,12],'alert':[]},'completed':{'count':[42],'alert':[99]}}
  ds=[self.d(11,5),self.d(12,30),self.d(42,120),self.d(99,150)];self.sample(0,ds);r=self.sample(1,ds)
  self.assertEqual(r['cumulative'],1);self.assertEqual(r['by_class']['pending'],{'11':1,'12':1});self.assertEqual(len(r['alerts']),1)
 def test_display_changes_do_not_reset_business_rules(self):
  old=self.config['materials'];new=deepcopy(old);new['names']['completed']='Finished';new['class_styles']={'2':{'name':'Good','color':'#22c55e'}};new['masks']['pending']=False
  self.assertFalse(material_behavior_changed(old,new));new['rules']['completed']['count']=[8];self.assertTrue(material_behavior_changed(old,new))
 def test_stale_snapshots_hide_quantities_detections_and_alarms(self):
  self.sample(0,[self.d(1)]);self.sample(1,[self.d(1)]);r=self.counter.snapshot(10,self.config,True,'s')
  self.assertIsNone(r['by_class']);self.assertIsNone(r['completed']);self.assertFalse(r['detections']);self.assertFalse(r['alerts'])
 def test_model_binding_and_class_validation(self):
  from jetson_worktime.studio import Studio
  from jetson_worktime.studio_store import digest
  studio=Studio(Path(self.temp.name));weight=Path(self.temp.name)/'material.pt';weight.write_bytes(b'material')
  studio.store.put('model',dict(id='m',role='material',path=str(weight),sha256=digest(weight),classes={'0':'box','1':'not_packed','2':'packed','3':'part'}))
  config=deepcopy(self.config);config['models']={'material':'m'};config['materials']['binding']={'model_id':'m','sha256':digest(weight)};studio.validate_selection(config)
  config['materials']['binding']['sha256']='f'*64
  with self.assertRaises(StudioError):studio.validate_selection(config)
  config['materials']['binding']=None;config['materials']['rules']['completed']['count']=[9]
  with self.assertRaises(StudioError):studio.validate_selection(config)

 def test_two_materials_two_finished_and_one_alert(self):
  ds=[self.d(0,5),self.d(3,30),self.d(2,110),self.d(2,138),self.d(1,170)]
  self.sample(0,ds);r=self.sample(1,ds)
  self.assertEqual(r['pending'],2);self.assertEqual(r['completed'],2);self.assertEqual(len(r['alerts']),1)
  self.assertEqual(r['cumulative'],2);self.assertEqual(r['by_class']['completed'],{'2':2})
 def test_alert_survives_short_occlusion_then_expires(self):
  self.sample(0,[self.d(1)]);r=self.sample(1,[self.d(1)]);self.assertEqual(len(r['alerts']),1)
  r=self.sample(2,[]);self.assertEqual(len(r['alerts']),1)
  r=self.sample(3.1,[]);self.assertFalse(r['alerts']);self.assertFalse(self.store.list('material_alert')[0]['active'])
 def test_alert_resolves_after_stable_move_outside_completed(self):
  self.sample(0,[self.d(1,96)]);self.sample(1,[self.d(1,96)])
  r=self.sample(1.5,[self.d(1,92)])
  self.assertTrue(r['alerts'])
  self.sample(2,[self.d(1,92)]);r=self.sample(2.5,[self.d(1,92)])
  self.assertFalse(r['alerts']);self.assertEqual(r['completed'],0)

 def test_single_label_flip_keeps_confirmed_count(self):
  self.sample(0,[self.d(2)]);self.sample(.5,[self.d(2)]);self.sample(1,[self.d(2)])
  r=self.sample(1.5,[self.d(1)]);self.assertEqual(r['completed'],1);self.assertFalse(r['alerts'])
  r=self.sample(2,[self.d(2)]);self.assertEqual(r['completed'],1);self.assertEqual(r['cumulative'],1)

 def test_continuous_frames_keep_time_confirmation_and_reject_one_frame_errors(self):
  for i in range(20):
   r=self.sample(i*.05,[self.d(2)])
   self.assertEqual(r['completed'],0)
  r=self.sample(1.,[self.d(2)]);self.assertEqual(r['completed'],1)
  r=self.sample(1.05,[]);self.assertEqual(r['completed'],1)
  r=self.sample(1.10,[self.d(1)]);self.assertEqual(r['completed'],1);self.assertFalse(r['alerts'])
  for i in range(23,45):
   r=self.sample(i*.05,[self.d(2)])
   self.assertEqual(r['completed'],1);self.assertFalse(r['alerts'])
  self.assertEqual(r['cumulative'],1)
 def test_three_of_four_votes_confirm_change_within_two_seconds(self):
  for t in (0,.5,1):self.sample(t,[self.d(2)])
  for t,c in [(1.5,1),(2,2),(2.5,1)]:
   r=self.sample(t,[self.d(c)]);self.assertEqual(r['completed'],1)
  r=self.sample(3,[self.d(1)]);self.assertEqual(r['completed'],0);self.assertEqual(len(r['alerts']),1)
 def test_one_miss_preserves_count_but_sparse_votes_do_not_confirm(self):
  self.sample(0,[self.d(2)]);self.sample(.5,[]);r=self.sample(1,[self.d(2)])
  self.assertEqual(r['completed'],0)
  self.sample(1.5,[self.d(2)]);r=self.sample(2,[self.d(2)]);self.assertEqual(r['completed'],1)
  r=self.sample(3,[]);self.assertEqual(r['completed'],1)
  r=self.sample(4.01,[]);self.assertEqual(r['completed'],0)
 def test_global_assignment_beats_greedy(self):
  from jetson_worktime.materials import assign_targets
  self.assertEqual(set(assign_targets([[.1,.2],[.15,10.]])),{(0,1),(1,0)})
  self.assertEqual(assign_targets([[10.]]),[])
 def test_configured_longer_confirmation_is_honored(self):
  self.config['materials']['stable_seconds']=2
  for t in (0,.5,1,1.5):self.assertEqual(self.sample(t,[self.d(2)])['completed'],0)
  self.assertEqual(self.sample(2,[self.d(2)])['completed'],1)
 def test_persistent_conflicting_labels_retire_confirmed_count(self):
  self.sample(0,[self.d(2)]);self.sample(1,[self.d(2)])
  ds=[self.d(2),self.d(1)]
  for t in (1.5,2,2.5):self.assertEqual(self.sample(t,ds)['completed'],1)
  self.assertEqual(self.sample(3.1,ds)['completed'],0)

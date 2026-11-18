"""Display-only follow must expire, invalidate and never modify detector evidence."""
from copy import deepcopy
from unittest.mock import patch
import unittest
import cv2
import numpy as np
from jetson_worktime.live_overlay import LiveOverlay

class LiveOverlayTests(unittest.TestCase):
 def setUp(self):
  self.image=np.zeros((160,240,3),np.uint8)
  rng=np.random.default_rng(42)
  self.image[30:110,40:120]=rng.integers(0,255,(80,80,3),dtype=np.uint8)
  self.meta={'session_id':'cam','receive_sequence':10}
  self.person={'bbox_xyxy':[40,30,120,110],'keypoints':[{'x':80,'y':60,'confidence':.9}]}
  self.obs=dict(frame=self.image,received=1_000_000_000,meta=self.meta,revision=3,epoch=4,
   persons=[self.person],materials={'available':True,'detections':[{'bbox_xyxy':[50,40,90,80],'class_id':2,'role':'count'}]})
 def render(self,image=None,t=1_050_000_000,**kw):
  return self.follower.render(self.image if image is None else image,t,kw.get('meta',{'session_id':'cam','receive_sequence':11}),kw.get('revision',3),kw.get('epoch',4),self.obs)
 def test_motion_follows_geometry_without_mutating_evidence(self):
  self.follower=LiveOverlay();original=deepcopy(self.person)
  shifted=cv2.warpAffine(self.image,np.float32([[1,0,4],[0,1,3]]),(240,160))
  people,material,evidence=self.render(shifted)
  self.assertAlmostEqual(people[0]['bbox_xyxy'][0],44,delta=1)
  self.assertAlmostEqual(people[0]['keypoints'][0]['y'],63,delta=1)
  self.assertEqual(evidence['kind'],'followed');self.assertEqual(evidence['source_frame_sequence'],10)
  self.assertEqual(self.person,original);self.assertEqual(self.obs['materials']['detections'][0]['bbox_xyxy'],[50,40,90,80])
 def test_expiry_and_invalidation_hide_all_dynamic_overlays(self):
  self.follower=LiveOverlay()
  for changes in [dict(t=1_300_000_001),dict(epoch=5),dict(revision=4),dict(meta={'session_id':'other','receive_sequence':11}),dict(t=999_999_999)]:
   people,materials,evidence=self.render(**changes)
   self.assertFalse(people);self.assertFalse(materials);self.assertIsNone(evidence)
 def test_exact_frame_is_identified_as_detector_evidence(self):
  self.follower=LiveOverlay();people,_,e=self.render(t=1_000_000_000,meta=self.meta)
  self.assertEqual(e['kind'],'detected');self.assertEqual(people[0],self.person)
 def test_textureless_frame_does_not_hold_an_old_box(self):
  self.follower=LiveOverlay();self.obs['frame']=np.zeros_like(self.image)
  self.assertFalse(self.render()[0])

 def test_empty_detection_layer_skips_image_processing_and_can_recover(self):
  self.follower=LiveOverlay();self.obs['persons']=[];self.obs['materials']['detections']=[]
  with patch('jetson_worktime.live_overlay.cv2.resize',side_effect=AssertionError('empty layer must not resize')):
   people,materials,evidence=self.render()
  self.assertFalse(people);self.assertEqual(materials['detections'],[]);self.assertIsNone(evidence)
  self.obs={**self.obs,'persons':[self.person]}
  self.assertTrue(self.render()[0])

 def test_newly_completed_result_is_not_expired_by_model_processing_time(self):
  self.follower=LiveOverlay();self.obs['completed']=1_250_000_000
  people,materials,evidence=self.render(t=1_400_000_000)
  self.assertTrue(people);self.assertTrue(materials['detections']);self.assertEqual(evidence['age_ms'],400)
  self.assertFalse(self.render(t=1_550_000_001)[0])

 def test_slow_inference_cannot_extend_the_absolute_source_age_limit(self):
  self.follower=LiveOverlay();self.obs['completed']=1_650_000_000
  self.assertTrue(self.render(t=1_740_000_000)[0])
  self.assertFalse(self.render(t=1_750_000_001)[0])

 def test_small_product_on_hd_frame_tracks_with_bounded_error(self):
  self.follower=LiveOverlay();rng=np.random.default_rng(4)
  frame=np.zeros((1080,1920,3),np.uint8);frame[400:460,700:760]=rng.integers(0,255,(60,60,3),dtype=np.uint8)
  self.obs['frame']=frame;self.obs['persons']=[];self.obs['materials']['detections']=[{'bbox_xyxy':[700,400,760,460],'class_id':2,'role':'count'}]
  moved=cv2.warpAffine(frame,np.float32([[1,0,8],[0,1,4]]),(1920,1080))
  _,material,_=self.render(moved)
  self.assertEqual(len(material.get('detections',[])),1)
  self.assertAlmostEqual(material['detections'][0]['bbox_xyxy'][0],708,delta=5)

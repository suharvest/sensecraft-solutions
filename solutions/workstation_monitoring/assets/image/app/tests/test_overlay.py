import unittest
import numpy as np
from jetson_worktime.overlay import draw_overlay

CONFIG={'image_size':[2560,1440],'keypoint_confidence':.4,
        'regions':{'station':[[0,0],[2559,0],[2559,1439],[0,1439]],'seat':[[2100,300],[2500,300],[2500,900],[2100,900]]}}

class OverlayTests(unittest.TestCase):
 def test_deterministic_and_cached(self):
  frame=np.zeros((720,1280,3),np.uint8)
  first=draw_overlay(frame.copy(),[],CONFIG,fresh=False)
  second=draw_overlay(frame.copy(),[],CONFIG,fresh=False)
  self.assertTrue(np.array_equal(first,second))
  self.assertEqual(first.shape,(720,1280,3))
 def test_person_and_anchor(self):
  frame=np.zeros((720,1280,3),np.uint8)
  person={'bbox_xyxy':[1800,400,2200,1100],'keypoints':[{'x':2000,'y':300,'confidence':.9} for _ in range(17)],'upper_body_anchor':[2000,450]}
  out=draw_overlay(frame.copy(),[person],CONFIG,fresh=True)
  self.assertEqual(out.shape,(720,1280,3))
  self.assertGreater(int(out.sum()),0)
 def test_frame_size_rebuilds_cache(self):
  for shape in ((720,1280,3),(360,640,3)):
   self.assertEqual(draw_overlay(np.zeros(shape,np.uint8),[],CONFIG,fresh=False).shape,shape)


class IndustrialOverlayTests(unittest.TestCase):
 def setUp(self):
  from copy import deepcopy
  self.config=deepcopy(CONFIG)
  self.config['display']=dict(boxes=True,regions=True,keypoints=True)
  self.person={'bbox_xyxy':[500,300,1700,1300], 'keypoints':[{'x':800+i*20,'y':650+i*10,'confidence':.9} for i in range(17)],'upper_body_anchor':[950,720]}

 def test_shared_style_and_sparse_corners(self):
  from jetson_worktime.overlay import STYLE,COLORS,dimensions,corner_segments
  from jetson_worktime.settings import DISPLAY_DEFAULTS
  self.assertEqual(DISPLAY_DEFAULTS,STYLE['defaults'])
  self.assertFalse(DISPLAY_DEFAULTS['keypoints'])
  self.assertEqual(COLORS['seat'],(36,191,251))
  self.assertEqual(len({COLORS[key] for key in ('station','seat','person','skeleton','keypoint','anchor')}),6)
  metrics=dimensions(1280)
  self.assertEqual(len(corner_segments((100,100,500,600),metrics)),4)
  self.config['display']=dict(boxes=True,regions=False,keypoints=False)
  image=draw_overlay(np.zeros((720,1280,3),np.uint8),[self.person],self.config)
  # The midpoint of the person's left edge has no continuous rectangle stroke.
  self.assertEqual(int(image[400,250].sum()),0)
  self.assertGreater(int(image[150,250].sum()),0)

 def test_fill_is_subtle_and_freshness_and_switches_are_independent(self):
  original=np.full((720,1280,3),100,np.uint8)
  self.config['display']=dict(boxes=False,regions=True,keypoints=False)
  regions=draw_overlay(original.copy(),[],self.config)
  self.assertLessEqual(int(np.abs(regions[300,1150].astype(int)-100).max()),40)
  self.assertFalse(np.array_equal(regions[300,1150],original[300,1150]))
  self.config['display']=dict(boxes=True,regions=False,keypoints=True)
  self.assertTrue(np.array_equal(draw_overlay(original.copy(),[self.person],self.config,fresh=False),original))
  for key in ('boxes','regions','keypoints'):
   self.config['display']={name:name==key for name in ('boxes','regions','keypoints')}
   self.assertFalse(np.array_equal(draw_overlay(original.copy(),[self.person],self.config),original))

 def test_labels_are_bounded_nonoverlapping_and_small_frames_survive(self):
  from jetson_worktime.overlay import _layer,place_labels,dimensions
  for width,height in ((1280,720),(640,360),(160,90),(24,16)):
   for locale in ('zh-CN','en'):
    layer=_layer(width,height,self.config,locale)
    labels=[(width-1,height-1,key) for key in list(layer['sprites'])*4]
    placed=place_labels(labels,layer['sprites'],width,height,dimensions(width))
    for i,(x,y,w,h,key) in enumerate(placed):
     self.assertTrue(0<=x<x+w<=width and 0<=y<y+h<=height)
     for a,b,c,d,_ in placed[:i]:
      self.assertFalse(x<a+c and x+w>a and y<b+d and y+h>b)
    self.assertEqual(draw_overlay(np.zeros((height,width,3),np.uint8),[self.person]*3,self.config,locale=locale).shape,(height,width,3))

 def test_privacy_hides_face_keypoints_and_keeps_body(self):
  from copy import deepcopy
  config=deepcopy(self.config)
  config['display']=dict(boxes=False,regions=False,keypoints=True)
  config['privacy']=dict(enabled=True)
  person=deepcopy(self.person)
  person['upper_body_anchor']=None
  person['keypoints']=[{'x':500,'y':100,'confidence':.9} for _ in range(5)]+[{'x':1000,'y':800,'confidence':.9} for _ in range(12)]
  protected=draw_overlay(np.zeros((720,1280,3),np.uint8),[person],config)
  self.assertEqual(int(protected[50,250].sum()),0)
  self.assertGreater(int(protected[400,500].sum()),0)
  config['privacy']['enabled']=False
  visible=draw_overlay(np.zeros((720,1280,3),np.uint8),[person],config)
  self.assertGreater(int(visible[50,250].sum()),0)

if __name__=='__main__':unittest.main()

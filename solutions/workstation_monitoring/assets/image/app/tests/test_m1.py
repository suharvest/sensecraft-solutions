import threading,time,unittest
import numpy as np
from jetson_worktime.video import VideoReader,Gst
from jetson_worktime.roi import observe_and_draw
class Sink:
 def __init__(self,pts):self.pts=pts
 def emit(self,*args):
  b=Gst.Buffer.new_allocate(None,16,None);b.fill(0,bytes(range(16)));b.pts=self.pts
  return Gst.Sample.new(b,Gst.Caps.from_string('video/x-raw,format=BGRx,width=2,height=2,framerate=20/1'),None,None)
class Bus:
 def timed_pop_filtered(self,*args):return None
class Pipeline:
 def get_bus(self):return Bus()
def reader():
 r=VideoReader.__new__(VideoReader);r.condition=threading.Condition();r.rtsp=True;r.closed=False;r.latest=None;r.timeout=.02;r.session_id='original';r.received=r.dropped=r.consumed=0;r.last_pts=None;r.duplicate_pts=0;r.last_rx_ns=None;r.pipeline=Pipeline();return r
class M1Tests(unittest.TestCase):
 def test_latest_once_and_bounded(self):
  r=reader()
  for pts in range(10):r._on_sample(Sink(pts))
  self.assertEqual(r.snapshot()['queue_depth'],1);self.assertEqual(r.dropped,9)
  self.assertEqual(r.read()[1],9)
  with self.assertRaises(TimeoutError):r.read()
  r._on_sample(Sink(10));self.assertEqual(r.read()[1],10)
  self.assertEqual(r.last_meta['receive_sequence'],11)
 def test_duplicate_pts_not_new_observation(self):
  r=reader();r._on_sample(Sink(10));r.read();r._on_sample(Sink(10))
  self.assertEqual(r.duplicate_pts,1)
  with self.assertRaises(TimeoutError):r.read()
 def test_pts_reset_new_session(self):
  r=reader();r._on_sample(Sink(100));r.read();old=r.session_id
  r._on_sample(Sink(0));r.read();self.assertNotEqual(old,r.session_id)
 def test_roi_unscaled_and_missing_wrist(self):
  im=np.zeros((20,30,3),np.uint8);p={'bbox_xyxy':[1,1,5,5],'keypoints':[]}
  roi={'image_size':[30,20],'calibrated':False,'regions':{'station':[[0,0],[10,0],[10,10],[0,10]]}}
  observe_and_draw(im,[p],roi)
  self.assertTrue(p['roi']['regions']['station']['person_bottom_center']);self.assertIsNone(p['roi']['regions']['station']['left_wrist']);self.assertFalse(p['roi']['calibrated'])
  roi['image_size']=[60,40];observe_and_draw(im,[p],roi);self.assertIsNone(p['roi']['regions']['station']['person_bottom_center'])
if __name__=='__main__':unittest.main()

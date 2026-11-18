import unittest
from jetson_worktime.behavior import SessionEngine,DEFAULTS,deduplicate,classify
class TimingTests(unittest.TestCase):
 def feed(self,e,a,b,label,step=.2,stream='s'):
  for i in range(round((b-a)/step)+1):e.observe(round(a+i*step,6),label,stream)
 def working(self):
  e=SessionEngine();self.feed(e,0,12,'SEATED');return e
 def test_stable_start_backdated(self):
  e=SessionEngine();self.feed(e,0,9,'SEATED');self.assertIsNone(e.current)
  self.feed(e,9.2,12,'SEATED');self.assertEqual(e.current['start'],0);self.assertAlmostEqual(e.snapshot(12)['work_seconds'],12)
 def test_short_59_seconds(self):
  e=self.working();self.feed(e,13,71,'NEARBY');e.observe(72,'SEATED','s');self.assertAlmostEqual(e.snapshot(72)['work_seconds'],72);self.assertEqual(e.snapshot(72)['rest_seconds'],0)
 def test_61_seconds_entire_absence_is_rest(self):
  e=self.working();self.feed(e,13,73,'NEARBY');e.observe(74,'SEATED','s');s=e.snapshot(74);self.assertAlmostEqual(s['work_seconds'],13);self.assertAlmostEqual(s['rest_seconds'],61)
 def test_long_absence_backdated(self):
  e=self.working();self.feed(e,13,313,'MISSING');self.assertIsNone(e.current);self.assertEqual(e.completed[0]['end'],13);self.assertAlmostEqual(e.totals(e.completed[0])['work_seconds'],13)
  self.feed(e,314,325,'SEATED');self.assertIsNotNone(e.current);self.assertEqual(e.current['start'],314)
 def test_nearby_does_not_end_session(self):
  e=self.working();self.feed(e,13,400,'NEARBY');self.assertIsNotNone(e.current);self.assertEqual(e.snapshot(400)['state'],'REST')
 def test_short_missing_bridges(self):
  e=self.working();self.feed(e,13,14,'MISSING');e.observe(15,'SEATED','s');self.assertAlmostEqual(e.snapshot(15)['work_seconds'],15)
 def test_unknown_does_not_count(self):
  e=self.working();self.feed(e,13,23,'UNKNOWN');s=e.snapshot(23);self.assertAlmostEqual(s['work_seconds'],13);self.assertAlmostEqual(s['unknown_seconds'],10)
 def test_tick_does_not_extend_work_forever(self):
  e=self.working();e.tick(100);self.assertAlmostEqual(e.snapshot(100)['work_seconds'],13.5);self.assertEqual(e.snapshot(100)['state'],'OBSERVATION_UNKNOWN');self.assertIsNotNone(e.current)
 def test_stream_change_and_interruption(self):
  e=self.working();e.observe(13,'SEATED','new');self.assertEqual(e.completed[0]['end'],12);self.assertIsNone(e.current);self.feed(e,13.2,24,'SEATED',stream='new');self.assertIsNotNone(e.current)
  e.interrupt(30);self.assertIsNone(e.current);self.assertEqual(e.completed[-1]['end'],24)
 def test_late_and_repeated_observations_ignored(self):
  e=self.working();self.assertFalse(e.observe(13,'SEATED','s',now=20));self.assertFalse(e.observe(12,'SEATED','s',now=12));self.assertAlmostEqual(e.snapshot(20)['work_seconds'],13.5)
 def test_manual_and_review(self):
  e=SessionEngine();e.observe(0,'SEATED');e.manual('start',0);e.manual('review',.1);self.assertTrue(e.current['review']);e.observe(1,'SEATED');e.manual('end',1);self.assertEqual(e.completed[0]['end_reason'],'manual')
 def test_manual_end_holds_until_leave_or_manual_start(self):
  e=self.working();e.manual('end',12);self.feed(e,13,30,'SEATED');self.assertIsNone(e.current)
  e.manual('start',30);self.assertIsNotNone(e.current)
 def test_frame_rate_independent(self):
  values=[]
  for step in (1,.2):
   e=SessionEngine();self.feed(e,0,20,'SEATED',step);self.feed(e,21,80,'NEARBY',step);e.observe(81,'SEATED','s');values.append(e.snapshot(81))
  self.assertEqual(values[0]['work_seconds'],values[1]['work_seconds']);self.assertEqual(values[0]['rest_seconds'],values[1]['rest_seconds'])
class DetectionTests(unittest.TestCase):
 def person(self,x=80):
  k=[{'x':x,'y':30,'confidence':.9} for _ in range(17)]
  return {'bbox_xyxy':[60,0,100,100],'keypoints':k,'confidence':.9}
 def test_dedup(self):
  self.assertEqual(len(deduplicate([self.person(),self.person()],100,100,DEFAULTS)),1)
 def test_regions_multipeople_and_size(self):
  cfg={'image_size':[100,100],'regions':{'station':[[50,0],[100,0],[100,100],[50,100]],'seat':[[70,20],[100,20],[100,60],[70,60]]}}
  self.assertEqual(classify([self.person(),self.person()],100,100,cfg)[0],'SEATED')
  p=self.person(55);p['bbox_xyxy']=[50,0,60,100];self.assertEqual(classify([self.person(),p],100,100,cfg)[0],'UNKNOWN')
  self.assertEqual(classify([],100,100,cfg)[0],'MISSING');self.assertEqual(classify([],200,100,cfg)[0],'UNKNOWN')
if __name__=='__main__':unittest.main()

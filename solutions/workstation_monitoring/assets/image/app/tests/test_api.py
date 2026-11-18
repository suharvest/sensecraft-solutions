import json
import unittest
from jetson_worktime.api import ObservationCache, make_observation, work_status

class ApiContractTest(unittest.TestCase):
    def observation(self, sequence=1, accepted=True):
        return make_observation('run',{'session_id':'stream','receive_sequence':sequence},None,
            9007199254740993,9007199254741003,9007199255741003,2560,1440,1280,720,
            [],'MISSING','no person',accepted,{'regions':{'seat':[[1,1],[2,1],[2,2]]}},False)

    def test_lossless_nanoseconds_and_null_pts(self):
        o=self.observation()
        self.assertEqual(o['frame']['receive_monotonic_ns'],'9007199254740993')
        self.assertIsNone(o['frame']['pts_ns'])
        self.assertAlmostEqual(o['inference']['local_processing_ms'],1.)
        s=work_status({'frame_ref':{'pts_ns':None,'receive_monotonic_ns':9007199254740993},'work_seconds':12.5})
        self.assertEqual(s['frame_ref']['receive_monotonic_ns'],'9007199254740993')
        self.assertEqual(s['work_seconds'],12.5)

    def test_model_class_ids_do_not_break_work_status_or_observation_cache(self):
        # YOLO model.names uses integer keys; enabled assembly counting exposes it.
        materials={'class_names':{0:'box',1:'not_packed',2:'packed',3:'part'},
                   'source':{'receive_monotonic_ns':9007199254740993}}
        snapshot=work_status({'materials':materials,'active':False})
        payload=json.loads(json.dumps(snapshot))
        self.assertEqual(payload['materials']['class_names']['2'],'packed')
        self.assertEqual(payload['materials']['source']['receive_monotonic_ns'],'9007199254740993')
        observation=self.observation()
        observation['material_observation']=materials
        cache=ObservationCache()
        cache.publish(observation,b'image')
        result=json.loads(json.dumps(cache.snapshot(9007199254740993)))
        self.assertTrue(result['fresh'])
        self.assertEqual(result['observation']['material_observation']['class_names']['0'],'box')

    def test_bounded_atomic_pair_and_immutable_public_snapshot(self):
        c=ObservationCache(2)
        first=self.observation();c.publish(first,b'first');first['persons'].append('mutated')
        c.publish(self.observation(2),b'second');c.publish(self.observation(3),b'third')
        self.assertIsNone(c.frame(first['observation_id']))
        self.assertEqual(len(c.entries),2)
        s=c.snapshot(9007199255741003);key=s['observation']['observation_id']
        self.assertEqual(c.frame(key)[1],b'third')
        s['observation']['persons'].append('mutated')
        self.assertEqual(c.snapshot(9007199255741003)['observation']['persons'],[])
        with self.assertRaises(ValueError):c.publish(self.observation(3),b'duplicate')

    def test_freshness_uses_receive_time_and_acceptance_not_query_time(self):
        c=ObservationCache();self.assertFalse(c.snapshot(1)['available'])
        c.publish(self.observation(),b'image');t=9007199254740993
        self.assertTrue(c.snapshot(t+1000000)['fresh'])
        self.assertFalse(c.snapshot(t+1500000001)['fresh'])
        self.assertFalse(c.snapshot(t+1000000,connected=False)['fresh'])
        self.assertFalse(c.snapshot(t+1000000,algorithm_error='RuntimeError')['fresh'])
        c.publish(self.observation(2,accepted=False),b'late')
        self.assertFalse(c.snapshot(t+1000000)['fresh'])
        self.assertTrue(c.snapshot(t+1000000)['available'])

if __name__=='__main__':unittest.main()

"""Actual bounded IPC/process checks without a camera, CUDA or H.264 dependency."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np

from jetson_worktime.encoder_process import ProcessPublisher, draw_config
from jetson_worktime.runtime_quality import RuntimeQuality


@unittest.skipUnless(sys.platform == 'linux', 'Jetson Unix seqpacket transport')
class EncoderProcessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.log = self.root / 'encoded.jsonl'
        script = self.root / 'fake_worker.py'
        script.write_text('import json,time\nfrom jetson_worktime.encoder_process import worker_main\n'
            'class Sink:\n'
            ' def __init__(self,*args):pass\n'
            ' def write(self,image,received):\n'
            '  time.sleep(.05)\n'
            f'  with open({str(self.log)!r},"a") as f:f.write(json.dumps({{"pixel":int(image[0,0,0]),"received":received}})+"\\n")\n'
            ' def close(self):pass\n'
            'worker_main(Sink)\n')
        self.quality = RuntimeQuality()
        self.publisher = ProcessPublisher('raw',64,48,'local',self.quality,self.root,command=[sys.executable,str(script)])
        self.addCleanup(self.publisher.close)
        self.config = dict(revision=1,privacy={'enabled':True},operation={'detection_enabled':False},max_observation_age=1.5)

    def write(self, value, received=None):
        return self.publisher.write(np.full((48,64,3),value,np.uint8),
            time.monotonic_ns() if received is None else received,[],self.config,False,True)

    def records(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def wait_pixel(self, value):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            self.write(value)
            if any(x['pixel']==value for x in self.records()):return
            time.sleep(.05)
        self.fail('isolated worker did not publish the latest frame')

    def test_latest_only_mailbox_replaces_a_burst_instead_of_queuing_all_frames(self):
        self.wait_pixel(1)
        for value in range(2,102):self.write(value)
        self.wait_pixel(101)
        records=self.records()
        self.assertEqual(records[-1]['pixel'],101)
        self.assertLess(len(records),30)
        self.publisher.poll_updates()
        self.assertIn('encoder_submit_ms',self.quality.snapshot())

    def test_privacy_processed_pixels_are_transferred_without_substitution(self):
        self.wait_pixel(0)
        self.assertTrue(all(x['pixel']==0 for x in self.records()))
        self.config['privacy']['enabled']=False
        self.wait_pixel(200)

    def test_stale_source_is_not_published_but_fresh_source_recovers(self):
        self.write(42,time.monotonic_ns()-3_000_000_000)
        time.sleep(.4)
        self.assertEqual(self.records(),[])
        self.wait_pixel(43)
        self.assertNotIn(42,[x['pixel']for x in self.records()])

    def test_cancel_is_nonblocking_and_closes_the_process_and_mapping(self):
        self.wait_pixel(5)
        started=time.monotonic();self.publisher.cancel()
        self.assertLess(time.monotonic()-started,.1)
        self.assertFalse(self.write(8))
        self.publisher.close()
        self.assertIsNotNone(self.publisher.process.poll())
        self.assertIsNone(self.publisher.mapping)

    def test_changed_dimensions_cannot_reuse_an_old_mailbox(self):
        with self.assertRaisesRegex(ValueError,'dimensions'):
            self.publisher.write(np.zeros((50,64,3),np.uint8),time.monotonic_ns(),[],self.config,False,True)


class EncoderMetadataTests(unittest.TestCase):
    def test_only_drawing_metadata_crosses_the_process_boundary(self):
        value=draw_config({'privacy':{'enabled':True},'camera_source':{'password':'secret'},
            'max_observation_age':.8,'keypoint_confidence':.85,'_material_status':{'available':True,'detections':[],
                'reviews':[{'private':'history'}],'alerts':[{'region':'completed','private':'history'}]}})
        self.assertEqual(value['max_observation_age'],.8)
        self.assertEqual(value['keypoint_confidence'],.85)
        self.assertNotIn('camera_source',value)
        self.assertNotIn('reviews',value['_material_status'])
        self.assertEqual(value['_material_status']['alerts'],[{'region':'completed'}])

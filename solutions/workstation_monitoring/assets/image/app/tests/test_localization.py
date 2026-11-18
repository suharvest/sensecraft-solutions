from copy import deepcopy
import unittest
import cv2
import numpy as np
from jetson_worktime.localization import reason, reason_fields, LocalizedError, translate
from jetson_worktime.behavior import SessionEngine, classify
from jetson_worktime.overlay import draw_overlay, encode_overlays
from jetson_worktime.api import make_observation

CONFIG = dict(image_size=[640,360], regions={
    'station':[[10,10],[630,10],[630,350],[10,350]],
    'seat':[[250,100],[600,100],[600,330],[250,330]]}, revision=1,
    display=dict(boxes=True,regions=True,keypoints=True),privacy=dict(enabled=True))


class LocalizationTests(unittest.TestCase):
    def test_reason_metadata_preserves_existing_string_and_tuple_contracts(self):
        label, detail, persons = classify([],640,360,CONFIG)
        self.assertEqual(label,'MISSING')
        self.assertEqual(detail,'有效画面中未观察到工位人员')
        self.assertEqual(reason_fields(deepcopy(detail))['reason_code'],'reason.missing')
        engine=SessionEngine()
        engine.observe(0,'MISSING',reason=detail)
        self.assertEqual(engine.snapshot(0)['reason_code'],'reason.missing')
        stale=engine.snapshot(10)
        self.assertEqual(stale['reason_code'],'reason.stale')
        self.assertEqual(stale['reason_params'],{'seconds':1.5})
        error=LocalizedError('error.timingRange',field='start_seconds',minimum=.1)
        self.assertIsInstance(error,ValueError)
        self.assertEqual(error.message_key,'error.timingRange')

    def test_observation_carries_reason_details(self):
        observation=make_observation('run',dict(session_id='stream',receive_sequence=1),None,
            1,2,3,640,360,640,360,[],'MISSING',reason('reason.missing'),True,CONFIG,False)
        self.assertEqual(observation['inference']['reason_code'],'reason.missing')
        self.assertEqual(observation['inference']['reason_params'],{})

    def test_language_cache_isolated_and_geometry_and_privacy_layers_preserved(self):
        frame=np.zeros((360,640,3),np.uint8)
        chinese=draw_overlay(frame.copy(),[],CONFIG,locale='zh-CN')
        english=draw_overlay(frame.copy(),[],CONFIG,locale='en')
        self.assertFalse(np.array_equal(chinese,english))
        self.assertTrue(np.array_equal(chinese,draw_overlay(frame.copy(),[],CONFIG,locale='zh-CN')))
        variants=encode_overlays(frame,[],CONFIG)
        self.assertEqual(set(variants),{'zh-CN','en'})
        for data in variants.values():
            self.assertEqual(cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR).shape,frame.shape)
        hidden={**CONFIG,'display':dict(boxes=False,regions=False,keypoints=False)}
        self.assertEqual(encode_overlays(frame,[],hidden)['zh-CN'],encode_overlays(frame,[],hidden)['en'])
        self.assertTrue(np.array_equal(draw_overlay(frame.copy(),[],hidden,locale='en'),frame))
        self.assertEqual(translate('overlay.seat',locale='en'),'Presence zone')

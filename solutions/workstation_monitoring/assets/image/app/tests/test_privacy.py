from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
import yaml
from jetson_worktime.media import protect_frame, write_image, _head_bounds
from jetson_worktime.overlay import draw_overlay
from jetson_worktime.settings import SettingsStore


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.frame = np.random.default_rng(5).integers(0, 255, (200,200,3), dtype=np.uint8)
        self.config = dict(image_size=[200,200], revision=0, privacy={'enabled':True},
                           display=dict(boxes=True,regions=True,keypoints=True),
                           regions={'station':[[0,0],[199,0],[199,199],[0,199]],
                                    'seat':[[100,20],[190,20],[190,160],[100,160]]})
        keypoints = [dict(x=80+i*3, y=35+i*2, confidence=.9) for i in range(17)]
        self.person = dict(bbox_xyxy=[60,15,140,190], keypoints=keypoints)

    def test_head_mask_preserves_lower_body_and_input(self):
        before = self.frame.copy()
        output = protect_frame(self.frame, [self.person], self.config)
        self.assertTrue(np.array_equal(before,self.frame))
        bounds = _head_bounds(self.person,.4)
        x1,y1,x2,y2 = [max(0,int(v)) for v in bounds]
        patch=output[y1+1:y2-1,x1+1:x2-1]
        self.assertLessEqual(len(np.unique(patch.reshape(-1,3),axis=0)),100)
        self.assertGreater(len(np.unique(patch.reshape(-1,3),axis=0)),1)
        self.assertFalse(np.array_equal(patch,before[y1+1:y2-1,x1+1:x2-1]))
        self.assertTrue(np.array_equal(output[120:],before[120:]))

    def test_missing_head_masks_whole_person_and_bad_result_masks_frame(self):
        person = deepcopy(self.person)
        person['keypoints'] = []
        output = protect_frame(self.frame,[person],self.config)
        patch=output[15:190,60:140]
        self.assertLessEqual(len(np.unique(patch.reshape(-1,3),axis=0)),200)
        self.assertFalse(np.array_equal(patch,self.frame[15:190,60:140]))
        self.assertTrue(np.all(protect_frame(self.frame,None,self.config,reliable=False) == [38,44,42]))

    def test_disabled_privacy_and_empty_scene(self):
        self.assertTrue(np.array_equal(protect_frame(self.frame,[],self.config),self.frame))
        self.config['privacy']['enabled'] = False
        self.assertTrue(np.array_equal(protect_frame(self.frame,[self.person],self.config),self.frame))

    def test_multiple_people_and_clipped_bounds(self):
        people = [self.person, dict(bbox_xyxy=[-10,-10,30,100],keypoints=[])]
        output = protect_frame(self.frame,people,self.config)
        self.assertFalse(np.array_equal(output[:100,:30],self.frame[:100,:30]))
        self.assertLessEqual(len(np.unique(output[:100,:30].reshape(-1,3),axis=0)),100)
        self.assertFalse(np.array_equal(output[35:43,80:92],self.frame[35:43,80:92]))

    def test_profile_and_partial_head_keep_every_visible_landmark_in_core(self):
        person=deepcopy(self.person)
        person['keypoints']=[dict(x=None,y=None,confidence=0) for _ in range(17)]
        for i,x,y in ((0,105,32),(2,100,28),(4,94,31)):
            person['keypoints'][i]=dict(x=x,y=y,confidence=.9)
        bounds=_head_bounds(person,.4)
        self.assertNotEqual(bounds,person['bbox_xyxy'])
        for point in person['keypoints'][:5]:
            if point['x'] is not None:
                self.assertTrue(bounds[0]<point['x']<bounds[2] and bounds[1]<point['y']<bounds[3])
        person['keypoints'][4]['confidence']=.1
        self.assertEqual(_head_bounds(person,.4),person['bbox_xyxy'])

    def test_mosaic_core_is_fully_pixelated_and_feather_only_expands_outwards(self):
        from jetson_worktime.media import _mosaic
        original=self.frame.copy()
        image=original.copy()
        _mosaic(image,[40,40,160,160])
        core=image[40:160,40:160]
        self.assertLessEqual(len(np.unique(core.reshape(-1,3),axis=0)),100)
        self.assertTrue(np.array_equal(image[:20],original[:20]))
        self.assertTrue(np.array_equal(image[180:],original[180:]))
        self.assertFalse(np.array_equal(image[35:40,60:140],original[35:40,60:140]))

    def test_invalid_geometry_keeps_full_frame_failure_protection(self):
        for box in ([50,50,40,40],[1,2,float('nan'),100]):
            self.assertTrue(np.all(protect_frame(self.frame,[dict(bbox_xyxy=box)],self.config)==[38,44,42]))

    def test_all_layers_off_equals_protected_image(self):
        self.config['display'] = dict(boxes=False,regions=False,keypoints=False)
        protected = protect_frame(self.frame,[self.person],self.config)
        self.assertTrue(np.array_equal(draw_overlay(protected.copy(),[self.person],self.config),protected))

    def test_geometry_cache_changes_with_revision(self):
        empty = np.zeros_like(self.frame)
        first = draw_overlay(empty.copy(),[],self.config)
        self.config['regions']['seat'] = [[20,100],[70,100],[70,150],[20,150]]
        self.config['revision'] += 1
        second = draw_overlay(empty.copy(),[],self.config)
        self.assertFalse(np.array_equal(first,second))

    def test_diagnostic_writer_masks_unknown_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'behavior.yaml'
            path.write_text(yaml.safe_dump(self.config))
            output = Path(directory)/'diagnostic.png'
            write_image(output,self.frame,SettingsStore(path))
            self.assertTrue(np.all(cv2.imread(str(output)) == [38,44,42]))


if __name__ == '__main__':
    unittest.main()

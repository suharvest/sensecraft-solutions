from copy import deepcopy
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
import yaml
from jetson_worktime.settings import SettingsStore, SettingsConflict
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.overlay import draw_overlay
from jetson_worktime.visualization import DEFAULT_VISUALIZATION

CONFIG=dict(image_size=[200,200],regions={'station':[[0,0],[199,0],[199,199],[0,199]],'seat':[[100,80],[190,80],[190,190],[100,190]]})

class VisualizationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);(self.root/'configs').mkdir()
        self.path=self.root/'configs/behavior.yaml';self.path.write_text(yaml.safe_dump(CONFIG))
        self.store=SettingsStore(self.path)

    def test_legacy_defaults_and_saved_palette_survive_reload(self):
        before=self.path.read_bytes()
        self.assertEqual(self.store.snapshot()['visualization'],DEFAULT_VISUALIZATION)
        self.assertEqual(self.path.read_bytes(),before)
        palette=deepcopy(DEFAULT_VISUALIZATION);palette['colors']['seat']='#AABBCC';palette['station_fill_alpha']=.2
        result,changed,detection=self.store.commit(dict(expected_revision=0,visualization=palette))
        self.assertTrue(changed);self.assertFalse(detection)
        self.assertEqual(SettingsStore(self.path).snapshot()['visualization']['colors']['seat'],'#aabbcc')
        result,changed,_=self.store.commit(dict(expected_revision=1,visualization=palette))
        self.assertFalse(changed);self.assertEqual(result['revision'],1)
        with self.assertRaises(SettingsConflict):self.store.commit(dict(expected_revision=0,visualization=palette))

    def test_invalid_palettes_never_modify_disk(self):
        before=self.path.read_bytes()
        for change in ({'station_fill_alpha':True},{'station_fill_alpha':float('nan')},{'seat_fill_alpha':1.01},{'colors':{'station':'red'}}, {'unknown':1}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.store.commit(dict(expected_revision=0,visualization={**deepcopy(DEFAULT_VISUALIZATION),**change}))
            self.assertEqual(self.path.read_bytes(),before)

    def test_color_only_save_preserves_active_session_and_invalidates_media(self):
        service=BehaviorService(self.root,start_workers=False);self.addCleanup(service.close)
        now=time.monotonic();service.engine.observe(now,'SEATED');service.engine.manual('start',now)
        session=service.engine.current['session_id'];service.media={'old':True}
        palette=deepcopy(DEFAULT_VISUALIZATION);palette['colors']['person']='#123456'
        service.apply_settings(dict(expected_revision=0,visualization=palette),{})
        self.assertEqual(service.engine.current['session_id'],session)
        self.assertIsNone(service.media)
        self.assertEqual(len(service.engine.completed),0)

    def test_cached_region_fill_uses_saved_color_and_opacity(self):
        config=self.store.snapshot();config['display']=dict(boxes=False,regions=True,keypoints=False)
        config['visualization']=deepcopy(DEFAULT_VISUALIZATION)
        config['visualization']['station_fill_alpha']=0
        config['visualization']['seat_fill_alpha']=1
        config['visualization']['colors']['seat']='#ff0000'
        frame=np.full((200,200,3),80,np.uint8)
        output=draw_overlay(frame.copy(),[],config,fresh=False)
        self.assertEqual(output[150,150].tolist(),[0,0,255])
        config['visualization']['colors']['seat']='#00ff00'
        output=draw_overlay(frame.copy(),[],config,fresh=False)
        self.assertEqual(output[150,150].tolist(),[0,255,0])

    def test_failed_palette_save_keeps_configuration_and_session(self):
        from unittest.mock import patch
        service=BehaviorService(self.root,start_workers=False);self.addCleanup(service.close)
        now=time.monotonic();service.engine.observe(now,'SEATED');service.engine.manual('start',now)
        session=service.engine.current['session_id'];before=self.path.read_bytes()
        palette=deepcopy(DEFAULT_VISUALIZATION);palette['seat_fill_alpha']=.3
        with patch('jetson_worktime.settings.os.replace',side_effect=OSError('full disk')):
            with self.assertRaises(OSError):service.apply_settings(dict(expected_revision=0,visualization=palette),{})
        self.assertEqual(service.engine.current['session_id'],session)
        self.assertEqual(self.path.read_bytes(),before)

    def test_regions_are_independent_and_legacy_switch_is_inherited(self):
        config=self.store.snapshot()
        self.assertTrue(config['display']['station'] and config['display']['seat'])
        config['display'].update(boxes=False,keypoints=False,station=True,seat=False)
        config['visualization']['station_fill_alpha']=1
        config['visualization']['colors']['station']='#0000ff'
        frame=np.full((200,200,3),80,np.uint8)
        image=draw_overlay(frame.copy(),[],config,fresh=False)
        self.assertGreater(int(image[150,150,0]),int(image[80,150,0]))
        self.assertLess(int(image[150,150,1]),80)
        self.assertLess(int(image[150,150,0]),255)
        config['display'].update(station=False,seat=True)
        config['visualization']['seat_fill_alpha']=1
        config['visualization']['colors']['seat']='#ff0000'
        image=draw_overlay(frame.copy(),[],config,fresh=False)
        self.assertEqual(image[150,150].tolist(),[0,0,255])
        self.assertEqual(image[150,50].tolist(),[80,80,80])
        saved,_,changed=self.store.commit(dict(expected_revision=0,display=dict(boxes=True,keypoints=False,regions=False)))
        self.assertFalse(changed)
        self.assertFalse(saved['display']['station'] or saved['display']['seat'])


class StationGradientTests(unittest.TestCase):
    def test_gradient_feathers_inside_and_has_no_perimeter(self):
        from jetson_worktime.overlay import draw_overlay
        config=deepcopy(CONFIG);config['regions']['station']=[[20,20],[180,20],[180,180],[20,180]]
        config['display']={'boxes':False,'station':True,'seat':False,'keypoints':False}
        config['visualization']=deepcopy(DEFAULT_VISUALIZATION)
        config['visualization']['colors']['station']='#0000ff';config['visualization']['station_fill_alpha']=.4
        image=np.full((200,200,3),80,np.uint8);out=draw_overlay(image.copy(),[],config)
        self.assertTrue(np.array_equal(out[150,10],image[150,10]))
        self.assertGreater(int(out[150,100,0]),int(out[80,100,0]))
        self.assertLess(int(out[150,20,0]),int(out[150,100,0]))
        self.assertLess(int(out[150,20,0]),120)  # no fully colored outline

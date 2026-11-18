"""Real production HTTP dispatcher, without camera or GPU processes."""
import ast
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit,parse_qs
import cv2
import numpy as np
import yaml
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.studio_http import StudioHTTP
from jetson_worktime.studio_store import StudioError
from jetson_worktime.localization import LocalizedError
from jetson_worktime.deployment import maintenance

ROOT=Path(__file__).resolve().parents[1]
class StudioHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'configs').mkdir()
        config=dict(image_size=[100,100],regions={'station':[[0,0],[99,0],[99,99],[0,99]],'seat':[[10,10],[90,10],[90,90],[10,90]]},privacy={'enabled':False})
        (self.root/'configs/behavior.yaml').write_text(yaml.safe_dump(config))
        self.service=BehaviorService(self.root,start_workers=False)
        tree=ast.parse((ROOT/'scripts/preview.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Handler')
        namespace=dict(BaseHTTPRequestHandler=BaseHTTPRequestHandler,studio_http=StudioHTTP(self.service.studio),behavior=self.service,
            StudioError=StudioError,LocalizedError=LocalizedError,maintenance=maintenance,json=json,urlsplit=urlsplit,parse_qs=parse_qs)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'production_http','exec'),namespace)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),namespace['Handler']);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}/api/v1/'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.service.close();self.temp.cleanup()
    def api(self,path,data=None,method=None,raw=None,headers=None):
        req=Request(self.base+path,data=raw if raw is not None else json.dumps(data).encode() if data is not None else None,
            method=method or ('POST' if raw is not None or data is not None else 'GET'),headers={'Content-Type':'application/octet-stream' if raw else 'application/json',**(headers or {})})
        try:
            with urlopen(req,timeout=5) as response:return response.status,json.load(response)
        except HTTPError as error:return error.code,json.load(error)
    def project(self):return self.api('datasets',{'name':'test','class_name':'part'})[1]
    def image(self,ds,group):
        ok,jpeg=cv2.imencode('.jpg',np.full((30,40,3),group*50,np.uint8));assert ok
        return self.api('datasets/'+ds['id']+'/images?group='+str(group),raw=jpeg.tobytes())[1]
    def test_models_metadata_and_same_origin(self):
        status,result=self.api('models');self.assertEqual(status,200);self.assertNotIn('path',result['models'][0])
        status,result=self.api('datasets',{'name':'x','class_name':'x'},headers={'Origin':'http://other.invalid'})
        self.assertEqual(status,403)
        self.assertEqual(self.api('models/downloads',{'catalog_id':'https://other.invalid/model.pt'})[0],400)
    def test_annotation_conflict_and_grouped_snapshot(self):
        ds=self.project()
        for group in range(3):
            image=self.image(ds,group);path='datasets/'+ds['id']+'/images/'+image['id']+'/annotations'
            payload={'boxes':[[1,1,10,10]],'annotated':True,'expected_revision':image['revision']}
            self.assertEqual(self.api(path,payload,'PUT')[0],200)
            self.assertEqual(self.api(path,payload,'PUT')[0],409)
        ds=self.api('datasets/'+ds['id'])[1]
        status,snapshot=self.api('datasets/'+ds['id']+'/snapshots',{'expected_revision':ds['revision'],'ratios':[80,10,10]})
        self.assertEqual(status,200);self.assertEqual(snapshot['counts'],dict(train=1,val=1,test=1));self.assertNotIn('directory',snapshot)
    def test_invalid_files_and_boxes_rejected(self):
        ds=self.project()
        self.assertEqual(self.api('datasets/'+ds['id']+'/images?group=x',raw=b'not an image')[0],400)
        image=self.image(ds,1);path='datasets/'+ds['id']+'/images/'+image['id']+'/annotations'
        self.assertEqual(self.api(path,{'boxes':[[0,0,400,400]],'annotated':True,'expected_revision':1},'PUT')[0],400)
        self.assertEqual(self.api(path,{'boxes':[],'annotated':True},'PUT')[0],409)
    def test_capture_without_valid_matching_frame_fails_closed(self):
        ds=self.project();self.assertEqual(self.api('datasets/'+ds['id']+'/captures',{'group_id':'g'})[0],409)
    def test_event_evidence_is_persisted_and_obeys_current_privacy_policy(self):
        from types import SimpleNamespace
        self.service.transport=SimpleNamespace(condition=threading.Condition(),output_sockets=set(),close=lambda:None)
        store=self.service.studio.store
        event=store.event('evidence-session','review','item',0,config_revision=0,frame_sequence=17,
                          stream_session_id='stream',review_reason='completion_unverified')
        frame=np.full((100,100,3),93,np.uint8)
        self.service.evidence_writer.submit([event],frame,self.service.config)
        self.service.evidence_writer.queue.join()
        status,history=self.api('materials/sessions/evidence-session')
        self.assertEqual(status,200);self.assertEqual(history['events'][0]['frame_sequence'],17)
        path=history['events'][0]['evidence_frame_url'];self.assertTrue(path)
        url=self.base.split('/api/v1/')[0]+path
        with urlopen(url,timeout=5) as response:
            self.assertEqual(response.status,200)
            decoded=cv2.imdecode(np.frombuffer(response.read(),np.uint8),cv2.IMREAD_COLOR)
            self.assertLess(abs(float(decoded.mean())-93),2)
        self.service.config,_,_=self.service.store.commit({'expected_revision':0,'privacy':{'enabled':True}})
        self.assertIsNone(self.api('materials/sessions/evidence-session')[1]['events'][0]['evidence_frame_url'])
        with self.assertRaises(HTTPError) as result:urlopen(url,timeout=5)
        self.assertEqual(result.exception.code,404)
        self.assertEqual(self.api('materials/evidence/not-an-event.jpg')[0],404)
        self.service.config,_,_=self.service.store.commit({'expected_revision':1,'privacy':{'enabled':False}})
        with urlopen(url,timeout=5) as response:
            self.assertEqual(response.status,200)
            self.assertEqual(response.headers['X-Evidence-Config-Revision'],'0')
    def test_training_requires_healthy_supervisor(self):
        status,value=self.api('training/jobs',{'token':'valid-token','expected_revision':0})
        self.assertEqual(status,503);self.assertEqual(value['error']['message_key'],'studio.error.agentOffline')

    def test_material_display_save_preserves_active_session(self):
        from copy import deepcopy
        model_path=self.root/'models/yolo11n-pose.pt';model_path.parent.mkdir();model_path.write_bytes(b'metadata-fixture')
        from jetson_worktime.studio_store import digest
        meta=self.service.studio.store.get('model','builtin-person');meta.update(sha256=digest(model_path),installed=True);self.service.studio.store.put('model',meta)
        self.service.engine._start(time.monotonic())
        session_id=self.service.engine.current['session_id']
        material=deepcopy(self.service.config['materials']);material['colors']['pending']='#123456';material['display']['pending']=False
        result=self.service.apply_settings({'expected_revision':0,'materials':material},{})
        self.assertEqual(result['revision'],1)
        self.assertEqual(self.service.engine.current['session_id'],session_id)

    def test_camera_confirmation_cannot_reactivate_old_material_zones(self):
        from copy import deepcopy
        from jetson_worktime.studio_store import digest
        model_path=self.root/'models/yolo11n-pose.pt';model_path.parent.mkdir();model_path.write_bytes(b'metadata-fixture')
        meta=self.service.studio.store.get('model','builtin-person');meta.update(sha256=digest(model_path),installed=True);self.service.studio.store.put('model',meta)
        material=deepcopy(self.service.config['materials']);material.update(configured=True,regions={'pending':[[1,1],[30,1],[30,30],[1,30]],'completed':[[60,1],[90,1],[90,30],[60,30]]})
        self.service.config,_,_=self.service.store.commit({'expected_revision':0,'materials':material})
        self.service.camera_changed=True
        self.service.action('confirm_camera')
        self.assertFalse(self.service.config['materials']['configured'])
        self.assertFalse(self.service.config['materials']['enabled'])
        self.assertEqual(self.service.config['materials']['regions'],{'pending':[],'completed':[]})

    def test_failed_gpu_activation_restores_previous_model_and_exposes_error(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import gc
        service=self.service
        service.config,_,_=service.store.commit({'expected_revision':0,'models':{'person':'builtin-person','material':'bad'}})
        service.submit(np.zeros((100,100,3),np.uint8),0,time.monotonic_ns(),{'session_id':'s','receive_sequence':1})
        def factory(path):
            def predict(*args,**kwargs):
                if path=='bad':
                    service.stop.set()
                    raise RuntimeError('GPU allocation failed')
            return SimpleNamespace(predict=predict)
        torch=SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:None,synchronize=lambda:None))
        try:
            with patch.object(service.studio,'model',side_effect=lambda ident,*args:{'path':ident}):
                service._run_models(torch,cv2,factory,lambda *a:[],gc)
            self.assertIsNone(service.config['models']['material'])
            self.assertEqual(service.model_activation_error['code'],'modelActivation')
            status,result=self.api('models')
            self.assertEqual(status,200);self.assertEqual(result['activation_error']['code'],'modelActivation')
        finally:
            service.stop.clear();service.gpu_lease.release()

import concurrent.futures
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from jetson_worktime.materials import MATERIAL_DEFAULTS, MaterialCounter, validate_materials
from jetson_worktime.studio import Studio
from jetson_worktime.studio_store import StudioError, StudioStore, atomic
from jetson_worktime.training import TrainingQueue, GpuLease


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.studio=Studio(self.root);self.store=self.studio.store
    def tearDown(self): self.temp.cleanup()

    def test_idempotency_atomic_across_threads(self):
        def once(_):
            return self.store.operation('test','same-token-123',lambda db:self.store.event('s','adjust','k',1,db))
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            values=list(pool.map(once,range(12)))
        self.assertEqual(len({v['id'] for v in values}),1)
        self.assertEqual(self.store.total('s'),1)

    def test_versions_and_failure_do_not_change_record(self):
        v=self.store.put('thing',{'id':'a','count':1});self.assertEqual(v['revision'],1)
        with self.assertRaises(StudioError):self.store.put('thing',{'id':'a','count':2},0)
        self.assertEqual(self.store.get('thing','a')['count'],1)
        with self.assertRaises(ValueError):self.store.put('thing',{'id':'a','count':float('nan')},1)
        self.assertEqual(self.store.get('thing','a')['count'],1)

    def make_dataset(self):
        ds=self.studio.create_dataset({'name':'Modules','class_name':'module'})
        for group in range(5):
            for index in range(3):
                ident=f'image-{group}-{index}';path=self.root/'images'/(ident+'.jpg');atomic(path,ident.encode())
                self.store.put('image',dict(id=ident,dataset_id=ds['id'],group_id=str(group),path=str(path),sha256=hashlib.sha256(ident.encode()).hexdigest(),
                    width=100,height=100,boxes=[[10,10,30,30]],annotated=True))
        return ds

    def test_snapshots_are_grouped_and_immutable(self):
        ds=self.make_dataset();snap=self.studio.snapshot(ds['id'],{'expected_revision':ds['revision'],'ratios':[80,10,10]})
        root=Path(snap['directory']);manifest=json.loads((root/'manifest.json').read_text())
        groups=[{im['group_id'] for im in v} for v in manifest.values()]
        self.assertFalse(groups[0]&groups[1] or groups[1]&groups[2] or groups[0]&groups[2])
        self.assertEqual(sum(snap['counts'].values()),15)
        image=self.store.list('image')[0]
        self.studio.annotate(ds['id'],image['id'],{'expected_revision':image['revision'],'boxes':[],'annotated':True})
        self.assertEqual(hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),snap['sha256'])
        self.assertTrue(all(im['boxes'] for values in manifest.values() for im in values))

    def test_dataset_validation_and_conflicts(self):
        ds=self.make_dataset();im=self.store.list('image')[0]
        for box in ([[0,0,101,40]],[[30,0,10,40]],[[0,0,float('nan'),20]]):
            with self.assertRaises(StudioError):self.studio.annotate(ds['id'],im['id'],{'expected_revision':im['revision'],'boxes':box,'annotated':True})
        with self.assertRaises(StudioError):self.studio.snapshot(ds['id'],{'expected_revision':0,'ratios':[80,10,10]})
        for ratios in ([100,0,0],[80,10,11],[80,True,19]):
            with self.assertRaises(StudioError):self.studio.snapshot(ds['id'],{'expected_revision':ds['revision'],'ratios':ratios})

    def test_three_positive_groups_required(self):
        ds=self.studio.create_dataset({'name':'one','class_name':'part'})
        with self.assertRaises(StudioError) as e:self.studio.snapshot(ds['id'],{'expected_revision':ds['revision']})
        self.assertEqual(e.exception.code,'splitGroups')

    def test_training_queue_is_idempotent_validates_and_allows_one(self):
        ds=self.make_dataset();snapshot=self.studio.snapshot(ds['id'],{'expected_revision':ds['revision']})
        weight=self.root/'base.pt';atomic(weight,b'base')
        model=self.store.put('model',dict(id='base',name='YOLO11n',role='material',path=str(weight),sha256=hashlib.sha256(b'base').hexdigest(),source='official'))
        queue=TrainingQueue(self.studio)
        request=dict(token='queue-token-123',snapshot_id=snapshot['id'],base_model_id=model['id'],parameters={})
        job=queue.create(request);self.assertEqual(job['parameters']['optimizer'],'AdamW');self.assertEqual(job['parameters']['batch'],4)
        self.assertEqual(queue.create(request),job)
        with self.assertRaises(StudioError):queue.create({**request,'token':'other-token-123'})
        paused=queue.action(job['id'],dict(token='stop-token-123',action='stop',expected_revision=job['revision']))
        self.assertEqual(paused['state'],'paused')
        with self.assertRaises(StudioError):queue.create({**request,'token':'invalid-token','parameters':{'lr0':True}})
        with self.assertRaises(StudioError):queue.action(job['id'],dict(token='resume-token',action='resume'))

    def test_gpu_lease_exclusive_and_released(self):
        a=GpuLease(self.store.data);b=GpuLease(self.store.data)
        self.assertTrue(a.acquire());self.assertFalse(b.acquire());a.release();self.assertTrue(b.acquire());b.release()

    def test_changed_model_bytes_cannot_reuse_verified_metadata(self):
        path=self.root/'custom.pt';path.write_bytes(b'good-weights')
        self.store.put('model',dict(id='custom',role='material',path=str(path),sha256=hashlib.sha256(b'good-weights').hexdigest()))
        self.assertEqual(self.studio.model('custom')['id'],'custom')
        path.write_bytes(b'corrupt-weights')
        with self.assertRaises(StudioError) as error:self.studio.model('custom')
        self.assertEqual(error.exception.code,'checksum')

    def test_builtin_model_cannot_be_removed(self):
        item=self.store.get('model','builtin-person')
        with self.assertRaises(StudioError):self.studio.remove_model('builtin-person',item['revision'],{'models':{}})


class CountingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=StudioStore(Path(self.temp.name));self.counter=MaterialCounter(self.store)
        mat=deepcopy(MATERIAL_DEFAULTS);mat.update(enabled=True,configured=True,regions={'pending':[[0,0],[90,0],[90,99],[0,99]],'completed':[[100,0],[199,0],[199,99],[100,99]]})
        self.config=dict(revision=1,image_size=[200,100],materials=mat)
    def tearDown(self):self.temp.cleanup()
    def objects(self,n,side='completed'):
        x=105 if side=='completed' else 5
        return [dict(class_id=0,confidence=.9,bbox_xyxy=[x+16*i,20,x+16*i+10,40]) for i in range(n)]
    def observe(self,t,n,session='s',side='completed'):
        self.counter.observe(self.objects(n,side),t,self.config,session,session_started=0)
    def test_initial_five_and_new_session_count_inventory(self):
        self.observe(0,5);self.observe(1,5)
        self.assertEqual(self.store.total('s'),5)
        self.observe(1,5);self.observe(2,5)
        self.assertEqual(self.store.total('s'),5)
        self.observe(3,5,'next')
        self.assertEqual(self.store.total('next'),5)
    def test_new_arrival_removal_and_short_return(self):
        self.observe(0,1);self.observe(1,1);self.observe(2,2);self.observe(3,2)
        self.assertEqual(self.store.total('s'),2)
        self.observe(3.5,0);self.observe(4,2)
        self.assertEqual(self.store.total('s'),2)
        self.observe(7,0);self.assertEqual(self.store.total('s'),2)
    def test_long_return_requires_review_and_resolution_is_once(self):
        self.observe(0,1);self.observe(1,1);self.observe(4,0);self.observe(5,1);self.observe(6,1)
        status=self.counter.snapshot(6,self.config,True,'s')
        self.assertEqual(len(status['reviews']),1);self.assertEqual(status['cumulative'],1)
        event=status['reviews'][0]
        request=dict(token='resolution-token',delta=0,reason='return',event_id=event['id'],expected_total=1)
        a=self.counter.adjust('s',request);self.assertEqual(a,self.counter.adjust('s',request));self.assertFalse(self.counter.snapshot(6,self.config,True,'s')['reviews'])
    def test_continuously_tracked_pending_product_still_counts_after_collection(self):
        self.observe(0,1);self.observe(1,1);self.observe(4,0)
        def sample(t,box):self.counter.observe([dict(class_id=0,confidence=.9,bbox_xyxy=box)],t,self.config,'s',session_started=0)
        sample(5,[50,20,90,60]);sample(6,[50,20,90,60]);sample(6.5,[70,20,110,60]);sample(7,[90,20,130,60]);sample(8,[90,20,130,60]);sample(8.5,[90,20,130,60])
        result=self.counter.snapshot(8.5,self.config,True,'s')
        self.assertEqual(result['cumulative'],2);self.assertFalse(result['reviews'])

    def test_no_session_and_stale_are_not_zero(self):
        self.observe(0,2,None);self.observe(1,2,None)
        self.assertEqual(self.store.total('s'),0)
        self.assertIsNone(self.counter.snapshot(10,self.config,True)['completed'])
        self.assertEqual(self.counter.snapshot(1,self.config,True)['completed'],2)
        self.assertIsNone(self.counter.snapshot(1,self.config,False)['completed'])
    def test_adjustment_conflicts_and_negative_totals(self):
        self.observe(0,1);self.observe(1,1)
        req=dict(token='adjustment-token',delta=-2,reason='correction',expected_total=1)
        with self.assertRaises(StudioError):self.counter.adjust('s',req)
        req.update(delta=3);self.assertEqual(self.counter.adjust('s',req)['cumulative'],4)
        self.assertEqual(self.counter.adjust('s',req)['cumulative'],4)
        with self.assertRaises(StudioError):self.counter.adjust('s',{**req,'token':'different-token'})
    def test_material_geometry_does_not_depend_on_seat(self):
        self.assertEqual(validate_materials(self.config['materials'],[200,100]),self.config['materials'])
        bad=deepcopy(self.config['materials']);bad['regions']['pending']=bad['regions']['completed']
        with self.assertRaises(StudioError):validate_materials(bad,[200,100])
        bad=deepcopy(self.config['materials']);bad['sample_hz']=float('nan')
        with self.assertRaises(StudioError):validate_materials(bad,[200,100])


class RestartProbeTests(unittest.TestCase):
    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'start.sh').exists(), 'Native launcher is outside the container snapshot')
    def test_restart_accepts_closed_http_socket_but_rejects_active_listener(self):
        import ast
        import socket
        script=(Path(__file__).resolve().parents[1]/'start.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        tree=ast.parse(script)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_port_available')
        namespace={'socket':socket};exec(compile(ast.Module(body=[node],type_ignores=[]),'launcher_probe','exec'),namespace)
        probe=namespace['check_port_available']
        listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('0.0.0.0',0));listener.listen(1);port=listener.getsockname()[1]
        try:
            with self.assertRaises(OSError):probe(port)
            client=socket.create_connection(('127.0.0.1',port));conn,_=listener.accept();conn.close();client.close()
        finally:listener.close()
        probe(port)


class CheckpointTests(unittest.TestCase):
    def test_corrupt_primary_and_partial_commit_preserve_healthy_fallback(self):
        from unittest.mock import patch
        from jetson_worktime.training import save_checkpoint,find_checkpoint
        from jetson_worktime.studio_store import atomic as real_atomic
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.pt'
            source.write_bytes(b'epoch-one');save_checkpoint(root,source,1)
            source.write_bytes(b'epoch-two');save_checkpoint(root,source,2)
            (root/'resume.pt').write_bytes(b'broken')
            self.assertEqual(find_checkpoint(root).name,'previous.pt')
            source.write_bytes(b'epoch-three');save_checkpoint(root,source,3)
            self.assertEqual((root/'previous.pt').read_bytes(),b'epoch-one')
            source.write_bytes(b'epoch-four')
            def fail_metadata(path,data):
                if Path(path).name=='resume.json':raise OSError('simulated power loss')
                return real_atomic(path,data)
            with patch('jetson_worktime.training.atomic',side_effect=fail_metadata):
                with self.assertRaises(OSError):save_checkpoint(root,source,4)
            self.assertEqual(find_checkpoint(root).name,'previous.pt')
            self.assertEqual(find_checkpoint(root).read_bytes(),b'epoch-three')

class MultiClassTests(StudioTests):
    def test_multiclass_export_and_snapshot_names_are_frozen(self):
        import yaml
        ds=self.make_dataset();ds=self.studio.update_classes(ds['id'],dict(action='add',name='second',expected_revision=ds['revision']))
        for im in self.studio.dataset(ds['id'])['images']:
            self.studio.annotate(ds['id'],im['id'],dict(boxes=[[10,10,30,30,0],[40,40,60,60,1]],annotated=True,expected_revision=im['revision']))
        ds=self.studio.dataset(ds['id']);snap=self.studio.snapshot(ds['id'],dict(expected_revision=ds['revision']))
        self.assertEqual(yaml.safe_load((Path(snap['directory'])/'data.yaml').read_text())['names'],{0:'module',1:'second'})
        for p in (Path(snap['directory'])/'labels').rglob('*.txt'):self.assertEqual([l.split()[0] for l in p.read_text().splitlines()],['0','1'])
        ds=self.studio.update_classes(ds['id'],dict(action='rename',class_id=1,name='renamed',expected_revision=ds['revision']))
        with self.assertRaises(StudioError):self.studio.update_classes(ds['id'],dict(action='delete',class_id=1,expected_revision=ds['revision']))
        self.assertEqual(yaml.safe_load((Path(snap['directory'])/'data.yaml').read_text())['names'][1],'second')

    def test_class_ids_are_not_reused_and_unknown_labels_rejected(self):
        ds=self.make_dataset();ds=self.studio.update_classes(ds['id'],dict(action='add',name='unused',expected_revision=ds['revision']))
        ds=self.studio.update_classes(ds['id'],dict(action='delete',class_id=1,expected_revision=ds['revision']))
        ds=self.studio.update_classes(ds['id'],dict(action='add',name='third',expected_revision=ds['revision']))
        self.assertEqual(set(ds['classes']),{'0','2'})
        im=self.studio.dataset(ds['id'])['images'][0]
        with self.assertRaises(StudioError):self.studio.annotate(ds['id'],im['id'],dict(boxes=[[1,1,3,3,1]],annotated=True,expected_revision=im['revision']))
        with self.assertRaises(StudioError):self.studio.update_classes(ds['id'],dict(action='rename',class_id=2,name='MODULE',expected_revision=ds['revision']))

    def test_download_unknown_size_reports_verification_and_checksum_failure(self):
        import io
        from unittest.mock import patch
        payload=b'official-test-model';(self.root/'configs').mkdir(exist_ok=True)
        (self.root/'configs/model-catalog.json').write_text(json.dumps({'yolo11n':{'sha256':hashlib.sha256(payload).hexdigest()}}))
        states=[];original=self.store.put
        def record(kind,value,*args,**kwargs):
            if kind=='download':states.append(value['state'])
            return original(kind,value,*args,**kwargs)
        for data,expected in [(payload,'completed'),(b'corrupted','failed')]:
            source=io.BytesIO(data);source.headers={}
            item=self.store.put('download',dict(id=__import__('uuid').uuid4().hex,catalog_id='yolo11n',state='queued',bytes=0,total=None))
            with patch('urllib.request.urlopen',return_value=source),patch.object(self.studio,'import_model',return_value={'id':'verified','sha256':'test'}),patch.object(self.store,'put',side_effect=record):self.studio._download(item)
            result=self.store.get('download',item['id']);self.assertEqual(result['state'],expected);self.assertIsNone(result['total']);self.assertEqual(result['bytes'],len(data))
        self.assertIn('validating',states)

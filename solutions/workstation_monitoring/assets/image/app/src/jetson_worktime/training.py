"""Persistent training queue, process identity and cross-process GPU ownership."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from .studio import Studio, ACTIVE_JOBS, public
from .studio_store import StudioError, atomic, digest, uid


def boot_id():
    try: return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError: return ''


def process_start(pid):
    try:
        fields=Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0]=='Z' else fields[19]
    except (OSError,ValueError,IndexError,TypeError): return None


def valid_checkpoint(path):
    path=Path(path)
    try:
        meta=json.loads(path.with_suffix('.json').read_text())
        return path.is_file() and digest(path)==meta['sha256'] and type(meta['epoch']) is int
    except (OSError,ValueError,KeyError): return False


def find_checkpoint(directory):
    candidates=[Path(directory)/name for name in ('resume.pt','previous.pt')]
    candidates=[p for p in candidates if valid_checkpoint(p)]
    return max(candidates,key=lambda p:json.loads(p.with_suffix('.json').read_text())['epoch']) if candidates else None


def save_checkpoint(directory,source,epoch):
    directory=Path(directory);resume=directory/'resume.pt'
    # Never rotate damaged primary data over the only healthy fallback.
    if valid_checkpoint(resume):
        atomic(directory/'previous.pt',resume.read_bytes())
        atomic(directory/'previous.json',resume.with_suffix('.json').read_bytes())
    data=Path(source).read_bytes()
    atomic(resume,data)
    atomic(directory/'resume.json',json.dumps(dict(sha256=hashlib.sha256(data).hexdigest(),epoch=epoch)).encode())


class GpuLease:
    def __init__(self, data):
        self.path=Path(data)/'gpu.lock';self.handle=None

    def acquire(self):
        if self.handle is not None: return True
        handle=self.path.open('a')
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close();return False
        self.handle=handle;return True

    def release(self):
        if self.handle:
            fcntl.flock(self.handle,fcntl.LOCK_UN);self.handle.close();self.handle=None


class TrainingQueue:
    def __init__(self, studio):
        self.studio=studio;self.store=studio.store

    def create(self, request):
        model=self.studio.model(request.get('base_model_id'),'material')
        if model.get('source')!='official': raise StudioError('baseModel')
        snapshot=self.store.get('snapshot',request.get('snapshot_id'))
        params=request.get('parameters',{})
        if not isinstance(params,dict) or set(params)-{'epochs','lr0','batch'}: raise StudioError('trainingParams')
        epochs=params.get('epochs',100);lr=params.get('lr0',.001)
        import psutil
        default_batch = 1 if psutil.virtual_memory().total < 12*1024**3 else (4 if model['name']=='YOLO11n' else 1)
        batch=params.get('batch', default_batch)
        if (type(epochs) is not int or not 1<=epochs<=1000 or type(batch) is not int or not 1<=batch<=16
            or isinstance(lr,bool) or not isinstance(lr,(int,float)) or not 1e-6<=lr<=.1):
            raise StudioError('trainingParams')
        fixed=dict(epochs=epochs,lr0=lr,batch=batch,optimizer='AdamW',warmup_bias_lr=0.0,imgsz=640,workers=0,seed=42,patience=20,device=0,amp=True)
        def create(db):
            if any(j['state'] in ACTIVE_JOBS for j in self.store.list('job',db)): raise StudioError('busy',409)
            job=dict(id=uid(),base_model_id=model['id'],base_sha256=model['sha256'],snapshot_id=snapshot['id'],
                snapshot_sha256=snapshot['sha256'],parameters=fixed,state='queued',stage='queued',progress=0.,epoch=0,
                created_at=time.time(),control_revision=1,metrics={},error=None,command=None,stop_requested=None,checkpoint=None)
            return public(self.store.put('job',job,db=db))
        return self.store.operation('training',request.get('token'),create)

    def action(self, ident, request):
        action=request.get('action')
        if action not in ('stop','cancel','resume'): raise StudioError('trainingParams')
        def apply(db):
            job=self.store.get('job',ident,db)
            if request.get('expected_revision') is not None and request['expected_revision']!=job.get('control_revision',1):
                raise StudioError('conflict',409)
            if action=='resume':
                if job['state'] not in ('paused','interrupted','failed') or not job.get('checkpoint'): raise StudioError('checkpoint')
                if any(j['state'] in ACTIVE_JOBS for j in self.store.list('job',db)): raise StudioError('busy',409)
                job.update(state='queued',stage='queued',stop_requested=None,error=None,resuming=True)
                for key in ('pid','pid_start','boot_id','signal_sent'): job.pop(key,None)
            else:
                if job['state'] not in ACTIVE_JOBS: raise StudioError('conflict',409)
                if job['state']=='queued':
                    job.update(state='cancelled' if action=='cancel' else 'paused',stage='stopped')
                else:
                    job.update(stop_requested=action,stop_requested_at=time.time(),state='stopping')
            job['control_revision']=job.get('control_revision',1)+1
            return public(self.store.put('job',job,db=db))
        return self.store.operation('job:'+ident,request.get('token'),apply)

    def recover(self):
        for job in self.store.list('job'):
            if job['state'] in ACTIVE_JOBS and job.get('pid'):
                started=process_start(job['pid'])
                alive=bool(started is not None and job.get('boot_id')==boot_id() and started==job.get('pid_start'))
                if not alive:
                    directory=self.store.data/'training'/job['id']
                    found=find_checkpoint(directory)
                    if found: job['checkpoint']=found.name
                    state='cancelled' if job.get('stop_requested')=='cancel' else 'paused' if job.get('stop_requested') else 'interrupted'
                    job.update(state=state,stage=state,error=None if job.get('stop_requested') else 'interrupted')
                    self.store.put('job',job)

    def tick(self):
        self.recover()
        for job in self.store.list('job'):
            if job['state']=='queued':
                directory=self.store.data/'training'/job['id'];directory.mkdir(parents=True,exist_ok=True)
                # Persist preparing before spawn; a restarted web process sees the same gate.
                job.update(state='preparing',stage='preparing',boot_id=boot_id(),directory=str(directory))
                self.store.put('job',job)
                try:
                    with (directory/'worker.log').open('ab') as log:
                        worker=subprocess.Popen([sys.executable,str(self.studio.root/'scripts/studio_train_worker.py'),job['id']],
                            cwd=self.studio.root,stdout=log,stderr=log,start_new_session=True)
                except OSError:
                    with self.store.transaction() as db:
                        current=self.store.get('job',job['id'],db);current.update(state='failed',stage='failed',error='workerStart');self.store.put('job',current,db=db)
                    return
                with self.store.transaction() as db:
                    current=self.store.get('job',job['id'],db)
                    current.update(pid=worker.pid,pid_start=process_start(worker.pid),boot_id=boot_id())
                    self.store.put('job',current,db=db)
                return
            if job['state']=='stopping' and job.get('stop_requested_at') and time.time()-job['stop_requested_at']>30:
                started=process_start(job.get('pid'))
                if started is not None and job.get('boot_id')==boot_id() and started==job.get('pid_start'):
                    try:
                        elapsed=time.time()-job['stop_requested_at']
                        if elapsed>35: os.killpg(job['pid'],signal.SIGKILL)
                        elif not job.get('signal_sent'):
                            os.killpg(job['pid'],signal.SIGTERM)
                            with self.store.transaction() as db:
                                current=self.store.get('job',job['id'],db);current['signal_sent']=True;self.store.put('job',current,db=db)
                    except ProcessLookupError: pass


def resource_preflight(model, snapshot, params):
    """Use real labelled images, batch and optimizer; never silently shrink a job."""
    import cv2
    import gc
    import numpy as np
    import torch
    from ultralytics.nn.tasks import DetectionModel
    manifest=json.loads((Path(snapshot['directory'])/'manifest.json').read_text())
    samples=manifest['train']
    images=[];indices=[];classes=[];boxes=[]
    for n in range(params['batch']):
        entry=samples[n%len(samples)]
        image=cv2.imread(str(Path(snapshot['directory'])/'images/train'/(entry['image_id']+'.jpg')))
        if image is None: raise StudioError('imageInvalid')
        h,w=image.shape[:2]
        images.append(cv2.resize(image,(640,640))[...,::-1].copy())
        for box in entry['boxes']:
            x1,y1,x2,y2=box[:4]
            indices.append(n);classes.append([box[4] if len(box)==5 else 0]);boxes.append([(x1+x2)/2/w,(y1+y2)/2/h,(x2-x1)/w,(y2-y1)/h])
    batch=dict(img=torch.from_numpy(np.stack(images).transpose(0,3,1,2)).cuda().float()/255,
        batch_idx=torch.tensor(indices,device='cuda',dtype=torch.float32),
        cls=torch.tensor(classes,device='cuda',dtype=torch.float32).reshape(-1,1),
        bboxes=torch.tensor(boxes,device='cuda',dtype=torch.float32).reshape(-1,4))
    import yaml
    names=yaml.safe_load((Path(snapshot['directory'])/'data.yaml').read_text())['names']
    probe=DetectionModel(model.model.yaml,nc=len(names),verbose=False).cuda().train()
    # Loss construction needs the same hyperparameters as the real trainer.
    from ultralytics.cfg import get_cfg
    probe.args=get_cfg()
    probe.load(model.model,verbose=False)
    optimizer=torch.optim.AdamW(probe.parameters(),lr=params['lr0'])
    try:
        loss,_=probe(batch)
        if not torch.isfinite(loss).all(): raise StudioError('trainingFailed')
        loss.sum().backward();optimizer.step();optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        amp_ok=True
        try:
            with torch.autocast('cuda'):
                loss,_=probe(batch)
            if not torch.isfinite(loss).all(): amp_ok=False
            else: loss.sum().backward();torch.cuda.synchronize()
        except (RuntimeError,AssertionError) as exc:
            if 'out of memory' in str(exc).lower(): raise
            amp_ok=False
        return amp_ok
    finally:
        del optimizer,probe,batch
        gc.collect();torch.cuda.empty_cache()


def run_worker(root, ident):
    studio=Studio(root);store=studio.store;lease=GpuLease(store.data)
    os.environ['YOLO_CONFIG_DIR']=str(store.data/'ultralytics')
    def update(**fields):
        with store.transaction() as db:
            job=store.get('job',ident,db)
            if job.get('stop_requested') and fields.get('state') in ('preparing','running','validating','saving'):
                fields['state']='stopping'
            if job.get('stop_requested') and fields.get('state')=='completed':
                fields['state']='cancelled' if job['stop_requested']=='cancel' else 'paused';fields['stage']='stopped'
            job.update(fields);return store.put('job',job,db=db)
    job=update(pid=os.getpid(),pid_start=process_start(os.getpid()),boot_id=boot_id())
    directory=store.data/'training'/ident
    # The serving process releases its lease only after settling the session and unloading models.
    deadline=time.monotonic()+120
    try:
        while not lease.acquire():
            if time.monotonic()>deadline: raise StudioError('gpuBusy')
            if store.get('job',ident).get('stop_requested'): raise InterruptedError()
            time.sleep(.25)
        if store.get('job',ident).get('stop_requested'): raise InterruptedError()
        import torch
        if not torch.cuda.is_available(): raise StudioError('cuda')
        if shutil.disk_usage(store.data).free<2*1024**3: raise StudioError('diskSpace')
        snap=store.get('snapshot',job['snapshot_id'])
        manifest=Path(snap['directory'])/'manifest.json'
        if digest(manifest)!=job['snapshot_sha256']: raise StudioError('checksum')
        for split,images in json.loads(manifest.read_text()).items():
            for im in images:
                if digest(Path(snap['directory'])/'images'/split/(im['image_id']+'.jpg'))!=im['sha256']:
                    raise StudioError('checksum')
        base=studio.model(job['base_model_id'],'material')
        if digest(base['path'])!=job['base_sha256']: raise StudioError('checksum')
        from ultralytics import YOLO
        from ultralytics.utils import USER_CONFIG_DIR
        # Use installed system fonts; offline training must not trigger hidden font downloads.
        for name,source in [('Arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),('Arial.Unicode.ttf','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]:
            target=Path(USER_CONFIG_DIR)/name
            if not target.exists() and Path(source).exists():
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        params=job['parameters'].copy()
        checkpoint=None
        if job.get('resuming'):
            checkpoint=find_checkpoint(directory)
            if checkpoint is None: raise StudioError('checkpoint')
        import psutil
        if psutil.virtual_memory().available<512*1024**2: raise StudioError('memory')
        model=YOLO(str(checkpoint or base['path']))
        update(stage='preflight')
        checked_amp=resource_preflight(model,snap,params)
        # Avoid the framework's hidden YOLO11n download during AMP checks.
        import ultralytics.engine.trainer as trainer_module
        trainer_module.check_amp=lambda _: checked_amp
        params['amp']=checked_amp
        update(effective_amp=checked_amp)
        start=time.monotonic();last_batch_update=[0.];batch_index=[0]
        elapsed_before=job.get('elapsed_seconds',0) if job.get('resuming') else 0
        def epoch_start(trainer): batch_index[0]=0
        resume_epoch=[job.get('epoch',0)]
        def batch_end(trainer):
            batch_index[0]+=1
            if time.monotonic()-last_batch_update[0]>1:
                current=store.get('job',ident)
                if current.get('stop_requested'): trainer.stop=True
                epoch=trainer.epoch+1
                update(state='stopping' if current.get('stop_requested') else 'running',stage='training',epoch=epoch,
                    elapsed_seconds=elapsed_before+time.monotonic()-start,batch_index=batch_index[0],batches_total=len(trainer.train_loader),
                    progress=min(.94,(trainer.epoch+batch_index[0]/max(1,len(trainer.train_loader)))/max(1,trainer.epochs)*.94),
                    losses={str(k):float(v) for k,v in trainer.label_loss_items(trainer.tloss,prefix='train').items()},
                    memory_allocated_bytes=torch.cuda.memory_allocated(),peak_memory_allocated_bytes=torch.cuda.max_memory_allocated(),lr={str(k):float(v) for k,v in getattr(trainer,'lr',{}).items()})
                last_batch_update[0]=time.monotonic()
        def epoch_saved(trainer):
            path=Path(trainer.last)
            if path.exists():
                save_checkpoint(directory,path,trainer.epoch+1)
            metrics={k:float(v) for k,v in {**trainer.metrics,**trainer.label_loss_items(trainer.tloss,prefix='train')}.items() if isinstance(v,(int,float)) and float('-inf')<float(v)<float('inf')}
            elapsed=time.monotonic()-start;completed=trainer.epoch+1
            current=store.get('job',ident)
            update(epoch=completed,checkpoint='resume.pt' if path.exists() else None,metrics=metrics,
                elapsed_seconds=elapsed_before+elapsed,eta_seconds=elapsed/max(1,completed-resume_epoch[0])*max(0,trainer.epochs-completed),
                progress=min(.94,completed/max(1,trainer.epochs)*.94))
            if current.get('stop_requested'): trainer.stop=True
        model.add_callback('on_train_epoch_start',epoch_start)
        model.add_callback('on_train_batch_end',batch_end)
        model.add_callback('on_model_save',epoch_saved)
        update(state='running',stage='training',started_at=time.time())
        # No implicit downloader, cloud integration or package mutation during train.
        os.environ['YOLO_AUTOINSTALL']='False'
        from ultralytics import settings as yolo_settings
        yolo_settings.update({'sync':False,'wandb':False,'mlflow':False,'comet':False,'clearml':False,'neptune':False,'dvc':False,'hub':False})
        if store.get('job',ident).get('stop_requested'): raise InterruptedError()
        args=dict(data=str(Path(snap['directory'])/'data.yaml'),project=str(directory),name='run',exist_ok=True,
                  save=True,save_period=-1,plots=True,verbose=False,**params)
        # A single real forward/backward and optimizer allocation is performed by trainer startup;
        # CUDA OOM is caught and never retried with silently changed parameters.
        if checkpoint: args.update(resume=str(checkpoint))
        if not job.get('training_complete'):
            model.train(**args)
        current=store.get('job',ident)
        if current.get('stop_requested'):
            update(state='cancelled' if current['stop_requested']=='cancel' else 'paused',stage='stopped',finished_at=time.time())
            return
        update(training_complete=True)
        best=directory/'run/weights/best.pt'
        if not best.exists(): raise StudioError('modelInvalid')
        update(state='validating',stage='testing',progress=.95)
        tested=YOLO(str(best)).val(data=args['data'],split='test',device=0,workers=0,batch=params['batch'],plots=True,
            project=str(directory),name='test',exist_ok=True,verbose=False)
        test_metrics={k:float(v) for k,v in tested.results_dict.items() if isinstance(v,(int,float)) and float('-inf')<float(v)<float('inf')}
        current=store.get('job',ident)
        if current.get('stop_requested'): raise InterruptedError()
        update(state='saving',stage='saving',progress=.99)
        artifact=studio.import_model(best,'material',f'{studio.store.get("dataset",snap["dataset_id"])["name"]} / {ident[:8]}','trained',
            info=dict(task='detect',classes={str(k):str(v) for k,v in model.names.items()}))
        update(state='completed',stage='completed',progress=1.,result_model_id=artifact['id'],test_metrics=test_metrics,finished_at=time.time())
    except BaseException as exc:
        if isinstance(exc,(KeyboardInterrupt,InterruptedError,SystemExit)):
            current=store.get('job',ident)
            state='cancelled' if current.get('stop_requested')=='cancel' else 'paused' if current.get('stop_requested') else 'interrupted'
            update(state=state,stage=state,error=None if current.get('stop_requested') else 'interrupted')
        else:
            code=getattr(exc,'code','trainingFailed')
            if 'out of memory' in str(exc).lower(): code='memory'
            update(state='failed',stage='failed',error=code,exception_type=type(exc).__name__,finished_at=time.time())
            import traceback;traceback.print_exc()
    finally:
        lease.release()

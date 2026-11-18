"""Device-local model and dataset registry; no CUDA allocation in HTTP handlers."""
from copy import deepcopy
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

from .studio_store import StudioStore, StudioError, atomic, digest, uid

ACTIVE_JOBS = {'queued','preparing','running','validating','saving','stopping'}
CATALOG = {f'yolo11{s}':dict(id=f'yolo11{s}',name=f'YOLO11{s}',task='detect',
    url=f'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11{s}.pt') for s in ('n','m','l')}


def public(value):
    return {k:v for k,v in value.items() if k not in ('path','directory','pid','pid_start','worker_log','boot_id')}


class Studio:
    def __init__(self, root, behavior=None):
        self.root = Path(root)
        self.store = StudioStore(root)
        self.behavior = behavior
        self.lock = threading.RLock()
        self.verified = {}
        if behavior is not None:
            for item in self.store.list('download'):
                if item['state'] in ('queued','running','validating'):
                    item.update(state='interrupted',error='interrupted');self.store.put('download',item)
        path = self.root/'models/yolo11n-pose.pt'
        try:
            builtin=self.store.get('model','builtin-person')
            if not builtin.get('sha256') and path.exists():
                builtin.update(sha256=digest(path),installed=True);self.store.put('model',builtin)
        except StudioError:
            self.store.put('model',dict(id='builtin-person',name='YOLO11n Pose',role='person',task='pose',
                classes={'0':'person'},path=str(path),sha256=digest(path) if path.exists() else None,
                builtin=True,installed=path.exists(),source='builtin',created_at=time.time()))

    def active_job(self):
        return next((j for j in self.store.list('job') if j['state'] in ACTIVE_JOBS),None)

    def model(self, ident, role=None):
        value = self.store.get('model',ident)
        if role and value['role'] != role or not Path(value['path']).is_file():
            raise StudioError('modelMissing')
        path=Path(value['path']);stat=path.stat();fingerprint=(stat.st_size,stat.st_mtime_ns)
        if self.verified.get(ident)!=fingerprint:
            if not value.get('sha256') or digest(path)!=value['sha256']:raise StudioError('checksum')
            self.verified[ident]=fingerprint
        return value

    def validate_selection(self, config):

        for role,ident in config['models'].items():
            if ident is not None:
                self.model(ident,role)
        if config['materials']['enabled']:
            ident=config['models']['material']
            if not ident: raise StudioError('modelMissing')
            model=self.model(ident,'material')
            material=config['materials']
            binding=material.get('binding')
            if binding and binding!={'model_id':ident,'sha256':model['sha256']}: raise StudioError('classMissing')
            selected={c for rule in material['rules'].values() for ids in rule.values() for c in ids}
            if any(str(c) not in model['classes'] for c in selected) or any(k not in model['classes'] for k in [*material['class_styles'],*material.get('confidence_by_class',{})]):
                raise StudioError('classMissing')

    def inspect_model(self, path, role):
        if role not in ('person','material'): raise StudioError('modelInvalid')
        out = Path(str(path)+'.inspection.json')
        result=subprocess.run([sys.executable,str(self.root/'scripts/studio_model_check.py'),str(path),role,str(out)],
            cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90,
            env={**os.environ,'YOLO_CONFIG_DIR':str(self.store.data/'ultralytics'),'YOLO_AUTOINSTALL':'False'})
        try:
            info=json.loads(out.read_text())
        except (OSError,ValueError):
            raise StudioError('modelInvalid')
        finally:
            out.unlink(missing_ok=True)
        if result.returncode or not info.get('valid'): raise StudioError('modelInvalid')
        return info

    def import_model(self, path, role, name, source='upload', builtin=False, info=None):
        path=Path(path)
        from .deployment import require_space
        require_space(self.store.data, path.stat().st_size)
        info=info or self.inspect_model(path,role)
        checksum=digest(path)
        duplicate=next((m for m in self.store.list('model') if m['sha256']==checksum and m['role']==role and m['source']==source and Path(m['path']).exists()),None)
        if duplicate:
            if digest(duplicate['path'])!=checksum: atomic(duplicate['path'],path.read_bytes())
            return duplicate
        ident=uid()
        target=self.store.data/'models'/ident/'weights.pt'
        atomic(target,path.read_bytes())
        value=dict(id=ident,name=str(name)[:100] or path.name,role=role,task=info['task'],classes=info['classes'],
            path=str(target),sha256=checksum,builtin=builtin,installed=True,source=source,created_at=time.time())
        return self.store.put('model',value)

    def remove_model(self, ident, expected, config):
        with self.lock:
            model=self.store.get('model',ident)
            if model['revision'] != expected: raise StudioError('conflict',409)
            if model['builtin'] or ident in config['models'].values() or any(j.get('base_model_id')==ident for j in self.store.list('job')):
                raise StudioError('referenced',409)
            with self.store.transaction() as db:
                db.execute('DELETE FROM objects WHERE kind=? AND id=?',('model',ident))
            Path(model['path']).unlink(missing_ok=True)
            return {'deleted':True}

    def download(self, name):
        if name not in CATALOG: raise StudioError('modelInvalid')
        with self.lock:
            ready=next((m for m in self.store.list('model') if m.get('source')=='official' and m['name']==CATALOG[name]['name'] and Path(m['path']).exists() and digest(m['path'])==m['sha256']),None)
            if ready:
                return public(self.store.put('download',dict(id=uid(),catalog_id=name,state='completed',bytes=Path(ready['path']).stat().st_size,total=Path(ready['path']).stat().st_size,model_id=ready['id'],sha256=ready['sha256'])))
            old=next((d for d in self.store.list('download') if d['catalog_id']==name and d['state'] in ('queued','running','validating')),None)
            if old: return public(old)
            from .deployment import require_space
            require_space(self.store.data, 512*1024*1024)
            item=self.store.put('download',dict(id=uid(),catalog_id=name,state='queued',bytes=0,total=None,created_at=time.time()))
            threading.Thread(target=self._download,args=(item,),daemon=True).start()
            return public(item)

    def _download(self, item):
        path=self.store.data/'downloads'/item['id']/'weights.pt'
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            item['state']='running';self.store.put('download',item)
            # Only the bundled official catalog can initiate network downloads.
            with urllib.request.urlopen(CATALOG[item['catalog_id']]['url'],timeout=30) as source, path.open('wb') as target:
                item['total']=int(source.headers.get('Content-Length') or 0) or None
                last=0
                while True:
                    data=source.read(256*1024)
                    if not data: break
                    target.write(data);item['bytes']+=len(data)
                    if item['bytes']>512*1024*1024: raise StudioError('fileSize')
                    if time.monotonic()-last>1:
                        self.store.put('download',item);last=time.monotonic()
            item['state']='validating';self.store.put('download',item)
            # Release checksum manifest is bundled with the application, never supplied by the client.
            manifest=json.loads((self.root/'configs/model-catalog.json').read_text())
            if digest(path)!=manifest[item['catalog_id']]['sha256']: raise StudioError('checksum')
            model=self.import_model(path,'material',CATALOG[item['catalog_id']]['name'],'official',True)
            item.update(state='completed',model_id=model['id'],sha256=model['sha256'])
        except Exception as exc:
            item.update(state='failed',error=getattr(exc,'code','downloadFailed'))
        finally:
            self.store.put('download',item);path.unlink(missing_ok=True)

    def create_dataset(self, request):
        name=request.get('name','').strip();label=request.get('class_name','').strip()
        if not name or len(name)>100 or not label or len(label)>100:
            raise StudioError('datasetInvalid')
        return self.store.put('dataset',dict(id=uid(),name=name,class_name=label,classes={'0':label},next_class_id=1,created_at=time.time()))

    def dataset(self, ident):
        ds=self.store.get('dataset',ident)
        ds['classes']=self.dataset_classes(ds)
        ds['images']=[public(v) for v in self.store.list('image') if v['dataset_id']==ident and not v.get('deleted')]
        return ds

    @staticmethod
    def dataset_classes(ds):
        return ds.get('classes',{'0':ds['class_name']})

    def update_classes(self, ident, request):
        with self.store.transaction() as db:
            ds=self.store.get('dataset',ident,db)
            if type(request.get('expected_revision')) is not int or request.get('expected_revision')!=ds['revision']: raise StudioError('conflict',409)
            if not isinstance(request.get('name',''),str): raise StudioError('classInvalid')
            if request.get('action') in ('rename','delete') and type(request.get('class_id')) is not int: raise StudioError('classMissing')
            classes=deepcopy(self.dataset_classes(ds));action=request.get('action')
            name=request.get('name','').strip();key=str(request.get('class_id'))
            if action in ('add','rename'):
                if not name or len(name)>100 or any(v.casefold()==name.casefold() for k,v in classes.items() if action=='add' or k!=key): raise StudioError('classInvalid')
                if action=='add':
                    next_id=ds.get('next_class_id',max(map(int,classes),default=-1)+1)
                    key=str(next_id);ds['next_class_id']=next_id+1
                elif key not in classes: raise StudioError('classMissing')
                classes[key]=name
            elif action=='delete':
                if key not in classes: raise StudioError('classMissing')
                if len(classes)==1: raise StudioError('classReferenced')
                for im in self.store.list('image',db):
                    if im['dataset_id']==ident and not im.get('deleted') and any(str(b[4] if len(b)==5 else 0)==key for b in im['boxes']): raise StudioError('classReferenced')
                for snap in self.store.list('snapshot',db):
                    if snap['dataset_id']==ident and key in snap.get('project_classes',{'0':ds['class_name']}): raise StudioError('classReferenced')
                del classes[key]
            else: raise StudioError('request')
            ds['classes']=classes
            return self.store.put('dataset',ds,request['expected_revision'],db)

    def add_image(self, ident, data, group, config, provenance=None, protected=False):
        from .deployment import require_space
        require_space(self.store.data, len(data))
        import cv2
        import numpy as np
        self.store.get('dataset',ident)
        if not isinstance(group,str) or not 1<=len(group)<=100 or len(data)>20*1024*1024:
            raise StudioError('fileSize')
        # Check dimensions before allocating a decompression buffer.
        self._image_dimensions(data)
        frame=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
        if frame is None or frame.size>24_000_000*3: raise StudioError('imageInvalid')
        if config['privacy']['enabled'] and not protected:
            from ultralytics import YOLO
            from .runtime import extract_persons
            from .media import protect_frame
            person=self.model(config['models']['person'],'person')
            result=YOLO(person['path']).predict(frame,device='cpu',imgsz=640,conf=.10,verbose=False)[0]
            frame=protect_frame(frame,extract_persons(result),config)
        ok,jpeg=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,92])
        if not ok: raise StudioError('imageInvalid')
        encoded=jpeg.tobytes();checksum=hashlib.sha256(encoded).hexdigest()
        original_hash=hashlib.sha256(data).hexdigest()
        image_id=uid();path=self.store.data/'datasets'/ident/'images'/(image_id+'.jpg')
        value=dict(id=image_id,dataset_id=ident,group_id=group,sha256=checksum,original_sha256=original_hash,
            width=frame.shape[1],height=frame.shape[0],path=str(path),boxes=[],annotated=False,
            privacy_applied=config['privacy']['enabled'],config_revision=config['revision'],provenance=provenance or {},created_at=time.time())
        with self.store.transaction() as db:
            ds=self.store.get('dataset',ident,db)
            old=next((v for v in self.store.list('image',db) if v['dataset_id']==ident and (v['sha256']==checksum or v.get('original_sha256')==original_hash) and not v.get('deleted')),None)
            if old: return public(old)
            atomic(path,encoded)
            value=self.store.put('image',value,db=db)
            self.store.put('dataset',ds,db=db)
        return public(value)

    @staticmethod
    def _image_dimensions(data):
        # JPEG/PNG header parsing avoids adding imaging dependencies to the runtime.
        import struct
        if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24:
            w,h=struct.unpack('>II',data[16:24])
        elif data.startswith(b'\xff\xd8'):
            index=2;w=h=0
            while index+4<len(data):
                if data[index]!=255: raise StudioError('imageInvalid')
                marker=data[index+1];index+=2
                if marker in (0xD9,0xDA): break
                length=int.from_bytes(data[index:index+2],'big')
                if length<2 or index+length>len(data): raise StudioError('imageInvalid')
                if marker in (0xC0,0xC1,0xC2):
                    h=int.from_bytes(data[index+3:index+5],'big');w=int.from_bytes(data[index+5:index+7],'big');break
                index+=length
        else: raise StudioError('imageInvalid')
        if min(w,h)<2 or w*h>24_000_000: raise StudioError('imageInvalid')
        return w,h

    def annotate(self, dataset_id, image_id, request):
        if type(request.get('expected_revision')) is not int: raise StudioError('conflict',409)
        boxes=request.get('boxes')
        if not isinstance(boxes,list) or len(boxes)>1000 or type(request.get('annotated')) is not bool:
            raise StudioError('annotationInvalid')
        with self.store.transaction() as db:
            image=self.store.get('image',image_id,db)
            if image['dataset_id']!=dataset_id or image.get('deleted'): raise StudioError('notFound',404)
            ds=self.store.get('dataset',dataset_id,db);classes=self.dataset_classes(ds)
            for b in boxes:
                if (not isinstance(b,list) or len(b) not in (4,5) or any(not isinstance(v,(float,int)) or isinstance(v,bool) or not math.isfinite(v) for v in b[:4])
                    or not 0<=b[0]<b[2]<=image['width'] or not 0<=b[1]<b[3]<=image['height']):
                    raise StudioError('annotationInvalid')
                if len(b)==4 and (len(classes)!=1 or '0' not in classes): raise StudioError('annotationInvalid')
                if len(b)==5 and (type(b[4]) is not int or str(b[4]) not in classes): raise StudioError('classMissing')
            image.update(boxes=deepcopy(boxes),annotated=request['annotated'])
            image=self.store.put('image',image,request.get('expected_revision'),db)
            ds=self.store.get('dataset',dataset_id,db);self.store.put('dataset',ds,db=db)
            return public(image)

    def delete_image(self, dataset_id, image_id, request):
        with self.store.transaction() as db:
            image=self.store.get('image',image_id,db)
            if image['dataset_id']!=dataset_id: raise StudioError('notFound',404)
            image['deleted']=True
            self.store.put('image',image,request.get('expected_revision'),db)
            self.store.put('dataset',self.store.get('dataset',dataset_id,db),db=db)
        # Keep source files while immutable snapshots may reference them.
        return {'deleted':True}

    def snapshot(self, ident, request):
        ratios=request.get('ratios',[80,10,10])
        if not isinstance(ratios,list) or len(ratios)!=3 or any(type(v) is not int or v<=0 for v in ratios) or sum(ratios)!=100:
            raise StudioError('splitInvalid')
        with self.store.transaction() as db:
            ds=self.store.get('dataset',ident,db)
            if request.get('expected_revision')!=ds['revision']: raise StudioError('conflict',409)
            images=[v for v in self.store.list('image',db) if v['dataset_id']==ident and not v.get('deleted')]
            incomplete=sum(not im['annotated'] for im in images)
            if incomplete: raise StudioError('annotationIncomplete',count=incomplete)
            groups={}
            for im in images: groups.setdefault(im['group_id'],[]).append(im)
            if len(groups)<3: raise StudioError('splitGroups')
            keys=sorted(groups);random.Random(42).shuffle(keys)
            # Seed each split with a positive group; greedily balance remaining whole groups.
            positives=[k for k in keys if any(im['boxes'] for im in groups[k])]
            if len(positives)<3: raise StudioError('splitPositive')
            splits={name:[] for name in ('train','val','test')}
            for name,key in zip(splits,positives[:3]): splits[name].extend(groups.pop(key));keys.remove(key)
            for key in sorted(keys,key=lambda k:len(groups[k]),reverse=True):
                name=min(splits,key=lambda n:len(splits[n])/(len(images)*ratios[list(splits).index(n)]/100))
                splits[name].extend(groups[key])
            project_classes=self.dataset_classes(ds)
            mapping={int(k):i for i,k in enumerate(sorted(project_classes,key=int))}
            names={mapping[int(k)]:v for k,v in project_classes.items()}
            snap_id=uid();directory=self.store.data/'datasets'/ident/'snapshots'/snap_id
            for name,items in splits.items():
                lines=[]
                for im in items:
                    target=directory/'images'/name/(im['id']+'.jpg')
                    atomic(target,Path(im['path']).read_bytes())
                    labels=[]
                    mapped=[]
                    for box in im['boxes']:
                        x1,y1,x2,y2=box[:4];class_id=mapping[box[4] if len(box)==5 else 0]
                        mapped.append([x1,y1,x2,y2,class_id])
                        labels.append(f'{class_id} {(x1+x2)/2/im["width"]:.8f} {(y1+y2)/2/im["height"]:.8f} {(x2-x1)/im["width"]:.8f} {(y2-y1)/im["height"]:.8f}')
                    atomic(directory/'labels'/name/(im['id']+'.txt'),('\n'.join(labels)+'\n').encode())
                    lines.append(dict(image_id=im['id'],sha256=im['sha256'],group_id=im['group_id'],boxes=mapped,width=im['width'],height=im['height']))
                splits[name]=lines
            import yaml
            atomic(directory/'data.yaml',yaml.safe_dump(dict(path=str(directory),train='images/train',val='images/val',test='images/test',names=names),allow_unicode=True).encode())
            manifest=json.dumps(splits,sort_keys=True).encode();atomic(directory/'manifest.json',manifest)
            snap=dict(id=snap_id,dataset_id=ident,dataset_revision=ds['revision'],directory=str(directory),
                project_classes=project_classes,class_mapping=mapping,classes=names,counts={k:len(v) for k,v in splits.items()},ratios=ratios,seed=42,sha256=hashlib.sha256(manifest).hexdigest(),created_at=time.time())
            return self.store.put('snapshot',snap,db=db)

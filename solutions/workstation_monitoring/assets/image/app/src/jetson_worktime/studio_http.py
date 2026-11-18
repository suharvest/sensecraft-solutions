"""Same-origin studio routes, bounded uploads, opaque IDs and versioned writes."""
import base64
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
from urllib.parse import parse_qs,urlsplit
from .studio import public
from .studio_store import StudioError
from .training import TrainingQueue


class StudioHTTP:
    def __init__(self, studio):
        self.studio=studio;self.store=studio.store
        self.training=TrainingQueue(studio)

    def handle(self, handler, method):
        parsed=urlsplit(handler.path);parts=parsed.path.strip('/').split('/')
        if len(parts)<3 or parts[:2]!=['api','v1'] or parts[2] not in ('models','datasets','training','materials'):
            return False
        if method!='GET' and not handler.check_origin(): return True
        try:
            result=self.route(handler,method,parts[2:],parse_qs(parsed.query))
            if result is not None: handler.json(result)
        except StudioError as exc:
            exc.message_key='studio.error.'+exc.code;exc.message_params=exc.params
            handler.error(exc.status,'STUDIO_ERROR',exc)
        except (ValueError,TypeError,KeyError,IndexError,UnicodeError):
            exc=StudioError('request');exc.message_key='studio.error.request'
            handler.error(400,'STUDIO_ERROR',exc)
        except (OSError,TimeoutError,sqlite3.Error):
            exc=StudioError('storage',500);exc.message_key='studio.error.storage'
            handler.error(500,'STUDIO_ERROR',exc)
        return True

    def route(self,h,method,p,q):
        s=self.studio;behavior=s.behavior
        def body(): return h.read_json(1024*1024)
        if p==['models'] and method=='GET':
            return {'models':[public(m) for m in self.store.list('model')],'selection':behavior.config['models'],'activation_error':behavior.model_activation_error}
        if p==['models','catalog'] and method=='GET':
            from .studio import CATALOG
            return {'models':[{k:v for k,v in m.items() if k!='url'} for m in CATALOG.values()]}
        if p==['models','downloads']:
            if method=='GET': return {'downloads':[public(d) for d in self.store.list('download')]}
            if method=='POST': return s.download(body().get('catalog_id'))
        if p==['models'] and method=='POST':
            if s.active_job(): raise StudioError('busy',409)
            role=q.get('role',['material'])[0];name=q.get('name',['Custom model'])[0]
            if role not in ('person','material'): raise StudioError('modelInvalid')
            length=int(h.headers.get('Content-Length','0'))
            if not 0<length<=512*1024*1024: raise StudioError('fileSize')
            h.connection.settimeout(120)
            with tempfile.TemporaryDirectory(dir=self.store.data) as directory:
                path=Path(directory)/'weights.pt'
                with path.open('wb') as target:
                    remaining=length
                    while remaining:
                        block=h.rfile.read(min(256*1024,remaining))
                        if not block: raise StudioError('request')
                        target.write(block);remaining-=len(block)
                return public(s.import_model(path,role,name))
        if len(p)==2 and p[0]=='models' and method=='DELETE':
            return s.remove_model(p[1],body().get('expected_revision'),behavior.config)
        if p==['datasets']:
            if method=='GET': return {'datasets':self.store.list('dataset')}
            if method=='POST': return s.create_dataset(body())
        if len(p)>=2 and p[0]=='datasets':
            ident=p[1]
            if len(p)==2 and method=='GET': return s.dataset(ident)
            if p[2:]==['classes'] and method=='PUT': return s.update_classes(ident,body())
            if len(p)==3 and p[2]=='images' and method=='POST':
                if s.active_job(): raise StudioError('busy',409)
                length=int(h.headers.get('Content-Length','0'))
                if not 0<length<=20*1024*1024: raise StudioError('fileSize')
                h.connection.settimeout(30);data=h.rfile.read(length)
                if len(data)!=length: raise StudioError('request')
                with behavior.store.output_policy() as config:
                    return s.add_image(ident,data,q.get('group',['upload'])[0],config)
            if len(p)==3 and p[2]=='captures' and method=='POST':
                request=body()
                import cv2
                # Copy references while locked, then encode/store outside the inference lock.
                with behavior.lock:
                    packet=behavior.full_frame
                    if (not packet or packet[3]!=behavior.config['revision'] or not behavior.connected
                        or behavior.operating_mode not in ('business','preview') or time.monotonic()-packet[2]/1e9>behavior.config['max_observation_age']):
                        raise StudioError('frameUnavailable',409)
                    image,meta,received,revision=packet
                with behavior.store.output_policy() as config:
                    if config['revision']!=revision: raise StudioError('staleReference',409)
                    ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,95])
                    if not ok: raise StudioError('imageInvalid')
                    return s.add_image(ident,jpeg.tobytes(),request.get('group_id'),config,provenance=meta,protected=True)
            if len(p)==3 and p[2]=='snapshots':
                if method=='GET': return {'snapshots':[public(v) for v in self.store.list('snapshot') if v['dataset_id']==ident]}
                if method=='POST': return public(s.snapshot(ident,body()))
            if len(p)>=4 and p[2]=='images':
                image_id=p[3];image=self.store.get('image',image_id)
                if image['dataset_id']!=ident or image.get('deleted'): raise StudioError('notFound',404)
                if len(p)==4 and method=='GET':
                    h.send_bytes(Path(image['path']).read_bytes(),'image/jpeg',headers={'X-Privacy-Applied':str(image['privacy_applied']).lower()});return
                if len(p)==4 and method=='DELETE': return s.delete_image(ident,image_id,body())
                if p[4:]==['annotations'] and method=='PUT': return s.annotate(ident,image_id,body())
        if p==['training','jobs']:
            if method=='GET': return {'jobs':[public(j) for j in self.store.list('job')]}
            if method=='POST':
                request=body()
                if request.get('expected_revision')!=behavior.config['revision']: raise StudioError('conflict',409)
                # Service liveness is checked, not assumed, before reserving business downtime.
                marker=self.store.data/'agent-heartbeat'
                if not marker.exists() or time.time()-marker.stat().st_mtime>30: raise StudioError('agentOffline',503)
                return self.training.create(request)
        if len(p)>=3 and p[:2]==['training','jobs']:
            job=self.store.get('job',p[2])
            if len(p)==3 and method=='GET':
                result=public(job)
                log=self.store.data/'training'/job['id']/'worker.log'
                if log.exists():
                    with log.open('rb') as f:
                        f.seek(max(0,log.stat().st_size-16000));result['log']=f.read(16000).decode(errors='replace')
                return result
            if p[3:]==['actions'] and method=='POST': return self.training.action(job['id'],body())
            if p[3:]==['preview'] and method=='POST':
                if job['state']!='completed': raise StudioError('modelMissing')
                if behavior.operating_mode!='business': raise StudioError('busy',409)
                # Preview uses the protected matching still, never the unprotected camera stream.
                import cv2
                from ultralytics import YOLO
                with behavior.lock:
                    packet=behavior.full_frame
                    if not packet or time.monotonic()-packet[2]/1e9>behavior.config['max_observation_age']: raise StudioError('frameUnavailable')
                    if packet[3]!=behavior.config['revision']: raise StudioError('staleReference',409)
                    frame=packet[0].copy();revision=packet[3];privacy=behavior.config['privacy']['enabled'];meta=packet[1].copy()
                result=YOLO(s.model(job['result_model_id'],'material')['path']).predict(frame,device='cpu',imgsz=640,verbose=False)[0]
                for box in result.boxes.xyxy.cpu().tolist():
                    x1,y1,x2,y2=map(round,box);cv2.rectangle(frame,(x1,y1),(x2,y2),(45,212,191),2)
                ok,jpeg=cv2.imencode('.jpg',frame)
                if not ok: raise StudioError('imageInvalid')
                response={'jpeg':base64.b64encode(jpeg).decode(),'detections':len(result.boxes),'config_revision':revision,'privacy_applied':privacy,'frame':meta}
                h.send_media(json.dumps(response).encode(),headers={'X-Config-Revision':revision,'X-Privacy-Applied':str(privacy).lower()},content_type='application/json; charset=utf-8')
                return None
        if p==['materials','alerts'] and method=='GET':
            alerts=self.store.list('material_alert')
            if q.get('session_id'): alerts=[a for a in alerts if a.get('session_id')==q['session_id'][0]]
            if q.get('active') and q['active'][0] in ('true','false'): alerts=[a for a in alerts if a['active']==(q['active'][0]=='true')]
            return dict(alerts=alerts[:200])
        if p==['materials','status'] and method=='GET': return behavior.snapshot()['materials']
        if len(p)==3 and p[:2]==['materials','evidence'] and method=='GET':
            if not re.fullmatch('[0-9a-f]{64}\\.jpg',p[2]):raise StudioError('notFound',404)
            saved=self.store.get('material_evidence',p[2][:-4])
            with behavior.lock,behavior.store.output_policy() as policy:
                if policy['privacy']['enabled'] and not saved['privacy_applied']:raise StudioError('notFound',404)
                h.send_media((self.store.data/'evidence'/p[2]).read_bytes(),headers={
                    'X-Privacy-Applied':str(saved['privacy_applied']).lower(),
                    'X-Config-Revision':policy['revision'],
                    'X-Evidence-Config-Revision':saved['config_revision'],
                    'X-Frame-Sequence':saved.get('frame_sequence','')},content_type='image/jpeg')
            return None
        if len(p)>=3 and p[:2]==['materials','sessions']:
            if len(p)==3 and method=='GET':
                from .evidence import event_history
                events=event_history(self.store,p[2],behavior.config['privacy']['enabled'])
                if not events: raise StudioError('notFound',404)
                return dict(session_id=p[2],events=events,cumulative=sum(e['delta'] for e in events))
            if p[3:]==['adjustments'] and method=='POST':
                with behavior.lock: return behavior.material_counter.adjust(p[2],body())
        raise StudioError('notFound',404)

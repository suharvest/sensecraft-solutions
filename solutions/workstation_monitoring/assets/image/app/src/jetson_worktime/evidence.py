"""Bounded asynchronous event evidence, sourced from the exact protected frame."""
import queue
import threading
import time
from .studio_store import atomic


class EvidenceWriter:
    def __init__(self,store,quality):
        self.store=store;self.quality=quality;self.queue=queue.Queue(16)
        self.stop=threading.Event();self.error=None
        self.thread=threading.Thread(target=self.run,daemon=True,name='event-evidence')
        self.thread.start()

    def submit(self,events,frame,config):
        if not events:return
        from .inference import workbench_crop
        x1,y1,x2,y2=workbench_crop(config,frame.shape[1],frame.shape[0])
        try:self.queue.put_nowait((events,frame[y1:y2,x1:x2].copy(),(x1,y1),config['privacy']['enabled']))
        except queue.Full:self.quality.sample('evidence_dropped',len(events));self.error='EvidenceQueueFull'

    def run(self):
        import cv2
        while not self.stop.is_set() or not self.queue.empty():
            try:events,frame,offset,privacy=self.queue.get(timeout=.1)
            except queue.Empty:continue
            try:
                started=time.monotonic_ns();h,w=frame.shape[:2];scale=min(1,800/max(w,h))
                if scale<1:frame=cv2.resize(frame,(round(w*scale),round(h*scale)))
                ok,jpg=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,88])
                if not ok:raise OSError('JPEG failure')
                for event in events:
                    ident=event['id'];target=self.store.data/'evidence'/(ident+'.jpg')
                    atomic(target,jpg.tobytes())
                    self.store.put('material_evidence',dict(id=ident,session_id=event['session_id'],
                        config_revision=event['config_revision'],frame_sequence=event.get('frame_sequence'),
                        stream_session_id=event.get('stream_session_id'),privacy_applied=privacy,
                        source_offset=list(offset),scale=scale,image_size=[frame.shape[1],frame.shape[0]],created_at=time.time()))
                self.quality.sample('evidence_write_ms',(time.monotonic_ns()-started)/1e6)
            except Exception:self.error='EvidenceStorageError'
            finally:self.queue.task_done()

    def close(self):
        self.stop.set();self.thread.join(timeout=5)


def event_history(store,session_id,privacy):
    events=store.events(session_id)
    saved={e['id']:e for e in store.list('material_evidence') if e['session_id']==session_id}
    resolved={e.get('event_id') for e in events if e['kind']=='resolution'}
    result=[]
    for event in events:
        evidence=saved.get(event['id']);allowed=evidence and (not privacy or evidence['privacy_applied'])
        result.append({**event,'resolved':event['id'] in resolved,
                       'evidence_geometry':{k:evidence[k] for k in ('source_offset','scale','image_size') if k in evidence} if allowed else None,
                       'evidence_frame_url':f"/api/v1/materials/evidence/{event['id']}.jpg" if allowed else None})
    return result

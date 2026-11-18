import argparse, json, os, sys, time, threading, uuid, re, signal
from pathlib import Path
os.environ['YOLO_AUTOINSTALL']='False'
import cv2, torch, yaml, psutil
from ultralytics import YOLO
from .video import VideoReader
from .roi import observe_and_draw
from .behavior import SessionEngine
from .detection import DETECTION_DEFAULTS, detection_settings, filter_persons, TRACKING_CONFIDENCE, KEYPOINT_EXTRACTION_FLOOR
from .settings import SettingsStore, TIMING_KEYS
from .media import protect_frame, RedactedRecorder
from .overlay import draw_overlay
from copy import deepcopy

def load_env(path):
    if not path.exists(): return
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        key,sep,value=line.partition('=')
        if sep and key.strip()=='RTSP_URL':os.environ.setdefault('RTSP_URL',value.strip().strip('\"\''))

def extract_persons(result):
    persons=[]
    if result.boxes is None:return persons
    boxes=result.boxes.xyxy.cpu().tolist()
    confidences=result.boxes.conf.cpu().tolist()
    ids=result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None]*len(boxes)
    kps=result.keypoints.data.cpu().tolist() if result.keypoints is not None else [[] for _ in boxes]
    assert len(boxes)==len(ids)==len(kps)==len(confidences)
    for box,tid,points,confidence in zip(boxes,ids,kps,confidences):
        persons.append({'person_track_id':tid,'bbox_xyxy':box,'valid':True,'confidence':confidence,
            'keypoints':[{'x':p[0] if len(p)>2 and p[2]>=KEYPOINT_EXTRACTION_FLOOR else None,'y':p[1] if len(p)>2 and p[2]>=KEYPOINT_EXTRACTION_FLOOR else None,'confidence':p[2] if len(p)>2 else None} for p in points]})
    return persons

def main():
    def terminate(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/station.example.yaml'); ap.add_argument('--duration',type=float,default=0)
    ap.add_argument('--output');ap.add_argument('--record-raw',action='store_true',help='record privacy-aware decoded H264 segments with media timestamps');ap.add_argument('--max-frames',type=int,default=0)
    args=ap.parse_args();load_env(Path('.env'))
    settings_store=SettingsStore(Path('configs/behavior.yaml'))
    behavior_config=settings_store.snapshot()
    behavior_engine=SessionEngine(behavior_config) if behavior_config else None
    behavior_epoch=None
    cfg=yaml.safe_load(Path(args.config).read_text());source=cfg['source'];rtsp=source['type']=='rtsp'
    url=os.environ.get(source.get('rtsp_env','RTSP_URL')) if rtsp else source['path']
    if not url:raise SystemExit('RTSP_URL is missing; configure local .env or environment')
    if source['sample_hz']<=0:raise SystemExit('sample_hz must be positive')
    if not torch.cuda.is_available():raise SystemExit('CUDA required')
    output=Path(args.output or cfg['output_dir']);output.mkdir(parents=True,exist_ok=True)
    # One isolated directory per real run avoids overwriting previous evidence.
    run_id=uuid.uuid4().hex; started=time.monotonic_ns()
    if behavior_engine:behavior_engine.run_id=run_id
    stats={'run_id':run_id,'input_type':source['type'],'decoder':'nvv4l2decoder','processed_frames':0,'received_frames':0,'overwritten_frames':0,'sample_skipped_frames':0,'timeouts':0,'reconnections':0,'sessions':[], 'status':'RUNNING','latency_definition':'local decoded-frame callback to GPU completion; not camera exposure latency','resources':{}}
    stop=threading.Event();lock=threading.Lock();state={'reader':None,'session_started_ns':started};writer=None;model=YOLO(cfg['model']['path'])
    recorder=RedactedRecorder(output, sample_hz=source['sample_hz']) if args.record_raw else None
    def write_json(path,value):path.write_text(json.dumps(value,indent=2))
    def watchdog():
        proc=psutil.Process();proc.cpu_percent()
        with (output/'health.jsonl').open('w') as f:
            while not stop.is_set():
                with lock:r=state['reader'];origin=state['session_started_ns']
                snapshot=r.snapshot() if r else {}
                now=time.monotonic_ns();last=snapshot.get('last_rx_monotonic_ns') or origin
                health='timeout' if now-last>source['timeout_seconds']*1e9 else ('healthy' if snapshot.get('last_rx_monotonic_ns') else 'connecting')
                event={'monotonic_ns':now,'health':health,**snapshot,'rss_bytes':proc.memory_info().rss,'cpu_percent':proc.cpu_percent(),'system_available_bytes':psutil.virtual_memory().available}
                f.write(json.dumps(event)+'\n');f.flush();stop.wait(1)
    monitor=threading.Thread(target=watchdog,daemon=True);monitor.start()
    error=None;latencies=[];last_session=None;last_sample=None;frame_id=0;last_success_ns=0;last_failure_ns=0
    try:
        with (output/'observations.jsonl').open('w') as observations,(output/'events.jsonl').open('w') as events:
            while not stop.is_set():
                if args.duration and (time.monotonic_ns()-started)/1e9>=args.duration:break
                reader=None
                try:
                    record_path=None  # All recordings pass through the shared privacy boundary.
                    reader=VideoReader(url,source['codec'],rtsp,source['queue_limit'],source['timeout_seconds'],record_path=record_path)
                    with lock:state.update(reader=reader,session_started_ns=time.monotonic_ns())
                    while True:
                        if args.duration and (time.monotonic_ns()-started)/1e9>=args.duration:break
                        if args.max_frames and stats['processed_frames']>=args.max_frames:break
                        packet=reader.read()
                        if packet is None:
                            if rtsp:raise RuntimeError('RTSP EOS')
                            break
                        effective_config=settings_store.snapshot()
                        if effective_config['revision']!=behavior_config['revision']:
                            detection_changed=any(effective_config[k]!=behavior_config[k] for k in ('regions','image_size',*TIMING_KEYS,*DETECTION_DEFAULTS))
                            if detection_settings(effective_config)!=detection_settings(behavior_config):
                                if getattr(model,'predictor',None) is not None:
                                    for tracker in getattr(model.predictor,'trackers',[]):tracker.reset()
                            if detection_changed:
                                behavior_engine.interrupt(behavior_engine.last_obs or 0,'configuration_changed')
                                completed_sessions=behavior_engine.completed
                                pending_events=behavior_engine.events
                                behavior_engine=SessionEngine(effective_config,run_id=run_id)
                                behavior_engine.completed=completed_sessions
                                behavior_engine.events=pending_events
                            else:
                                behavior_engine.cfg=deepcopy(effective_config)
                            events.write(json.dumps(dict(event='configuration_changed',config_revision=effective_config['revision'],detection=detection_settings(effective_config),monotonic_ns=time.monotonic_ns()))+'\n');events.flush()
                            behavior_config=effective_config
                        frame,pts,received=packet;meta=reader.last_meta.copy();session=meta['session_id']
                        if session!=last_session:
                            if getattr(model,'predictor',None) is not None:
                                for tracker in getattr(model.predictor,'trackers',[]):tracker.reset()
                            stats['sessions'].append(session);last_session=session;last_sample=None
                            events.write(json.dumps({'event':'new_session','session_id':session,'monotonic_ns':received,'config_revision':behavior_config['revision'],'detection':detection_settings(behavior_config)})+'\n');events.flush()
                        timestamp=received if rtsp or pts is None else pts
                        current_frame_id=frame_id;frame_id+=1
                        if last_sample is not None and timestamp>=last_sample and timestamp-last_sample<1e9/source['sample_hz']:
                            stats['sample_skipped_frames']+=1;continue
                        last_sample=timestamp;infer_started=time.monotonic_ns()
                        result=model.track(frame,persist=True,tracker=cfg['tracker'],device=cfg['model']['device'],imgsz=cfg['model']['imgsz'],conf=TRACKING_CONFIDENCE,verbose=False)[0]
                        if next(model.model.parameters()).device.type!='cuda':raise RuntimeError('pose model is not on CUDA')
                        torch.cuda.synchronize();done=time.monotonic_ns();all_persons=extract_persons(result)
                        persons=filter_persons(all_persons,behavior_config)
                        # Visualization is built from the privacy-protected source after inference.
                        record={'run_id':run_id,'frame_id':current_frame_id,'source_id':cfg.get('source_id','station-1'),**meta,'pts_ns':pts,'receive_monotonic_ns':received,'inference_started_monotonic_ns':infer_started,'inference_complete_monotonic_ns':done,'local_processing_ms':(done-infer_started)/1e6,'local_receive_to_result_ms':(done-received)/1e6,'width':frame.shape[1],'height':frame.shape[0],'color_format':'BGR','stream_health':'healthy','observation_valid':True,'persons':persons,'workpiece':'UNKNOWN','activity':'UNKNOWN','config_revision':behavior_config['revision'],'privacy_applied':behavior_config['privacy']['enabled'],'detection':detection_settings(behavior_config)}
                        if behavior_engine:
                            if behavior_epoch is None:behavior_epoch=received/1e9-(pts/1e9 if pts is not None else 0)
                            behavior_time=received/1e9 if rtsp or pts is None else behavior_epoch+pts/1e9
                            behavior_engine.observe_persons(behavior_time,persons,frame.shape[1],frame.shape[0],session,
                                now=time.monotonic() if rtsp else behavior_time,sequence=meta['receive_sequence'])
                            persons=behavior_engine.persons
                            record['persons']=persons
                            record['behavior']=behavior_engine.raw
                            record['work_session']=behavior_engine.snapshot(behavior_time)
                            record['ownership']=record['work_session']['ownership']
                        with settings_store.output_policy() as policy:
                            if policy['revision']!=behavior_config['revision']:
                                continue
                            protected=protect_frame(frame,all_persons,policy)
                            annotated=protected.copy()
                            visual_config=deepcopy(policy)
                            if policy['image_size']!=[frame.shape[1],frame.shape[0]]:
                                visual_config['image_size']=[frame.shape[1],frame.shape[0]]
                                full=[[0,0],[frame.shape[1]-1,0],[frame.shape[1]-1,frame.shape[0]-1],[0,frame.shape[0]-1]]
                                visual_config['regions']={'station':full,'seat':full}
                                visual_config['display']['regions']=False
                            draw_overlay(annotated,persons,visual_config)
                            observe_and_draw(annotated,persons,cfg.get('roi',{}),draw=False)
                            if recorder:
                                recorder.write(frame,pts if pts is not None else received,policy,all_persons)
                            observations.write(json.dumps(record)+'\n');observations.flush();latencies.append(record['local_receive_to_result_ms'])
                            if writer is None:
                                writer=cv2.VideoWriter(str(output/'annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),float(source['sample_hz']),(frame.shape[1],frame.shape[0]))
                                if not writer.isOpened():raise RuntimeError('video writer failed')
                                cv2.imwrite(str(output/'source.jpg'),protected)
                                write_json(output/'stream.json',{'width':frame.shape[1],'height':frame.shape[0],'configured_codec':source['codec'],'decoder':'nvv4l2decoder','input_type':source['type'],'negotiated_caps':reader.stream_info,'roi':cfg.get('roi',{}),'privacy_applied':policy['privacy']['enabled'],'config_revision':policy['revision'],'recording':'decoded H264 with media timestamps' if recorder else None})
                            writer.write(annotated);cv2.imwrite(str(output/'annotated.jpg'),annotated)
                            stats['processed_frames']+=1;last_success_ns=done
                    break
                except (TimeoutError,RuntimeError) as exc:
                    last_failure_ns=time.monotonic_ns()
                    if isinstance(exc,TimeoutError):stats['timeouts']+=1
                    events.write(json.dumps({'event':'stream_failure','config_revision':behavior_config['revision'],'exception_type':type(exc).__name__,'error':re.sub(r'rtsp[s]?://[^\s]+','rtsp://<redacted>',str(exc)),'session_id':getattr(reader,'session_id',None),'monotonic_ns':time.monotonic_ns()})+'\n');events.flush()
                    if not rtsp or stats['reconnections']>=source.get('max_reconnects',3):raise
                    stats['reconnections']+=1
                finally:
                    if reader:
                        snap=reader.snapshot();reader.close()
                        stats['pending_discarded_frames']=stats.get('pending_discarded_frames',0)+snap['queue_depth']
                        stats['duplicate_pts_frames']=stats.get('duplicate_pts_frames',0)+snap['duplicate_pts_frames']
                        stats['received_frames']+=snap['received_frames'];stats['overwritten_frames']+=snap['overwritten_frames']
                    with lock:state['reader']=None
                stop.wait(min(2**max(0,stats['reconnections']-1),8))
        if not stats['processed_frames'] or last_failure_ns>last_success_ns:
            raise RuntimeError('no valid observations after latest failure')
        stats['status']='PASS'
    except KeyboardInterrupt:
        stats['status']='STOPPED'
    except Exception as exc:
        stats['status']='FAIL';stats['error_type']=type(exc).__name__;error=exc
    finally:
        stop.set();monitor.join(timeout=3)
        if writer:writer.release()
        if recorder:
            try:recorder.close()
            except RuntimeError as exc:
                stats['status']='FAIL';stats['error_type']=type(exc).__name__;error=exc
        if behavior_engine:
            behavior_engine.interrupt(time.monotonic(),'input_ended')
            stats['work_sessions']=behavior_engine.completed
            (output/'behavior-events.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in behavior_engine.events))
        stats['elapsed_seconds']=(time.monotonic_ns()-started)/1e9
        stats['processing_fps']=stats['processed_frames']/max(stats['elapsed_seconds'],1e-9)
        if latencies:
            import numpy as np
            stats['local_receive_to_result_ms']={'p50':float(np.percentile(latencies,50)),'p95':float(np.percentile(latencies,95)),'max':max(latencies)}
        samples=[json.loads(line) for line in (output/'health.jsonl').read_text().splitlines()]
        if samples:
            rss=[s['rss_bytes'] for s in samples]
            stats['resources']={'samples':len(samples),'rss_first_bytes':rss[0],'rss_last_bytes':rss[-1],'rss_max_bytes':max(rss),'rss_delta_bytes':rss[-1]-rss[0],'cpu_max_percent':max(s['cpu_percent'] for s in samples),'queue_max':max(s.get('queue_depth',0) for s in samples)}
        stats['frames']=stats['processed_frames']
        write_json(output/'statistics.json',stats)
    if error:raise SystemExit('Run failed: '+type(error).__name__+'; see redacted events.jsonl')
if __name__=='__main__':main()

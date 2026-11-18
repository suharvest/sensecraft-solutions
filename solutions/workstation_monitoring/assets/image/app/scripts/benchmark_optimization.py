"""Real backend workers on repeated still frames; NOT a field-accuracy test."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--production',type=Path,required=True);ap.add_argument('--workspace',type=Path,required=True)
    ap.add_argument('--baseline',action='store_true');ap.add_argument('--seconds',type=int,default=60)
    args=ap.parse_args();root=args.root;prod=args.production;workspace=args.workspace
    if root.exists():raise RuntimeError('Use a fresh benchmark root')
    os.environ['WORKTIME_MEDIA_PORT_OFFSET']='200'
    import cv2
    import psutil
    import yaml
    from jetson_worktime.behavior_service import BehaviorService
    from jetson_worktime.studio_store import StudioStore
    from jetson_worktime.streaming import VideoTransport
    cv2.setNumThreads(4);root.mkdir(parents=True);(root/'configs').mkdir()
    config=yaml.safe_load((prod/'configs/behavior.yaml').read_text())
    # Calibration for this existing still: two annotated finished pieces at top,
    # assembly items below. These polygons never touch production settings.
    config['materials']['regions']={'completed':[[760,660],[970,660],[970,830],[760,830]],
                                   'pending':[[850,890],[1250,890],[1250,1250],[850,1250]]}
    original=StudioStore(prod);selection=json.loads((workspace/'selection.json').read_text())
    model=deepcopy(original.get('model',config['models']['material']))
    if not args.baseline:
        model.update(id='benchmark-material',path=selection['model'],sha256=hashlib.sha256(Path(selection['model']).read_bytes()).hexdigest())
        config['models']['material']=model['id']
        config['materials'].update(inference_region='workbench' if selection['selected']=='crop' else 'full',
            production_policy='verified',confidence=selection['confidence'],binding={'model_id':model['id'],'sha256':model['sha256']},show_confidence=False)
        config['materials']['confidence_by_class']=selection.get('confidence_by_class',{})
        config['display'].update(keypoints=False)
    config['privacy']['enabled']=False
    (root/'configs/behavior.yaml').write_text(yaml.safe_dump(config))
    store=StudioStore(root);store.put('model',model)
    person=original.get('model',config['models']['person']);store.put('model',person)
    (root/'vendor').symlink_to(prod/'vendor',target_is_directory=True)
    if not args.baseline:(root/'data/acceleration').symlink_to(workspace/'acceleration',target_is_directory=True)
    frame=cv2.imread(str(sorted((workspace/'dataset/full/images/val').glob('*.jpg'))[0]))
    service=BehaviorService(root);transport=VideoTransport(root);service.transport=transport
    with transport.condition:transport.pending['benchmark-viewer']=(('zh-CN','local'),transport.epoch);transport.condition.notify_all()
    process=psutil.Process();start=time.monotonic();measure=None;sequence=0;memory=[];errors=[]
    try:
        while measure is None or time.monotonic()-measure<args.seconds:
            t=time.monotonic();sequence+=1
            if measure is None and t-start>60:raise RuntimeError('Backend did not establish a counting session')
            service.submit(frame.copy(),round(t*1e9),time.monotonic_ns(),dict(session_id='repeated-still-benchmark',receive_sequence=sequence))
            if measure is None and t-start>=15 and service.engine.current and service.material_counter.initialized:
                measure=t
                for quality in (service.quality,transport.quality):
                    with quality.lock:quality.samples.clear();quality.counts.clear();quality.last.clear()
            if measure is not None and sequence%20==0:
                memory.append(process.memory_info().rss)
                if service.error or service.material_error:errors.append([service.error,service.material_error])
            time.sleep(max(0,.05-(time.monotonic()-t)))
        status=service.snapshot();video=transport.status()
        events=store.events(status['session_id']) if status['session_id'] else []
        report=dict(kind='repeated still-frame backend workload, no camera decode or browser playback',baseline=args.baseline,
            input_fps=20,measured_seconds=time.monotonic()-measure,frame_size=list(frame.shape[1::-1]),
            material_hz=service.quality.rate('material_result'),pose_hz=service.quality.rate('result'),
            video=video,quality=service.quality.snapshot(),backend=status.get('inference_backend'),
            memory_rss_mb=dict(first=memory[0]/2**20,last=memory[-1]/2**20,max=max(memory)/2**20),
            errors=errors,completed_events=sum(e['kind']=='completed' for e in events),
            review_events=sum(e['kind']=='review' for e in events),production_total=status['materials'].get('production_total'),
            initial_inventory=status['materials'].get('initial'),expected_initial_inventory=2,
            evidence_error=status.get('evidence_error'))
        (root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    finally:service.close()


if __name__=='__main__':main()

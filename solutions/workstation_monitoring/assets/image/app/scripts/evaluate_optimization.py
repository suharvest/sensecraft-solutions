"""Select on grouped validation only, freeze confidence, then report one test pass."""
import argparse
import json
import os
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args();root=args.root
    if (root/'selection.json').exists() and json.loads((root/'selection.json').read_text()).get('test_evaluated'):raise RuntimeError('Test already evaluated; preserve the frozen decision')
    os.environ['YOLO_AUTOINSTALL']='False';os.environ['YOLO_CONFIG_DIR']=str(root/'ultralytics')
    import cv2
    import numpy as np
    import torch
    import ultralytics.utils.checks as checks
    import ultralytics.data.utils as data_utils
    from ultralytics.utils import plotting
    checks.check_font=data_utils.check_font=plotting.check_font=lambda *a,**k:Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    from ultralytics import YOLO
    torch.set_num_threads(2);cv2.setNumThreads(2)
    reports={v:json.loads((root/'training'/v/'report.json').read_text()) for v in ('full','crop')}
    selected=max(reports,key=lambda v:reports[v]['validation']['metrics/mAP50-95(B)'])
    model=YOLO(reports[selected]['model']);data=root/'dataset'/selected
    # Fixed, documented threshold sweep over validation predictions only.
    samples=[]
    for p in sorted((data/'images/val').glob('*.jpg')):
        frame=cv2.imread(str(p));h,w=frame.shape[:2]
        pred=model.predict(frame,device=0,imgsz=640,rect=False,conf=.1,verbose=False)[0].boxes.data.cpu().numpy()
        truth=[]
        for line in (data/'labels/val'/(p.stem+'.txt')).read_text().splitlines():
            c,x,y,bw,bh=map(float,line.split());truth.append([int(c),(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h])
        samples.append((pred,truth))
    sweep=[]
    for threshold in (.2,.25,.3,.35,.4,.45,.5,.55,.6):
        counts={i:[0,0,0] for i in range(4)}
        for preds,truth in samples:
            used=set()
            for box in sorted((b for b in preds if b[4]>=threshold),key=lambda b:-b[4]):
                cid=int(box[5]);best=0.;index=None
                for j,target in enumerate(truth):
                    if j in used or target[0]!=cid:continue
                    a=np.maximum(box[:2],target[1:3]);b=np.minimum(box[2:4],target[3:5]);area=np.maximum(0,b-a).prod()
                    overlap=area/(np.prod(box[2:4]-box[:2])+(target[3]-target[1])*(target[4]-target[2])-area+1e-9)
                    if overlap>best:best=overlap;index=j
                if best>=.5:used.add(index);counts[cid][0]+=1
                else:counts[cid][1]+=1
            for j,target in enumerate(truth):
                if j not in used:counts[target[0]][2]+=1
        metrics={}
        for cid,(tp,fp,fn) in counts.items():
            p=tp/max(1,tp+fp);r=tp/max(1,tp+fn)
            metrics[str(cid)]=dict(tp=tp,fp=fp,fn=fn,precision=p,recall=r,f05=1.25*p*r/max(1e-9,.25*p+r))
        sweep.append(dict(confidence=threshold,classes=metrics))
    # Packed products drive completion counting. Prefer lower thresholds on ties.
    choice=max(sweep,key=lambda x:(x['classes']['2']['f05'],-x['confidence']))
    class_thresholds={str(c):max(sweep,key=lambda x:(x['classes'][str(c)]['f05'],-x['confidence']))['confidence'] for c in range(4)}
    decision=dict(selected=selected,model=reports[selected]['model'],confidence=choice['confidence'],
                  criterion='highest validation mAP50-95; packed-class F0.5 confidence sweep, lower threshold on ties',
                  candidates=reports,threshold_sweep=sweep,confidence_by_class=class_thresholds,test_evaluated=False)
    (root/'selection.json').write_text(json.dumps(decision,indent=2))
    test=model.val(data=str(data/'data.yaml'),split='test',device=0,workers=0,batch=4,plots=True,
                   project=str(root/'evaluation'),name='selected-test',exist_ok=True,verbose=False)
    decision.update(test_evaluated=True,test=dict(metrics=test.results_dict,per_class_ap50=test.box.ap50.tolist(),class_ids=test.box.ap_class_index.tolist(),speed=test.speed),
                    limitation='One camera and one short capture session; temporal minute groups, not independent sites. No field accuracy claim.')
    (root/'selection.json').write_text(json.dumps(decision,indent=2));print(json.dumps(decision),flush=True)


if __name__=='__main__':main()

"""Reproducible baseline/crop comparison on a frozen grouped split."""
import argparse
import json
import os
from pathlib import Path
import time


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--base',required=True)
    ap.add_argument('--variant',choices=['full','crop'],required=True);ap.add_argument('--epochs',type=int,default=100)
    args=ap.parse_args();root=args.root;out=root/'training'/args.variant;out.mkdir(parents=True,exist_ok=True)
    os.environ['YOLO_CONFIG_DIR']=str(root/'ultralytics');os.environ['YOLO_AUTOINSTALL']='False'
    import torch
    torch.set_num_threads(2)
    import ultralytics.utils.checks as checks
    import ultralytics.data.utils as data_utils
    from ultralytics.utils import plotting
    local_font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    checks.check_font=data_utils.check_font=plotting.check_font=lambda *a,**kw:local_font
    checks.check_amp=lambda model:True  # Existing Jetson FP16 path; avoid external download during checks.
    import ultralytics.engine.trainer as trainer
    trainer.check_amp=checks.check_amp
    from ultralytics import YOLO
    import yaml
    data=root/'dataset'/args.variant/'data.yaml';cfg=yaml.safe_load(data.read_text());cfg['path']=str(data.parent);data.write_text(yaml.safe_dump(cfg))
    start=time.time();model=YOLO(args.base)
    model.train(data=str(data),epochs=args.epochs,patience=20,batch=4,imgsz=640,device=0,workers=0,
                optimizer='AdamW',lr0=.001,warmup_bias_lr=0.,seed=42,deterministic=True,
                project=str(out),name='run',exist_ok=True,plots=True,amp=True,
                degrees=3,translate=.05,scale=.25,fliplr=0.,mosaic=.3,close_mosaic=15,
                hsv_h=.01,hsv_s=.15,hsv_v=.20,verbose=False)
    best=out/'run/weights/best.pt'
    validation=YOLO(str(best)).val(data=str(data),split='val',device=0,workers=0,batch=4,plots=True,
                                   project=str(out),name='validation',exist_ok=True,verbose=False)
    report=dict(variant=args.variant,model=str(best),seconds=time.time()-start,validation=validation.results_dict,
                speed=validation.speed,per_class_ap50=validation.box.ap50.tolist(),names=validation.names,
                test_evaluated=False,limitation='Grouped same-camera validation; not field accuracy.')
    (out/'report.json').write_text(json.dumps(report,indent=2));print('OPTIMIZATION_RESULT',json.dumps(report),flush=True)


if __name__=='__main__':main()

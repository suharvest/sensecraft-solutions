"""Bounded CPU compatibility check for trusted YOLO11 weights, never on live GPU."""
import json
import os
from pathlib import Path
import sys
os.environ['YOLO_AUTOINSTALL']='False'
os.environ['OMP_NUM_THREADS']='1'
try:
    import numpy as np
    import torch
    torch.set_num_threads(1)
    from ultralytics import YOLO
    model=YOLO(sys.argv[1])
    task='pose' if sys.argv[2]=='person' else 'detect'
    assert model.task==task
    name=str(model.model.yaml.get('yaml_file','')).lower()
    assert 'yolo11' in name
    if task=='pose':
        assert list(model.model.yaml.get('kpt_shape',[]))==[17,3]
        assert model.model.yaml.get('nc')==1 and list(model.names.values())==['person']
    result=model.predict(np.zeros((320,320,3),dtype=np.uint8),device='cpu',imgsz=320,verbose=False)[0]
    info=dict(valid=True,task=task,classes={str(k):v for k,v in model.names.items()})
    code=0
except Exception:
    info=dict(valid=False);code=1
Path(sys.argv[3]).write_text(json.dumps(info))
sys.exit(code)

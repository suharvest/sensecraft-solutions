"""Bounded workbench crops and optional, verified TensorRT acceleration."""
import hashlib
import json
from pathlib import Path


def workbench_crop(config, width, height):
    """Include both material zones and the operating space between them."""
    mat=config.get('materials',{})
    if not mat.get('configured') or config.get('image_size') != [width,height]:
        return (0,0,width,height)
    points=[p for polygon in mat.get('regions',{}).values() for p in polygon]
    if not points:return (0,0,width,height)
    xs,ys=zip(*points);w=max(xs)-min(xs);h=max(ys)-min(ys)
    px=max(96,w*.35);py=max(80,h*.12)
    return (max(0,int(min(xs)-px)),max(0,int(min(ys)-py)),
            min(width,int(max(xs)+px)),min(height,int(max(ys)+py)))


def material_input(frame, config):
    if config.get('materials',{}).get('inference_region','full') != 'workbench':
        return frame,(0,0)
    x1,y1,x2,y2=workbench_crop(config,frame.shape[1],frame.shape[0])
    return frame[y1:y2,x1:x2],(x1,y1)


def material_results(result, offset=(0,0)):
    dx,dy=offset
    return [dict(bbox_xyxy=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy],class_id=int(c),confidence=float(q))
            for b,c,q in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist())]


def acceleration_path(root, metadata):
    """Engine cache is opt-in and bound to weights, TensorRT and this hardware.

    PT remains authoritative. A missing/mismatched cache silently uses PT; a
    failed engine warmup is caught by the caller and also falls back to PT.
    """
    import platform
    if not metadata.get('sha256'):return metadata['path'],'pytorch'
    manifest=Path(root)/'data/acceleration'/f"{metadata['sha256']}.json"
    if not manifest.exists():return metadata['path'],'pytorch'
    try:
        import tensorrt
        value=json.loads(manifest.read_text())
        engine=Path(value['engine'])
        if not engine.is_absolute():engine=manifest.parent/engine
        from .deployment import device_model
        hardware=device_model()
        if (value['weights_sha256']!=metadata['sha256'] or value['tensorrt']!=tensorrt.__version__
                or value['machine']!=platform.machine() or value['hardware']!=hardware
                or not value.get('validated') or not engine.is_file()):return metadata['path'],'pytorch'
        if hashlib.sha256(engine.read_bytes()).hexdigest()!=value['engine_sha256']:return metadata['path'],'pytorch'
        return str(engine),'tensorrt-fp16'
    except (ImportError,OSError,ValueError,KeyError):return metadata['path'],'pytorch'


def load_accelerated(YOLO, root, metadata, frame, confidence=.1):
    path,backend=acceleration_path(root,metadata)
    try:
        model=YOLO(path,task=metadata.get('task')) if backend!='pytorch' else YOLO(path)
        model.predict(frame,device='cuda:0',imgsz=640,conf=confidence,verbose=False)
    except Exception:
        if backend=='pytorch':raise
        model=YOLO(metadata['path']);backend='pytorch-fallback'
        model.predict(frame,device='cuda:0',imgsz=640,conf=confidence,verbose=False)
    return model,backend

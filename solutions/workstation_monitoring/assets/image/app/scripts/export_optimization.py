"""Build a device-bound FP16 cache and check numerical parity before enabling it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import time


def build_static_engine(onnx_file,engine_file,workspace,half,int8,dynamic,shape,**options):
    """Bound compilation search on Jetson; same Ultralytics metadata format."""
    import tensorrt as trt
    if int8 or dynamic or not half:raise ValueError('This release uses static FP16 only')
    logger=trt.Logger(trt.Logger.INFO);builder=trt.Builder(logger)
    network=builder.create_network(1<<int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser=trt.OnnxParser(network,logger)
    if not parser.parse_from_file(str(onnx_file)):
        raise RuntimeError('; '.join(str(parser.get_error(i)) for i in range(parser.num_errors)))
    config=builder.create_builder_config();config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,int(workspace*2**30))
    config.set_flag(trt.BuilderFlag.FP16);config.builder_optimization_level=1
    cache_path=Path(engine_file).parent/'timing.cache'
    cache=config.create_timing_cache(cache_path.read_bytes() if cache_path.exists() else b'')
    config.set_timing_cache(cache,False)
    print('Building static FP16 with optimization level 1',flush=True)
    engine=builder.build_serialized_network(network,config)
    if engine is None:raise RuntimeError('TensorRT build failed')
    metadata=json.dumps(options['metadata']).encode()
    Path(engine_file).write_bytes(len(metadata).to_bytes(4,'little',signed=True)+metadata+bytes(engine))
    cache_path.write_bytes(bytes(config.get_timing_cache().serialize()))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--weights',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--samples',type=Path,required=True)
    ap.add_argument('--confidence',type=float,default=.2)
    ap.add_argument('--reuse-engine',action='store_true')
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    os.environ['YOLO_AUTOINSTALL']='False'
    import cv2
    import numpy as np
    import torch
    import tensorrt
    from ultralytics import YOLO
    import ultralytics.engine.exporter as exporter
    from jetson_worktime.deployment import device_model
    exporter.export_engine=build_static_engine
    torch.set_num_threads(2);cv2.setNumThreads(2)
    digest=hashlib.sha256(args.weights.read_bytes()).hexdigest()
    copied=out/(digest+'.pt');shutil.copy2(args.weights,copied)
    model=YOLO(str(copied));task=model.task
    engine=str(copied.with_suffix('.engine')) if args.reuse_engine else model.export(format='engine',half=True,device=0,imgsz=640,batch=1,dynamic=False,
                        workspace=2,simplify=False,opset=17,verbose=False)
    accelerated=YOLO(engine,task=task)
    images=[cv2.imread(str(p)) for p in sorted(args.samples.glob('*.jpg'))[:20]]
    if not images:raise RuntimeError('No validation samples')
    timings={'pytorch':[],'tensorrt':[]};matches=0;expected=0;extra=0;keypoint_errors=[]
    for i,frame in enumerate(images):
        results=[]
        for name,net in [('pytorch',model),('tensorrt',accelerated)]:
            if i==0:
                for _ in range(5):net.predict(frame,device=0,imgsz=640,rect=False,conf=args.confidence,verbose=False)
            start=time.perf_counter();result=net.predict(frame,device=0,imgsz=640,rect=False,conf=args.confidence,verbose=False)[0]
            torch.cuda.synchronize();timings[name].append((time.perf_counter()-start)*1000);results.append(result)
        a,b=results;used=set();expected+=len(a.boxes)
        for item,(box,cid) in enumerate(zip(a.boxes.xyxy.cpu().numpy(),a.boxes.cls.cpu().numpy())):
            best=0.;index=None
            for j,(other,cls) in enumerate(zip(b.boxes.xyxy.cpu().numpy(),b.boxes.cls.cpu().numpy())):
                if j in used or cid!=cls:continue
                left=np.maximum(box[:2],other[:2]);right=np.minimum(box[2:],other[2:]);intersection=np.maximum(0,right-left).prod()
                overlap=intersection/(np.prod(box[2:]-box[:2])+np.prod(other[2:]-other[:2])-intersection+1e-9)
                if overlap>best:best=overlap;index=j
            if best>=.8:
                matches+=1;used.add(index)
                if task=='pose':
                    ka=a.keypoints.data[item].cpu().numpy();kb=b.keypoints.data[index].cpu().numpy()
                    visible=(ka[:,2]>=.4)&(kb[:,2]>=.4)
                    keypoint_errors.extend((np.linalg.norm(ka[visible,:2]-kb[visible,:2],axis=1)/frame.shape[1]).tolist())
        extra+=len(b.boxes)-len(used)
    ratio=matches/max(1,expected);extra_ratio=extra/max(1,expected)
    keypoint_p95=float(np.percentile(keypoint_errors,95)) if keypoint_errors else None
    report=dict(weights_sha256=digest,engine=Path(engine).name,engine_sha256=hashlib.sha256(Path(engine).read_bytes()).hexdigest(),
        tensorrt=tensorrt.__version__,machine=platform.machine(),hardware=device_model(),
        task=task,validated=ratio>=.97 and extra_ratio<=.03 and (task!='pose' or keypoint_p95 is not None and keypoint_p95<=.01),
        parity=dict(expected=expected,matches=matches,extra=extra,matched_fraction=ratio,keypoint_p95_width_fraction=keypoint_p95),
        latency_ms={k:dict(median=statistics.median(v),p95=sorted(v)[int(.95*(len(v)-1))]) for k,v in timings.items()},
        samples='validation only',confidence=args.confidence,builder_optimization_level=1,created_at=time.time())
    (out/(digest+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    if not report['validated']:raise RuntimeError('Engine failed parity gate; PT retained')


if __name__=='__main__':main()

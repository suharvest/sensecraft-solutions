"""Conservative operation-time estimate; never reinterprets presence history."""
from copy import deepcopy
import math


class ActivityEstimator:
    BASIS='operation_estimate_v1'

    def __init__(self):
        self.session_id=None;self.context=None;self.last=None;self.state='unknown'
        self.candidate=None;self.since=None;self.reason='no_observation'
        self.totals={s:0. for s in ('active','idle','absent','unknown')}
        self.previous_gray=None;self.previous_wrists={};self.last_signal=None

    def reset_context(self):
        self.context=None;self.state='unknown';self.candidate=None;self.since=None
        self.previous_gray=None;self.previous_wrists={};self.last_signal=None

    def settle(self,t,signal,reason,session_id,context):
        if session_id is None:
            self.last=None;self.state='unknown';self.reason='no_session';return
        if session_id!=self.session_id:
            self.__init__();self.session_id=session_id
        if context!=self.context:
            self.reset_context();self.context=context
        if self.last is not None and t<=self.last:return
        if self.last is not None:
            dt=t-self.last
            # Gaps are unknown, not inferred activity or absence.
            if dt>1.5:self.totals['unknown']+=dt;self.state='unknown';self.candidate=None
            else:self.totals[self.state]+=dt
        self.last=t;self.reason=reason
        if signal in ('unknown','absent'):
            self.state=signal;self.candidate=None;self.since=None;return
        if signal!=self.candidate:self.candidate=signal;self.since=t
        confirmation=1.5 if signal=='active' else 2.
        if t-self.since>=confirmation:self.state=signal

    def observe(self,t,frame,persons,detections,config,session_id,context,valid=True):
        import cv2
        import numpy as np
        from .inference import workbench_crop
        x1,y1,x2,y2=workbench_crop(config,frame.shape[1],frame.shape[0])
        gray=cv2.cvtColor(cv2.resize(frame[y1:y2,x1:x2],(320,256)),cv2.COLOR_BGR2GRAY)
        owners=[p for p in persons if p.get('is_session_operator')]
        signal='unknown';reason='insufficient_evidence';wrists={}
        same=self.context==context and self.session_id==session_id and self.last is not None and 0<t-self.last<=1.5
        if not valid:reason='observation_unavailable'
        elif not owners:
            signal='absent' if not persons else 'unknown';reason='operator_not_visible'
        else:
            person=owners[0];points=person.get('keypoints',[])
            for j in (9,10):
                if len(points)>j:
                    k=points[j]
                    if k.get('confidence',0)>=config.get('keypoint_confidence',.4) and k.get('x') is not None and k.get('y') is not None:
                        wrists[j]=(k['x'],k['y'])
            if wrists and same and self.previous_gray is not None:
                diff=cv2.absdiff(gray,self.previous_gray).astype(np.float32)
                # Reject uniform illumination changes as evidence of handling.
                diff=np.maximum(0,diff-np.median(diff))
                active=False;inside=False;near=False
                for j,(x,y) in wrists.items():
                    if not (x1<=x<x2 and y1<=y<y2):continue
                    inside=True;px=int((x-x1)/(x2-x1)*320);py=int((y-y1)/(y2-y1)*256)
                    patch=diff[max(0,py-18):min(256,py+19),max(0,px-18):min(320,px+19)]
                    moving=bool(patch.size and np.mean(patch>18)>.035)
                    previous=self.previous_wrists.get(j)
                    speed=math.dist((x,y),previous)/(t-self.last) if previous else 0
                    close=any(math.dist((x,y),((d['bbox_xyxy'][0]+d['bbox_xyxy'][2])/2,(d['bbox_xyxy'][1]+d['bbox_xyxy'][3])/2))
                              < max(100,math.hypot(d['bbox_xyxy'][2]-d['bbox_xyxy'][0],d['bbox_xyxy'][3]-d['bbox_xyxy'][1])*2)
                              for d in (detections or []))
                    near|=close;active|=moving and speed>frame.shape[1]*.008 and close
                if active:signal='active';reason='hand_motion_near_material'
                elif not inside or near:signal='idle';reason='no_handling_motion'
                else:reason='material_interaction_unconfirmed'
            elif not wrists:reason='wrists_occluded'
        self.settle(t,signal,reason,session_id,context)
        self.previous_gray=gray;self.previous_wrists=wrists;self.last_signal=signal

    def snapshot(self,now,available=True,session_id=None):
        current=session_id==self.session_id and session_id is not None
        fresh=current and available and self.last is not None and 0<=now-self.last<=1.5
        return dict(basis=self.BASIS,experimental=True,session_id=self.session_id,
                    available=bool(fresh),state=self.state if fresh else 'unknown',
                    reason=self.reason if fresh else 'observation_unavailable',
                    active_estimated_seconds=round(self.totals['active'],3),
                    idle_seconds=round(self.totals['idle'],3),absent_seconds=round(self.totals['absent'],3),
                    unknown_seconds=round(self.totals['unknown'],3),
                    observed_seconds=round(sum(self.totals.values()),3))

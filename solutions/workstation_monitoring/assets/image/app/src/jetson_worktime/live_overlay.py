"""Display-only optical flow. Never feeds business state or privacy protection."""
from copy import deepcopy
import cv2
import numpy as np

MAX_FOLLOW_NS = 300_000_000
MAX_SOURCE_AGE_NS = 750_000_000


class _FlowLayer:
    def __init__(self,width=384):
        self.width=width
        self.reset()

    def reset(self):
        self.source = None
        self.gray = None
        self.objects = []
        self.points = None
        self.owners = []
        self.crop=None

    def gray_frame(self,frame):
        x1,y1,x2,y2=self.crop or (0,0,frame.shape[1],frame.shape[0])
        view=frame[y1:y2,x1:x2];width=min(self.width,view.shape[1]);height=max(1,round(view.shape[0]*width/view.shape[1]))
        return cv2.cvtColor(cv2.resize(view,(width,height)),cv2.COLOR_BGR2GRAY)

    def seed(self, observation):
        self.source=observation
        self.objects=[('person',deepcopy(p)) for p in observation['persons']]
        self.objects += [('material',deepcopy(d)) for d in observation['materials'].get('detections',[])]
        if not self.objects:
            self.crop=None;self.gray=None;self.points=None;self.owners=[]
            return
        frame=observation['frame'];boxes=[o['bbox_xyxy'] for _,o in self.objects]
        if boxes:
            self.crop=(max(0,int(min(b[0] for b in boxes))-80),max(0,int(min(b[1] for b in boxes))-80),
                       min(frame.shape[1],int(max(b[2] for b in boxes))+80),min(frame.shape[0],int(max(b[3] for b in boxes))+80))
        else:self.crop=(0,0,frame.shape[1],frame.shape[0])
        self.gray=self.gray_frame(frame)
        self.scale=self.gray.shape[1]/(self.crop[2]-self.crop[0])
        points=[];self.owners=[]
        for index,(_,obj) in enumerate(self.objects):
            x1,y1,x2,y2=[round((v-self.crop[i%2])*self.scale) for i,v in enumerate(obj['bbox_xyxy'])]
            x1=max(0,x1);y1=max(0,y1);x2=min(self.gray.shape[1],x2);y2=min(self.gray.shape[0],y2)
            if x2<=x1 or y2<=y1: continue
            # Extract corners only inside this object. A full-layer mask still
            # computes corner responses across the whole workbench per object.
            found=cv2.goodFeaturesToTrack(self.gray[y1:y2,x1:x2],maxCorners=12,qualityLevel=.02,minDistance=2)
            if found is not None:
                found += np.array([x1,y1],dtype=np.float32)
                points.extend(found[:,0].tolist());self.owners.extend([index]*len(found))
        self.points=np.array(points,np.float32).reshape(-1,1,2) if points else None

    def render(self,frame,received,meta,revision,epoch,observation):
        # Model processing is not display hold time. A newly completed result may
        # already be >300 ms from capture when both models are busy. Still cap the
        # total source age and require current-frame optical-flow validation.
        deadline=min(observation['received']+MAX_SOURCE_AGE_NS,
                     observation.get('completed',observation['received'])+MAX_FOLLOW_NS) if observation else 0
        if (not observation or observation['revision']!=revision or observation['epoch']!=epoch
            or observation['meta']['session_id']!=meta['session_id']
            or received<observation['received'] or received>deadline
            or frame.shape!=observation['frame'].shape):
            self.reset();return [],{},None
        if self.source is not observation: self.seed(observation)
        if not self.objects:return [],deepcopy(observation['materials']),None
        exact=meta['receive_sequence']==observation['meta']['receive_sequence']
        if not exact:
            gray=self.gray_frame(frame)
            if self.points is None: return [],{},None
            nxt,ok,_=cv2.calcOpticalFlowPyrLK(self.gray,gray,self.points,None,winSize=(15,15),maxLevel=1)
            if nxt is None: self.reset();return [],{},None
            back,back_ok,_=cv2.calcOpticalFlowPyrLK(gray,self.gray,nxt,None,winSize=(15,15),maxLevel=1)
            if back is None: self.reset();return [],{},None
            good=ok[:,0].astype(bool)&back_ok[:,0].astype(bool)&(np.linalg.norm(back[:,0]-self.points[:,0],axis=1)<.75)
            good &= (nxt[:,0,0]>=0)&(nxt[:,0,1]>=0)&(nxt[:,0,0]<gray.shape[1])&(nxt[:,0,1]<gray.shape[0])
            for index,(_,obj) in enumerate(self.objects):
                selected=good & (np.asarray(self.owners)==index)
                if selected.sum()<4: obj['_hidden']=True;continue
                delta=(nxt[selected,0]-self.points[selected,0])/self.scale
                shift=np.median(delta,axis=0)
                # Reject incoherent motion / an occluding hand replacing the target.
                if np.median(np.linalg.norm(delta-shift,axis=1))>6 or np.linalg.norm(shift)>frame.shape[1]*.08:
                    obj['_hidden']=True;continue
                dx,dy=map(float,shift);b=obj['bbox_xyxy']
                obj['bbox_xyxy']=[max(0,min(frame.shape[1]-1,b[0]+dx)),max(0,min(frame.shape[0]-1,b[1]+dy)),
                    max(0,min(frame.shape[1]-1,b[2]+dx)),max(0,min(frame.shape[0]-1,b[3]+dy))]
                for point in obj.get('keypoints',[]):
                    if point.get('x') is not None and point.get('y') is not None: point['x']+=dx;point['y']+=dy
                if obj.get('upper_body_anchor'): obj['upper_body_anchor']=[obj['upper_body_anchor'][0]+dx,obj['upper_body_anchor'][1]+dy]
            self.gray=gray;self.points=nxt[good].reshape(-1,1,2);self.owners=[owner for owner,valid in zip(self.owners,good) if valid]
        persons=[deepcopy(obj) for kind,obj in self.objects if kind=='person' and not obj.get('_hidden')]
        material=deepcopy(observation['materials'])
        material['detections']=[deepcopy(obj) for kind,obj in self.objects if kind=='material' and not obj.get('_hidden')]
        evidence=dict(kind='detected' if exact else 'followed',source_frame_sequence=observation['meta']['receive_sequence'],
            source_received_ns=observation['received'],age_ms=(received-observation['received'])/1e6,config_revision=revision)
        return persons,material,evidence


class LiveOverlay:
    """Separate person and workbench flow; small products retain real texture."""
    def __init__(self):
        self.people=_FlowLayer(384);self.products=_FlowLayer(480)
        self.reset()

    def reset(self):
        self.people.reset();self.products.reset();self.source=None;self.layers=None

    def render(self,frame,received,meta,revision,epoch,observation):
        if observation is not self.source:
            self.source=observation
            self.layers=({**observation,'materials':{}},{**observation,'persons':[]}) if observation else (None,None)
        layers=self.layers or (None,None)
        people,_,pe=self.people.render(frame,received,meta,revision,epoch,layers[0])
        _,materials,me=self.products.render(frame,received,meta,revision,epoch,layers[1])
        return people,materials,pe or me

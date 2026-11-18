"""Time-based, conservative product counting, independent of human identity."""
from copy import deepcopy
from collections import deque
import math
import re
import time
from .studio_store import StudioError, uid

MATERIAL_DEFAULTS = dict(enabled=False, class_id=0, confidence=.25, stable_seconds=1.,
    missing_seconds=2., sample_hz=2., configured=False, regions={'pending':[], 'completed':[]},
    display={'pending':True, 'completed':True},
    colors={'pending':'#fbbf24', 'completed':'#38bdf8'}, opacity={'pending':.12,'completed':.12},
    rules={'pending':{'count':[0],'alert':[]},'completed':{'count':[0],'alert':[]}},
    names={'pending':'','completed':''}, masks={'pending':True,'completed':True}, class_styles={}, binding=None, show_confidence=True,
    inference_region='full', production_policy='legacy',confidence_by_class={})
MODEL_DEFAULTS = {'person':'builtin-person', 'material':None}


def number(value, low, high):
    return isinstance(value, (float,int)) and not isinstance(value,bool) and math.isfinite(value) and low <= value <= high


def material_threshold(material,cid):
    return max(material['confidence'],material.get('confidence_by_class',{}).get(str(cid),0))


def material_behavior_changed(old,new):
    keys=('enabled','confidence','confidence_by_class','stable_seconds','missing_seconds','sample_hz','configured','regions','rules','binding','inference_region','production_policy')
    return any(old.get(k)!=new.get(k) for k in keys)


def validate_materials(value, image_size):
    from .settings import validate_polygon, polygons_intersect
    if not isinstance(value,dict) or set(value)-set(MATERIAL_DEFAULTS):
        raise StudioError('materialsInvalid')
    value=deepcopy(value)
    value.setdefault('show_confidence', True)
    value.setdefault('inference_region','full')
    value.setdefault('production_policy','legacy')
    value.setdefault('confidence_by_class',{})
    if not isinstance(value['confidence_by_class'],dict) or any(not isinstance(k,str) or not re.fullmatch(r'0|[1-9][0-9]{0,2}',k) or not number(v,.01,1) for k,v in value['confidence_by_class'].items()):
        raise StudioError('materialsInvalid')
    if value['inference_region'] not in ('full','workbench') or value['production_policy'] not in ('legacy','verified'):
        raise StudioError('materialsInvalid')
    if type(value['show_confidence']) is not bool: raise StudioError('materialsInvalid')
    for key in ('rules','names','masks','class_styles','binding'):
        if key not in value:
            value[key]=deepcopy(MATERIAL_DEFAULTS[key])
            if key=='rules':
                value[key]={r:{'count':[value.get('class_id',0)],'alert':[]} for r in ('pending','completed')}
    if set(value)!=set(MATERIAL_DEFAULTS): raise StudioError('materialsInvalid')
    if any(type(value[k]) is not bool for k in ('enabled','configured')) or type(value['class_id']) is not int or not 0 <= value['class_id'] <= 999:
        raise StudioError('materialsInvalid')
    for key, low, high in [('confidence',.01,1),('stable_seconds',.1,60),('missing_seconds',.1,60),('sample_hz',.2,10)]:
        if not number(value[key],low,high): raise StudioError('materialsInvalid')
    for key in ('regions','display','colors','opacity','rules','names','masks'):
        if not isinstance(value[key],dict) or set(value[key]) != {'pending','completed'}: raise StudioError('materialsInvalid')
    for region in ('pending','completed'):
        if (type(value['display'][region]) is not bool or type(value['masks'][region]) is not bool
            or not re.fullmatch('#[0-9a-fA-F]{6}',str(value['colors'][region])) or not number(value['opacity'][region],0,1)
            or not isinstance(value['names'][region],str) or len(value['names'][region])>60): raise StudioError('materialsInvalid')
        rule=value['rules'][region]
        if not isinstance(rule,dict) or set(rule)!={'count','alert'}: raise StudioError('materialsInvalid')
        for role,ids in rule.items():
            if not isinstance(ids,list) or len(ids)!=len(set(str(i) for i in ids)) or any(type(i) is not int or not 0<=i<=999 for i in ids): raise StudioError('materialsInvalid')
        if set(rule['count']) & set(rule['alert']): raise StudioError('materialsInvalid')
        if value['configured'] or value['regions'][region]: validate_polygon(value['regions'][region],image_size,region)
    if not isinstance(value['class_styles'],dict): raise StudioError('materialsInvalid')
    for key,style in value['class_styles'].items():
        if (not re.fullmatch(r'0|[1-9][0-9]{0,2}',str(key)) or not isinstance(style,dict) or set(style)!={'name','color'}
            or not isinstance(style['name'],str) or len(style['name'])>100 or not re.fullmatch('#[0-9a-fA-F]{6}',str(style['color']))): raise StudioError('materialsInvalid')
    binding=value['binding']
    if binding is not None and (not isinstance(binding,dict) or set(binding)!={'model_id','sha256'}
        or not isinstance(binding['model_id'],str) or not binding['model_id'] or not re.fullmatch('[0-9a-f]{64}',str(binding['sha256']))): raise StudioError('materialsInvalid')
    if value['configured'] and polygons_intersect(*value['regions'].values()): raise StudioError('materialsOverlap')
    if value['enabled'] and (not value['configured'] or not value['rules']['completed']['count']): raise StudioError('materialsRoi')
    return value


def assign_targets(costs, unmatched=1.0):
    """Rectangular Hungarian assignment with a private unmatched column per row.

    No class information enters this assignment. Costs >= unmatched are gated out.
    """
    n = len(costs)
    if not n: return []
    real = len(costs[0]); m = real+n
    a = [row+[unmatched]*n for row in costs]
    u, v, p, way = [0.]*(n+1), [0.]*(m+1), [0]*(m+1), [0]*(m+1)
    for i in range(1,n+1):
        p[0]=i; j0=0; minimum=[float('inf')]*(m+1); used=[False]*(m+1)
        while True:
            used[j0]=True; i0=p[j0]; delta=float('inf'); j1=0
            for j in range(1,m+1):
                if not used[j]:
                    cur=a[i0-1][j-1]-u[i0]-v[j]
                    if cur<minimum[j]: minimum[j]=cur;way[j]=j0
                    if minimum[j]<delta: delta=minimum[j];j1=j
            for j in range(m+1):
                if used[j]: u[p[j]]+=delta;v[j]-=delta
                else: minimum[j]-=delta
            j0=j1
            if not p[j0]: break
        while j0:
            j1=way[j0];p[j0]=p[j1];j0=j1
    return [(p[j]-1,j-1) for j in range(1,real+1) if p[j] and a[p[j]-1][j-1]<unmatched]


def matching_cost(track, box, t):
    from .behavior import iou
    old=track['bbox']; dt=min(.5,max(0,t-track['last_seen']))
    velocity=track.get('velocity',(0.,0.))
    predicted=[old[0]+velocity[0]*dt,old[1]+velocity[1]*dt,
               old[2]+velocity[0]*dt,old[3]+velocity[1]*dt]
    w,h=max(1,old[2]-old[0]),max(1,old[3]-old[1])
    nw,nh=max(1,box[2]-box[0]),max(1,box[3]-box[1])
    ratio=max(w*h/(nw*nh),nw*nh/(w*h))
    distance=math.hypot((predicted[0]+predicted[2]-box[0]-box[2])/2,
                        (predicted[1]+predicted[3]-box[1]-box[3])/2)/math.hypot(w,h)
    # A handled part often stops abruptly when put down. Constant velocity alone
    # overshoots its resting position and creates a second identity.
    overlap=max(iou(predicted,box),iou(old,box))
    stationary_distance=math.hypot((old[0]+old[2]-box[0]-box[2])/2,
                                   (old[1]+old[3]-box[1]-box[3])/2)/math.hypot(w,h)
    distance=min(distance,stationary_distance)
    if ratio>3 or (overlap<.1 and distance>1.25): return 10.
    return .6*(1-overlap)+.3*min(distance,2)+.1*min(abs(math.log(ratio)),2)


class MaterialCounter:
    def __init__(self, store):
        self.store = store
        for alert in store.list('material_alert'):
            if alert.get('active'):
                alert.update(active=False,resolved_at=time.time(),resolution='service_restarted');store.put('material_alert',alert)
        self.reset()

    def reset(self):
        for tr in getattr(self,'tracks',{}).values(): self._close_alert(tr,'reset')
        self.tracks = {}
        self.last_time = None
        self.session_id = None
        self.initialized = False
        self.departed = False
        self.counts = {'pending':0, 'completed':0}
        self.by_class = {'pending':{},'completed':{}}
        self.last_meta = {}
        self.sample_times = deque(maxlen=30)
        self.retired = deque(maxlen=256)
        self.pending_evidence = []

    def _close_alert(self,tr,reason):
        alert=tr.pop('alert',None)
        if alert:
            alert.update(active=False,resolved_at=time.time(),resolution=reason)
            self.store.put('material_alert',alert)
            if alert.get('session_id'): self.store.event(alert['session_id'],'alert_resolved',alert['id'],0,alert_id=alert['id'],resolution=reason,**self.last_meta)

    def _session(self, session_id):
        if self.session_id != session_id:
            for track in self.tracks.values():
                self._close_alert(track,'session_changed')
                track.update(counted=False,reviewed=False,abnormal_reviewed=False,
                             production_counted=False,returned=False,pending_confirmed=False)
            self.session_id = session_id
            self.initialized = False
            self.departed = False
            self.retired.clear()

    def _record(self, kind, key, delta=0, **metadata):
        event=self.store.event(self.session_id,kind,key,delta,**metadata,**self.last_meta)
        self.pending_evidence.append(event)
        return event

    def _role(self,tr,material):
        if tr.get('conflict') and not tr['stable']: return None
        rule=material['rules'].get(tr['region'],{})
        return 'alert' if tr['class_id'] in rule.get('alert',[]) else 'count' if tr['class_id'] in rule.get('count',[]) else None

    def _review(self,key,tr,reason):
        if self.session_id:
            event_key=key+(':'+reason if reason!='return' else '')
            self._record('review',event_key,0,track_id=key,review_reason=reason,
                class_id=tr['class_id'],region=tr['region'],bbox_xyxy=list(tr['bbox']),
                production_counted=tr.get('production_counted',False),already_counted=tr.get('counted',False))

    @staticmethod
    def _vote(tr,t,vote,material):
        history=tr['history']; history.append((t,vote))
        window=material['stable_seconds']+1/material['sample_hz']
        while history and t-history[0][0]>window+1e-9: history.popleft()
        if vote is None: return
        support=[at for at,value in history if value==vote]
        if len(support)>=2 and len(support)/len(history)>=.75 and support[-1]-support[0]+1e-9>=material['stable_seconds']:
            tr.update(region=vote[0],class_id=vote[1],stable=True,last_reliable=t)

    def observe(self, detections, t, config, session_id=None, **meta):
        from .behavior import iou, point_in_polygon
        if self.last_time is not None and t <= self.last_time: return
        self._session(session_id)
        material=config['materials']
        # Direct callers with legacy configurations retain their original class filter.
        if 'rules' not in material:
            material={**material,'rules':{r:{'count':[material['class_id']],'alert':[]} for r in ('pending','completed')}}
        verified=material.get('production_policy')=='verified'
        self.last_meta=dict(config_revision=config['revision'],class_styles=deepcopy(material.get('class_styles',{})),rules=deepcopy(material['rules']),
                           production_basis='completion_events_v1' if verified else 'legacy',**meta)
        for key in list(self.tracks):
            tr=self.tracks[key]
            if t-tr['last_seen']>material['missing_seconds']:
                self._close_alert(tr,'left_or_missing')
                if tr['counted'] or tr['reviewed']: self.departed=True
                if verified and tr['stable'] and tr['region']=='completed':self.retired.append(deepcopy(tr))
                del self.tracks[key]
        selected={c for r in material['rules'].values() for ids in r.values() for c in ids}
        candidates=[d for d in detections if d.get('class_id') in selected and d['confidence']>=material_threshold(material,d['class_id'])]
        # Collapse conflicting duplicate detections before one-to-one matching.
        grouped=[]
        for det in sorted(candidates,key=lambda d:d['confidence'],reverse=True):
            duplicate=next((d for d in grouped if iou(det['bbox_xyxy'],d['bbox_xyxy'])>=.75),None)
            if duplicate is not None:
                if duplicate['class_id']!=det['class_id']: duplicate['conflict']=True
            else: grouped.append(dict(det))
        keys=list(self.tracks)
        costs=[[matching_cost(self.tracks[key],d['bbox_xyxy'],t) for d in grouped] for key in keys]
        assignments={j:keys[i] for i,j in assign_targets(costs)}
        seen=set()
        for j,det in enumerate(grouped):
            box=det['bbox_xyxy'];cid=det['class_id']
            center=[(box[0]+box[2])/2,(box[1]+box[3])/2]
            region=next((r for r,p in material['regions'].items() if point_in_polygon(center,p)),None)
            key=assignments.get(j)
            # A nearly tied identity cannot generate new production.
            nearby=sorted(row[j] for row in costs if row[j]<1)
            ambiguous=len(nearby)>1 and nearby[1]-nearby[0]<.08
            returned=False
            if key is None:
                key=uid()
                returned=verified and any(iou(old['bbox'],box)>.3 for old in self.retired)
            tr=self.tracks.setdefault(key,dict(bbox=box,region=region,class_id=cid,since=t,last_seen=t,
                last_reliable=t,stable=False,counted=False,reviewed=False,pending_confirmed=False,
                observations=0,history=deque(),velocity=(0.,0.),returned=returned,production_counted=False))
            dt=t-tr['last_seen']
            if dt>0:
                old=tr['bbox'];tr['velocity']=tuple(.5*tr['velocity'][k]+.5*((box[k]+box[k+2]-old[k]-old[k+2])/2)/dt for k in (0,1))
            conflict=bool(det.get('conflict') or ambiguous)
            tr.update(bbox=box,last_seen=t,confidence=det['confidence'],raw_class_id=cid,raw_region=region,conflict=conflict)
            vote=None if conflict else (region,cid)
            self._vote(tr,t,vote,material)
            if conflict:
                # A handled object can have transient class ambiguity outside
                # either counting zone. Queue business-impacting conflicts,
                # while unresolved identity still invalidates its origin proof.
                needs_review=not verified or region=='completed' or tr.get('counted',False)
                if needs_review and not tr.get('conflict_reviewed'):
                    self._review(key,tr,'label_conflict' if det.get('conflict') else 'identity_ambiguous')
                    tr['conflict_reviewed']=True
                if ambiguous:
                    if needs_review:tr['reviewed']=True
                    else:tr['pending_confirmed']=False
            elif tr['stable'] and (tr['region'],tr['class_id'])==vote:
                tr['last_reliable']=t
            if conflict and t-tr['last_reliable']>material['missing_seconds']:
                tr['stable']=False;self._close_alert(tr,'unconfirmed')
            role=self._role(tr,material)
            if not conflict and tr['stable'] and tr['region']=='pending' and role=='count': tr['pending_confirmed']=True
            if tr['stable'] and role=='alert':
                if tr.get('alert') and (tr['alert']['class_id']!=tr['class_id'] or tr['alert']['region']!=tr['region']): self._close_alert(tr,'label_changed')
                if not tr.get('alert'):
                    alert=dict(id=uid(),track_id=key,session_id=session_id,region=tr['region'],class_id=tr['class_id'],
                        active=True,timestamp=time.time(),**self.last_meta)
                    tr['alert']=self.store.put('material_alert',alert)
                    if session_id:self.store.event(session_id,'alert',alert['id'],0,alert_id=alert['id'],region=tr['region'],class_id=tr['class_id'],**self.last_meta)
                if tr['counted'] and not tr.get('abnormal_reviewed'):
                    self._review(key,tr,'counted_became_abnormal');tr['abnormal_reviewed']=True
            elif tr['stable']: self._close_alert(tr,'normal')
            seen.add(key)
        for key,tr in self.tracks.items():
            if key not in seen: self._vote(tr,t,None,material)
        if any((tr['counted'] or tr['reviewed']) and tr['last_seen']<t for tr in self.tracks.values()): self.departed=True
        self.last_time=t
        self.sample_times.append(t)
        self.by_class={r:{str(cid):sum(tr['stable'] and tr['region']==r and tr['class_id']==cid and self._role(tr,material)=='count' for tr in self.tracks.values()) for cid in material['rules'][r]['count']} for r in ('pending','completed')}
        self.counts={r:sum(values.values()) for r,values in self.by_class.items()}
        if not session_id: return
        if not self.initialized:
            if any(tr['region']=='completed' and not tr['stable'] for tr in self.tracks.values()): return
            if not self.tracks and t-meta.get('session_started',t)<material['stable_seconds']: return
            initial=[key for key,tr in self.tracks.items() if tr['region']=='completed' and tr['stable'] and self._role(tr,material)=='count']
            self._record('initial','initial',len(initial),tracks=initial)
            for key in initial:self.tracks[key]['counted']=True
            self.initialized=True
        for key,tr in self.tracks.items():
            if tr['stable'] and tr['region']=='completed' and self._role(tr,material)=='count' and not tr['counted'] and not tr['reviewed']:
                if verified and (tr.get('returned') or not tr['pending_confirmed']):
                    self._review(key,tr,'return' if tr.get('returned') else 'completion_unverified');tr['reviewed']=True
                elif self.departed and not tr['pending_confirmed']:
                    self._review(key,tr,'return');tr['reviewed']=True
                else:
                    self._record('completed',key,1,track_id=key,class_id=tr['class_id'],region='completed',bbox_xyxy=list(tr['bbox']))
                    tr['counted']=True;tr['production_counted']=True

    def snapshot(self, now, config, available=True, session_id=None):
        mat=config['materials']
        fresh=(available and mat['enabled'] and mat['configured'] and self.last_time is not None
            and now-self.last_time<=max(2.,3/mat['sample_hz']) and self.last_meta.get('config_revision')==config['revision'])
        events=self.store.events(session_id) if session_id else []
        verified=any(e.get('production_basis')=='completion_events_v1' for e in events)
        production=sum(e['delta'] if e['kind']=='completed' else e.get('production_delta',0) for e in events)
        resolved={e.get('event_id') for e in events if e['kind']=='resolution'}
        confirming=any(not tr['stable'] or tr.get('raw_class_id')!=tr['class_id'] or tr.get('raw_region')!=tr['region'] for tr in self.tracks.values())
        hz=(len(self.sample_times)-1)/(self.sample_times[-1]-self.sample_times[0]) if len(self.sample_times)>1 else 0.
        return dict(enabled=mat['enabled'],available=bool(fresh),initialized=self.initialized,
            observation_state=('confirming' if confirming else 'valid') if fresh else 'unavailable',
            actual_sample_hz=round(hz,2) if fresh else 0.,degradation_reason=None if fresh else 'observation_unavailable',
            pending=self.counts['pending'] if fresh else None,completed=self.counts['completed'] if fresh else None,
            by_class=deepcopy(self.by_class) if fresh else None,
            region_names=deepcopy(mat.get('names',{})),class_styles=deepcopy(mat.get('class_styles',{})),
            initial=sum(e['delta'] for e in events if e['kind']=='initial'),
            added=sum(e['delta'] for e in events if e['kind']=='completed'),
            cumulative=sum(e['delta'] for e in events),session_id=session_id,
            production_total=max(0,production) if verified else None,
            production_basis='completion_events_v1' if verified else 'legacy',
            age_ms=max(0,(now-self.last_time)*1000) if self.last_time is not None else None,
            alerts=[deepcopy(tr['alert']) for tr in self.tracks.values() if tr.get('alert')] if fresh else [],
            detections=[dict(bbox_xyxy=tr['bbox'],class_id=tr['class_id'],confidence=tr.get('confidence',0),region=tr['region'],role=self._role(tr,mat),stable=tr['stable']) for tr in self.tracks.values() if tr['last_seen']==self.last_time and not tr.get('conflict')] if fresh and 'rules' in mat else [],
            reviews=[e for e in events if e['kind']=='review' and e['id'] not in resolved],**{k:v for k,v in self.last_meta.items() if k not in ('class_styles','production_basis')})

    def adjust(self, session_id, request):
        reason = request.get('reason','').strip()
        delta = request.get('delta')
        if not reason or len(reason)>500 or type(delta) is not int:
            raise StudioError('adjustment')
        def apply(db):
            events=self.store.events(session_id,db)
            if not events:
                raise StudioError('notFound',404)
            if request.get('expected_total') != sum(e['delta'] for e in events):
                raise StudioError('conflict',409)
            event_id=request.get('event_id')
            production_delta=0
            if event_id:
                if not any(e['id']==event_id and e['kind']=='review' for e in events) or any(e.get('event_id')==event_id and e['kind']=='resolution' for e in events):
                    raise StudioError('conflict',409)
                review=next(e for e in events if e['id']==event_id)
                allowed=(-1,0) if review.get('review_reason')=='counted_became_abnormal' else (0,) if review.get('review_reason')=='label_conflict' or review.get('already_counted') else (0,1)
                if delta not in allowed: raise StudioError('adjustment')
                if review.get('production_basis')=='completion_events_v1':
                    production_delta=delta if delta>=0 or review.get('production_counted') else 0
            elif request.get('scope')=='production':production_delta=delta
            if sum(e['delta'] if e['kind']=='completed' else e.get('production_delta',0) for e in events)+production_delta<0:
                raise StudioError('adjustment')
            total=sum(e['delta'] for e in events)+delta
            if total<0: raise StudioError('adjustment')
            result=self.store.event(session_id,'resolution' if event_id else 'adjustment',request['token'],delta,db,
                reason=reason,event_id=event_id,before=total-delta,after=total,production_delta=production_delta)
            return dict(event=result,cumulative=total)
        result=self.store.operation('adjust:'+session_id,request.get('token'),apply)
        # A reviewed arrival becomes a counted identity too. A later abnormal
        # classification must be reviewable without counting the same item again.
        if session_id==self.session_id and request.get('event_id'):
            events=self.store.events(session_id)
            review=next((e for e in events if e['id']==request['event_id']),None)
            track=self.tracks.get(review.get('track_id')) if review else None
            if track:
                key=review['track_id'];reviews={e['id'] for e in events if e.get('track_id')==key and e['kind']=='review'}
                deltas=[e['delta'] for e in events if e['kind']=='completed' and e.get('track_id')==key]
                deltas.extend(e.get('production_delta',0) for e in events if e['kind']=='resolution' and e.get('event_id') in reviews)
                if any(d>0 for d in deltas):track['counted']=True
                track['production_counted']=sum(deltas)>0
        return result

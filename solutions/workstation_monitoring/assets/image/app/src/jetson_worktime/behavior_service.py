"""Shared inference, versioned settings and frame-matched media publication."""
from collections import deque
from copy import deepcopy
import json
import os
import threading
import time
import uuid

from .api import ObservationCache, make_observation
from .behavior import SessionEngine
from .ownership import spatially_continuous, valid_track_id
from .detection import detection_settings, filter_persons, TRACKING_CONFIDENCE
from .media import protect_frame
from .overlay import draw_overlay, encode_overlays
from .localization import reason as reason_text, reason_fields, LocalizedError
from .settings import SettingsStore, normalize
from .runtime_quality import RuntimeQuality, ObservationWriter
from .activity import ActivityEstimator
from .evidence import EvidenceWriter
from .inference import load_accelerated, material_input, material_results


class BehaviorService:
    def __init__(self, root, config=None, *, start_workers=True):
        self.root = root
        self.store = SettingsStore(root/'configs/behavior.yaml')
        self.config = self.store.snapshot()
        self.lock = threading.RLock()
        self.condition = threading.Condition()
        self.latest = None
        self.live_condition = threading.Condition()
        self.live_latest = None
        self.live_ref = {}
        self.live_observation = None
        self.stop = threading.Event()
        self.quality = RuntimeQuality()
        self.media_work = threading.Condition()
        self.media_latest = None
        self.run_id = uuid.uuid4().hex
        self.engine = SessionEngine(self.config, run_id=self.run_id)
        self.persons = []
        self.frame_ref = {}
        self.error = None
        self.camera_changed = False
        self.guard_reference = None
        self.guard_last = 0
        self.guard_reset = False
        self.last_mode = None
        self.connected = False
        self.source_session = None
        self.source_size = None
        self.observations = ObservationCache(8)
        self.media_condition = threading.Condition(self.lock)
        self.media = None
        self.transport = None
        from .studio import Studio
        from .materials import MaterialCounter
        from .training import GpuLease
        self.studio = Studio(self.root, self)
        self.material_counter = MaterialCounter(self.studio.store)
        self.activity = ActivityEstimator()
        self.evidence_writer = EvidenceWriter(self.studio.store,self.quality)
        self.inference_backend = {}
        self.gpu_lease = GpuLease(self.studio.store.data)
        self.operating_mode = 'business' if self.config['operation']['detection_enabled'] else 'preview'
        self.runtime_epoch = 0
        resets = self.studio.store.list('display_control')
        self.display_reset = resets[0] if resets else None
        self.full_frame = None
        self.material_error = None
        self.model_activation_error = None
        self.models_epoch = None
        self.media_sequence = 0
        self.publish_times = deque(maxlen=60)
        self.output = root/'outputs/behavior'/self.run_id
        self.output.mkdir(parents=True)
        self.event_file = (self.output/'events.jsonl').open('a', buffering=1)
        self.observation_file = (self.output/'observations.jsonl').open('a', buffering=1) if os.environ.get('WORKTIME_DIAGNOSTICS', '1') == '1' else open(os.devnull, 'w')
        self.writer = ObservationWriter(self.observation_file, self.quality)
        self.threads = []
        previous = root/'outputs/behavior/latest.json'
        if previous.exists():
            try:
                old = json.loads(previous.read_text())
                if old.get('active'):
                    self.log(dict(event='previous_process_interrupted', previous_status=old,
                                  effective_end=old.get('last_observation_monotonic_seconds')))
            except (OSError, ValueError):
                pass
        if start_workers:
            os.environ['YOLO_CONFIG_DIR']=str(self.studio.store.data/'ultralytics')
            for target in (self.worker, self.monitor, self.media_worker, self.live_worker):
                thread = threading.Thread(target=target, daemon=True)
                self.threads.append(thread)
                thread.start()

    def model_hashes(self, config=None):
        from .studio_store import StudioError
        values={}
        for role,ident in (config or self.config)['models'].items():
            try: values[role]=self.studio.store.get('model',ident)['sha256'] if ident else None
            except StudioError: values[role]=None
        return values

    def log(self, event):
        self.event_file.write(json.dumps({'run_id':self.run_id, 'model_weights':self.model_hashes(), 'models':self.config['models'], 'config_revision':self.config['revision'],
                                         'detection':detection_settings(self.config), **event}, ensure_ascii=False)+'\n')

    def flush(self):
        while self.engine.events:
            event = self.engine.events[0]
            if event['event'] in ('session_start','session_end'):
                session_id=event['session_id']
                self.material_counter.store.event(session_id,event['event'],event['event'],0,work_event=event,models=self.config['models'],model_weights=self.model_hashes())
                if event['event']=='session_end':
                    event['materials']={'cumulative':self.material_counter.store.total(session_id)}
                    if self.activity.session_id==session_id:
                        summary=self.activity.snapshot(time.monotonic(),False,session_id)
                        self.studio.store.put('activity_summary',dict(id=session_id,**summary))
                        event['activity']=summary
            self.log(event)
            self.engine.events.pop(0)

    def submit(self, frame, pts, received, meta):
        self.quality.mark("receive", received)
        with self.lock:
            self.connected = True
            self.source_session = meta['session_id']
            self.source_size = [frame.shape[1], frame.shape[0]]
            revision = self.config['revision']
            epoch = self.runtime_epoch
        with self.live_condition:
            self.live_latest = (frame, pts, received, meta, revision, epoch)
            self.live_condition.notify()
        with self.condition:
            self.latest = (frame, pts, received, meta, revision, epoch)
            self.condition.notify()

    def invalidate_media(self, keep_video=False):
        if self.transport and not keep_video:
            self.transport.invalidate()
        self.media = None
        self.full_frame = None
        self.live_ref = {}
        self.live_observation = None
        with self.live_condition:
            self.live_latest = None
        with self.media_work:
            self.media_latest = None
        self.observations = ObservationCache(8)
        self.persons = []
        self.activity.reset_context()
        self.publish_times.clear()
        self.media_condition.notify_all()

    def disconnected(self):
        with self.lock:
            self.connected = False
            self.source_session = None
            self.engine.interrupt(time.monotonic())
            self.flush()
            self.invalidate_media()
        with self.condition:
            self.latest = None

    def settings(self):
        with self.lock:
            return SettingsStore.public(self.config)

    def apply_settings(self, request, camera):
        with self.lock:
            from .materials import material_behavior_changed
            material_business='materials' in request and isinstance(request['materials'],dict) and material_behavior_changed(self.config['materials'],request['materials'])
            if (any(key in request for key in ('models','camera_source','regions','timing','detection','operation')) or material_business) and self.studio.active_job():
                from .studio_store import StudioError
                raise StudioError('busy',409)
            if 'models' in request or 'materials' in request:
                candidate=deepcopy(self.config)
                for key in ('models','materials'):
                    if key in request: candidate[key]=request[key]
                candidate=normalize(candidate)
                self.studio.validate_selection(candidate)
                if candidate['models']['material']!=self.config['models']['material'] and candidate['materials']['enabled'] and not candidate['materials'].get('binding'):
                    from .studio_store import StudioError
                    raise StudioError('classMissing')
            roi_request = 'regions' in request or 'image_size' in request
            if roi_request and self.camera_changed and self.config['materials']['configured'] and 'materials' not in request:
                request={**request,'materials':{**self.config['materials'],'enabled':False,'configured':False,'regions':{'pending':[],'completed':[]}}}
            if roi_request:
                reference = request.get('reference_frame', {})
                if not isinstance(reference, dict):
                    raise LocalizedError('error.reference')
                if (not self.connected or reference.get('stream_session_id') != self.source_session
                        or reference.get('image_size') != self.source_size
                        or reference.get('camera_changed', False) != self.camera_changed
                        or camera['status'] != 'online' or camera.get('age_ms') is None or camera['age_ms'] >= 5000
                        or reference.get('stream_session_id') != camera['stream_session_id']
                        or reference.get('image_size') != [camera['width'], camera['height']]
                        or request.get('image_size') != reference.get('image_size')):
                    from .settings import SettingsConflict
                    raise SettingsConflict('error.staleReference')
            if ('materials' in request and request['materials'].get('configured') and (request['materials'].get('regions')!=self.config['materials']['regions'] or not self.config['materials']['configured'])):
                ref=request.get('reference_frame') or {}
                if (ref.get('stream_session_id')!=self.source_session or ref.get('image_size')!=self.source_size
                    or self.source_size!=self.config['image_size'] or not self.connected or self.camera_changed):
                    from .studio_store import StudioError
                    raise StudioError('staleReference',409)
            config, changed, detection_changed = self.store.commit(request)
            if not changed:
                return self.settings()
            old_revision = self.config['revision']
            if detection_changed:
                self.runtime_epoch += 1
                self.latest = None
                self.frame_ref = {}
                now = time.monotonic()
                self.engine.tick(now)
                self.engine._advance(now)
                reason = 'detection_disabled' if not config['operation']['detection_enabled'] and self.config['operation']['detection_enabled'] else 'configuration_changed'
                self.engine._finish(now, reason)
                try:
                    self.flush()
                except OSError:
                    self.error = 'StorageError'
                pending_events = self.engine.events[:]
                completed = self.engine.completed
                display_start_index = self.engine.display_start_index
                self.engine = SessionEngine(config, run_id=self.run_id)
                self.engine.completed = completed
                self.engine.display_start_index = display_start_index
                self.engine.events = pending_events
                self.material_counter.reset()
                if roi_request:
                    self.camera_changed = False
                    self.guard_reset = True
            else:
                self.engine.cfg = deepcopy(config)
            if 'camera_source' in request:
                self.camera_changed = True
                self.guard_reset = True
                self.latest = None
                self.frame_ref = {}
                self.source_size = None
            if 'models' in request and request['models']!=self.config['models']:
                self.model_activation_error=None
            self.config = config
            if self.operating_mode != 'training':
                self.operating_mode = 'business' if config['operation']['detection_enabled'] else 'preview'
            self.invalidate_media()
            try:
                self.log(dict(event='configuration_changed', previous_revision=old_revision,
                              detection_changed=detection_changed, monotonic_seconds=time.monotonic()))
            except OSError:
                self.error = 'StorageError'
            return self.settings()

    def observation_snapshot(self):
        with self.lock:
            result = self.observations.snapshot(time.monotonic_ns(), self.connected, self.error,
                                                self.config['max_observation_age'])
            result.update(config_revision=self.config['revision'], privacy_applied=self.config['privacy']['enabled'],
                          detection_enabled=self.config['operation']['detection_enabled'], operating_mode=self.operating_mode,
                          max_observation_age_ms=self.config['max_observation_age']*1000)
            return result

    def observation_frame(self, key):
        with self.lock:
            return self.observations.frame(key)

    def snapshot(self):
        with self.lock:
            result = self.engine.snapshot(time.monotonic())
            result.update(run_id=self.run_id, frame_ref=self.frame_ref, algorithm_error=self.error,
                          roi_provisional=not self.config['roi_configured'], camera_changed=self.camera_changed,
                          regions=self.config['regions'], image_size=self.config['image_size'],
                          last_observation_monotonic_seconds=self.engine.last_obs,
                          server_monotonic_seconds=time.monotonic(), server_wall_time_ms=time.time()*1000,
                          config_revision=self.config['revision'], privacy_applied=self.config['privacy']['enabled'])
            progress = result['start_confirmation']
            blocker = ('camera.disconnected' if not self.connected else
                       'reason.algorithm' if self.error or self.writer.error else
                       'source.roiRequired' if not self.config['roi_configured'] else
                       'reason.size' if self.source_size and self.source_size != self.config['image_size'] else
                       'reason.moved' if self.camera_changed else None)
            if blocker:
                progress.update(state='BLOCKED', blocker_code=blocker, blocker_params=dict(type=self.error or self.writer.error) if blocker == 'reason.algorithm' else {}, elapsed_seconds=0.)
            if self.operating_mode=='training':
                reason=reason_text('studio.reason.training')
                result.update(reason=reason,**reason_fields(reason))
                progress.update(state='BLOCKED',blocker_code='studio.reason.training',blocker_params={},elapsed_seconds=0.)
            result['operating_mode'] = self.operating_mode
            result['detection_enabled'] = self.config['operation']['detection_enabled']
            result['display_reset'] = self.display_reset
            if self.operating_mode == 'preview':
                result.update(state='DETECTION_DISABLED', reason_code='operation.preview', reason_params={})
                progress.update(state='BLOCKED', blocker_code='operation.preview', blocker_params={}, elapsed_seconds=0.)
            result['materials'] = self.material_counter.snapshot(time.monotonic(),self.config,self.connected and not self.error and self.material_error in (None,'budget') and not self.camera_changed and self.operating_mode=='business',result['session_id'])
            result['material_error'] = self.material_error
            result['materials']['degradation_reason'] = self.material_error or result['materials']['degradation_reason']
            result['runtime_quality'] = self.quality.snapshot()
            result['inference_backend'] = self.inference_backend.copy()
            result['activity'] = self.activity.snapshot(time.monotonic(),not blocker and self.operating_mode=='business' and result['active'],result['session_id'])
            if result['session_id'] and self.activity.session_id!=result['session_id']:
                saved=next((s for s in self.studio.store.list('activity_summary') if s['id']==result['session_id']),None)
                if saved:result['activity']={**saved,'available':False,'state':'unknown'}
            result['evidence_error']=self.evidence_writer.error
            result['persistence'] = dict(queue_size=self.writer.queue.qsize(), capacity=self.writer.queue.maxsize,
                                         written=self.writer.written, error=self.writer.error)
            return result

    def action(self, action, payload=None):
        with self.lock:
            if action == 'reset_display':
                return self.reset_display(payload or {})
            if self.operating_mode != 'business' and action!='review':
                from .studio_store import StudioError
                raise StudioError('busy',409)
            if action == 'start' and self.config.get('camera_source') and not self.config['roi_configured']:
                raise LocalizedError('source.roiRequired')
            if action == 'confirm_return':
                with self.store.output_policy() as policy:
                    if policy['revision'] != self.config['revision']:
                        raise LocalizedError('ownership.staleConfirmation')
                    self._confirm_return(payload or {})
            elif action == 'confirm_camera':
                if self.camera_changed and self.config['materials']['configured']:
                    self.apply_settings({'expected_revision':self.config['revision'],'materials':{**self.config['materials'],'enabled':False,'configured':False,'regions':{'pending':[],'completed':[]}}},{})
                self.camera_changed = False
                self.guard_reset = True
                self.log(dict(event='camera_position_confirmed', monotonic_seconds=time.monotonic()))
            else:
                self.engine.manual(action, time.monotonic())
            self.flush()
            return self.snapshot()

    def reset_display(self, payload):
        """Commit the receipt and settlement before publishing any reset state."""
        from .studio_store import StudioError
        from .settings import SettingsConflict
        if self.studio.active_job(): raise StudioError('busy', 409)
        staged = deepcopy(self.engine)
        now = time.monotonic()
        staged.tick(now)
        staged._advance(now)
        staged._finish(now, 'manual_reset')
        marker = dict(id='latest', token=payload.get('token'), wall_time_ms=time.time()*1000,
                      run_id=self.run_id, session_id=self.engine.current['session_id'] if self.engine.current else None)
        def commit(db):
            if type(payload.get('expected_revision')) is not int or payload['expected_revision'] != self.config['revision']:
                raise SettingsConflict('error.SETTINGS_CONFLICT')
            for event in staged.events:
                if event['event'] in ('session_start', 'session_end'):
                    self.studio.store.event(event['session_id'],event['event'],event['event'],0,db=db,
                        work_event=event, models=self.config['models'], model_weights=self.model_hashes(),
                        materials={'cumulative':self.studio.store.total(event['session_id'],db)})
            return self.studio.store.put('display_control',marker,db=db)
        receipt = self.studio.store.operation('reset_display', payload.get('token'), commit)
        if self.display_reset and self.display_reset.get('token') == receipt['token']:
            return self.snapshot()
        # A replay of an older receipt must never reset a newer session.
        if self.display_reset and self.display_reset['revision'] >= receipt['revision']:
            return self.snapshot()
        self.display_reset = receipt
        self.runtime_epoch += 1
        replacement = SessionEngine(self.config, run_id=self.run_id)
        replacement.completed = staged.completed
        replacement.display_start_index = len(staged.completed)
        self.engine = replacement
        self.latest = None
        self.frame_ref = {}
        self.material_counter.reset()
        # A timer reset invalidates business observations, not the camera/privacy stream.
        self.invalidate_media(keep_video=True)
        try:
            for event in staged.events: self.log(event)
            self.log(dict(event='display_reset', **{k:v for k,v in receipt.items() if k!='id'}))
        except OSError:
            self.error = 'StorageError'
        return self.snapshot()

    def _confirm_return(self, payload):
        """Validate both the selected evidence and the latest candidate under lock."""
        now = time.monotonic()
        track_id = payload.get('track_id')
        current = self.engine.current
        pair = self.observations.frame(payload.get('observation_id', ''))
        if (not current or not pair or not valid_track_id(track_id)
                or not self.connected or self.error or self.camera_changed
                or payload.get('session_id') != current['session_id']
                or type(payload.get('config_revision')) is not int
                or payload['config_revision'] != self.config['revision']
                or payload.get('stream_session_id') != self.source_session
                or not self.engine.ownership or not self.engine.ownership.needs_confirmation):
            raise LocalizedError('ownership.staleConfirmation')
        observation = pair[0]
        observed_at = int(observation['frame']['receive_monotonic_ns']) / 1e9
        if (observation['config_revision'] != self.config['revision']
                or observation['frame']['stream_session_id'] != self.source_session
                or not observation['inference']['accepted'] or observation.get('camera_changed')
                or now-observed_at > self.config['max_observation_age']
                or self.engine.last_obs is None or now-self.engine.last_obs > self.config['max_observation_age']):
            raise LocalizedError('ownership.staleConfirmation')
        selected = [p for p in observation['persons'] if p.get('person_track_id') == track_id
                    and p.get('ownership_zone') == 'SEATED']
        latest = [p for p in self.persons if p.get('person_track_id') == track_id
                  and p.get('ownership_zone') == 'SEATED']
        if len(selected) != 1 or len(latest) != 1 or not spatially_continuous(selected[0], latest[0]):
            raise LocalizedError('ownership.staleConfirmation')
        self.engine.confirm_return(latest[0], observed_at, now, observation_id=observation['observation_id'])

    def monitor(self):
        while not self.stop.wait(1):
            try:
                with self.lock:
                    if self.writer.error:
                        self.error = self.writer.error
                        self.engine._unknown(reason_text('reason.storage'))
                    self.engine.tick(time.monotonic())
                    self.flush()
                    snapshot = self.snapshot()
                    if snapshot['state'] != self.last_mode:
                        self.log(dict(event='state_transition', state=snapshot['state'],
                                      monotonic_seconds=time.monotonic(), frame_ref=self.frame_ref))
                        self.last_mode = snapshot['state']
                self._save_snapshot(snapshot)
            except OSError:
                with self.lock:
                    self.error = 'StorageError'

    def _save_snapshot(self, snapshot):
        path = self.root/'outputs/behavior/latest.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
        temporary.replace(path)

    def guard(self, frame, protected):
        import cv2
        import numpy as np
        now = time.monotonic()
        if now-self.guard_last < 5:
            return
        self.guard_last = now
        gray = cv2.cvtColor(cv2.resize(frame, (640, 360)), cv2.COLOR_BGR2GRAY)[:, :256]
        orb = cv2.ORB_create(700)
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        points = np.float32([point.pt for point in keypoints]).reshape(-1, 2)
        reference_path = self.root/'outputs/behavior/position-reference.npz'
        if self.guard_reference is None or self.guard_reset:
            if reference_path.exists() and not self.guard_reset:
                try:
                    with np.load(reference_path, allow_pickle=False) as reference:
                        self.guard_reference = (reference['points'].copy(), reference['descriptors'].copy())
                except (ValueError, OSError, KeyError):
                    self.guard_reference = None
            if self.guard_reference is None or self.guard_reset:
                self.guard_reference = (points, descriptors)
                if descriptors is not None:
                    temporary = reference_path.with_suffix('.tmp')
                    with temporary.open('wb') as handle:
                        np.savez(handle, points=points, descriptors=descriptors)
                    temporary.replace(reference_path)
            self.guard_reset = False
            cv2.imwrite(str(self.output/'camera-reference.jpg'), protected)
            return
        old, old_descriptors = self.guard_reference
        if descriptors is None or old_descriptors is None or not len(old_descriptors):
            return
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(old_descriptors, descriptors, k=2)
        matches = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .7*pair[1].distance]
        if len(matches) < 20:
            return
        matrix, inliers = cv2.estimateAffinePartial2D(
            np.float32([old[m.queryIdx] for m in matches]),
            np.float32([points[m.trainIdx] for m in matches]), method=cv2.RANSAC, ransacReprojThreshold=3)
        if matrix is not None and inliers is not None and inliers.sum() >= 15:
            angle = abs(float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0]))))
            shift = float(np.hypot(matrix[0, 2], matrix[1, 2]))
            scale = float(np.hypot(matrix[0, 0], matrix[1, 0]))
            if shift > 18 or angle > 3 or not .94 < scale < 1.06:
                if not self.camera_changed:
                    self.log(dict(event='camera_position_changed', monotonic_seconds=now,
                        shift_pixels=shift, angle_degrees=angle, scale=scale, matches=len(matches), inliers=int(inliers.sum())))
                self.camera_changed = True

    def worker(self):
        os.environ['YOLO_AUTOINSTALL'] = 'False'
        while not self.stop.is_set():
            try:
                self._inference_loop()
            except Exception as exc:
                self.gpu_lease.release()
                with self.lock:
                    self.error = type(exc).__name__
                    self.engine.reason = reason_text('reason.algorithm', type=self.error)
                    self.invalidate_media()
                    try:
                        self.log(dict(event='algorithm_error', exception_type=self.error))
                    except OSError:
                        pass
                self.stop.wait(3)

    def _inference_loop(self):
        import torch
        torch.set_num_threads(2)
        import cv2
        from ultralytics import YOLO
        from .runtime import extract_persons
        model = None
        material_model = None
        loaded_models = None
        import gc
        try:
            self._run_models(torch, cv2, YOLO, extract_persons, gc)
        finally:
            self.gpu_lease.release()

    def _run_models(self, torch, cv2, YOLO, extract_persons, gc):
        model = material_model = None
        loaded_models = None
        stream = None
        tracked_detection = None
        weights={}
        loaded_operation = None
        while not self.stop.is_set():
            job=self.studio.active_job()
            if job:
                if self.operating_mode!='training':
                    with self.lock:
                        now=time.monotonic()
                        self.engine.tick(now)
                        self.engine._finish(now,'training_started')
                        self.engine._unknown(reason_text('studio.reason.training'))
                        self.flush()
                        self.material_counter.reset()
                        self.operating_mode='training'
                        self.invalidate_media()
                    model=material_model=None
                    gc.collect()
                    if torch.cuda.is_available(): torch.cuda.synchronize();torch.cuda.empty_cache()
                    self.gpu_lease.release()
                self.stop.wait(.25)
                continue
            if not self.gpu_lease.acquire():
                self.stop.wait(.25);continue
            desired_mode = 'business' if self.config['operation']['detection_enabled'] else 'preview'
            if self.operating_mode != desired_mode:
                with self.lock:
                    self.operating_mode=desired_mode
                    self.latest=None
                    self.engine.seat_since=None
                    self.invalidate_media()
                loaded_models=None
            with self.condition:
                self.condition.wait_for(lambda: self.latest is not None or self.stop.is_set(), timeout=1)
                if self.latest is None:
                    continue
                frame, pts, received, meta, revision, epoch = self.latest
                self.latest = None
            with self.lock:
                config = deepcopy(self.config)
            if revision != config['revision'] or epoch != self.runtime_epoch:
                continue
            # Every marked image uses its own detector result, with either privacy policy.
            if time.monotonic()-received/1e9 > config['max_observation_age']:
                continue
            if not config['operation']['detection_enabled'] and not config['privacy']['enabled']:
                self._preview_frame(frame, pts, received, meta, config, epoch)
                stream = None
                continue
            selected=config['models']
            if loaded_models!=selected or loaded_operation != config['operation']['detection_enabled']:
                model=material_model=None;gc.collect();torch.cuda.empty_cache()
                try:
                    model,person_backend=load_accelerated(YOLO,self.root,self.studio.model(selected['person'],'person'),frame)
                    if selected['material'] and config['operation']['detection_enabled']:
                        cropped,_=material_input(frame,config)
                        material_model,material_backend=load_accelerated(YOLO,self.root,self.studio.model(selected['material'],'material'),cropped,config['materials']['confidence'])
                    else:material_backend=None
                    # Warm up on this real frame before accepting a GPU model change.
                    # A CPU upload check cannot establish GPU memory compatibility.
                    torch.cuda.synchronize()
                    self.inference_backend={'person':person_backend,'material':material_backend}
                    loaded_models=deepcopy(selected)
                    loaded_operation=config['operation']['detection_enabled']
                    weights=self.model_hashes(config)
                except Exception:
                    model=material_model=None;gc.collect();torch.cuda.empty_cache()
                    fallback=loaded_models or {'person':'builtin-person','material':None}
                    if fallback!=selected:
                        with self.lock:
                            if revision!=self.config['revision']:
                                loaded_models=None
                                continue
                            request={'expected_revision':self.config['revision'],'models':deepcopy(fallback)}
                            # Disable product counting until the recovered class and zones are confirmed.
                            request['materials']={**self.config['materials'],'enabled':False}
                            recovered,_,_=self.store.commit(request)
                            self.config=recovered;self.engine.cfg=deepcopy(recovered)
                            self.material_counter.reset();self.invalidate_media()
                            self.log(dict(event='model_activation_failed',requested_models=selected,restored_models=fallback))
                            self.material_error='modelInvalid'
                            self.model_activation_error=dict(code='modelActivation',requested_models=selected,restored_models=fallback)
                        loaded_models=None
                        continue
                    raise
            detection = detection_settings(config)
            if meta['session_id'] != stream or (detection, epoch) != tracked_detection:
                if model.predictor is not None:
                    for tracker in getattr(model.predictor, 'trackers', []):
                        tracker.reset()
                stream = meta['session_id']
                tracked_detection = (detection, epoch)
            started = time.monotonic_ns()
            result = model.track(frame, persist=True, tracker='bytetrack.yaml', device='cuda:0', imgsz=640, conf=TRACKING_CONFIDENCE, verbose=False)[0]
            torch.cuda.synchronize()
            if hasattr(model.model,'parameters') and next(model.model.parameters()).device.type != 'cuda':
                raise RuntimeError('CUDA required')
            completed = time.monotonic_ns()
            self.quality.sample('inference_ms', (completed-started)/1e6)
            self.quality.sample('receive_to_result_ms', (completed-received)/1e6)
            self.quality.mark('result', completed)
            all_persons = extract_persons(result)
            privacy_started=time.monotonic_ns()
            protected = protect_frame(frame, all_persons, config)
            self.quality.sample('privacy_ms',(time.monotonic_ns()-privacy_started)/1e6)
            if not config['operation']['detection_enabled']:
                self._preview_frame(protected, pts, received, meta, config, epoch, started, completed)
                continue
            material_detections=None
            if config['materials']['enabled'] and material_model:
                # Detect products on every processed source frame, alongside people.
                # Counting still uses the temporal voting/missing-grace state machine;
                # the legacy sample_hz setting must not make live boxes blink at 2 Hz.
                # Person results must still be fresh before spending the next GPU slot on products.
                if (time.monotonic_ns()-received)/1e9 < config['max_observation_age']*.5:
                    try:
                        material_started=time.monotonic_ns()
                        cropped,offset=material_input(frame,config)
                        result_m=material_model.predict(cropped,device='cuda:0',imgsz=640,conf=config['materials']['confidence'],verbose=False)[0]
                        material_detections=material_results(result_m,offset)
                        from .materials import material_threshold
                        material_detections=[d for d in material_detections if d['confidence']>=material_threshold(config['materials'],d['class_id'])]
                        self.quality.sample('material_inference_ms',(time.monotonic_ns()-material_started)/1e6)
                        self.quality.mark('material_result')
                        self.material_error=None
                    except Exception as exc:
                        self.material_error=type(exc).__name__
                else:
                    self.material_error='budget'
            del result
            if 'result_m' in locals(): del result_m
            height, width = frame.shape[:2]
            filtered_persons = filter_persons(all_persons, config)
            with self.lock:
                if self.stop.is_set() or epoch != self.runtime_epoch or revision != self.config['revision'] or not self.connected or stream != self.source_session:
                    continue
                # Hold the settings lock until every file/output for this revision is ready.
                with self.store.output_policy() as policy:
                    if policy['revision'] != revision:
                        continue
                    self.guard(frame, protected)
                    blocked_reason = None
                    if self.writer.error:
                        blocked_reason = reason_text('reason.storage')
                    elif config.get('camera_source') and not config['roi_configured']:
                        blocked_reason = reason_text('source.roiRequired')
                    elif self.camera_changed:
                        blocked_reason = reason_text('reason.moved')
                    accepted = self.engine.observe_persons(received/1e9, filtered_persons, width, height,
                        stream, now=time.monotonic(), sequence=meta['receive_sequence'], blocked_reason=blocked_reason)
                    if not accepted:
                        continue
                    persons = self.engine.persons
                    label, reason = self.engine.raw, self.engine.reason
                    self.persons = persons
                    current=self.engine.current
                    self.activity.observe(received/1e9,frame,persons,material_detections,config,
                        current['session_id'] if current else None,(stream,revision,epoch),
                        valid=not blocked_reason and material_detections is not None and label!='UNKNOWN')
                    self.full_frame=(protected,dict(meta),received,revision)
                    if material_detections is not None and not self.camera_changed and config['image_size']==[width,height] and not self.writer.error:
                        current=self.engine.current
                        self.material_counter.observe(material_detections,received/1e9,config,current['session_id'] if current else None,
                            session_started=current['start'] if current else received/1e9,
                            class_names=deepcopy(material_model.names),model_id=config['models']['material'],model_sha256=self.studio.model(config['models']['material'])['sha256'],
                            stream_session_id=stream,frame_sequence=meta['receive_sequence'])
                    evidence,self.material_counter.pending_evidence=self.material_counter.pending_evidence,[]
                    self.evidence_writer.submit(evidence,protected,config)
                    self.quality.sample('pipeline_result_ms',(time.monotonic_ns()-received)/1e6)
                    self.frame_ref = dict(meta, pts_ns=pts, receive_monotonic_ns=received)
                    self.error = None
                    self.flush()
                    # Deliver fresh protected video before JPEG variants and disk I/O.
                    material_status=self.material_counter.snapshot(time.monotonic(),config,self.material_error in (None,'budget'),self.engine.current['session_id'] if self.engine.current else None)
                    # Short-lived material layers retain explicit source frame metadata.
                    if material_status.get('age_ms') is None or material_status['age_ms']>max(750,1500/config['materials']['sample_hz']):
                        material_status={**material_status,'detections':[],'alerts':[]}
                    if material_detections is None:
                        material_status={**material_status,'detections':[]}
                    overlay_config = {**config, '_material_status':material_status, 'model_weights':weights, 'regions_confirmed': not self.camera_changed and config['roi_configured'], 'materials_confirmed': not self.camera_changed and config['materials']['configured']}
                    self.live_observation=dict(frame=frame,received=received,completed=time.monotonic_ns(),meta=dict(meta),revision=revision,epoch=epoch,
                        persons=deepcopy(persons),materials=deepcopy(material_status))
                    if self.transport and config['privacy']['enabled']:
                        self.live_ref = self.frame_ref.copy()
                        self.transport.submit(protected, persons, overlay_config, accepted,
                                              config['image_size'] == [width, height], received, self.frame_ref.copy())
                    ownership = self.engine.snapshot(time.monotonic())['ownership']
                    self.writer.submit(dict(observation_id=f"{self.run_id}-{stream}-{meta['receive_sequence']}",
                        run_id=self.run_id, config_revision=revision, privacy_applied=config['privacy']['enabled'],
                        detection=detection, inference_started_monotonic_ns=started,
                        inference_complete_monotonic_ns=completed, **self.frame_ref,
                        width=width, height=height, behavior=label, reason=reason, accepted=accepted,
                        persons=deepcopy(persons), models=config['models'], model_weights=weights, materials=self.material_counter.snapshot(time.monotonic(),config,self.material_error in (None,'budget'),self.engine.current['session_id'] if self.engine.current else None),
                        activity=self.activity.snapshot(time.monotonic(),not blocked_reason,current['session_id'] if current else None), ownership=ownership, camera_changed=self.camera_changed,
                        roi_configured=config['roi_configured'], **reason_fields(reason)))
                    packet = dict(epoch=epoch, protected=protected, persons=deepcopy(persons), config=overlay_config,
                        accepted=accepted, pts=pts, received=received, started=started, completed=completed,
                        width=width, height=height, meta=meta.copy(), label=label, reason=reason,
                        ownership=ownership, camera_changed=self.camera_changed)
                    with self.media_work:
                        if self.media_latest is not None:
                            self.quality.sample('media_replaced', 1)
                        self.media_latest = packet
                        self.media_work.notify()

    def _preview_frame(self, protected, pts, received, meta, config, epoch, started=None, completed=None):
        """Publish protected camera video without observing or advancing business state."""
        with self.lock:
            if (epoch != self.runtime_epoch or config['revision'] != self.config['revision']
                    or not self.connected or self.stop.is_set() or self.operating_mode == 'training'
                    or meta['session_id'] != self.source_session):
                return
            with self.store.output_policy() as policy:
                if policy['revision'] != config['revision']: return
                self.guard(protected, protected)
                self.error = None
                self.frame_ref = dict(meta, pts_ns=pts, receive_monotonic_ns=received)
                self.full_frame = (protected, dict(meta), received, config['revision'])
                if self.transport and config['privacy']['enabled']:
                    self.live_ref = self.frame_ref.copy()
                    self.transport.submit(protected, [], config, False, True, received, self.frame_ref.copy())
                packet = dict(epoch=epoch, protected=protected, persons=[], config=config, accepted=False,
                    pts=pts, received=received, started=started or received, completed=completed or time.monotonic_ns(),
                    width=protected.shape[1], height=protected.shape[0], meta=meta.copy(), label='UNKNOWN',
                    reason=reason_text('operation.preview'), ownership={}, camera_changed=self.camera_changed)
                with self.media_work:
                    self.media_latest = packet
                    self.media_work.notify()

    def live_worker(self):
        """Latest capture -> video, independent of business inference and JPEG work.

        Privacy-enabled output is deliberately gated by the same-frame protection
        path in the inference worker. Display-only flow is never a privacy mask.
        """
        from .live_overlay import LiveOverlay
        import cv2
        follower=LiveOverlay()
        while not self.stop.is_set():
            with self.live_condition:
                self.live_condition.wait_for(lambda:self.live_latest is not None or self.stop.is_set(),timeout=1)
                packet,self.live_latest=self.live_latest,None
            if packet is None or self.stop.is_set(): continue
            frame,pts,received,meta,revision,epoch=packet
            with self.lock:
                config=self.config
                if (revision!=config['revision'] or epoch!=self.runtime_epoch or not self.connected
                    or meta['session_id']!=self.source_session or self.operating_mode=='training'
                    or config['privacy']['enabled']):
                    follower.reset();continue
                enabled=config['operation']['detection_enabled']
                observation=self.live_observation if enabled and not self.error and not self.camera_changed else None
                material_error=self.material_error
                moved=self.camera_changed
            try:
                follow_started=time.monotonic_ns()
                persons,materials,evidence=follower.render(frame,received,meta,revision,epoch,observation)
                self.quality.sample('live_overlay_ms',(time.monotonic_ns()-follow_started)/1e6)
                if material_error: materials={**materials,'detections':[],'alerts':[]}
                overlay={**config,'_material_status':materials,'_overlay_evidence':evidence,
                    'regions_confirmed':not moved and config['roi_configured'],
                    'materials_confirmed':not moved and config['materials']['configured']}
                started=time.monotonic_ns()
                with self.lock:
                    if (self.stop.is_set() or revision!=self.config['revision'] or epoch!=self.runtime_epoch
                        or not self.connected or meta['session_id']!=self.source_session
                        or self.operating_mode=='training' or self.config['privacy']['enabled']): continue
                    self.live_ref=dict(meta,pts_ns=pts,receive_monotonic_ns=received)
                    if self.transport:
                        self.transport.submit(frame,persons,overlay,bool(evidence),config['image_size']==[frame.shape[1],frame.shape[0]],received,self.live_ref.copy())
                self.quality.sample('live_submit_ms',(time.monotonic_ns()-started)/1e6)
                self.quality.mark('live_frame')
            except (ValueError,RuntimeError,cv2.error):
                follower.reset();self.quality.sample('live_overlay_errors',1)

    def media_worker(self):
        """Latest-only JPEG work; settings are checked again before publication."""
        import cv2
        last_published=0.
        while not self.stop.is_set():
            with self.media_work:
                self.media_work.wait_for(lambda: self.media_latest is not None or self.stop.is_set(), timeout=1)
                packet, self.media_latest = self.media_latest, None
            if packet is None or self.stop.is_set():
                continue
            delay=.2-(time.monotonic()-last_published)
            if delay>0:
                self.stop.wait(delay)
                with self.media_work:
                    if self.media_latest is not None:
                        packet,self.media_latest=self.media_latest,None
            try:
                self._publish_media(packet)
                last_published=time.monotonic()
            except (OSError, RuntimeError, ValueError):
                self.quality.sample('media_errors', 1)

    def _publish_media(self, p):
        import cv2
        config, protected, persons = p['config'], p['protected'], p['persons']
        started = time.monotonic_ns()
        preview = cv2.resize(protected, (1280, round(p['height']*1280/p['width'])), interpolation=cv2.INTER_AREA) if p['width'] > 1280 else protected
        ok, jpeg = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 78])
        if not ok:
            raise RuntimeError('Preview encoding failed')
        annotated = encode_overlays(preview, persons, config, fresh=p['accepted'],
                                    regions_match=config['image_size'] == [p['width'], p['height']])
        self.quality.sample('jpeg_encode_ms', (time.monotonic_ns()-started)/1e6)
        observation = make_observation(self.run_id, p['meta'], p['pts'], p['received'], p['started'], p['completed'],
            p['width'], p['height'], preview.shape[1], preview.shape[0], persons, p['label'], p['reason'],
            p['accepted'], config, p['camera_changed'])
        observation['ownership'] = p['ownership']
        with self.lock:
            if (self.stop.is_set() or p.get('epoch', self.runtime_epoch) != self.runtime_epoch or not self.connected or config['revision'] != self.config['revision']
                    or p['meta']['session_id'] != self.source_session
                    or time.monotonic()-p['received']/1e9 > config['max_observation_age']):
                return
            with self.store.output_policy() as policy:
                if policy['revision'] != config['revision']:
                    return
                self.observations.publish(observation, jpeg.tobytes())
                self.media_sequence += 1
                self.media = dict(jpeg=jpeg.tobytes(), annotated=annotated['zh-CN'], annotated_locales=annotated,
                    received=p['received'], meta=p['meta'], revision=config['revision'],
                    privacy_applied=config['privacy']['enabled'], sequence=self.media_sequence)
                self.publish_times.append(time.monotonic())
                self.quality.mark('jpeg_publish')
                self.media_condition.notify_all()
        # A separate JPEG worker may save evidence without delaying GPU inference.
        region_path = self.output/f"regions-v{config['revision']}.jpg"
        if p['accepted'] and not region_path.exists():
            region_image = protected.copy()
            draw_overlay(region_image, [], config, fresh=False)
            with self.lock, self.store.output_policy() as policy:
                if policy['revision'] == config['revision'] and self.config['revision'] == config['revision']:
                    cv2.imwrite(str(region_path), region_image)

    def close(self):
        with self.lock:
            if self.stop.is_set():
                return
            self.stop.set()
            self.engine.interrupt(time.monotonic(), 'process_stopped')
            try:
                self.flush()
            except OSError:
                pass
            self.media_condition.notify_all()
        with self.condition:
            self.condition.notify_all()
        with self.media_work:
            self.media_work.notify_all()
        with self.live_condition:
            self.live_condition.notify_all()
        if self.transport:
            self.transport.close()
        for thread in self.threads:
            thread.join(timeout=5)
        try:
            self._save_snapshot(self.snapshot())
        except OSError:
            pass
        self.gpu_lease.release()
        self.event_file.close()
        self.writer.close()
        self.evidence_writer.close()

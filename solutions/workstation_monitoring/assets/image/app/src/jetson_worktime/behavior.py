"""Deterministic work sessions, using monotonic seconds and explicit ownership."""
import math
import uuid
from copy import deepcopy

from .detection import DETECTION_DEFAULTS, detection_settings
from .localization import reason as reason_text, reason_fields, LocalizedError

DEFAULTS = dict(start_seconds=10, short_away_seconds=60, stop_absent_seconds=300,
                missing_grace_seconds=3, max_observation_age=1.5,
                dedup_iou=.4, dedup_distance=.03, **DETECTION_DEFAULTS)


class SessionEngine:
    def __init__(self, config=None, *, run_id=None):
        self.cfg = {**DEFAULTS, **(config or {})}
        self.run_id = run_id
        self.current = None
        self.completed = []
        self.display_start_index = 0
        self.events = []
        self.cursor = None
        self.last_obs = None
        self.stream = None
        self.raw = 'UNKNOWN'
        self.seat_since = None
        self.away_since = None
        self.absent_since = None
        self.missing_since = None
        self.missing_previous = None
        self.away_elapsed = 0.
        self.absent_elapsed = 0.
        self.missing_evidence = False
        self.reason = reason_text('reason.waiting')
        self.manual_hold = False
        self.ownership = None
        self.persons = []
        self.last_sequence = None
        self.start_reset = None
        self.interrupted_stream = None

    def event(self, kind, t, **data):
        self.events.append(dict(event=kind, monotonic_seconds=t,
            config_revision=self.cfg.get('revision', 0),
            detection=detection_settings(self.cfg), **data))

    def _segment(self, a, b, kind):
        if not self.current or b <= a:
            return
        evidence = 'missing' if self.missing_evidence else 'observed'
        segments = self.current['segments']
        if (segments and segments[-1]['kind'] == kind
                and segments[-1].get('evidence') == evidence
                and abs(segments[-1]['end'] - a) < 1e-6):
            segments[-1]['end'] = b
        else:
            segments.append(dict(start=a, end=b, kind=kind, evidence=evidence))

    def _advance(self, t):
        if self.cursor is None:
            self.cursor = t
            return
        if t <= self.cursor:
            return
        deadline = None if self.last_obs is None else self.last_obs + self.cfg['max_observation_age']
        if deadline is not None and t > deadline and (self.raw != 'UNKNOWN' or self.missing_evidence):
            self._advance(max(self.cursor, deadline))
            self._unknown(reason_text('reason.stale', seconds=self.cfg['max_observation_age']))
        delta = t - self.cursor
        if self.current:
            reliable_away = self.raw in ('NEARBY', 'ABSENT') or self.missing_evidence
            if self.away_since is not None and reliable_away:
                self.away_elapsed += delta
            if self.absent_since is not None and self.missing_evidence:
                self.absent_elapsed += delta
            kind = 'unknown'
            if self.raw == 'SEATED':
                kind = 'work'
            elif self.raw in ('NEARBY', 'ABSENT'):
                kind = 'rest' if self.away_elapsed > self.cfg['short_away_seconds'] else 'pending'
            self._segment(self.cursor, t, kind)
            if self.away_elapsed > self.cfg['short_away_seconds']:
                self._relabel(self.away_since, ('pending',), 'rest')
        self.cursor = t
        self._check_absence()

    def _relabel(self, start, kinds, to, *, end=None, evidence=None):
        if not self.current or start is None:
            return
        stop = float('inf') if end is None else end
        segments = []
        for segment in self.current['segments']:
            left, right = max(start, segment['start']), min(stop, segment['end'])
            eligible = segment['kind'] in kinds and (evidence is None or segment.get('evidence') == evidence)
            if not eligible or left >= right:
                segments.append(segment)
                continue
            if segment['start'] < left:
                segments.append({**segment, 'end': left})
            segments.append({**segment, 'start': left, 'end': right, 'kind': to})
            if right < segment['end']:
                segments.append({**segment, 'start': right})
        self.current['segments'] = segments

    def _clear_away(self):
        self.away_since = None
        self.absent_since = None
        self.away_elapsed = 0.
        self.absent_elapsed = 0.
        self.missing_since = None
        self.missing_evidence = False

    def _unknown(self, reason):
        # Unknown input suspends existing deadlines. It never restarts them.
        self.raw = 'UNKNOWN'
        self.seat_since = None
        self.missing_since = None
        self.missing_evidence = False
        self.reason = reason

    def _start(self, t, manual=False):
        self.current = dict(session_id=uuid.uuid4().hex, start=t, end=None,
            segments=[], manual=manual, review=False,
            config_revision=self.cfg.get('revision', 0), detection=detection_settings(self.cfg))
        if self.ownership:
            self.ownership.bind(t, self.stream, self.run_id)
            self.current['ownership'] = self.ownership.identity()
            self.event('operator_bound', t, session_id=self.current['session_id'],
                       ownership=self.ownership.identity())
        self.event('session_start', t, session_id=self.current['session_id'], manual=manual,
                   ownership=self.current.get('ownership'))

    def _finish(self, t, reason):
        if not self.current:
            return
        session = self.current
        session['end'] = max(session['start'], t)
        session['end_reason'] = reason
        session['segments'] = [{**s, 'end': min(s['end'], session['end'])}
                               for s in session['segments'] if s['start'] < session['end']]
        self.completed.append(session)
        self.event('session_end', session['end'], session_id=session['session_id'], reason=reason,
                   summary=self.totals(session), intervals=session['segments'],
                   ownership=session.get('ownership'))
        self.current = None
        self.seat_since = None
        self._clear_away()
        if self.ownership:
            self.ownership.reset()

    def _change_stream(self, stream):
        if self.stream is not None and stream != self.stream:
            self.interrupt(self.last_obs if self.last_obs is not None else self.cursor or 0)
            self.cursor = None
            self.last_obs = None
            self.last_sequence = None
            self.interrupted_stream = None
        self.stream = stream

    def observe(self, t, label, stream='default', now=None, reason=''):
        """Label-only compatibility entry. Live/video callers use observe_persons."""
        now = t if now is None else now
        if now - t > self.cfg['max_observation_age']:
            self.tick(now)
            return False
        if self.interrupted_stream == stream:
            return False
        self._change_stream(stream)
        if self.last_obs is not None and t <= self.last_obs:
            return False
        self._advance(t)
        self.last_obs = t
        self.reason = reason
        is_missing = label in ('MISSING', 'ABSENT')
        self.missing_evidence = is_missing
        if is_missing:
            if self.missing_since is None:
                self.missing_since = t
                self.missing_previous = self.raw
            if self.current and self.away_since is None:
                self.away_since = t
            if self.current and self.absent_since is None:
                self.absent_since = t
            if label == 'MISSING' and t - self.missing_since < self.cfg['missing_grace_seconds']:
                label = 'UNKNOWN'
            else:
                label = 'ABSENT'
                self._relabel(self.absent_since, ('unknown',), 'pending', evidence='missing')
        elif label == 'SEATED':
            if self.current:
                if self.away_since is not None and self.away_elapsed <= self.cfg['short_away_seconds']:
                    self._relabel(self.away_since, ('pending',), 'work')
                if (self.missing_since is not None and self.missing_previous == 'SEATED'
                        and t - self.missing_since <= self.cfg['missing_grace_seconds']):
                    self._relabel(self.missing_since, ('unknown',), 'work', evidence='missing')
                self._clear_away()
            else:
                if not self.manual_hold:
                    if self.seat_since is None:
                        self.seat_since = t
                    if t - self.seat_since >= self.cfg['start_seconds']:
                        self._start(self.seat_since)
                        self._segment(self.seat_since, t, 'work')
                self.missing_since = None
        elif label == 'NEARBY':
            self.seat_since = None
            self.manual_hold = False
            if self.current and self.away_since is None:
                self.away_since = t
            # A reliably observed owner near the station is no longer absent.
            self.absent_since = None
            self.absent_elapsed = 0.
            self.missing_since = None
        else:
            self._unknown(reason)
        if label != 'SEATED':
            self.seat_since = None
        if is_missing:
            self.manual_hold = False
        self.raw = label
        self._check_absence()
        return True

    def _check_absence(self):
        if self.current and self.missing_evidence and self.absent_since is not None:
            if self.absent_elapsed >= self.cfg['stop_absent_seconds']:
                self._finish(self.absent_since, 'long_not_observed')

    def observe_persons(self, t, persons, width, height, stream='default', *, now=None,
                        sequence=None, blocked_reason=None):
        from .ownership import SessionOwnership
        now = t if now is None else now
        if (now - t > self.cfg['max_observation_age'] or self.interrupted_stream == stream
                or (self.stream == stream and self.last_obs is not None and t <= self.last_obs)
                or (self.stream == stream and sequence is not None and self.last_sequence is not None
                    and sequence <= self.last_sequence)
                or (self.ownership is not None and self.ownership.confirmation_time is not None
                    and self.stream == stream and t < self.ownership.confirmation_time)):
            self.tick(now)
            return False
        self._change_stream(stream)
        if self.ownership is None:
            self.ownership = SessionOwnership()
        self._advance(t)
        previous = self.ownership.state
        label, detail, people, reset_start = self.ownership.classify(
            persons, width, height, self.cfg, t, blocked_reason=blocked_reason)
        self.persons = people
        if reset_start:
            if self.seat_since is not None and not self.current:
                code = 'startup.trackChanged' if label == 'SEATED' else reason_fields(detail)['reason_code']
                self.start_reset = dict(reason_code=code, reason_params=reason_fields(detail)['reason_params'] if label != 'SEATED' else {}, monotonic_seconds=t)
                self.event('start_confirmation_reset', t, reason_code=code)
            self.seat_since = None
        if previous != self.ownership.state:
            self.event('operator_association_changed', t, previous=previous,
                       state=self.ownership.state, ownership=self.ownership.identity())
        if self.ownership.ignored_changed:
            self.event('other_person_ignored', t, track_ids=self.ownership.ignored,
                       session_id=self.current['session_id'] if self.current else None)
        accepted = self.observe(t, label, stream, now=now, reason=detail)
        if accepted:
            self.last_sequence = sequence
        return accepted

    def tick(self, now):
        if self.current and self.missing_evidence and self.last_obs is not None and self.cursor is not None:
            fresh_until = min(now, self.last_obs+self.cfg['max_observation_age'])
            if self.absent_elapsed+max(0, fresh_until-self.cursor) >= self.cfg['stop_absent_seconds']:
                self._advance(fresh_until)
        if self.last_obs is None or now - self.last_obs > self.cfg['max_observation_age']:
            self._advance(now)
            self._unknown(reason_text('reason.stale', seconds=self.cfg['max_observation_age']))

    def interrupt(self, now, reason='stream_interrupted'):
        self.interrupted_stream = self.stream
        if self.last_obs is not None:
            # A health tick may already have projected time beyond the last frame.
            self._advance(self.last_obs)
            self._finish(self.last_obs, reason)
        self._unknown(reason_text('reason.interrupted'))
        self._clear_away()
        if self.ownership:
            self.ownership.reset()

    def confirm_return(self, person, observed_at, now, *, observation_id):
        if not self.current or not self.ownership or not self.ownership.needs_confirmation:
            raise LocalizedError('ownership.staleConfirmation')
        self.tick(now)
        if not self.current:
            raise LocalizedError('ownership.staleConfirmation')
        self._advance(now)
        if not self.current:
            raise LocalizedError('ownership.staleConfirmation')
        effective_away = 0.
        for segment in self.current['segments']:
            if segment['kind'] in ('pending', 'rest') or segment.get('evidence') == 'missing':
                start = self.away_since if self.away_since is not None else observed_at
                effective_away += max(0, min(observed_at, segment['end']) - max(start, segment['start']))
        to = 'work' if effective_away <= self.cfg['short_away_seconds'] else 'rest'
        self._relabel(self.away_since, ('pending', 'rest'), to, end=observed_at)
        self._relabel(self.away_since, ('unknown',), to, end=observed_at, evidence='missing')
        self._relabel(observed_at, ('pending', 'rest'), 'work')
        self._relabel(observed_at, ('unknown',), 'work', evidence='missing')
        previous_track = self.ownership.track_id
        self.ownership.confirm(person, self.last_obs)
        self.ownership.confirmation_time = now
        self.current['ownership'] = self.ownership.identity()
        self.event('operator_return_confirmed', observed_at,
                   session_id=self.current['session_id'], observation_id=observation_id,
                   previous_track_id=previous_track, ownership=self.ownership.identity(),
                   confirmed_monotonic_seconds=now)
        self._clear_away()
        self.raw = 'SEATED'
        self.reason = reason_text('ownership.confirmed')

    def manual(self, action, now):
        self.tick(now)
        if action == 'start':
            if self.current or self.raw != 'SEATED':
                raise LocalizedError('error.start')
            self.manual_hold = False
            self._start(now, True)
        elif action == 'end':
            if not self.current:
                raise LocalizedError('error.end')
            self._advance(now)
            self._finish(now, 'manual')
            self._unknown(reason_text('reason.waiting'))
            self.manual_hold = True
        elif action == 'review':
            session = self.current or (self.completed[-1] if self.completed else None)
            if not session:
                raise LocalizedError('error.review')
            session['review'] = True
            self.event('review_marker', now, session_id=session['session_id'])
        else:
            raise LocalizedError('error.ACTION_UNAVAILABLE')

    @staticmethod
    def totals(session):
        result = dict(work_seconds=0., rest_seconds=0., unknown_seconds=0., pending_seconds=0.)
        if session:
            for segment in session['segments']:
                result[segment['kind'] + '_seconds'] += max(0, segment['end'] - segment['start'])
        return result

    def snapshot(self, now):
        self.tick(now)
        visible = self.completed[self.display_start_index:]
        session = self.current or (visible[-1] if visible else None)
        totals = self.totals(session)
        away_elapsed, absent_elapsed = self.away_elapsed, self.absent_elapsed
        # Display fresh time without committing a prediction ahead of the next
        # frame's receive timestamp. Poll frequency must not change settlement.
        if self.current and self.cursor is not None and now > self.cursor:
            delta = now-self.cursor
            if self.raw == 'SEATED':
                totals['work_seconds'] += delta
            elif self.raw in ('NEARBY', 'ABSENT') or self.missing_evidence:
                away_elapsed += delta
                if self.missing_evidence:
                    absent_elapsed += delta
                if self.raw == 'UNKNOWN':
                    totals['unknown_seconds'] += delta
                elif away_elapsed > self.cfg['short_away_seconds']:
                    totals['rest_seconds'] += totals['pending_seconds']+delta
                    totals['pending_seconds'] = 0.
                else:
                    totals['pending_seconds'] += delta
        mode = 'NOT_STARTED'
        if self.raw == 'UNKNOWN':
            mode = 'OBSERVATION_UNKNOWN'
        elif self.current:
            mode = 'WORKING' if self.raw == 'SEATED' else (
                'REST' if away_elapsed > self.cfg['short_away_seconds'] else 'AWAY_PENDING')
        elif self.seat_since is not None:
            mode = 'START_PENDING'
        ownership = self.ownership.snapshot() if self.ownership else dict(state='UNVERIFIED', operator_id=None,
            track_id=None, needs_confirmation=False, candidates=[], ignored_track_ids=[])
        ownership.update(away_since=self.away_since, absent_since=self.absent_since,
            away_seconds=away_elapsed, absent_seconds=absent_elapsed,
            end_remaining_seconds=max(0, self.cfg['stop_absent_seconds'] - absent_elapsed)
                if self.current and self.absent_since is not None else None)
        if not self.current and session and session.get('ownership'):
            ownership.update(session['ownership'])
            ownership['state'] = 'ENDED'
        return dict(state=mode, behavior=self.raw, reason=self.reason, **reason_fields(self.reason),
            session_id=session['session_id'] if session else None, active=bool(self.current),
            session_start=session['start'] if session else None, session_end=session.get('end') if session else None,
            review=session.get('review', False) if session else False, **totals,
            start_pending_seconds=max(0, now-self.seat_since) if self.seat_since is not None and not self.current else 0,
            completed_sessions=len(self.completed), thresholds={k: self.cfg[k] for k in DEFAULTS},
            ownership=deepcopy(ownership),
            start_confirmation=dict(state='ACTIVE' if self.current else 'BLOCKED' if self.raw == 'UNKNOWN' else 'CONFIRMING' if self.seat_since is not None else 'WAITING',
                elapsed_seconds=min(self.cfg['start_seconds'], max(0, now-self.seat_since)) if self.seat_since is not None else 0.,
                required_seconds=self.cfg['start_seconds'], candidate_track_id=self.ownership.track_id if self.ownership and not self.current else None,
                blocker_code=reason_fields(self.reason)['reason_code'] if self.raw == 'UNKNOWN' else None,
                blocker_params=reason_fields(self.reason)['reason_params'], last_reset=deepcopy(self.start_reset)))


def iou(a,b):
 area=lambda r:max(0,r[2]-r[0])*max(0,r[3]-r[1])
 inter=area([max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]);return inter/max(1,area(a)+area(b)-inter)
def deduplicate(persons,width,height,cfg):
 kept=[]
 for p in sorted(persons,key=lambda p:p.get('confidence',0),reverse=True):
  duplicate=False
  for q in kept:
   shared=[(a,b) for j,(a,b) in enumerate(zip(p['keypoints'],q['keypoints'])) if j in (0,5,6,7,8,9,10,11,12) and a.get('confidence',0)>=cfg['keypoint_confidence'] and b.get('confidence',0)>=cfg['keypoint_confidence'] and a.get('x') is not None and b.get('x') is not None]
   if iou(p['bbox_xyxy'],q['bbox_xyxy'])>=cfg['dedup_iou'] and len(shared)>=3 and sum(math.hypot(a['x']-b['x'],a['y']-b['y']) for a,b in shared)/len(shared)<math.hypot(width,height)*cfg['dedup_distance']:duplicate=True;break
  if not duplicate:kept.append(p)
 return kept

def point_in_polygon(point,polygon):
 x,y=point;inside=False
 for (a,b),(c,d) in zip(polygon,polygon[1:]+polygon[:1]):
  if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:inside=not inside
 return inside

def classify(persons,width,height,config):
 cfg={**DEFAULTS,**config};roi=cfg['regions']
 if cfg['image_size']!=[width,height]:return 'UNKNOWN',reason_text('reason.size'),[]
 persons=deduplicate(persons,width,height,cfg);candidates=[];uncertain=False
 for p in persons:
  k=p['keypoints'];valid=lambda j:len(k)>j and k[j].get('confidence',0)>=cfg['keypoint_confidence'] and k[j].get('x') is not None
  if valid(5) and valid(6):anchor=((k[5]['x']+k[6]['x'])/2,(k[5]['y']+k[6]['y'])/2)
  elif valid(0) and (valid(5) or valid(6)):
   j=5 if valid(5) else 6;anchor=((k[0]['x']+k[j]['x'])/2,(k[0]['y']+k[j]['y'])/2)
  else:
   if iou(p['bbox_xyxy'],[min(x[0] for x in roi['station']),min(x[1] for x in roi['station']),max(x[0] for x in roi['station']),max(x[1] for x in roi['station'])])>.05:uncertain=True
   continue
  p['upper_body_anchor']=list(anchor)
  if point_in_polygon(anchor,roi['station']):candidates.append(p)
 if uncertain or len(candidates)>1:return 'UNKNOWN',reason_text('reason.ambiguous'),persons
 if not candidates:return 'MISSING',reason_text('reason.missing'),persons
 return ('SEATED',reason_text('reason.seated'),persons) if point_in_polygon(candidates[0]['upper_body_anchor'],roi['seat']) else ('NEARBY',reason_text('reason.nearby'),persons)

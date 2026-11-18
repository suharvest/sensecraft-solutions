"""Conservative session-local association. Track IDs are never employee identities."""
from copy import deepcopy
import math
import uuid

from .localization import reason


def valid_track_id(value):
    return type(value) is int and value >= 0


def spatially_continuous(previous, current):
    from .behavior import iou
    old, new = previous['bbox_xyxy'], current['bbox_xyxy']
    old_area = max(0, old[2]-old[0]) * max(0, old[3]-old[1])
    new_area = max(0, new[2]-new[0]) * max(0, new[3]-new[1])
    if not old_area or not .5 <= new_area / old_area <= 2:
        return False
    a, b = previous.get('upper_body_anchor'), current.get('upper_body_anchor')
    close = a is not None and b is not None and math.dist(a, b) <= .5 * math.hypot(old[2]-old[0], old[3]-old[1])
    return iou(old, new) >= .2 or close


class SessionOwnership:
    def __init__(self):
        self.reset()

    def reset(self):
        self.operator_id = None
        self.run_id = None
        self.stream = None
        self.track_id = None
        self.last_person = None
        self.last_seen = None
        self.state = 'UNBOUND'
        self.needs_confirmation = False
        self.confirmation_time = None
        self.candidates = []
        self.ignored = []
        self.ignored_changed = False

    def identity(self):
        return dict(operator_id=self.operator_id, track_id=self.track_id,
                    run_id=self.run_id, stream_session_id=self.stream)

    def snapshot(self):
        return dict(**self.identity(), state=self.state,
                    needs_confirmation=self.needs_confirmation,
                    candidates=deepcopy(self.candidates), ignored_track_ids=self.ignored[:])

    def bind(self, started_at, stream, run_id):
        if self.last_person is None or not valid_track_id(self.track_id):
            raise ValueError('a tracked operator is required')
        self.operator_id = uuid.uuid4().hex
        self.run_id, self.stream = run_id, stream
        self.state = 'TRACKED'

    def confirm(self, person, observed_at):
        self.track_id = person['person_track_id']
        self.last_person = deepcopy(person)
        self.last_seen = observed_at
        self.needs_confirmation = False
        self.state = 'TRACKED'

    def classify(self, persons, width, height, config, t, *, blocked_reason=None):
        from .behavior import classify, iou, point_in_polygon
        people = deepcopy(persons)
        for person in people:
            person.pop('upper_body_anchor', None)
        label, detail, people = classify(people, width, height, config)
        old_ignored = self.ignored
        self.ignored = []
        self.ignored_changed = False
        self.candidates = []
        if blocked_reason or config['image_size'] != [width, height]:
            self.state = 'INPUT_UNKNOWN'
            if self.operator_id is None:
                self.track_id = None
                self.last_person = None
            return 'UNKNOWN', blocked_reason or detail, people, True

        for person in people:
            anchor = person.get('upper_body_anchor')
            zone = 'UNKNOWN'
            if anchor is not None:
                zone = 'OUTSIDE'
                if point_in_polygon(anchor, config['regions']['station']):
                    zone = 'SEATED' if point_in_polygon(anchor, config['regions']['seat']) else 'NEARBY'
            person['ownership_zone'] = zone
            person['is_session_operator'] = False
            track_id = person.get('person_track_id')
            if valid_track_id(track_id) and zone == 'SEATED':
                self.candidates.append(dict(track_id=track_id, bbox_xyxy=person['bbox_xyxy'][:], zone=zone))

        if self.operator_id is None:
            seated = [p for p in people if p['ownership_zone'] == 'SEATED']
            eligible = len(seated) == 1 and label == 'SEATED' and valid_track_id(seated[0].get('person_track_id'))
            if not eligible:
                self.track_id = None
                self.last_person = None
                self.state = 'UNBOUND'
                return ('UNKNOWN' if label == 'SEATED' else label), (reason('startup.noTrack') if label == 'SEATED' else detail), people, True
            person = seated[0]
            reset_start = (person['person_track_id'] != self.track_id
                           or self.last_person is None or not spatially_continuous(self.last_person, person))
            self.track_id = person['person_track_id']
            self.last_person = deepcopy(person)
            self.last_seen = t
            self.state = 'CANDIDATE'
            return 'SEATED', reason('ownership.starting', track_id=self.track_id), people, reset_start

        same = [p for p in people if p.get('person_track_id') == self.track_id]
        person = same[0] if len(same) == 1 else None
        recent = self.last_seen is not None and t-self.last_seen <= config['missing_grace_seconds']
        continuous = person is not None and self.last_person is not None and spatially_continuous(self.last_person, person)
        competing = person is not None and any(p is not person and iou(p['bbox_xyxy'], person['bbox_xyxy']) >= .2 for p in people)
        if not recent or (person is not None and (not continuous or competing)) or len(same) > 1:
            self.needs_confirmation = True
        if person is not None and person['ownership_zone'] == 'UNKNOWN' and continuous and not competing:
            result = 'UNKNOWN'
            self.state = 'INPUT_UNKNOWN'
            detail = reason('reason.ambiguous')
        elif (person is not None and person['ownership_zone'] != 'UNKNOWN' and recent
                and continuous and not competing and not self.needs_confirmation):
            self.last_person = deepcopy(person)
            self.last_seen = t
            person['is_session_operator'] = True
            self.state = 'TRACKED'
            result = person['ownership_zone']
            if result == 'OUTSIDE':
                result = 'MISSING'
            detail = reason('ownership.present' if result == 'SEATED' else
                            'ownership.nearby' if result == 'NEARBY' else 'ownership.absent')
        else:
            result = 'MISSING'
            self.state = 'CONFIRMATION_REQUIRED' if self.needs_confirmation or self.candidates else 'MISSING'
            # Once a different track enters during absence, only explicit human
            # confirmation may associate it with this session.
            if self.candidates:
                self.needs_confirmation = True
            detail = reason('ownership.confirmRequired' if self.needs_confirmation else 'ownership.absent')
        self.ignored = sorted({p['person_track_id'] for p in people
                               if valid_track_id(p.get('person_track_id')) and not p['is_session_operator']})
        self.ignored_changed = self.ignored != old_ignored and bool(self.ignored)
        return result, detail, people, False

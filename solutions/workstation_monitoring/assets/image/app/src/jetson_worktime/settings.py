"""Versioned device settings shared by HTTP, inference and media writers."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import math
import json
import os
from pathlib import Path
import tempfile
import threading

import yaml
from .behavior import DEFAULTS
from .visualization import DEFAULT_VISUALIZATION, visualization_settings, validate_visualization
from .detection import DETECTION_DEFAULTS, DETECTION_MINIMUMS, detection_settings
from .localization import LocalizedError

TIMING_KEYS = ('start_seconds', 'short_away_seconds', 'stop_absent_seconds',
               'missing_grace_seconds', 'max_observation_age')
DISPLAY_DEFAULTS = json.loads((Path(__file__).resolve().parents[2]/'frontend/public/overlay-style.json').read_text())['defaults']


class SettingsConflict(LocalizedError):
    pass


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _on_segment(p, a, b):
    return abs(_cross(a, b, p)) < 1e-7 and all(min(a[i], b[i])-1e-7 <= p[i] <= max(a[i], b[i])+1e-7 for i in (0, 1))


def _intersects(a, b, c, d):
    products = (_cross(a, b, c)*_cross(a, b, d), _cross(c, d, a)*_cross(c, d, b))
    if products[0] < 0 and products[1] < 0:
        return True
    return any((_on_segment(c, a, b), _on_segment(d, a, b),
                _on_segment(a, c, d), _on_segment(b, c, d)))


def _inside(p, polygon):
    from .behavior import point_in_polygon
    return any(_on_segment(p, a, b) for a, b in zip(polygon, polygon[1:]+polygon[:1])) or point_in_polygon(p, polygon)


def validate_polygon(polygon, size, name='region'):
    if not isinstance(size,list) or len(size)!=2 or any(type(v) is not int or v<2 for v in size):
        raise LocalizedError('error.imageSize')
    if not isinstance(polygon,list) or not 3<=len(polygon)<=32:
        raise LocalizedError('roi.vertexCount',region=name)
    if any(not isinstance(p,list) or len(p)!=2 or any(not _number(v) for v in p) for p in polygon):
        raise LocalizedError('error.vertexNumber',region=name)
    if any(not all(0<=p[i]<=size[i]-1 for i in (0,1)) for p in polygon):
        raise LocalizedError('roi.bounds',region=name)
    if len({tuple(p) for p in polygon})!=len(polygon):
        raise LocalizedError('roi.duplicate',region=name)
    edges=list(zip(polygon,polygon[1:]+polygon[:1]))
    if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in edges))/2<1:
        raise LocalizedError('roi.area',region=name)
    for i,(a,b) in enumerate(edges):
        for j in range(i+1,len(edges)):
            if j==i+1 or (i==0 and j==len(edges)-1): continue
            if _intersects(a,b,*edges[j]): raise LocalizedError('roi.crossing',region=name)


def polygons_intersect(a,b):
    return (any(_inside(p,b) for p in a) or any(_inside(p,a) for p in b)
            or any(_intersects(c,d,e,f) for c,d in zip(a,a[1:]+a[:1]) for e,f in zip(b,b[1:]+b[:1])))


def validate_regions(regions, size):
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or v < 2 for v in size):
        raise LocalizedError('error.imageSize')
    if not isinstance(regions, dict) or set(regions) != {'station', 'seat'}:
        raise LocalizedError('error.regions')
    for name, polygon in regions.items():
        if not isinstance(polygon, list) or not 3 <= len(polygon) <= 32:
            raise LocalizedError('roi.vertexCount', region=name)
        for p in polygon:
            if not isinstance(p, list) or len(p) != 2 or any(not _number(v) for v in p):
                raise LocalizedError('error.vertexNumber', region=name)
            if not all(0 <= p[i] <= size[i]-1 for i in (0, 1)):
                raise LocalizedError('roi.bounds', region=name)
        if len({tuple(p) for p in polygon}) != len(polygon):
            raise LocalizedError('roi.duplicate', region=name)
        area = abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(polygon, polygon[1:]+polygon[:1])))/2
        if area < 1:
            raise LocalizedError('roi.area', region=name)
        edges = list(zip(polygon, polygon[1:]+polygon[:1]))
        for i, (a, b) in enumerate(edges):
            for j in range(i+1, len(edges)):
                if j == i+1 or (i == 0 and j == len(edges)-1):
                    continue
                if _intersects(a, b, *edges[j]):
                    raise LocalizedError('roi.crossing', region=name)
    outer, inner = regions['station'], regions['seat']
    if any(not _inside(p, outer) for p in inner):
        raise LocalizedError('roi.containment')
    # A concave outer polygon can contain all vertices but exclude part of an edge.
    for a, b in zip(inner, inner[1:]+inner[:1]):
        fractions = [0., 1.]
        for c, d in zip(outer, outer[1:]+outer[:1]):
            denominator = (b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0])
            if abs(denominator) > 1e-9:
                t = ((c[0]-a[0])*(d[1]-c[1])-(c[1]-a[1])*(d[0]-c[0]))/denominator
                if 0 < t < 1 and _on_segment([a[k]+t*(b[k]-a[k]) for k in (0, 1)], c, d):
                    fractions.append(t)
        fractions.sort()
        for left, right in zip(fractions, fractions[1:]):
            t = (left+right)/2
            if not _inside([a[k]+t*(b[k]-a[k]) for k in (0, 1)], outer):
                raise LocalizedError('roi.edgeContainment')


def normalize(config):
    config = deepcopy(config)
    for key, value in DEFAULTS.items():
        config.setdefault(key, value)
    config.setdefault('privacy_keypoint_confidence', config['keypoint_confidence'])
    # Older extraction discarded coordinates below .25, so lower legacy thresholds
    # have the same business behavior as the extraction floor. Keep privacy's old value.
    if _number(config['keypoint_confidence']) and 0 <= config['keypoint_confidence'] < .25:
        config['keypoint_confidence'] = .25
    for key, minimum in DETECTION_MINIMUMS.items():
        if not _number(config[key]) or not minimum <= config[key] <= 1:
            raise LocalizedError('detection.invalid', field=key, minimum=minimum)
    if not _number(config['privacy_keypoint_confidence']) or not 0 <= config['privacy_keypoint_confidence'] <= 1:
        raise LocalizedError('detection.invalidPrivacy')
    from .materials import MATERIAL_DEFAULTS, MODEL_DEFAULTS, validate_materials
    config.setdefault('models', deepcopy(MODEL_DEFAULTS))
    config.setdefault('materials', deepcopy(MATERIAL_DEFAULTS))
    if not isinstance(config['models'],dict) or set(config['models']) != {'person','material'} or not isinstance(config['models']['person'],str) or not config['models']['person'] or (config['models']['material'] is not None and not isinstance(config['models']['material'],str)):
        raise ValueError('Invalid model selection')
    config['materials'] = validate_materials(config['materials'],config['image_size'])
    config.setdefault('revision', 0)
    config.setdefault('operation', {'detection_enabled': True})
    if (not isinstance(config['operation'], dict) or set(config['operation']) != {'detection_enabled'}
            or type(config['operation']['detection_enabled']) is not bool):
        raise LocalizedError('error.unknownField')
    config.setdefault('privacy', {'enabled': True})
    config.setdefault('display', DISPLAY_DEFAULTS.copy())
    config.setdefault('roi_configured', False)
    config['visualization'] = validate_visualization(visualization_settings(config))
    if 'camera_source' in config:
        from .camera_sources import normalize_source
        config['camera_source'] = normalize_source(config['camera_source'])
    validate_regions(config['regions'], config['image_size'])
    if type(config['revision']) is not int or config['revision'] < 0:
        raise LocalizedError('error.revision')
    if not isinstance(config['privacy'], dict) or set(config['privacy']) != {'enabled'} or type(config['privacy']['enabled']) is not bool:
        raise LocalizedError('error.privacy')
    display = config['display']
    legacy_keys = set(DISPLAY_DEFAULTS)
    if not isinstance(display,dict) or set(display) not in (legacy_keys,legacy_keys|{'station','seat'}) or any(type(v) is not bool for v in display.values()):
        raise LocalizedError('error.display')
    display.setdefault('station',display['regions'])
    display.setdefault('seat',display['regions'])
    display['regions'] = display['station'] or display['seat']
    for key in TIMING_KEYS:
        value = config[key]
        minimum = 0.1 if key in ('start_seconds', 'max_observation_age', 'stop_absent_seconds') else 0
        if not _number(value) or not minimum <= value <= 86400:
            raise LocalizedError('error.timingRange', field=key, minimum=minimum)
    if config['stop_absent_seconds'] <= max(config['short_away_seconds'], config['missing_grace_seconds']):
        raise LocalizedError('error.timingOrder')
    return config


class SettingsStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.lock_path = self.path.with_suffix('.lock')
        self.snapshot()  # Invalid persisted settings fail startup rather than disabling privacy.

    def snapshot(self):
        with self.lock:
            return normalize(yaml.safe_load(self.path.read_text()))

    @contextmanager
    def output_policy(self):
        """Serialize media writes against policy commits, including other processes."""
        with self.lock, self.lock_path.open('a') as guard:
            fcntl.flock(guard, fcntl.LOCK_SH)
            try:
                yield self.snapshot()
            finally:
                fcntl.flock(guard, fcntl.LOCK_UN)

    def commit(self, request):
        allowed = {'expected_revision', 'privacy', 'display', 'timing', 'regions', 'image_size', 'reference_frame', 'camera_source', 'detection', 'visualization', 'models', 'materials', 'operation'}
        if not isinstance(request, dict) or set(request)-allowed:
            raise LocalizedError('error.unknownField')
        if type(request.get('expected_revision')) is not int:
            raise LocalizedError('error.expectedRevision')
        with self.lock, self.lock_path.open('a') as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            try:
                old = self.snapshot()
                if request['expected_revision'] != old['revision']:
                    raise SettingsConflict('error.SETTINGS_CONFLICT')
                new = deepcopy(old)
                for key in ('privacy', 'display', 'regions', 'image_size', 'visualization', 'models', 'materials', 'operation'):
                    if key in request:
                        new[key] = deepcopy(request[key])
                if 'detection' in request:
                    detection = request['detection']
                    if not isinstance(detection, dict) or set(detection) != set(DETECTION_DEFAULTS):
                        raise LocalizedError('detection.allFields')
                    for key, minimum in DETECTION_MINIMUMS.items():
                        if not _number(detection[key]) or not minimum <= detection[key] <= 1:
                            raise LocalizedError('detection.invalid', field=key, minimum=minimum)
                    new.update(detection)
                if 'timing' in request:
                    timing = request['timing']
                    if not isinstance(timing, dict) or set(timing) != set(TIMING_KEYS):
                        raise LocalizedError('error.allTiming')
                    new.update(timing)
                source_changed = 'camera_source' in request and request['camera_source'] != old.get('camera_source')
                if source_changed:
                    from .camera_sources import normalize_source
                    new['camera_source'] = normalize_source(request['camera_source'])
                    new['roi_configured'] = False
                    new['materials']['enabled'] = False
                    new['materials']['configured'] = False
                    new['materials']['regions'] = {'pending':[], 'completed':[]}
                elif 'regions' in request:
                    new['roi_configured'] = True
                if new['image_size']!=old['image_size'] and 'materials' not in request:
                    new['materials'].update(enabled=False,configured=False,regions={'pending':[],'completed':[]})
                new = normalize(new)
                changed = old != new or 'regions' in request
                if changed:
                    new['revision'] += 1
                    temporary = None
                    try:
                        with tempfile.NamedTemporaryFile(mode='w', dir=self.path.parent, prefix='.behavior-', suffix='.tmp', delete=False) as handle:
                            temporary = handle.name
                            yaml.safe_dump(new, handle, allow_unicode=True, sort_keys=False)
                            handle.flush()
                            os.fsync(handle.fileno())
                        os.replace(temporary, self.path)
                    finally:
                        if temporary and os.path.exists(temporary):
                            os.unlink(temporary)
                detection_changed = source_changed or any(old[k] != new[k] for k in ('regions', 'image_size', *TIMING_KEYS, *DETECTION_DEFAULTS, 'models')) or ('regions' in request and changed)
                from .materials import material_behavior_changed
                detection_changed = detection_changed or material_behavior_changed(old['materials'],new['materials']) or old['operation'] != new['operation']
                return new, changed, detection_changed
            finally:
                fcntl.flock(guard, fcntl.LOCK_UN)

    @staticmethod
    def public(config):
        return dict(schema_version='1.0', revision=config['revision'],
                    operation=deepcopy(config['operation']),
                    privacy=deepcopy(config['privacy']), display=deepcopy(config['display']),
                    visualization=visualization_settings(config), visualization_defaults=deepcopy(DEFAULT_VISUALIZATION),
                    image_size=config['image_size'][:], regions=deepcopy(config['regions']),
                    roi_configured=config['roi_configured'], models=deepcopy(config['models']), materials=deepcopy(config['materials']),
                    detection=detection_settings(config), detection_defaults=DETECTION_DEFAULTS.copy(),
                    timing={k: config[k] for k in TIMING_KEYS},
                    defaults={k: DEFAULTS[k] for k in TIMING_KEYS})

"""Versioned wire format and bounded, atomic observation/image pairs. No GPU imports."""
from .visualization import visualization_settings
from collections import OrderedDict
from copy import deepcopy
from urllib.parse import urlencode
from .localization import reason_fields
from .settings import DISPLAY_DEFAULTS
from .detection import detection_settings

SCHEMA_VERSION = '1.0'

def wire(value):
    """Keep nanoseconds lossless for JavaScript without changing legacy records."""
    if isinstance(value, dict):
        return {k: (str(v) if isinstance(k, str) and k.endswith('_ns') and v is not None else wire(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [wire(v) for v in value]
    return value

def work_status(snapshot):
    return {'schema_version': SCHEMA_VERSION, **wire(snapshot)}

class ObservationCache:
    """Caller holds the service lock for publish, snapshot and frame access."""
    def __init__(self, capacity=8):
        if capacity < 1:
            raise ValueError('positive capacity required')
        self.capacity = capacity
        self.entries = OrderedDict()

    def publish(self, observation, jpeg):
        if not jpeg:
            raise ValueError('matching image required')
        key = observation['observation_id']
        if key in self.entries:
            raise ValueError('duplicate observation ID')
        self.entries[key] = (deepcopy(wire(observation)), bytes(jpeg))
        while len(self.entries) > self.capacity:
            self.entries.popitem(last=False)

    def snapshot(self, now_ns, connected=True, algorithm_error=None, max_age=1.5):
        observation = deepcopy(next(reversed(self.entries.values()))[0]) if self.entries else None
        age = max(0, (now_ns-int(observation['frame']['receive_monotonic_ns']))/1e6) if observation else None
        fresh = bool(observation and connected and not algorithm_error and observation['inference']['accepted'] and age <= max_age*1000)
        return dict(schema_version=SCHEMA_VERSION, available=observation is not None,
                    fresh=fresh, age_ms=age, algorithm_error=algorithm_error, observation=observation)

    def frame(self, key):
        return self.entries.get(key)

def make_observation(run_id, meta, pts, received, started, completed, width, height,
                     jpeg_width, jpeg_height, persons, label, reason, accepted, config, camera_changed):
    key = f"{run_id}-{meta['session_id']}-{meta['receive_sequence']}"
    return wire(dict(
        observation_id=key, run_id=run_id,
        frame=dict(stream_session_id=meta['session_id'], receive_sequence=meta['receive_sequence'],
                   pts_ns=pts, receive_monotonic_ns=received, source_width=width, source_height=height,
                   jpeg_width=jpeg_width, jpeg_height=jpeg_height, color_format='BGR'),
        inference=dict(started_monotonic_ns=started, completed_monotonic_ns=completed,
                       local_processing_ms=(completed-started)/1e6,
                       local_receive_to_result_ms=(completed-received)/1e6,
                       accepted=accepted, observation_valid=bool(accepted and label!='UNKNOWN'),
                       behavior=label, reason=reason, **reason_fields(reason)),
        persons=[{**p, 'upper_body_anchor': p.get('upper_body_anchor')} for p in persons],
        regions=config['regions'], roi_provisional=not config.get('roi_configured', False), camera_changed=camera_changed,
        config_revision=config.get('revision', 0), privacy_applied=config.get('privacy', {}).get('enabled', True),
        detection_enabled=config.get('operation', {}).get('detection_enabled', True),
        operating_mode='business' if config.get('operation', {}).get('detection_enabled', True) else 'preview',
        models=config.get('models'), model_weights=config.get('model_weights'), materials=config.get('materials'), material_observation=config.get('_material_status'), display=config.get('display', DISPLAY_DEFAULTS), visualization=visualization_settings(config), detection=detection_settings(config),
        matching_frame_url='/api/v1/observations/frame.jpg?'+urlencode({'observation_id': key})))

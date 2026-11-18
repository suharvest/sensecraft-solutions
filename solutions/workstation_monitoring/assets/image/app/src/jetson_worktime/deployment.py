"""Container readiness, resource checks and release maintenance state."""
import json
import os
from pathlib import Path
import shutil
import time


def container_mode():
    return os.environ.get('WORKTIME_CONTAINER') == '1'


def device_model():
    path = Path(os.environ.get('WORKTIME_DEVICE_MODEL_PATH', '/proc/device-tree/model'))
    try:
        return path.read_text().strip('\0\n')
    except OSError:
        return ''


def video_encoder():
    selected = os.environ.get('WORKTIME_ENCODER', 'auto')
    if selected not in ('auto', 'nvidia', 'x264'):
        raise ValueError('Invalid WORKTIME_ENCODER')
    if selected == 'auto':
        return 'x264' if 'orin nano' in device_model().lower().replace('-', ' ') else 'nvidia'
    return selected


def maintenance():
    path = os.environ.get('WORKTIME_RELEASE_STATE')
    if not path:
        return False
    try:
        return json.loads(Path(path).read_text()).get('phase') not in ('committed', 'rolled_back')
    except (OSError, ValueError):
        return True


def require_space(path, additional=0):
    minimum = int(os.environ.get('WORKTIME_MIN_FREE_BYTES', str(2 * 1024**3)))
    if shutil.disk_usage(path).free < minimum + additional:
        from .studio_store import StudioError
        raise StudioError('diskSpace', 507)


def readiness(root, behavior, transport):
    reasons = []
    try:
        with behavior.studio.store.connect() as connection:
            connection.execute('SELECT 1').fetchone()
    except Exception:
        reasons.append('database')
    heartbeat = Path(root) / 'data/agent-heartbeat'
    if not heartbeat.exists() or time.time() - heartbeat.stat().st_mtime > 30:
        reasons.append('trainer')
    if transport.process is None or transport.process.poll() is not None:
        reasons.append('media')
    marker = Path(root) / 'logs/gpu-startup.json'
    if container_mode():
        try:
            if json.loads(marker.read_text()).get('status') != 'PASS':
                reasons.append('gpu')
        except (OSError, ValueError):
            reasons.append('gpu')
    return {'ready': not reasons, 'reasons': reasons,
            'maintenance': maintenance(), 'mode': behavior.operating_mode}

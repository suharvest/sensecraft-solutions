"""Private camera configuration and bounded, frame-validated source switching."""
from copy import deepcopy
import fcntl
import os
from pathlib import Path
import secrets
import struct
import threading
import time
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from .localization import LocalizedError
from .settings import SettingsConflict

FORMATS = {'YUYV': 'yuyv', 'MJPG': 'mjpeg', 'H264': 'h264'}


def normalize_source(value, previous=None):
    if not isinstance(value, dict):
        raise LocalizedError('source.invalid')
    kind = value.get('type')
    if kind == 'usb':
        if set(value) - {'type', 'device', 'format'}:
            raise LocalizedError('source.invalid')
        device = value.get('device', '')
        if not isinstance(device, str) or not (device.startswith('/dev/video') or device.startswith('/dev/v4l/by-id/')) or '..' in device or '\x00' in device:
            raise LocalizedError('source.invalid')
        if value.get('format') not in FORMATS.values():
            raise LocalizedError('source.invalid')
        return dict(type='usb', device=device, format=value['format'])
    if kind != 'rtsp' or set(value) - {'type', 'url', 'username', 'password', 'codec'}:
        raise LocalizedError('source.invalid')
    try:
        raw = value.get('url', '')
        if not isinstance(raw, str) or len(raw) > 4096 or any(ord(c) < 33 for c in raw):
            raise ValueError()
        parsed = urlsplit(raw)
        if parsed.scheme not in ('rtsp', 'rtsps') or not parsed.hostname or parsed.fragment:
            raise ValueError()
        parsed.port  # Validate port syntax without echoing credentials.
        host = parsed.netloc.rsplit('@', 1)[-1]
        url = urlunsplit((parsed.scheme, host, parsed.path, parsed.query, ''))
        username = value.get('username') or unquote(parsed.username or '')
        password = value.get('password') or unquote(parsed.password or '')
        codec = value.get('codec', 'h264')
        if codec not in ('h264', 'h265') or any(not isinstance(v, str) or len(v) > 1024 or any(ord(c) < 32 for c in v) for v in (username, password)):
            raise ValueError()
    except (ValueError, TypeError):
        raise LocalizedError('source.invalid') from None
    if not password and previous and previous.get('type') == 'rtsp' and previous.get('url') == url and previous.get('username') == username:
        password = previous.get('password', '')
    return dict(type='rtsp', url=url, username=username, password=password, codec=codec)


def public_source(source):
    if source is None:
        return {'type': 'unconfigured', 'configured': False}
    result = deepcopy(source)
    if result.get('type') == 'rtsp':
        result['password_set'] = bool(result.pop('password', ''))
    return result


def source_uri(source):
    if source['type'] == 'usb':
        return str(usb_path(source['device']))
    parsed = urlsplit(source['url'])
    credentials = ''
    if source['username'] or source['password']:
        credentials = quote(source['username'], safe='') + ':' + quote(source['password'], safe='') + '@'
    return urlunsplit((parsed.scheme, credentials + parsed.netloc, parsed.path, parsed.query, ''))


def usb_path(device):
    root = Path(os.environ.get('WORKTIME_USB_DEVICE_ROOT', '/dev'))
    path = root / Path(device).relative_to('/dev')
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise LocalizedError('source.invalid')
    return resolved


def usb_devices():
    devices = []
    device_root = Path(os.environ.get('WORKTIME_USB_DEVICE_ROOT', '/dev'))
    stable = list((device_root/'v4l/by-id').glob('*'))
    for path in sorted(device_root.glob('video[0-9]*')):
        fd = None
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            cap = bytearray(104)
            fcntl.ioctl(fd, 0x80685600, cap, True)  # VIDIOC_QUERYCAP
            flags, device_flags = struct.unpack_from('II', cap, 84)
            if not ((device_flags if flags & 0x80000000 else flags) & 1):
                continue
            formats = []
            for index in range(64):
                entry = bytearray(64)
                struct.pack_into('II', entry, 0, index, 1)
                try:
                    fcntl.ioctl(fd, 0xc0405602, entry, True)  # VIDIOC_ENUM_FMT
                except OSError:
                    break
                code = bytes(entry[44:48]).decode('ascii', errors='replace')
                if code in FORMATS and FORMATS[code] not in formats:
                    formats.append(FORMATS[code])
            identifier = next((str(p) for p in stable if p.resolve() == path.resolve()), str(path))
            name = bytes(cap[16:48]).split(b'\0')[0].decode(errors='replace')
            if formats:
                devices.append(dict(device=str(Path('/dev') / Path(identifier).relative_to(device_root)), name=name, formats=formats))
        except OSError:
            continue
        finally:
            if fd is not None:
                os.close(fd)
    return dict(schema_version='1.0', devices=devices)


class CameraSources:
    """One live reader. Switching and frame submission share the same lock."""
    def __init__(self, behavior, fallback, reader_factory):
        self.behavior = behavior
        self.fallback = fallback
        self.factory = reader_factory
        self.lock = threading.RLock()
        self.test_lock = threading.Lock()
        self.reader = None
        self.tokens = {}
        self.last_error = None

    def current(self):
        return deepcopy(self.behavior.config.get('camera_source', self.fallback))

    def public(self):
        return public_source(self.current())

    def open(self, candidate):
        if candidate['type'] == 'usb':
            available = usb_devices()['devices']
            if not any(usb_path(item['device']) == usb_path(candidate['device'])
                       and candidate['format'] in item['formats'] for item in available):
                raise LocalizedError('source.usbUnavailable')
        try:
            return self.factory(source_uri(candidate), codec=candidate.get('codec', 'h264'),
                                rtsp=candidate['type'] == 'rtsp', usb_format=candidate.get('format'),
                                queue_limit=1, timeout=5)
        except Exception:
            raise LocalizedError('source.connectionFailed') from None

    def validated_reader(self, candidate):
        reader = self.open(candidate)
        try:
            packet = reader.read()
            if packet is None or packet[0].size == 0:
                raise ValueError()
            height, width = packet[0].shape[:2]
            return reader, dict(width=width, height=height)
        except Exception:
            reader.close()
            raise LocalizedError('source.connectionFailed') from None

    def test(self, request):
        if not self.test_lock.acquire(blocking=False):
            raise LocalizedError('source.busy')
        reader = None
        try:
            if set(request) != {'expected_revision', 'camera_source'}:
                raise LocalizedError('source.invalid')
            revision = request.get('expected_revision')
            with self.behavior.lock:
                if type(revision) is not int or revision != self.behavior.config['revision']:
                    raise SettingsConflict('error.SETTINGS_CONFLICT')
                candidate = normalize_source(request.get('camera_source'), self.current())
            reader, size = self.validated_reader(candidate)
            token = secrets.token_urlsafe(32)
            with self.lock:
                now = time.monotonic()
                self.tokens = {k: v for k, v in self.tokens.items() if v[2] > now}
                if len(self.tokens) >= 32:
                    self.tokens.pop(next(iter(self.tokens)))
                self.tokens[token] = (candidate, revision, now + 90)
            return dict(schema_version='1.0', test_token=token, expires_in_seconds=90, **size)
        finally:
            if reader:
                reader.close()
            self.test_lock.release()

    def switch(self, request, camera):
        if set(request) != {'expected_revision', 'camera_source', 'test_token'}:
            raise LocalizedError('source.separateSave')
        if type(request['expected_revision']) is not int:
            raise LocalizedError('error.expectedRevision')
        with self.lock:
            with self.behavior.lock:
                revision = self.behavior.config['revision']
                if request['expected_revision'] != revision:
                    raise SettingsConflict('error.SETTINGS_CONFLICT')
                candidate = normalize_source(request['camera_source'], self.current())
            tested = self.tokens.get(request['test_token'])
            if not tested or tested[0] != candidate or tested[1] != revision or tested[2] <= time.monotonic():
                raise LocalizedError('source.testExpired')
            if candidate == self.current() and 'camera_source' in self.behavior.config:
                return self.behavior.settings()
            new_reader, _ = self.validated_reader(candidate)
            try:
                result = self.behavior.apply_settings(dict(expected_revision=revision, camera_source=candidate), camera)
            except Exception:
                new_reader.close()
                raise
            old_reader = self.reader
            self.reader = new_reader
            with self.behavior.lock:
                self.behavior.connected = False
                self.behavior.source_session = None
            self.last_error = None
            self.tokens.clear()
            if old_reader:
                try:
                    old_reader.close()
                except Exception:
                    pass
            return result

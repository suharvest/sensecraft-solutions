"""Single camera, shared GPU worker, settings UI and versioned media API."""
import atexit
import json
import os
import re
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import yaml
import cv2
# Avoid several eight-thread image operations contending with GPU preprocessing.
cv2.setNumThreads(4)
from jetson_worktime.api import work_status
from jetson_worktime.behavior_service import BehaviorService
from jetson_worktime.localization import LANGUAGES, LocalizedError
from jetson_worktime.settings import SettingsConflict
from jetson_worktime.studio_store import StudioError
from jetson_worktime.system_metrics import SystemMetrics
from jetson_worktime.video import VideoReader
from jetson_worktime.streaming import VideoTransport, PROFILES, VIDEO_STREAMS
from jetson_worktime.camera_sources import CameraSources, normalize_source, usb_devices
from jetson_worktime.deployment import maintenance, readiness

os.chdir(ROOT)
behavior = BehaviorService(ROOT)
behavior.transport = VideoTransport(ROOT)
from jetson_worktime.studio_http import StudioHTTP
studio_http = StudioHTTP(behavior.studio)
system_metrics = SystemMetrics()
atexit.register(behavior.close)
if (ROOT/'.env').exists():
    for line in (ROOT/'.env').read_text().splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() == 'RTSP_URL':
            os.environ.setdefault('RTSP_URL', value.strip().strip('\"\''))
source = yaml.safe_load((ROOT/'configs/station.m1.yaml').read_text())['source']
url = os.environ.get(source.get('rtsp_env', 'RTSP_URL'))
try:
    fallback_source = behavior.config.get('camera_source') or normalize_source(
        dict(type='rtsp', url=url, codec=source['codec'])) if url or behavior.config.get('camera_source') else None
except ValueError:
    fallback_source = None
cameras = CameraSources(behavior, fallback_source, VideoReader)
state_lock = threading.Lock()
state = dict(status='connecting', timestamp=0, sequence=0, width=None, height=None,
             jpeg_width=None, jpeg_height=None, source_fps=None,
             stream_session_id=None, receive_sequence=None, pts_ns=None)


def capture():
    while not behavior.stop.is_set():
        started = time.monotonic()
        failed = False
        with cameras.lock:
            try:
                if cameras.current() is None:
                    behavior.stop.wait(1)
                    continue
                if cameras.reader is None:
                    cameras.reader = cameras.open(cameras.current())
                reader = cameras.reader
                packet = reader.read()
                if packet is None:
                    raise RuntimeError('stream ended')
                frame, pts, received = packet
                meta = reader.last_meta.copy()
                height, width = frame.shape[:2]
                fps = reader.stream_info
                with state_lock:
                    state.update(status='online', timestamp=time.monotonic(), sequence=state['sequence']+1,
                                 width=width, height=height, jpeg_width=min(1280, width),
                                 jpeg_height=round(height*min(1280, width)/width),
                                 source_fps=(fps.get('fps_numerator') or 0)/(fps.get('fps_denominator') or 1),
                                 stream_session_id=meta['session_id'], receive_sequence=meta['receive_sequence'],
                                 pts_ns=str(pts) if pts is not None else None)
                behavior.submit(frame, pts, received, meta)
                cameras.last_error = None
            except Exception as exc:
                failed = True
                behavior.disconnected()
                cameras.last_error = 'source.connectionFailed'
                with state_lock:
                    state.update(status='reconnecting')
                with behavior.lock:
                    try:
                        behavior.log(dict(event='stream_failure', exception_type=type(exc).__name__,
                                          monotonic_seconds=time.monotonic()))
                    except OSError:
                        pass
                if cameras.reader:
                    cameras.reader.close()
                    cameras.reader = None
        behavior.stop.wait(2 if failed else max(0, 1/20 - (time.monotonic()-started)))
    with cameras.lock:
        if cameras.reader:
            cameras.reader.close()
            cameras.reader = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_bytes(self, data, content_type, status=200, headers=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, str(value))
        self.end_headers()
        self.wfile.write(data)

    def json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), 'application/json; charset=utf-8', status)

    def error(self, status, code, message):
        self.json(dict(schema_version='1.0', error=dict(
            code=code, message=str(message),
            message_key=getattr(message, 'message_key', 'error.'+code),
            message_params=getattr(message, 'message_params', {}))), status)

    def camera(self):
        with state_lock:
            info = state.copy()
        timestamp = info.pop('timestamp')
        age = (time.monotonic()-timestamp)*1000 if timestamp else None
        info['age_ms'] = age
        if age is None or age >= 5000:
            info['status'] = 'connecting' if info['status'] == 'connecting' else 'reconnecting'
        with behavior.lock:
            times = behavior.publish_times
            output_fps = (len(times)-1)/(times[-1]-times[0]) if len(times) > 1 and time.monotonic()-times[-1] < 5 else 0
            live = behavior.live_ref.get('receive_monotonic_ns')
            live_age = max(0,(time.monotonic_ns()-live)/1e6) if live is not None else None
            observed = behavior.frame_ref.get('receive_monotonic_ns')
            age = max(0,(time.monotonic_ns()-observed)/1e6) if observed is not None else None
            info.update(algorithm_observation_age_ms=age, live_frame_age_ms=live_age,
                        jpeg_output_fps=round(output_fps,2),capture_fps=behavior.quality.rate("receive"),
                        detection_enabled=behavior.config['operation']['detection_enabled'],
                        preview_fresh=bool(behavior.connected and behavior.operating_mode!='training' and live_age is not None and live_age <= behavior.config['max_observation_age']*1000),
                        operating_mode=behavior.operating_mode,
                        algorithm_fresh=bool(behavior.operating_mode=='business' and behavior.connected and not behavior.error and age is not None
                                             and age <= behavior.config['max_observation_age']*1000))
            info.update(config_revision=behavior.config['revision'], privacy_applied=behavior.config['privacy']['enabled'],
                        output_fps=round(output_fps, 2), algorithm_error=behavior.error,
                        regions_match=behavior.config['image_size'] == [info['width'], info['height']],
                        camera_changed=behavior.camera_changed)
        if getattr(behavior, 'transport', None):
            info['video'] = behavior.transport.status()
        active_source = cameras.current() or {}
        if not active_source:
            info['status'] = 'unconfigured'
        return dict(configured=bool(active_source), schema_version='1.0', codec=active_source.get('codec', active_source.get('format')),
                    source_type=active_source.get('type', 'unconfigured'), device_name=active_source.get('device', 'RTSP') if active_source else None,
                    connection_error=cameras.last_error,
                    decoder='software' if active_source.get('format') in ('yuyv', 'mjpeg') else 'nvv4l2decoder',
                    preview_max_fps=20, preview_has_project_overlay=False, **info)

    @staticmethod
    def media_headers(media):
        return {'X-Stream-Session-ID': media['meta']['session_id'],
                'X-Frame-Sequence': media['meta']['receive_sequence'],
                'X-Config-Revision': media['revision'],
                'X-Privacy-Applied': str(media['privacy_applied']).lower()}

    def send_media(self, data, headers, content_type='image/jpeg'):
        transport = behavior.transport
        with transport.condition:
            if int(headers['X-Config-Revision']) != behavior.config['revision']:
                self.error(409, 'FRAME_EXPIRED', 'Media policy changed')
                return
            transport.output_sockets.add(self.connection)
        try:
            self.connection.settimeout(2)
            self.send_bytes(data,content_type,headers=headers)
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            self.close_connection = True
        finally:
            with transport.condition:
                transport.output_sockets.discard(self.connection)

    def stream(self, raw=False, locale='zh-CN'):
        transport = behavior.transport
        profile = parse_qs(urlsplit(self.path).query).get('profile',['remote'])
        if len(profile)!=1 or profile[0] not in ('local','remote'):
            self.error(400,'BAD_REQUEST','Invalid video profile')
            return
        profile=profile[0]
        key = ('raw' if raw else locale,profile)
        try:
            tokens=parse_qs(urlsplit(self.path).query,keep_blank_values=True).get('client_id',[])
            if len(tokens)>1 or tokens and not re.fullmatch('[a-f0-9]{32}',tokens[0]):
                self.error(400,'BAD_REQUEST','Invalid media session');return
            epoch = transport.add_socket(self.connection,profile,stream=key[0],token=tokens[0] if tokens else None)
        except ValueError as error:
            self.error(429, 'VIDEO_LIMIT', error)
            return
        previous = None
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Content-Language', locale)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Preview-Overlay', str(not raw).lower())
        self.end_headers()
        self.connection.settimeout(1)
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16384)
        try:
            while not behavior.stop.is_set():
                with transport.condition:
                    ready = transport.condition.wait_for(
                        lambda: transport.epoch != epoch or transport.stop.is_set() or
                        (transport.jpegs.get(key) is not None and transport.jpegs.get(key) is not previous), timeout=5)
                    if not ready or transport.epoch != epoch or transport.stop.is_set():
                        break
                    packet = transport.jpegs.get(key)
                    if packet is None:
                        break
                    if time.monotonic_ns()-packet[1] >= (packet[6] if len(packet)>6 else 1.5)*1e9:
                        previous = packet
                        continue
                    data = packet[2]
                # Network writes hold neither inference nor settings locks.
                header = '--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(data))+'\r\n'
                if len(packet) > 3:
                    header += 'X-Config-Revision: '+str(packet[3])+'\r\nX-Privacy-Applied: '+str(packet[4]).lower()+'\r\n'
                    header += 'X-Stream-Session-ID: '+str(packet[5].get('session_id',''))+'\r\n'
                    header += 'X-Frame-Sequence: '+str(packet[5].get('receive_sequence',''))+'\r\n'
                header += '\r\n'
                self.wfile.write(header.encode()+data+b'\r\n')
                self.wfile.flush()
                previous = packet
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass
        finally:
            transport.remove_socket(self.connection)
            self.close_connection = True

    def whep(self, method):
        if not self.check_origin():
            return
        parts = urlsplit(self.path).path.split('/')
        transport = behavior.transport
        try:
            if len(parts) != 6:
                raise ValueError('Invalid video resource')
            data = None
            if method in ('POST', 'PATCH'):
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= 131072:
                    raise ValueError('Invalid SDP size')
                self.connection.settimeout(5)
                data = self.rfile.read(length)
                if len(data) != length:
                    raise ValueError('Incomplete SDP')
            if parts[4] == 'whep' and method == 'POST' and parts[5] in VIDEO_STREAMS:
                profiles=parse_qs(urlsplit(self.path).query).get('profile',['remote'])
                if len(profiles)!=1 or profiles[0] not in PROFILES:
                    raise ValueError('Invalid video profile')
                token, answer, etag = transport.create(parts[5], data, profiles[0])
                try:
                    self.send_bytes(answer, 'application/sdp', 201, {
                        'Location':'/api/v1/video/sessions/'+token, 'ETag':etag,
                        'X-Video-Stream':parts[5], 'X-Preview-Overlay':str(parts[5]!='raw').lower()})
                except OSError:
                    transport.session_request(token, 'DELETE')
            elif parts[4] == 'sessions' and re.fullmatch('[a-f0-9]{32}', parts[5]):
                if method == 'DELETE' and parts[5] not in transport.sessions:
                    transport.cancel_fallback(parts[5])
                    self.send_bytes(b'', 'application/octet-stream', 204)
                    return
                if method == 'GET':
                    with transport.condition:
                        session = transport.sessions.get(parts[5])
                        if not session or session['epoch'] != transport.epoch:
                            raise ValueError('Expired media session')
                        session['created'] = time.monotonic()
                    self.json({'active':True})
                elif method in ('PATCH','DELETE'):
                    status, body = transport.session_request(parts[5],method,data,self.headers.get('If-Match','*'))
                    self.send_bytes(body,'application/trickle-ice-sdpfrag',status)
                else:
                    raise ValueError('Invalid video operation')
            else:
                raise ValueError('Invalid video resource')
        except ValueError as error:
            self.error(409, 'VIDEO_UNAVAILABLE', error)
        except OSError:
            self.error(503, 'VIDEO_UNAVAILABLE', 'Media service unavailable')

    def do_PATCH(self):
        self.whep('PATCH')

    def do_GET(self):
        if self.path == '/health/live':
            self.json({'live': True})
            return
        if self.path == '/health/ready':
            value = readiness(ROOT, behavior, behavior.transport)
            self.json(value, 200 if value['ready'] else 503)
            return
        if studio_http.handle(self,'GET'): return
        parsed = urlsplit(self.path)
        path = parsed.path
        locale = 'zh-CN'
        if path in ('/stream.mjpg', '/api/frame.jpg'):
            values = parse_qs(parsed.query, keep_blank_values=True).get('lang', ['zh-CN'])
            if len(values) != 1 or values[0] not in LANGUAGES:
                self.error(400, 'BAD_REQUEST', LocalizedError('error.language'))
                return
            locale = values[0]
        assets = {'/video-player.js': ('video-player.js', 'text/javascript; charset=utf-8'),
                  '/overlay-style.json': ('overlay-style.json', 'application/json; charset=utf-8'),
                  '/overlay.js': ('overlay.js', 'text/javascript; charset=utf-8'),
                  '/i18n.js': ('i18n.js', 'text/javascript; charset=utf-8'),
                  '/locales.json': ('locales.json', 'application/json; charset=utf-8'),
                  '/pipeline.js': ('pipeline.js', 'text/javascript; charset=utf-8'),
                  '/settings': ('settings.html', 'text/html; charset=utf-8'),
                  '/settings.html': ('settings.html', 'text/html; charset=utf-8'),
                  '/settings.js': ('settings.js', 'text/javascript; charset=utf-8'),
                  '/settings.css': ('settings.css', 'text/css; charset=utf-8'),
                  '/roi-editor.js': ('roi-editor.js', 'text/javascript; charset=utf-8'),
                  '/api.js': ('api.js', 'text/javascript; charset=utf-8'),
                  '/main.js': ('main.js', 'text/javascript; charset=utf-8'),
                  '/annotation.js': ('annotation.js','text/javascript; charset=utf-8'),
                  '/studio.js': ('studio.js','text/javascript; charset=utf-8'),
                  '/production.js': ('production.js','text/javascript; charset=utf-8'),
                  '/optimization.css': ('optimization.css','text/css; charset=utf-8'),
                  '/assembly.js': ('assembly.js','text/javascript; charset=utf-8'),
                  '/studio.css': ('studio.css','text/css; charset=utf-8'),
                  '/main.css': ('main.css', 'text/css; charset=utf-8')}
        if path == '/':
            self.send_bytes((ROOT/'frontend/public/index.html').read_bytes(), 'text/html; charset=utf-8')
        elif path in assets:
            filename, content_type = assets[path]
            self.send_bytes((ROOT/'frontend/public'/filename).read_bytes(), content_type)
        elif path.startswith('/api/v1/video/sessions/'):
            self.whep('GET')
        elif path == '/dev-info':
            self.json({'mode': 'device'})
        elif path == '/api/v1/system/metrics':
            self.json(system_metrics.snapshot())
        elif path == '/api/v1/camera/devices':
            self.json(usb_devices())
        elif path == '/api/v1/settings':
            result = behavior.settings()
            result['camera_source'] = cameras.public()
            result['camera'] = self.camera()
            self.json(result)
        elif path in ('/api/work-status', '/api/v1/work/status'):
            snapshot = behavior.snapshot()
            self.json(work_status(snapshot) if path.startswith('/api/v1/') else snapshot)
        elif path in ('/api/v1/camera', '/api/status'):
            self.json(self.camera())
        elif path == '/api/v1/observations/latest':
            self.json(behavior.observation_snapshot())
        elif path == '/api/v1/observations/frame.jpg':
            key = parse_qs(parsed.query).get('observation_id', [''])[0]
            if not key or len(key) > 256:
                self.error(400, 'BAD_REQUEST', 'observation_id required')
                return
            with behavior.lock:
                pair = behavior.observation_frame(key)
                if pair is None:
                    self.error(410, 'FRAME_EXPIRED', 'Fetch the latest observation again')
                    return
                observation, data = pair
            self.send_media(data, headers={
                    'X-Observation-ID': key, 'X-Stream-Session-ID': observation['frame']['stream_session_id'],
                    'X-Frame-Sequence': observation['frame']['receive_sequence'],
                    'X-Config-Revision': observation['config_revision'],
                    'X-Privacy-Applied': str(observation['privacy_applied']).lower()})
        elif path in ('/api/frame.jpg', '/api/v1/video.jpg'):
            with behavior.lock:
                media = behavior.media
                if media is None or (time.monotonic_ns()-media['received'])/1e9 >= behavior.config['max_observation_age']:
                    self.error(503, 'FRAME_UNAVAILABLE', 'No fresh protected frame')
                    return
                headers = self.media_headers(media)
                data = media['jpeg']
                if path == '/api/frame.jpg':
                    data = media['annotated_locales'][locale]
                    headers['Content-Language'] = locale
            self.send_media(data, headers=headers)
        elif path in ('/stream.mjpg', '/api/v1/video.mjpg'):
            self.stream(raw=path.startswith('/api/v1/'), locale=locale)
        else:
            self.error(404, 'NOT_FOUND', 'Unknown endpoint')

    def check_origin(self):
        if maintenance():
            self.error(503, 'MAINTENANCE', 'Deployment is in progress')
            return False
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            self.error(403, 'ORIGIN_REJECTED', 'Use a same-origin request or development proxy')
            return False
        return True

    def read_json(self, maximum):
        length = int(self.headers.get('Content-Length', '0'))
        if not 1 <= length <= maximum:
            raise LocalizedError('error.requestSize')
        self.connection.settimeout(5)
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise LocalizedError('error.jsonObject')
        return data

    def do_PUT(self):
        if maintenance():
            self.error(503, 'MAINTENANCE', 'Deployment is in progress')
            return
        if studio_http.handle(self,'PUT'): return
        if not self.check_origin():
            return
        if self.path != '/api/v1/settings':
            self.error(404, 'NOT_FOUND', 'Unknown endpoint')
            return
        try:
            request = self.read_json(32768)
            if 'camera_source' in request:
                result = cameras.switch(request, self.camera())
                if result['revision'] != request['expected_revision']:
                    with state_lock:
                        state.update(status='connecting', timestamp=0, stream_session_id=None,
                                     width=None, height=None, jpeg_width=None, jpeg_height=None,
                                     source_fps=None, receive_sequence=None, pts_ns=None)
            else:
                result = behavior.apply_settings(request, self.camera())
        except StudioError as exc:
            exc.message_key='studio.error.'+exc.code
            exc.message_params=exc.params
            self.error(exc.status,'STUDIO_ERROR',exc)
            return
        except SettingsConflict as exc:
            self.error(409, 'SETTINGS_CONFLICT', exc)
            return
        except (ValueError, TypeError, UnicodeError) as exc:
            self.error(400, 'BAD_REQUEST', exc)
            return
        except OSError:
            self.error(500, 'SETTINGS_SAVE_FAILED', '保存失败，请检查存储状态后重试')
            return
        result['camera_source'] = cameras.public()
        result['camera'] = self.camera()
        self.json(result)

    def do_DELETE(self):
        if maintenance():
            self.error(503, 'MAINTENANCE', 'Deployment is in progress')
            return
        if urlsplit(self.path).path.startswith('/api/v1/video/sessions/'):
            self.whep('DELETE')
            return
        studio_http.handle(self,'DELETE') or self.error(404,'NOT_FOUND','Unknown endpoint')

    def do_POST(self):
        if maintenance():
            self.error(503, 'MAINTENANCE', 'Deployment is in progress')
            return
        if studio_http.handle(self,'POST'): return
        if not self.check_origin():
            return
        if self.path.startswith('/api/v1/video/'):
            self.whep('POST')
            return
        if self.path == '/api/v1/camera/test':
            try:
                self.json(cameras.test(self.read_json(8192)))
            except SettingsConflict as exc:
                self.error(409, 'SETTINGS_CONFLICT', exc)
            except (ValueError, TypeError, UnicodeError) as exc:
                self.error(400, 'CAMERA_TEST_FAILED', exc)
            return
        if self.path not in ('/api/work-action', '/api/v1/work/actions'):
            self.error(404, 'NOT_FOUND', 'Unknown endpoint')
            return
        try:
            data = self.read_json(1024)
            if data.get('action') not in ('start', 'end', 'review', 'confirm_camera', 'confirm_return', 'reset_display'):
                raise ValueError('Unsupported action')
        except (ValueError, TypeError, UnicodeError) as exc:
            self.error(400, 'BAD_REQUEST', exc)
            return
        try:
            result = behavior.action(data['action'], data)
        except OSError:
            self.error(500, 'STORAGE_ERROR', 'Settings could not be saved')
            return
        except (ValueError, TypeError) as exc:
            self.error(409, 'ACTION_UNAVAILABLE', exc)
            return
        self.json(work_status(result) if self.path.startswith('/api/v1/') else result)


server = ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('WORKTIME_PORT', '8088'))), Handler)
server.daemon_threads = True
threading.Thread(target=capture, daemon=True).start()


def shutdown(*args):
    behavior.close()
    threading.Thread(target=server.shutdown, daemon=True).start()


signal.signal(signal.SIGTERM, shutdown)
try:
    server.serve_forever()
finally:
    behavior.close()
    server.server_close()

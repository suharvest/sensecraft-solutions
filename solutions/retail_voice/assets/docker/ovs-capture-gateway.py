#!/usr/bin/env python3
"""Candidate access boundary; preparing this file does not publish or deploy it.

Listens on all IPv4 interfaces for LAN HTTP access. OVS authenticates forwarded
Bearer credentials. It supports
neither X-API-Key nor X-API-Token for HTTP (server/core/api_auth.py:140-173).
No server credential is injected. No body/header/request-target is logged.
"""
from datetime import datetime, timezone
from email import policy
from email.message import EmailMessage
import http.client
import http.server
import json
import os
import stat
import sys
import re
import socket
import threading
import time

def endpoint_from_env():
    """Return the listen and voice-service endpoints for this deployment."""
    listen = (os.environ.get('OVS_GATEWAY_LISTEN_HOST', '0.0.0.0'),
              int(os.environ.get('OVS_GATEWAY_LISTEN_PORT', '18621')))
    upstream = (os.environ.get('CAPTURE_UPSTREAM_HOST', '127.0.0.1'),
                int(os.environ.get('CAPTURE_UPSTREAM_PORT', '8081')))
    return listen, upstream


LISTEN, (UPSTREAM_HOST, UPSTREAM_PORT) = endpoint_from_env()
MAX_AUDIO = 64 * 1024 * 1024
MAX_UPLOAD = 66 * 1024 * 1024
MAX_RESPONSE = 4 * 1024 * 1024
READ_TIMEOUT = int(os.environ.get('OVS_UPLOAD_TIMEOUT', '120'))
UPSTREAM_TIMEOUT = int(os.environ.get('OVS_UPSTREAM_TIMEOUT', '660'))
OBSERVED_METADATA_NAMES = frozenset((
    'device_id', 'mac_address', '_remote_id', 'capture_id', 'capture_mode',
    'upload_id', 'chunk_seq', 'metadata', 'extra_body', 'extra',
    'started_at_ms', 'ended_at_ms', 'is_final', 'probe_id',
    'recording_id', 'session_id', 'chunk_index', 'chunk_total',
))
STANDARD_MULTIPART_NAMES = frozenset((
    'file', 'model', 'language', 'prompt', 'response_format', 'temperature',
    'stream', 'timestamp_granularities',
))
METADATA_PROBE = 'sc-probe-20260909'
MAX_OBSERVED_METADATA_VALUE = 64 * 1024
ROUTES = {'/v1/models': 'GET', '/v1/audio/transcriptions': 'POST'}
UPSTREAM_ROUTES = {
    '/v1/models': '/api/v1/captures/models',
    '/v1/audio/transcriptions': '/api/v1/captures/ingest',
}
LOG_METHODS = frozenset(('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT'))
LOG_ROUTES = frozenset(('/v1/models', '/v1/audio/transcriptions', '/asr', '/asr/stream', '/inference', '/v1/asr', '/ws'))


class InvalidMultipart(ValueError):
    pass


def multipart_headers(raw):
    # No bare newlines, folded headers, or malformed/ambiguous MIME parameters.
    if len(raw) > 16384 or any(not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+:[^\r\n]*", line) for line in raw.split(b'\r\n')):
        raise InvalidMultipart()
    # HTTP multipart permits UTF-8 filenames. Decode strictly before MIME
    # parsing so valid UTF-8 is not mislabeled as undecodable RFC 5322 bytes.
    # Invalid UTF-8 still fails, and all structural/parser defects stay fatal.
    # Build headers only: Python 3.11 HeaderParser adds a spurious multipart
    # body invariant defect to a header-only multipart Content-Type message.
    parsed = EmailMessage(policy=policy.default)
    for line in raw.decode('utf-8').split('\r\n'):
        key, value = line.split(':', 1)
        parsed[key] = value.lstrip(' \t')
    if parsed.defects or any(getattr(value, 'defects', ()) for value in parsed.values()):
        raise InvalidMultipart()
    return parsed


def _observe_metadata_value(field_name, raw_value, names, marker):
    """Collect only allowlisted names and a fixed benign marker from one field."""
    if len(raw_value) > MAX_OBSERVED_METADATA_VALUE:
        return marker
    if field_name in OBSERVED_METADATA_NAMES:
        names.add(field_name)
    try:
        text = raw_value.decode('utf-8')
    except UnicodeDecodeError:
        return marker
    if METADATA_PROBE in text:
        marker = True
    try:
        value = json.loads(text)
    except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
        return marker

    # Keep diagnostic work bounded and independent from request acceptance.
    pending = [value]
    visited = 0
    while pending and visited < 2048:
        item = pending.pop()
        visited += 1
        if isinstance(item, str):
            if METADATA_PROBE in item:
                marker = True
        elif isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str) and key in OBSERVED_METADATA_NAMES:
                    names.add(key)
                if len(pending) + visited < 2048:
                    pending.append(child)
        elif isinstance(item, list):
            pending.extend(item[:max(0, 2048 - visited - len(pending))])
    return marker


def normalize_model(body, content_type, observation=None):
    """Rewrite only the model field byte span; every file/other field is untouched.

    Requires CRLF multipart framing without preamble/epilogue. No whole-body
    substitutions and no MIME reserialization of uploaded files are performed.
    """
    try:
        content = multipart_headers(('Content-Type: ' + content_type).encode('ascii'))
        if content.get_content_type() != 'multipart/form-data':
            raise InvalidMultipart()
        boundary = content.get_boundary()
        if not boundary or not re.fullmatch(r"[0-9A-Za-z'()+_,./:=? -]{1,70}", boundary) or boundary.endswith(' '):
            raise InvalidMultipart()
        boundary = boundary.encode('ascii')
        opening = b'--' + boundary + b'\r\n'
        if not body.startswith(opening):
            raise InvalidMultipart()
        delimiter = re.compile(rb'\r\n--' + re.escape(boundary) + rb'(?P<close>--)?(?:\r\n|$)')
        position = len(opening)
        model_span = None
        parts = 0
        observed_names = set()
        standard_names = set()
        unlisted_field_count = 0
        probe_marker = False
        while True:
            match = delimiter.search(body, position)
            if match is None:
                raise InvalidMultipart()
            end = match.start()
            header_end = body.find(b'\r\n\r\n', position, end)
            if header_end < 0:
                raise InvalidMultipart()
            part = multipart_headers(body[position:header_end])
            if len(part.get_all('Content-Disposition', [])) != 1 or part.get_content_disposition() != 'form-data':
                raise InvalidMultipart()
            name = part.get_param('name', header='content-disposition')
            if not isinstance(name, str) or not name:
                raise InvalidMultipart()
            if part.get_all('Content-Transfer-Encoding'):
                raise InvalidMultipart()
            filename = part.get_param('filename', header='content-disposition')
            if name in STANDARD_MULTIPART_NAMES:
                standard_names.add(name)
            elif name not in OBSERVED_METADATA_NAMES:
                unlisted_field_count += 1
            if filename is None:
                probe_marker = _observe_metadata_value(
                    name, body[header_end + 4:end], observed_names, probe_marker)
            elif name == 'file' and end - (header_end + 4) > MAX_AUDIO:
                raise InvalidMultipart()
            if name == 'model':
                if model_span is not None or filename is not None:
                    raise InvalidMultipart()
                model_span = (header_end + 4, end)
            parts += 1
            if parts > 128:
                raise InvalidMultipart()
            if match.group('close'):
                if match.end() != len(body):
                    raise InvalidMultipart()
                closing_start = match.start()
                break
            if not match.group().endswith(b'\r\n'):
                raise InvalidMultipart()
            position = match.end()
        if observation is not None:
            observation.clear()
            observation.update({
                'metadata_names': sorted(observed_names),
                'multipart_names': sorted(standard_names),
                'unlisted_field_count': unlisted_field_count,
                'probe_marker': bool(probe_marker),
            })
        if model_span is None:
            field = (b'\r\n--' + boundary + b'\r\nContent-Disposition: form-data; name="model"\r\n\r\nsensevoice')
            return body[:closing_start] + field + body[closing_start:]
        start, end = model_span
        if body[start:end].strip() in (b'', b'whisper', b'whisper-1'):
            return body[:start] + b'sensevoice' + body[end:]
        return body  # sensevoice and unknown models remain byte-for-byte unchanged.
    except (UnicodeError, TypeError, ValueError) as error:
        raise InvalidMultipart() from error


class Gateway(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'  # One request per connection, no body reuse.
    server_version = 'OVSGateway'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(READ_TIMEOUT)

    def log_message(self, *args):
        pass

    def log_error(self, *args):
        pass

    def diagnostic_event(self, event, status=None, multipart=None):
        # Only constants from allowlists enter the event, never user strings.
        # Query-bearing targets deliberately map to "other" in their entirety.
        try:
            method = self.__dict__.get('command', '')
            route = self.__dict__.get('path', '')
            record = {
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'event': event if event in ('received', 'response') else 'other',
                'method': method if method in LOG_METHODS else 'other',
                'route': route if route in LOG_ROUTES else 'other',
                'status': status if type(status) is int and 100 <= status <= 599 else None,
            }
            if multipart is not None:
                names = multipart.get('metadata_names', [])
                multipart_names = multipart.get('multipart_names', [])
                unknown_count = multipart.get('unlisted_field_count')
                if (
                    isinstance(names, list)
                    and all(name in OBSERVED_METADATA_NAMES for name in names)
                    and isinstance(multipart_names, list)
                    and all(name in STANDARD_MULTIPART_NAMES for name in multipart_names)
                    and type(unknown_count) is int
                    and 0 <= unknown_count <= 128
                ):
                    record['metadata_names'] = names
                    record['multipart_names'] = multipart_names
                    record['unlisted_field_count'] = unknown_count
                    record['probe_marker'] = multipart.get('probe_marker') is True
            line = (json.dumps(record, separators=(',', ':')) + '\n').encode('ascii')
            fd = sys.stdout.fileno()
            mode = os.fstat(fd).st_mode
            # O_NONBLOCK does not protect regular-file writes from disk stalls.
            # Diagnostics are best effort on pipe/socket sinks (e.g. journald).
            if len(line) > 512 or not (stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
                return
            os.set_blocking(fd, False)
            os.write(fd, line)  # One bounded write; drop on a full sink, never retry.
        except Exception:
            # A closed/full log sink cannot change the HTTP response path.
            pass

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler errors must never reflect request lines.
        self.reply(code, b'{"error":"invalid_request"}', 'application/json')

    def reply(self, status, body=b'', content_type='application/json', headers=None):
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if getattr(self, 'command', '') != 'HEAD':
                self.wfile.write(body)
            self.diagnostic_event('response', status, getattr(self, 'multipart_observation', None))
        except (OSError, ValueError):
            pass

    def reject(self, code, label):
        self.reply(code, json.dumps({'error': label}).encode())

    def handle_expect_100(self):
        self.reject(417, 'expect_not_supported')
        return False

    def __getattr__(self, name):
        # Unknown HTTP methods receive 404/405 via the same path boundary.
        if name.startswith('do_'):
            return self.dispatch
        raise AttributeError(name)

    def dispatch(self):
        self.diagnostic_event('received')
        if self.path == '/v1/audio/transcriptions' and self.command == 'OPTIONS':
            self.reply(204, b'', headers={'Allow': 'POST, OPTIONS'})
            return
        allowed = ROUTES.get(self.path)
        if allowed is None:  # Exact comparison rejects queries, encoded paths, root, admin, WS.
            self.reject(404, 'not_found')
            return
        if self.command != allowed:
            self.reply(405, b'{"error":"method_not_allowed"}', headers={'Allow': allowed})
            return
        if self.headers.get_all('Transfer-Encoding'):
            self.reject(400, 'transfer_encoding_not_supported')
            return
        if self.headers.get_all('Expect'):
            self.reject(417, 'expect_not_supported')
            return
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) > 1:
            self.reject(400, 'duplicate_content_length')
            return
        if self.command == 'POST' and not lengths:
            self.reject(411, 'content_length_required')
            return
        raw_length = lengths[0] if lengths else '0'
        if not raw_length.isascii() or not raw_length.isdigit():
            self.reject(400, 'invalid_content_length')
            return
        length = int(raw_length)
        if length > MAX_UPLOAD:
            self.reject(413, 'upload_too_large')
            return
        if self.command == 'GET' and length:
            self.reject(400, 'get_body_not_supported')
            return
        auth = self.headers.get_all('Authorization', [])
        if len(auth) > 1:
            self.reject(400, 'duplicate_authorization')
            return
        headers = {'Content-Length': str(length)}
        if auth:
            headers['Authorization'] = auth[0]
        if len(self.headers.get_all('Content-Type', [])) > 1:
            self.reject(400, 'duplicate_content_type')
            return
        if self.headers.get('Content-Type'):
            headers['Content-Type'] = self.headers['Content-Type']
        body = bytearray()
        deadline = time.monotonic() + READ_TIMEOUT
        try:
            while len(body) < length:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                self.connection.settimeout(remaining)
                part = self.rfile.read1(min(65536, length - len(body)))
                if not part:
                    self.reject(400, 'incomplete_body')
                    return
                body.extend(part)
        except (TimeoutError, OSError):
            self.reject(408, 'body_read_timeout')
            return
        if self.command == 'POST':
            observation = {}
            try:
                body = normalize_model(bytes(body), headers.get('Content-Type', ''), observation)
            except InvalidMultipart:
                self.reject(400, 'invalid_multipart')
                return
            self.multipart_observation = observation
            if len(body) > MAX_UPLOAD:
                self.reject(413, 'upload_too_large')
                return
            headers['Content-Length'] = str(len(body))
        self.connection.settimeout(READ_TIMEOUT)
        upstream = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=UPSTREAM_TIMEOUT)
        try:
            upstream.request(self.command, UPSTREAM_ROUTES[self.path], body=body, headers=headers)
            response = upstream.getresponse()
            payload = response.read(MAX_RESPONSE + 1)
            if len(payload) > MAX_RESPONSE:
                self.reject(502, 'upstream_response_too_large')
                return
            forwarded = {}
            for key in ('WWW-Authenticate', 'Retry-After'):
                value = response.getheader(key)
                if value is not None and '\r' not in value and '\n' not in value:
                    forwarded[key] = value
            # HTTPConnection does not follow redirects. Location is not exposed.
            content_type = response.getheader('Content-Type', 'application/octet-stream')
            if '\r' in content_type or '\n' in content_type:
                content_type = 'application/octet-stream'
            self.reply(response.status, payload, content_type, forwarded)
        except (TimeoutError, socket.timeout):
            self.reject(504, 'upstream_timeout')
        except (OSError, http.client.HTTPException, ValueError):
            self.reject(502, 'upstream_failure')
        finally:
            upstream.close()


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self.handler_slots = threading.BoundedSemaphore(4)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.handler_slots.acquire(blocking=False):
            try:
                request.settimeout(0.1)
                request.sendall(
                    b'HTTP/1.0 503 Service Unavailable\r\n'
                    b'Retry-After: 1\r\nContent-Length: 0\r\n'
                    b'Connection: close\r\n\r\n'
                )
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.handler_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.handler_slots.release()

    def handle_error(self, request, client_address):
        # Suppress traceback/request details as well as access logs.
        pass


def main():
    with Server(LISTEN, Gateway) as server:
        print(f'gateway_listen={LISTEN[0]}:{LISTEN[1]} upstream={UPSTREAM_HOST}:{UPSTREAM_PORT}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

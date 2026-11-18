"""Latest-only shared frames for an isolated drawing/H.264 process.

Only already privacy-processed pixels enter this mailbox. POSIX record locks
protect one replaceable frame; no image pickling or unbounded frame queue.
"""
import fcntl
import json
import mmap
import os
from pathlib import Path
import select
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

import numpy as np

META_SIZE = 2 * 1024 * 1024
HEADER = struct.Struct('<QQI')


def draw_config(config):
    keys = ('revision', 'image_size', 'regions', 'display', 'visualization', 'materials', 'max_observation_age',
            'privacy', 'operation', 'detection', 'keypoint_confidence',
            'regions_confirmed', 'materials_confirmed', '_overlay_evidence')
    value = {k: config[k] for k in keys if k in config}
    status = config.get('_material_status', {})
    value['_material_status'] = {k: status[k] for k in ('available', 'detections', 'class_names') if k in status}
    value['_material_status']['alerts'] = [{'region': a['region']} for a in status.get('alerts', [])]
    return value


class ProcessPublisher:
    def __init__(self, locale, width, height, profile, quality, root, command=None):
        self.size = (width, height)
        self.key = locale + '_' + profile
        self.quality = quality
        self.sequence = 0
        self.closed = False
        self.messages = b''
        self.file = tempfile.TemporaryFile(dir='/dev/shm' if Path('/dev/shm').is_dir() else None)
        os.ftruncate(self.file.fileno(), META_SIZE + width * height * 3)
        self.mapping = mmap.mmap(self.file.fileno(), 0)
        self.image = np.ndarray((height, width, 3), np.uint8, buffer=self.mapping, offset=META_SIZE)
        self.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.channel.setblocking(False)
        env = os.environ.copy()
        source = str(Path(__file__).resolve().parents[1])
        env['PYTHONPATH'] = source + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        argv = command or [sys.executable, '-m', 'jetson_worktime.encoder_process']
        args = [str(self.file.fileno()), str(child.fileno()), locale, profile, str(width), str(height)]
        log = Path(root) / 'logs/video-worker.log'
        log.parent.mkdir(exist_ok=True)
        try:
            with open('/proc/self/fd/1', 'ab') if os.environ.get('WORKTIME_CONTAINER') == '1' else log.open('ab') as output:
                self.process = subprocess.Popen([*argv, *args], env=env, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=subprocess.STDOUT, pass_fds=(self.file.fileno(), child.fileno()))
        except Exception:
            child.close(); self.channel.close()
            del self.image
            self.mapping.close(); self.file.close()
            raise
        child.close()

    def poll_updates(self):
        while True:
            try:
                data = self.channel.recv(65536)
            except BlockingIOError:
                break
            if not data:
                raise RuntimeError('Video worker disconnected')
            self.messages += data
            while b'\n' in self.messages:
                line, self.messages = self.messages.split(b'\n', 1)
                report = json.loads(line)
                if report['kind'] == 'error':
                    raise RuntimeError('Video worker: ' + report['type'])
                if report['kind'] == 'frame':
                    for key in ('video_resize_ms', 'video_overlay_ms', 'video_prepare_ms', 'encoder_submit_ms'):
                        self.quality.sample(key, report[key])
                    self.quality.mark('video_send_' + self.key, report['at_ns'])
        if self.process.poll() is not None:
            raise RuntimeError('Video worker exited')

    def write(self, image, received, persons, config, fresh, regions_match):
        if self.closed:
            return False
        self.poll_updates()
        if image.shape != self.image.shape:
            raise ValueError('Video dimensions changed')
        metadata = json.dumps(dict(persons=persons, config=draw_config(config), fresh=fresh,
                                   regions_match=regions_match), allow_nan=False).encode()
        if len(metadata) > META_SIZE - HEADER.size:
            raise ValueError('Video metadata too large')
        try:
            fcntl.lockf(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.quality.sample('video_mailbox_busy', 1)
            return False
        try:
            np.copyto(self.image, image)
            self.mapping[HEADER.size:HEADER.size + len(metadata)] = metadata
            self.sequence += 1
            self.mapping[:HEADER.size] = HEADER.pack(self.sequence, received, len(metadata))
        finally:
            fcntl.lockf(self.file.fileno(), fcntl.LOCK_UN)
        try:
            self.channel.send(b'\1')
        except BlockingIOError:
            pass  # An existing wakeup will read the newest mailbox contents.
        return True

    def cancel(self):
        if not self.closed:
            self.closed = True
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass

    def close(self):
        self.cancel()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill(); self.process.wait(timeout=3)
        self.channel.close()
        if self.mapping is not None:
            del self.image
            self.mapping.close(); self.mapping = None
            self.file.close()


def worker_main(factory=None):
    import cv2
    from .streaming import H264Publisher, PROFILES, preview_frame
    # Leave capacity for capture/inference while parallelizing HD preview resize.
    cv2.setNumThreads(3)
    fd, channel_fd, locale, profile, width, height = sys.argv[1:]
    fd, channel_fd, width, height = map(int, (fd, channel_fd, width, height))
    channel = socket.socket(fileno=channel_fd)
    mapping = mmap.mmap(fd, 0)
    view = np.ndarray((height, width, 3), np.uint8, buffer=mapping, offset=META_SIZE)
    publisher = None
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    previous = 0
    try:
        while not stopped:
            if not select.select([channel], [], [], .2)[0]:
                continue
            if not channel.recv(65536):
                break
            fcntl.lockf(fd, fcntl.LOCK_EX)
            try:
                sequence, received, length = HEADER.unpack(mapping[:HEADER.size])
                if sequence == previous:
                    continue
                previous = sequence
                metadata = json.loads(mapping[HEADER.size:HEADER.size + length])
                frame = view.copy()
            finally:
                fcntl.lockf(fd, fcntl.LOCK_UN)
            if stopped:
                break
            config = metadata['config']
            if time.monotonic_ns() - received > config.get('max_observation_age', 1.5) * 1e9:
                continue
            started = time.monotonic_ns()
            options = PROFILES[profile]
            target_width = min(options['width'], width) // 2 * 2
            target_height = max(2, round(height * target_width / width / 2) * 2)
            small = frame if frame.shape[:2] == (target_height,target_width) else cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
            resized = time.monotonic_ns()
            evidence = config.get('_overlay_evidence')
            if evidence and time.monotonic_ns() - evidence['source_received_ns'] > 750_000_000:
                metadata['fresh'] = False
                config['_material_status']['detections'] = []
            marked = preview_frame(small, metadata['persons'], config, metadata['fresh'], metadata['regions_match'], locale)
            drawn = time.monotonic_ns()
            if stopped:
                break
            if publisher is None:
                publisher = (factory or H264Publisher)(locale, small.shape[1], small.shape[0], profile)
            sent = time.monotonic_ns()
            publisher.write(marked, received)
            finished = time.monotonic_ns()
            report = dict(kind='frame', at_ns=finished, video_resize_ms=(resized-started)/1e6,
                video_overlay_ms=(drawn-resized)/1e6, video_prepare_ms=(drawn-started)/1e6,
                encoder_submit_ms=(finished-sent)/1e6)
            # Stats never block the encoder if the parent is temporarily busy.
            try: channel.send((json.dumps(report)+'\n').encode(), socket.MSG_DONTWAIT)
            except BlockingIOError: pass
    except Exception as error:
        try: channel.sendall((json.dumps(dict(kind='error', type=type(error).__name__))+'\n').encode())
        except OSError: pass
    finally:
        if publisher is not None:
            publisher.close()
        del view
        mapping.close(); os.close(fd); channel.close()


if __name__ == '__main__':
    worker_main()

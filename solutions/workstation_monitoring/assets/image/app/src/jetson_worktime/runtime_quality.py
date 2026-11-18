"""Bounded timing samples and ordered, non-blocking observation persistence."""
from collections import deque
import json
import queue
import threading
import time


class RuntimeQuality:
    def __init__(self, capacity=2048):
        self.capacity = capacity
        self.lock = threading.Lock()
        self.samples = {}
        self.last = {}
        self.counts = {}

    def sample(self, name, milliseconds):
        with self.lock:
            self.samples.setdefault(name, deque(maxlen=self.capacity)).append(float(milliseconds))
            self.counts[name] = self.counts.get(name, 0) + 1
            if milliseconds > 500 and name.endswith('_interval_ms'):
                key = name + '_over_500ms'
                self.counts[key] = self.counts.get(key, 0) + 1

    def mark(self, name, now_ns=None):
        now_ns = time.monotonic_ns() if now_ns is None else now_ns
        with self.lock:
            previous = self.last.get(name)
            self.last[name] = now_ns
        if previous is not None and now_ns > previous:
            self.sample(name + '_interval_ms', (now_ns-previous)/1e6)

    def rate(self,name):
        with self.lock:
            intervals=self.samples.get(name+'_interval_ms',[])
            if not intervals or time.monotonic_ns()-self.last.get(name,0)>5e9: return 0.
            recent=list(intervals)[-60:]
            return round(1000*len(recent)/sum(recent),2) if sum(recent)>0 else 0.

    def snapshot(self):
        with self.lock:
            result = {}
            for name, samples in self.samples.items():
                values = sorted(samples)
                result[name] = dict(count=self.counts[name], window_count=len(values),
                    p50=values[len(values)//2], p95=values[int((len(values)-1)*.95)], max=max(values),
                    over_500ms=self.counts.get(name+'_over_500ms', 0))
            return result


class ObservationWriter:
    """Overflow or disk failure is explicit; accepted rows are drained on close."""
    def __init__(self, handle, quality, capacity=256):
        self.handle, self.quality = handle, quality
        self.queue = queue.Queue(capacity)
        self.stopping = threading.Event()
        self.error = None
        self.written = 0
        self.thread = threading.Thread(target=self.run, daemon=True, name='observation-writer')
        self.thread.start()

    def submit(self, row):
        if self.error or self.stopping.is_set():
            raise OSError('Observation storage unavailable')
        try:
            self.queue.put_nowait(row)
        except queue.Full:
            self.error = 'StorageQueueFull'
            raise OSError('Observation storage queue full') from None

    def run(self):
        while not self.stopping.is_set() or not self.queue.empty():
            try:
                row = self.queue.get(timeout=.1)
            except queue.Empty:
                continue
            started = time.monotonic_ns()
            try:
                self.handle.write(json.dumps(row, ensure_ascii=False)+'\n')
                self.written += 1
                self.quality.sample('observation_write_ms', (time.monotonic_ns()-started)/1e6)
            except (OSError, ValueError):
                self.error = 'StorageError'
            finally:
                self.queue.task_done()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            self.error = 'StorageShutdownTimeout'
            return False
        self.handle.close()
        return True

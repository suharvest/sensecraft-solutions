"""Read-only Linux/Jetson telemetry, cached across concurrent HTTP clients."""
import math
from pathlib import Path
import threading
import time


def read_text(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return ''


class SystemMetrics:
    def __init__(self, proc_root=Path('/proc'), sys_root=Path('/sys'),
                 clock=time.monotonic, wall_clock=time.time):
        self.proc_root = Path(proc_root)
        self.sys_root = Path(sys_root)
        self.clock = clock
        self.wall_clock = wall_clock
        self.lock = threading.Lock()
        self.previous_cpu = None
        self.cached = None
        self.sample_time = None

    def cpu_percent(self):
        try:
            fields = read_text(self.proc_root/'stat').splitlines()[0].split()
            if fields[0] != 'cpu' or len(fields) < 9:
                raise ValueError('Incomplete CPU counters')
            # Guest time is already included in user/nice. Count only eight fields.
            counters = [int(value) for value in fields[1:9]]
            if min(counters) < 0:
                raise ValueError('Invalid CPU counter')
            current = (sum(counters), counters[3]+counters[4])
        except (IndexError, ValueError):
            self.previous_cpu = None
            return None
        previous = self.previous_cpu
        self.previous_cpu = current
        if previous is None:
            return None
        total = current[0]-previous[0]
        idle = current[1]-previous[1]
        if total <= 0 or idle < 0 or idle > total:
            return None
        return round(100*(total-idle)/total, 1)

    def memory_bytes(self):
        try:
            fields = dict(line.split(':', 1) for line in read_text(self.proc_root/'meminfo').splitlines())
            total = int(fields['MemTotal'].split()[0])*1024
            available = int(fields['MemAvailable'].split()[0])*1024
            if total <= 0 or not 0 <= available <= total:
                raise ValueError('Invalid memory counters')
            return total-available, total
        except (KeyError, IndexError, ValueError):
            return None, None

    def gpu_percent(self):
        # Jetson driver load uses 0..1000, i.e. tenths of one percent.
        paths = [self.sys_root/'devices/gpu.0/load']
        for pattern in ('class/devfreq/*gpu/device/load',
                        'devices/platform/*gpu/load',
                        'devices/platform/*/*gpu/load'):
            paths.extend(sorted(self.sys_root.glob(pattern)))
        for path in paths:
            try:
                value = int(read_text(path))
            except ValueError:
                continue
            if 0 <= value <= 1000:
                return value/10
        return None

    def temperature(self):
        readings = []
        for zone in self.sys_root.glob('class/thermal/thermal_zone*'):
            sensor = read_text(zone/'type')
            if not sensor.lower().startswith(('cpu', 'gpu', 'soc', 'cv', 'tj')):
                continue
            try:
                value = int(read_text(zone/'temp'))/1000
            except ValueError:
                continue
            if -40 <= value <= 150:
                readings.append((value, sensor))
        return max(readings) if readings else (None, None)

    def uptime_seconds(self):
        try:
            value = float(read_text(self.proc_root/'uptime').split()[0])
        except (ValueError, IndexError):
            return None
        return value if math.isfinite(value) and value >= 0 else None

    def snapshot(self):
        with self.lock:
            now = self.clock()
            if self.cached is None or now-self.sample_time >= 1:
                used, total = self.memory_bytes()
                temperature, sensor = self.temperature()
                self.cached = dict(
                    schema_version='1.0', sampled_at_ms=round(self.wall_clock()*1000),
                    cpu_percent=self.cpu_percent(), gpu_percent=self.gpu_percent(),
                    memory_used_bytes=used, memory_total_bytes=total,
                    temperature_celsius=temperature, temperature_sensor=sensor,
                    uptime_seconds=self.uptime_seconds())
                self.sample_time = self.clock()
            return {**self.cached, 'age_ms': max(0, (self.clock()-self.sample_time)*1000)}

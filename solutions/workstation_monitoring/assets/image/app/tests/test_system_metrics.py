import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jetson_worktime.system_metrics import SystemMetrics


class SystemMetricsTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.proc = self.root/'proc'
        self.sys = self.root/'sys'
        self.proc.mkdir()
        self.sys.mkdir()
        self.now = 10.
        self.metrics = SystemMetrics(self.proc, self.sys, clock=lambda: self.now, wall_clock=lambda: 100.)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def test_cpu_delta_shared_cache_and_guest_time_not_counted_twice(self):
        self.write(self.proc/'stat', 'cpu 100 0 20 800 10 0 0 0 50 0\n')
        first = self.metrics.snapshot()
        self.assertIsNone(first['cpu_percent'])
        first['gpu_percent'] = 99
        self.write(self.proc/'stat', 'cpu 120 0 30 860 20 0 0 0 65 0\n')
        self.now += .5
        self.assertEqual(self.metrics.snapshot()['age_ms'], 500)
        self.assertIsNone(self.metrics.snapshot()['gpu_percent'])
        self.now += 1
        result = self.metrics.snapshot()
        self.assertEqual(result['cpu_percent'], 30.)
        self.assertEqual(result['age_ms'], 0)
        self.assertEqual(result['sampled_at_ms'], 100000)

    def test_jetson_paths_units_available_memory_and_peak_chip_temperature(self):
        self.write(self.proc/'meminfo', 'MemTotal: 1000 kB\nMemAvailable: 700 kB\nMemFree: 200 kB\n')
        self.write(self.proc/'uptime', '7201.5 10000\n')
        self.write(self.sys/'devices/platform/bus@0/17000000.gpu/load', '347\n')
        for index, (sensor, value) in enumerate([('cpu-thermal', 55250), ('gpu-thermal', 56000), ('board', 90000)]):
            zone = self.sys/f'class/thermal/thermal_zone{index}'
            self.write(zone/'type', sensor)
            self.write(zone/'temp', str(value))
        result = self.metrics.snapshot()
        self.assertEqual(result['gpu_percent'], 34.7)
        self.assertEqual(result['memory_used_bytes'], 300*1024)
        self.assertEqual(result['memory_total_bytes'], 1000*1024)
        self.assertEqual(result['temperature_celsius'], 56.)
        self.assertEqual(result['temperature_sensor'], 'gpu-thermal')
        self.assertEqual(result['uptime_seconds'], 7201.5)

    def test_missing_and_invalid_sources_are_null_without_reusing_previous_values(self):
        self.write(self.sys/'devices/gpu.0/load', '0')
        self.assertEqual(self.metrics.snapshot()['gpu_percent'], 0.)
        self.write(self.sys/'devices/gpu.0/load', '1001')
        self.write(self.proc/'meminfo', 'MemTotal: 100 kB\nMemAvailable: 101 kB')
        self.write(self.proc/'stat', 'invalid counters')
        self.write(self.proc/'uptime', 'nan')
        self.now += 2
        result = self.metrics.snapshot()
        for key in ['cpu_percent', 'gpu_percent', 'memory_used_bytes', 'memory_total_bytes', 'temperature_celsius', 'uptime_seconds']:
            self.assertIsNone(result[key], key)
        json.dumps(result, allow_nan=False)

    def test_cpu_reset_reestablishes_baseline(self):
        self.write(self.proc/'stat', 'cpu 100 0 0 900 0 0 0 0\n')
        self.metrics.snapshot()
        self.write(self.proc/'stat', 'cpu 10 0 0 90 0 0 0 0\n')
        self.now += 2
        self.assertIsNone(self.metrics.snapshot()['cpu_percent'])
        self.write(self.proc/'stat', 'cpu 30 0 0 170 0 0 0 0\n')
        self.now += 2
        self.assertEqual(self.metrics.snapshot()['cpu_percent'], 20.)

import argparse
import gc
import glob as globmod
import json
import os
import queue
import sys
import threading
import time

import cv2
import numpy as np
from flask import Flask, Response, jsonify
from influxdb_client import InfluxDBClient, Point
from ultralytics import YOLO

# 尝试导入 TurboJPEG（可选，用于加速推流编码）
try:
    from turbojpeg import TurboJPEG
    TURBOJPEG_AVAILABLE = True
except ImportError:
    TURBOJPEG_AVAILABLE = False
    TurboJPEG = None

# 尝试导入 paho-mqtt（可选，用于 MQTT 发布检测数据）
try:
    import paho.mqtt.client as mqtt_client
    MQTT_AVAILABLE = True
except ImportError:
    mqtt_client = None
    MQTT_AVAILABLE = False

# Flask app for streaming
app = Flask(__name__)

# --- Global streaming config (set in main) ---
STREAM_QUALITY = 40
STREAM_SKIP_FRAMES = 2
turbo_jpeg = None  # TurboJPEG 实例（如果可用）

# --- Per-camera state (keyed by cam_id, e.g. "cam0", "cam1") ---
output_frames = {}       # cam_id -> latest display frame (numpy array)
frame_locks = {}         # cam_id -> threading.Lock for output_frames
runtime_states = {}      # cam_id -> dict (same schema as old runtime_state)
state_locks = {}         # cam_id -> threading.Lock for runtime_states
camera_ids = []          # ordered list of active camera IDs


def _make_runtime_state():
    """Create a fresh runtime_state dict for one camera."""
    return {
        "ts": 0.0,
        "frame_idx": 0,
        "source": "",
        "person_count": 0,
        "total_visitors": 0,
        "avg_confidence": 0.0,
        "confidences": [],
        "centers": [],
        "influx": {
            "last_person_write_ts": 0.0,
            "bucket": "",
            "org": "",
            "write_latency_ms": 0.0
        },
        "performance": {
            "fps": 0.0,
            "display_fps": 0.0,
            "inference_ms": 0.0
        }
    }


def _init_camera_state(cam_id):
    """Register per-camera global state containers."""
    output_frames[cam_id] = None
    frame_locks[cam_id] = threading.Lock()
    runtime_states[cam_id] = _make_runtime_state()
    state_locks[cam_id] = threading.Lock()


# ---- Flask video stream ------------------------------------------------

def generate(cam_id):
    last_frame_id = None
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, STREAM_QUALITY]
    lock = frame_locks.get(cam_id)
    if lock is None:
        return

    frame_counter = 0

    while True:
        with lock:
            frame = output_frames.get(cam_id)
        if frame is None:
            time.sleep(0.02)
            continue
        fid = id(frame)
        if fid == last_frame_id:
            time.sleep(0.005)
            continue
        last_frame_id = fid
        frame_counter += 1

        # 跳帧优化：减少编码压力
        if STREAM_SKIP_FRAMES > 1 and frame_counter % STREAM_SKIP_FRAMES != 0:
            continue

        # 尝试使用 TurboJPEG（比 OpenCV 快 2-4 倍）
        if turbo_jpeg is not None:
            try:
                jpeg_bytes = turbo_jpeg.encode(frame, quality=STREAM_QUALITY)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Cache-Control: no-store\r\n\r\n' +
                       jpeg_bytes + b'\r\n')
                continue
            except Exception:
                pass  # 回退到 OpenCV

        (flag, encodedImage) = cv2.imencode(".jpg", frame, encode_params)
        if not flag:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Cache-Control: no-store\r\n\r\n' +
               encodedImage.tobytes() + b'\r\n')


@app.route("/video_feed/<cam_id>")
def video_feed_cam(cam_id):
    if cam_id not in output_frames:
        return f"Camera {cam_id} not found", 404
    resp = Response(generate(cam_id), mimetype="multipart/x-mixed-replace; boundary=frame")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.route("/video_feed")
def video_feed():
    """Backward-compatible: return first camera stream."""
    if not camera_ids:
        return "No cameras available", 503
    cam_id = camera_ids[0]
    resp = Response(generate(cam_id), mimetype="multipart/x-mixed-replace; boundary=frame")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.route("/")
def index():
    streams = ""
    for cid in camera_ids:
        streams += (f'<div style="display:inline-block;margin:8px;vertical-align:top">'
                    f'<h3>{cid}</h3>'
                    f'<img src="/video_feed/{cid}" style="max-width:640px">'
                    f'</div>')
    if not streams:
        streams = "<p>No cameras detected</p>"
    return f"<h1>YOLO11n Multi-Camera Heatmap</h1>{streams}"


@app.route("/cameras")
def cameras_list():
    return jsonify({"cameras": camera_ids})


@app.route("/debug.json")
def debug_json():
    all_states = {}
    for cid in camera_ids:
        with state_locks[cid]:
            all_states[cid] = dict(runtime_states[cid])
    return jsonify(all_states)


@app.route("/debug")
def debug_page():
    columns = ""
    for cid in camera_ids:
        with state_locks[cid]:
            st = dict(runtime_states[cid])
        s = json.dumps(st, ensure_ascii=False, indent=2)
        columns += (f'<div style="flex:1;min-width:280px;margin:0 4px">'
                    f'<h3 style="margin:4px 0">{cid}</h3>'
                    f'<pre style="font-size:12px;margin:0;white-space:pre-wrap">{s}</pre></div>')
    return ("<html><head><meta charset='utf-8'><meta http-equiv='refresh' content='1'>"
            "<title>Debug</title></head><body style='margin:4px'>"
            "<div style='display:flex;flex-wrap:wrap'>" + columns +
            "</div></body></html>")


# ---- InfluxDB sender (with camera_id tag) --------------------------------

class InfluxDBSender:
    def __init__(self, url, token, org, bucket):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self._queue = queue.Queue(maxsize=40)
        self._worker = None
        self.connect()

    def connect(self):
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            from influxdb_client.client.write_api import SYNCHRONOUS
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self._worker = threading.Thread(target=self._write_worker, daemon=True)
            self._worker.start()
            print(f"成功连接到 InfluxDB: {self.url}")
        except Exception as e:
            print(f"连接 InfluxDB 失败: {e}")
            self.client = None

    def _write_worker(self):
        while True:
            item = self._queue.get()
            if item is None:
                break
            points = item
            try:
                self.write_api.write(bucket=self.bucket, record=points)
            except Exception as e:
                print(f"写入失败: {e}")
            self._queue.task_done()

    def send_person_count(self, count, camera_id="cam0", timestamp=None):
        if self.write_api is None:
            return False
        point = Point("person_count") \
            .tag("source", "yolo11n_camera") \
            .tag("device", "jetson") \
            .tag("camera", camera_id) \
            .field("count", int(count))
        if timestamp:
            point = point.time(timestamp)
        try:
            self._queue.put_nowait(point)
            return True
        except queue.Full:
            return False

    def send_all(self, count, avg_confidence, total_visitors, camera_id="cam0", timestamp=None):
        """合并写入 person_count 和 detection_details，减少网络往返"""
        if self.write_api is None:
            return False
        p1 = Point("person_count") \
            .tag("source", "yolo11n_camera") \
            .tag("device", "jetson") \
            .tag("camera", camera_id) \
            .field("count", int(count)) \
            .field("total_visitors", int(total_visitors))
        p2 = Point("detection_details") \
            .tag("source", "yolo11n_camera") \
            .tag("device", "jetson") \
            .tag("camera", camera_id) \
            .field("person_count", int(count)) \
            .field("avg_confidence", float(avg_confidence))
        if timestamp:
            p1 = p1.time(timestamp)
            p2 = p2.time(timestamp)
        try:
            self._queue.put_nowait([p1, p2])
            return True
        except queue.Full:
            return False

    def send_detection_details(self, count, avg_confidence, camera_id="cam0", timestamp=None):
        if self.write_api is None:
            return False
        point = Point("detection_details") \
            .tag("source", "yolo11n_camera") \
            .tag("device", "jetson") \
            .tag("camera", camera_id) \
            .field("person_count", int(count)) \
            .field("avg_confidence", float(avg_confidence))
        if timestamp:
            point = point.time(timestamp)
        try:
            self._queue.put_nowait(point)
            return True
        except queue.Full:
            return False

    def send_uptime(self, uptime_seconds, start_time=None):
        if self.write_api is None:
            return False
        point = Point("app_status") \
            .tag("source", "yolo11n_camera") \
            .tag("device", "jetson") \
            .field("uptime_seconds", float(uptime_seconds))
        if start_time:
            point = point.field("start_time", float(start_time))
        try:
            self._queue.put_nowait(point)
            return True
        except queue.Full:
            return False

    def close(self):
        if self._worker and self._worker.is_alive():
            self._queue.put(None)
            self._worker.join(timeout=3)
        if self.client:
            self.client.close()


# ---- MQTT publisher (optional) ---------------------------------------------

class MQTTPublisher:
    """Publishes detection data to MQTT broker for Node-RED / external consumers."""

    def __init__(self, host, port=1883):
        if not MQTT_AVAILABLE:
            raise RuntimeError("paho-mqtt not installed. Run: pip install paho-mqtt")
        self.host = host
        self.port = port
        self.client = mqtt_client.Client(client_id=f"jetson-yolo-{int(time.time())}")
        self._connected = False
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        try:
            self.client.connect(host, port, keepalive=60)
            self.client.loop_start()
            print(f"[MQTT] 正在连接 {host}:{port} ...")
        except Exception as e:
            print(f"[MQTT] 连接失败: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print(f"[MQTT] 已连接 {self.host}:{self.port}")
        else:
            print(f"[MQTT] 连接被拒绝, rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            print(f"[MQTT] 意外断开 (rc={rc}), 将自动重连")

    def publish_people_count(self, unique_count, total_visitors, camera_id="cam0"):
        """Publish people count to heatmap/{device_id}/people_count"""
        if not self._connected:
            return
        device_id = f"jetson-{camera_id}"
        topic = f"heatmap/{device_id}/people_count"
        payload = json.dumps({"unique_count": unique_count, "total_visitors": total_visitors})
        try:
            self.client.publish(topic, payload, qos=0)
        except Exception as e:
            print(f"[MQTT] publish_people_count 失败: {e}")

    def publish_detections(self, centers, width, height, camera_id="cam0"):
        """Publish each detection point as x_pct/y_pct (0-100) to heatmap/{device_id}/detections"""
        if not self._connected or not centers:
            return
        device_id = f"jetson-{camera_id}"
        topic = f"heatmap/{device_id}/detections"
        for (cx, cy) in centers:
            x_pct = int(round(cx / width * 100)) if width > 0 else 0
            y_pct = int(round(cy / height * 100)) if height > 0 else 0
            x_pct = max(0, min(100, x_pct))
            y_pct = max(0, min(100, y_pct))
            payload = json.dumps({"x_pct": x_pct, "y_pct": y_pct, "value": 1})
            try:
                self.client.publish(topic, payload, qos=0)
            except Exception as e:
                print(f"[MQTT] publish_detections 失败: {e}")
                break

    def close(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass


# ---- Heatmap generator (unchanged) ----------------------------------------

class HeatmapGenerator:
    def __init__(self, width, height, alpha=0.5, decay=0.95, ksize=51, scale=0.5):
        self.width = width
        self.height = height
        self.alpha = alpha
        self.decay = decay
        self.scale = scale
        self.hw = max(1, int(width * scale))
        self.hh = max(1, int(height * scale))
        self.heatmap = np.zeros((self.hh, self.hw), dtype=np.float32)
        if ksize % 2 == 0:
            ksize += 1
        ksize_scaled = max(3, int(ksize * scale))
        if ksize_scaled % 2 == 0:
            ksize_scaled += 1
        g = cv2.getGaussianKernel(ksize_scaled, -1)
        kernel = g @ g.T
        kernel = (kernel - kernel.min()) / (kernel.max() - kernel.min() + 1e-6)
        self.kernel = kernel.astype(np.float32)
        self.half = ksize_scaled // 2
        # Pre-allocate reusable buffers (avoid per-frame allocation ~240 times/sec)
        self._float_buf = np.zeros((self.hh, self.hw), dtype=np.float32)
        self._norm_buf = np.zeros((self.hh, self.hw), dtype=np.uint8)
        self._full_buf = np.zeros((height, width, 3), dtype=np.uint8)
        self._out_buf = np.zeros((height, width, 3), dtype=np.uint8)

    def update(self, centers):
        self.heatmap *= self.decay
        h = self.half
        k = self.kernel
        for x, y in centers:
            sx = int(x * self.scale)
            sy = int(y * self.scale)
            if 0 <= sx < self.hw and 0 <= sy < self.hh:
                x0 = max(0, sx - h)
                y0 = max(0, sy - h)
                x1 = min(self.hw, sx + h + 1)
                y1 = min(self.hh, sy + h + 1)
                kx0 = h - (sx - x0)
                ky0 = h - (sy - y0)
                kx1 = kx0 + (x1 - x0)
                ky1 = ky0 + (y1 - y0)
                self.heatmap[y0:y1, x0:x1] += k[ky0:ky1, kx0:kx1]
        np.clip(self.heatmap, 0, 1.0, out=self.heatmap)

    def apply_to_frame(self, frame):
        np.multiply(self.heatmap, 255, out=self._float_buf)
        np.copyto(self._norm_buf, self._float_buf, casting='unsafe')
        heatmap_color = cv2.applyColorMap(self._norm_buf, cv2.COLORMAP_JET)
        cv2.resize(heatmap_color, (self.width, self.height),
                   dst=self._full_buf, interpolation=cv2.INTER_LINEAR)
        cv2.addWeighted(frame, 1 - self.alpha, self._full_buf, self.alpha, 0,
                        dst=self._out_buf)
        return self._out_buf


class CentroidTracker:
    """质心跟踪器：用于统计当天出现过的不同个体数（真实人流量）。

    设计要点：
    1. 不活跃 ID 保留 5 分钟用于回匹配，检测不稳定不会虚增 ID
    2. 新质心需要连续出现 confirm_frames 次才算新人，过滤误检
    """

    def __init__(self, max_distance=400, confirm_frames=5):
        self.next_id = 0
        self.active = {}        # track_id -> (cx, cy)  当前帧在场的
        self.inactive = {}      # track_id -> (cx, cy)  最后已知位置
        self.inactive_ts = {}   # track_id -> timestamp
        self.pending = {}       # pending_key -> {"center": (cx,cy), "count": int}
        self.max_distance = max_distance
        self.confirm_frames = confirm_frames  # 新人需要连续确认的帧数
        self.seen_ids = set()
        self._inactive_ttl = 300

    def update(self, centers):
        now = time.time()

        # 清理过期不活跃 ID
        expired = [oid for oid, ts in self.inactive_ts.items()
                   if now - ts > self._inactive_ttl]
        for oid in expired:
            del self.inactive[oid]
            del self.inactive_ts[oid]

        if len(centers) == 0:
            for oid, pos in self.active.items():
                self.inactive[oid] = pos
                self.inactive_ts[oid] = now
            self.active.clear()
            # pending 全部重置（没检测到任何人）
            self.pending.clear()
            return self.active

        # 1) 匹配活跃对象
        unmatched_cols = list(range(len(centers)))
        new_active = {}

        if self.active:
            act_ids = list(self.active.keys())
            act_centers = [self.active[oid] for oid in act_ids]
            m_rows, m_cols = self._match(act_centers, centers)
            for row, col in zip(m_rows, m_cols):
                new_active[act_ids[row]] = centers[col]
                unmatched_cols.remove(col)
            for row in range(len(act_ids)):
                if row not in m_rows:
                    oid = act_ids[row]
                    self.inactive[oid] = self.active[oid]
                    self.inactive_ts[oid] = now

        # 2) 未匹配质心 → 尝试匹配不活跃对象
        still_unmatched = []
        if unmatched_cols and self.inactive:
            inact_ids = list(self.inactive.keys())
            inact_centers = [self.inactive[oid] for oid in inact_ids]
            remaining = [centers[c] for c in unmatched_cols]
            m_rows, m_cols = self._match(inact_centers, remaining)
            reactivated = set()
            for row, col in zip(m_rows, m_cols):
                oid = inact_ids[row]
                new_active[oid] = remaining[col]
                reactivated.add(col)
                del self.inactive[oid]
                del self.inactive_ts[oid]
            for idx in range(len(unmatched_cols)):
                if idx not in reactivated:
                    still_unmatched.append(unmatched_cols[idx])
        else:
            still_unmatched = unmatched_cols

        # 3) 剩余未匹配 → pending 确认（连续出现多帧才算新人）
        new_pending = {}
        for col in still_unmatched:
            c = centers[col]
            matched_pending = False
            for pk, pv in self.pending.items():
                dx = c[0] - pv["center"][0]
                dy = c[1] - pv["center"][1]
                if np.sqrt(dx*dx + dy*dy) < self.max_distance:
                    new_count = pv["count"] + 1
                    if new_count >= self.confirm_frames:
                        # 确认为新人
                        self._register(c)
                        new_active[self.next_id - 1] = c
                    else:
                        new_pending[pk] = {"center": c, "count": new_count}
                    matched_pending = True
                    break
            if not matched_pending:
                # 全新位置，开始 pending
                pk = f"p{now}_{col}"
                new_pending[pk] = {"center": c, "count": 1}

        self.pending = new_pending
        self.active = new_active
        return self.active

    def _match(self, existing, new_centers):
        M = len(existing)
        N = len(new_centers)
        dists = np.zeros((M, N), dtype=np.float32)
        for i, (ox, oy) in enumerate(existing):
            for j, (nx, ny) in enumerate(new_centers):
                dists[i, j] = np.sqrt((ox - nx) ** 2 + (oy - ny) ** 2)
        matched_rows = set()
        matched_cols = set()
        row_order = dists.min(axis=1).argsort()
        for row in row_order:
            best_col = -1
            best_dist = self.max_distance
            for j in range(N):
                if j in matched_cols:
                    continue
                if dists[row, j] < best_dist:
                    best_dist = dists[row, j]
                    best_col = j
            if best_col >= 0 and row not in matched_rows:
                matched_rows.add(row)
                matched_cols.add(best_col)
        return matched_rows, matched_cols

    def _register(self, center):
        self.next_id += 1
        self.seen_ids.add(self.next_id)

    @property
    def total_visitors(self):
        return len(self.seen_ids)

    def reset_daily(self):
        self.seen_ids.clear()
        self.inactive.clear()
        self.inactive_ts.clear()
        self.pending.clear()
        self.next_id += 1


# ---- Camera class (with discover_cameras) ----------------------------------

class Camera:
    """支持 USB 摄像头、GMSL/CSI 摄像头（通过 GStreamer）和视频文件"""

    USB_PIPELINE = (
        "v4l2src device=/dev/video{idx} ! "
        "image/jpeg,width={w},height={h},framerate={fps}/1 ! "
        "jpegdec ! videoconvert ! video/x-raw,format=BGR ! "
        "appsink max-buffers=1 drop=true sync=false"
    )
    GMSL_PIPELINE = (
        "v4l2src device=/dev/video{idx} ! "
        "video/x-raw,format=YUYV,width={w},height={h},framerate={fps}/1 ! "
        "videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
    )
    ARGUS_PIPELINE = (
        "nvarguscamerasrc sensor-id={idx} ! "
        "video/x-raw(memory:NVMM),width={w},height={h},framerate={fps}/1 ! "
        "nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
        "video/x-raw,format=BGR ! appsink drop=1"
    )

    # GMSL 验证用的 GStreamer pipeline（低分辨率、短超时）
    _GMSL_PROBE_PIPELINE = (
        "v4l2src device=/dev/video{idx} num-buffers=1 ! "
        "video/x-raw,format=YUYV,width=640,height=480,framerate=15/1 ! "
        "videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
    )

    def __init__(self, source=0, width=1920, height=1080, fps=30, camera_type="auto"):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.camera_type = camera_type
        self.cap = None
        self._bg_ret = False
        self._bg_frame = None
        self._bg_lock = threading.Lock()
        self._bg_running = False
        self._bg_thread = None

    @staticmethod
    def _detect_camera_type(idx):
        """通过 /sys/class/video4linux 的设备名自动判断摄像头类型"""
        try:
            with open(f"/sys/class/video4linux/video{idx}/name") as f:
                name = f.read().strip().lower()
            if "tegra" in name or "vi-output" in name or "nv_cam" in name:
                return "gmsl"
            return "usb"
        except Exception:
            return "usb"

    @staticmethod
    def _probe_gmsl(idx, timeout=5.0):
        """尝试打开 GMSL 摄像头并读一帧来验证可用性。
        先尝试 GStreamer pipeline，失败则回退到直接 V4L2。"""
        # 1) GStreamer pipeline
        pipeline = Camera._GMSL_PROBE_PIPELINE.format(idx=idx)
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            start = time.time()
            while time.time() - start < timeout:
                ret, _ = cap.read()
                if ret:
                    cap.release()
                    return True
                time.sleep(0.1)
        cap.release()

        # GMSL 设备 GStreamer 失败则直接跳过，不回退 V4L2
        # （V4L2 回退会误判无摄像头接入的 CSI 节点为可用）
        return False

    @staticmethod
    def discover_cameras(max_cameras=4):
        """Scan /dev/video* and return indices of usable cameras (USB + GMSL).

        For USB cameras: opens directly with V4L2 and reads a frame.
        For GMSL cameras: uses GStreamer pipeline to verify.
        Returns a sorted list of integer indices, capped at *max_cameras*.
        """
        candidates = []
        for dev in sorted(globmod.glob("/dev/video*")):
            try:
                idx = int(dev.replace("/dev/video", ""))
            except ValueError:
                continue

            cam_type = Camera._detect_camera_type(idx)

            if cam_type == "gmsl":
                # GMSL: 用 GStreamer pipeline 验证
                print(f"探测 GMSL 摄像头: /dev/video{idx} ...")
                if Camera._probe_gmsl(idx):
                    candidates.append(idx)
                    print(f"  ✓ 发现 GMSL 摄像头: /dev/video{idx}")
                else:
                    print(f"  ✗ /dev/video{idx} GMSL 打开失败，跳过")
            else:
                # USB: 直接用 V4L2 验证
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        candidates.append(idx)
                        print(f"发现 USB 摄像头: /dev/video{idx}")
                else:
                    cap.release()

            if len(candidates) >= max_cameras:
                break

        return candidates

    # 向后兼容别名
    discover_usb_cameras = discover_cameras

    def _build_gstreamer_pipeline(self, idx):
        if self.camera_type == "argus":
            return self.ARGUS_PIPELINE.format(idx=idx, w=self.width, h=self.height, fps=self.fps)
        elif self.camera_type == "usb":
            return self.USB_PIPELINE.format(idx=idx, w=self.width, h=self.height, fps=self.fps)
        else:
            return self.GMSL_PIPELINE.format(idx=idx, w=self.width, h=self.height, fps=self.fps)

    def open(self):
        if isinstance(self.source, str) and self.source.isdigit():
            self.source = int(self.source)

        if isinstance(self.source, str) and "!" in self.source:
            self.camera_type = "gst"
            print(f"使用自定义 GStreamer pipeline: {self.source}")
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_GSTREAMER)
            if not self.cap.isOpened():
                print(f"GStreamer pipeline 打开失败: {self.source}")
                return False
            return True

        if isinstance(self.source, str) and self.source.startswith("rtsp://"):
            self.camera_type = "rtsp"
            pipeline = (
                f"rtspsrc location={self.source} latency=200 protocols=tcp ! "
                "rtph264depay ! h264parse ! avdec_h264 ! "
                "videoconvert ! video/x-raw,format=BGR ! "
                "appsink drop=1 max-buffers=2 sync=false"
            )
            print(f"[RTSP] GStreamer pipeline: {pipeline}")
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if self.cap.isOpened():
                print("[RTSP] GStreamer 连接成功")
                return True
            print(f"[RTSP] GStreamer 失败, 回退到 ffmpeg: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                print(f"无法打开 RTSP 流: {self.source}")
                return False
            return True

        if isinstance(self.source, str):
            self.camera_type = "file"
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                print(f"无法打开视频文件: {self.source}")
                return False
            return True

        idx = self.source
        if self.camera_type == "auto":
            detected = self._detect_camera_type(idx)
            print(f"自动检测摄像头类型: /dev/video{idx} → {detected}")
            self.camera_type = detected

        if self.camera_type in ("gmsl", "argus"):
            pipeline = self._build_gstreamer_pipeline(idx)
            print(f"使用 {self.camera_type.upper()} GStreamer pipeline: {pipeline}")
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if not self.cap.isOpened():
                print("GStreamer 打开失败，回退到 V4L2")
                self.cap = cv2.VideoCapture(idx)
        elif self.camera_type == "usb":
            # 优先用 GStreamer MJPG pipeline（appsink drop=true 避免帧积压）
            pipeline = self._build_gstreamer_pipeline(idx)
            print(f"USB GSTREAMER pipeline: {pipeline}")
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if not self.cap.isOpened():
                # 回退到 V4L2 + MJPG
                print("GStreamer 打开失败，回退到 V4L2 MJPG")
                self.cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                    actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                    actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"USB V4L2 MJPG: {actual_w}x{actual_h} @ {actual_fps:.0f}fps")
                else:
                    self.cap = cv2.VideoCapture(idx)
        else:
            self.cap = cv2.VideoCapture(idx)

        if not self.cap.isOpened():
            print(f"无法打开源: {self.source} (类型: {self.camera_type})")
            return False

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if self.camera_type != "file":
            self._start_bg_reader()
        return True

    def _start_bg_reader(self):
        self._bg_running = True
        self._bg_thread = threading.Thread(target=self._bg_read_loop, daemon=True)
        self._bg_thread.start()

    def _bg_read_loop(self):
        while self._bg_running:
            ret, frame = self.cap.read()
            with self._bg_lock:
                self._bg_ret = ret
                self._bg_frame = frame
            if not ret:
                time.sleep(0.01)

    def read(self):
        if self.cap is None:
            return False, None
        if self._bg_running:
            with self._bg_lock:
                ret = self._bg_ret
                frame = self._bg_frame
            if frame is not None:
                return ret, frame.copy()
            return self.cap.read()
        return self.cap.read()

    def release(self):
        self._bg_running = False
        if self._bg_thread:
            self._bg_thread.join(timeout=1)
        if self.cap:
            self.cap.release()

USBCamera = Camera


# ---- Inference worker (round-robin over multiple cameras) -----------------

def inference_worker(model, cameras_dict, device, half, imgsz, infer_results, infer_locks, running_flag):
    """Single inference thread: round-robin across all cameras.

    cameras_dict: {cam_id: Camera}
    infer_results: {cam_id: dict}
    infer_locks:   {cam_id: threading.Lock}
    """
    cam_ids = list(cameras_dict.keys())
    n = len(cam_ids)
    idx = 0
    frame_counts = {cid: 0 for cid in cam_ids}
    last_fps_time = time.time()
    last_gc_time = time.time()

    # Check CUDA availability once
    _has_cuda = False
    try:
        import torch
        _has_cuda = torch.cuda.is_available()
    except Exception:
        pass

    while running_flag[0]:
        cam_id = cam_ids[idx]
        idx = (idx + 1) % n
        camera = cameras_dict[cam_id]

        ret, frame = camera.read()
        if not ret:
            time.sleep(0.005)
            continue

        t0 = time.time()
        results = model.predict(source=frame, classes=[0], verbose=False,
                                device=device, half=half, imgsz=imgsz)
        dt = time.time() - t0

        count = 0
        confidences = []
        centers = []
        for r in results:
            for box in r.boxes:
                count += 1
                confidences.append(float(box.conf[0]))
                xyxy = box.xyxy[0]
                cx = int((xyxy[0].item() + xyxy[2].item()) / 2)
                cy = int((xyxy[1].item() + xyxy[3].item()) / 2)
                centers.append((cx, cy))
        del results

        with infer_locks[cam_id]:
            infer_results[cam_id]["count"] = count
            infer_results[cam_id]["confidences"] = confidences
            infer_results[cam_id]["centers"] = centers
            infer_results[cam_id]["inference_ms"] = dt * 1000

        frame_counts[cam_id] += 1
        now = time.time()
        elapsed = now - last_fps_time
        if elapsed >= 5.0:
            fps_info = []
            for cid in cam_ids:
                infer_fps = frame_counts[cid] / elapsed
                fps_info.append(f"{cid}={infer_fps:.1f}")
                with state_locks[cid]:
                    runtime_states[cid]["performance"]["fps"] = round(infer_fps, 1)
                    runtime_states[cid]["performance"]["inference_ms"] = round(
                        infer_results[cid].get("inference_ms", 0), 1)
            print(f"[推理] 每摄像头 FPS: {', '.join(fps_info)}, 推理耗时: {dt*1000:.1f}ms")
            frame_counts = {cid: 0 for cid in cam_ids}
            last_fps_time = now

        if now - last_gc_time >= 30:
            gc.collect()
            if _has_cuda:
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass
            # Clear YOLO predictor cache to prevent memory accumulation
            if hasattr(model, 'predictor') and model.predictor is not None:
                if hasattr(model.predictor, 'results'):
                    model.predictor.results = None
            last_gc_time = now


# ---- Display loop (one per camera, runs in its own thread) ----------------

def display_loop(cam_id, camera, infer_result, infer_lock, influx, args,
                 stream_w, stream_h, scale_x, scale_y, heatmap_gen, running_flag,
                 mqtt_publisher=None):
    """Per-camera display thread: reads frames, applies heatmap, pushes to Flask stream,
    and writes to InfluxDB."""
    tracker = CentroidTracker(max_distance=400)
    last_day = time.localtime().tm_mday
    last_send_time = time.time()
    last_status_send = last_send_time
    start_time = last_send_time

    disp_count = 0
    last_disp_fps_time = time.time()
    last_gc_time = time.time()
    TARGET_DT = 1.0 / 30.0
    prev_raw_centers = None  # 仅在推理结果变化时更新 tracker

    # Pre-allocate display frame buffer
    _small_buf = np.zeros((stream_h, stream_w, 3), dtype=np.uint8)

    while running_flag[0]:
        t_loop = time.time()

        ret, frame = camera.read()
        if not ret:
            time.sleep(0.01)
            continue

        cv2.resize(frame, (stream_w, stream_h), dst=_small_buf,
                   interpolation=cv2.INTER_LINEAR)
        del frame

        with infer_lock:
            person_count = infer_result["count"]
            confidences = list(infer_result["confidences"])
            raw_centers = list(infer_result["centers"])
            inference_ms = infer_result["inference_ms"]

        centers = [(int(x * scale_x), int(y * scale_y)) for x, y in raw_centers]

        # 仅在推理结果实际变化时更新跟踪器（避免 30fps 重复调用导致 disappeared 计数膨胀）
        if raw_centers != prev_raw_centers:
            tracker.update(raw_centers)
            prev_raw_centers = raw_centers

        if args.blur:
            for (cx, cy) in centers:
                bx1 = max(0, cx - stream_w // 20)
                by1 = max(0, cy - stream_h // 15)
                bx2 = min(stream_w, cx + stream_w // 20)
                by2 = min(stream_h, cy + stream_h // 15)
                roi = _small_buf[by1:by2, bx1:bx2]
                if roi.size > 0:
                    _small_buf[by1:by2, bx1:bx2] = cv2.GaussianBlur(roi, (31, 31), 10)
                cv2.rectangle(_small_buf, (bx1, by1), (bx2, by2), (0, 255, 0), 2)

        heatmap_gen.update(centers)
        disp = heatmap_gen.apply_to_frame(_small_buf)

        cv2.putText(disp, f"{cam_id} | Persons: {person_count} | Visitors: {tracker.total_visitors}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        with frame_locks[cam_id]:
            output_frames[cam_id] = disp.copy()

        if not args.headless:
            try:
                cv2.imshow(f'YOLO11n {cam_id}', disp)
                cv2.waitKey(1)
            except Exception:
                pass

        current_time = time.time()
        if current_time - last_send_time >= 0.2:
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            write_timestamp = int(current_time * 1e9)
            current_day = time.localtime().tm_mday
            if current_day != last_day:
                tracker.reset_daily()
                last_day = current_day
            total_visitors = tracker.total_visitors
            influx.send_all(person_count, avg_conf, total_visitors,
                            camera_id=cam_id, timestamp=write_timestamp)
            # MQTT publish (if enabled)
            if mqtt_publisher is not None:
                cam_w = int(camera.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if camera.cap else stream_w
                cam_h = int(camera.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if camera.cap else stream_h
                mqtt_publisher.publish_people_count(person_count, total_visitors, camera_id=cam_id)
                mqtt_publisher.publish_detections(raw_centers, cam_w, cam_h, camera_id=cam_id)
            last_send_time = current_time
            with state_locks[cam_id]:
                runtime_states[cam_id]["ts"] = current_time
                runtime_states[cam_id]["frame_idx"] = -1
                runtime_states[cam_id]["source"] = str(camera.source)
                runtime_states[cam_id]["person_count"] = int(person_count)
                runtime_states[cam_id]["total_visitors"] = int(total_visitors)
                runtime_states[cam_id]["avg_confidence"] = float(avg_conf)
                runtime_states[cam_id]["confidences"] = [float(c) for c in confidences]
                runtime_states[cam_id]["centers"] = [(int(x), int(y)) for (x, y) in raw_centers]
                runtime_states[cam_id]["influx"]["last_person_write_ts"] = float(last_send_time)
                runtime_states[cam_id]["influx"]["bucket"] = args.influx_bucket
                runtime_states[cam_id]["influx"]["org"] = args.influx_org
                runtime_states[cam_id]["influx"]["write_latency_ms"] = 0.0
                runtime_states[cam_id]["performance"]["inference_ms"] = round(inference_ms, 1)

        # Uptime only from first camera to avoid duplicates
        if cam_id == camera_ids[0] and current_time - last_status_send >= 10.0:
            influx.send_uptime(uptime_seconds=current_time - start_time, start_time=start_time)
            last_status_send = current_time

        disp_count += 1
        if current_time - last_disp_fps_time >= 10.0:
            disp_fps = disp_count / (current_time - last_disp_fps_time)
            print(f"[显示][{cam_id}] FPS: {disp_fps:.1f}")
            with state_locks[cam_id]:
                runtime_states[cam_id]["performance"]["display_fps"] = round(disp_fps, 1)
            disp_count = 0
            last_disp_fps_time = current_time

        # Periodic GC to prevent memory fragmentation
        if current_time - last_gc_time >= 60:
            gc.collect()
            last_gc_time = current_time

        elapsed = time.time() - t_loop
        sleep_t = TARGET_DT - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)


# ---- main() ---------------------------------------------------------------

def main():
    global camera_ids

    parser = argparse.ArgumentParser(description='YOLO11n Person Detection with InfluxDB & Grafana (multi-camera)')
    parser.add_argument('--source', type=str, default=os.getenv("VIDEO_SOURCE", "0"),
                        help='Video source: "auto" to discover USB cameras, or comma-separated indices like "0,2"')
    parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    parser.add_argument('--influx-url', type=str, default=os.getenv("INFLUX_URL", "http://localhost:8086"))
    parser.add_argument('--influx-token', type=str, default=os.getenv("INFLUX_TOKEN", "XcOGuS__bo4NKPEk0zBYlOBIRrhMXlufMaaVLgmFMObXts_mCF-43kgUWhHGKtQfTEuPITWcB57eI32qlGy5TA=="))
    parser.add_argument('--influx-org', type=str, default=os.getenv("INFLUX_ORG", "jetson"))
    parser.add_argument('--influx-bucket', type=str, default=os.getenv("INFLUX_BUCKET", "person_detection"))
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (no display)')
    parser.add_argument('--blur', action='store_true', help='Blur detected persons')
    parser.add_argument('--heatmap-alpha', type=float, default=0.5, help='Heatmap transparency (0-1)')
    parser.add_argument('--device', type=str, default=os.getenv("DEVICE", "auto"),
                        help='Device: auto/cpu/cuda or GPU index')
    parser.add_argument('--fp16', action='store_true', help='Enable FP16 on GPU')
    parser.add_argument('--heatmap-ksize', type=int, default=51, help='Heatmap Gaussian kernel size (odd)')
    parser.add_argument('--web-port', type=int, default=int(os.getenv("WEB_PORT", "5001")), help='Flask web server port')
    parser.add_argument('--camera-type', type=str, default=os.getenv("CAMERA_TYPE", "auto"),
                        choices=["auto", "usb", "gmsl", "argus", "gst"],
                        help='Camera type: auto/usb/gmsl/argus/gst')
    parser.add_argument('--imgsz', type=int, default=int(os.getenv("IMGSZ", "640")),
                        help='YOLO input size (smaller=faster, default: 640)')
    parser.add_argument('--stream-width', type=int, default=int(os.getenv("STREAM_WIDTH", "640")),
                        help='Display/stream width in pixels')
    parser.add_argument('--max-cameras', type=int, default=int(os.getenv("MAX_CAMERAS", "4")),
                        help='Maximum number of cameras to discover (default: 4)')
    parser.add_argument('--mqtt-host', type=str, default=os.getenv("MQTT_HOST", ""),
                        help='MQTT broker host (empty=disabled)')
    parser.add_argument('--mqtt-port', type=int, default=int(os.getenv("MQTT_PORT", "1883")),
                        help='MQTT broker port (default: 1883)')

    args = parser.parse_args()

    # --- Determine camera sources ---
    source_str = args.source.strip()
    source_indices = []

    if source_str.lower() == "auto":
        print(f"自动发现摄像头 (最多 {args.max_cameras} 个)...")
        source_indices = Camera.discover_cameras(max_cameras=args.max_cameras)
        if not source_indices:
            print("未发现可用 USB 摄像头，尝试 /dev/video0")
            source_indices = [0]
    elif "," in source_str:
        # Comma-separated indices: "0,2,4"
        for part in source_str.split(","):
            part = part.strip()
            if part.isdigit():
                source_indices.append(int(part))
            else:
                source_indices.append(part)  # could be a file path
    elif source_str.isdigit():
        source_indices = [int(source_str)]
    else:
        # Single file path or GStreamer pipeline
        source_indices = [source_str]

    # Cap at max_cameras
    source_indices = source_indices[:args.max_cameras]

    print(f"摄像头源列表: {source_indices}")

    # --- Init InfluxDB ---
    influx = InfluxDBSender(args.influx_url, args.influx_token, args.influx_org, args.influx_bucket)

    # --- Init MQTT (optional) ---
    mqtt_publisher = None
    if args.mqtt_host:
        if not MQTT_AVAILABLE:
            print("[MQTT] paho-mqtt 未安装，MQTT 功能已禁用。安装: pip install paho-mqtt")
        else:
            mqtt_publisher = MQTTPublisher(args.mqtt_host, args.mqtt_port)
    else:
        print("[MQTT] 未设置 MQTT_HOST，MQTT 发布已禁用")

    # --- Init YOLO model (single shared instance) ---
    env_model = os.getenv("YOLO_MODEL")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    engine_path = os.path.join(script_dir, 'yolo11n.engine')
    pt_path = os.path.join(script_dir, 'yolo11n.pt')
    if env_model and os.path.exists(env_model):
        model_path = env_model
    elif os.path.exists('/app/models/yolo11n.engine'):
        model_path = '/app/models/yolo11n.engine'
    elif os.path.exists('/app/yolo11n.engine'):
        model_path = '/app/yolo11n.engine'
    elif os.path.exists(engine_path):
        model_path = engine_path
    elif os.path.exists('/app/yolo11n.pt'):
        model_path = '/app/yolo11n.pt'
    elif os.path.exists(pt_path):
        model_path = pt_path
    else:
        model_path = 'yolo11n.pt'
    print(f"正在加载 YOLO11n 模型: {model_path}")
    model = YOLO(model_path)

    selected_device = args.device
    if selected_device == "auto":
        if os.path.exists('/dev/nvidia0'):
            selected_device = 0
        else:
            selected_device = "cpu"
    elif selected_device.isdigit():
        selected_device = int(selected_device)
    use_half = args.fp16 or (selected_device != "cpu")
    print(f"使用设备: {selected_device}, FP16: {use_half}, 输入尺寸: {args.imgsz}")

    # --- Open cameras and init per-camera state ---
    cameras_dict = {}       # cam_id -> Camera
    infer_results = {}      # cam_id -> dict
    infer_locks = {}        # cam_id -> Lock
    stream_params = {}      # cam_id -> (stream_w, stream_h, scale_x, scale_y)
    heatmap_gens = {}       # cam_id -> HeatmapGenerator

    for i, src in enumerate(source_indices):
        cam_id = f"cam{i}"
        camera = Camera(src, camera_type=args.camera_type)
        if not camera.open():
            print(f"[警告] 摄像头 {src} 打开失败，跳过 {cam_id}")
            continue

        cam_w = int(camera.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cam_h = int(camera.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[{cam_id}] 源: {src}, 分辨率: {cam_w}x{cam_h}")

        STREAM_W = args.stream_width
        STREAM_H = int(STREAM_W * cam_h / cam_w) if cam_w > 0 else int(STREAM_W * 9 / 16)
        sx = STREAM_W / cam_w if cam_w > 0 else 1.0
        sy = STREAM_H / cam_h if cam_h > 0 else 1.0

        cameras_dict[cam_id] = camera
        infer_results[cam_id] = {"count": 0, "confidences": [], "centers": [], "inference_ms": 0.0}
        infer_locks[cam_id] = threading.Lock()
        stream_params[cam_id] = (STREAM_W, STREAM_H, sx, sy)
        heatmap_gens[cam_id] = HeatmapGenerator(STREAM_W, STREAM_H, alpha=args.heatmap_alpha,
                                                  ksize=args.heatmap_ksize, scale=1.0)
        _init_camera_state(cam_id)
        camera_ids.append(cam_id)

    if not cameras_dict:
        print("没有可用摄像头，退出")
        sys.exit(1)

    print(f"已初始化 {len(cameras_dict)} 个摄像头: {camera_ids}")

    # --- Start Flask ---
    t = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=args.web_port,
                                                 debug=False, use_reloader=False, threaded=True))
    t.daemon = True
    t.start()

    # --- Start single inference thread (round-robin) ---
    running_flag = [True]
    infer_thread = threading.Thread(
        target=inference_worker,
        args=(model, cameras_dict, selected_device, use_half, args.imgsz,
              infer_results, infer_locks, running_flag),
        daemon=True
    )
    infer_thread.start()
    print("推理线程已启动 (round-robin)")

    # --- Start per-camera display loops ---
    display_threads = []
    for cam_id in camera_ids:
        sw, sh, sx, sy = stream_params[cam_id]
        dt = threading.Thread(
            target=display_loop,
            args=(cam_id, cameras_dict[cam_id], infer_results[cam_id], infer_locks[cam_id],
                  influx, args, sw, sh, sx, sy, heatmap_gens[cam_id], running_flag,
                  mqtt_publisher),
            daemon=True
        )
        dt.start()
        display_threads.append(dt)
        print(f"[{cam_id}] 显示线程已启动")

    print(f"所有线程已启动，{len(camera_ids)} 个摄像头运行中")

    # --- Memory monitoring thread ---
    def _mem_monitor():
        while running_flag[0]:
            try:
                with open('/proc/self/status') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            rss_kb = int(line.split()[1])
                            rss_mb = rss_kb / 1024
                            print(f"[内存] RSS: {rss_mb:.0f} MB")
                            break
            except Exception:
                pass
            time.sleep(300)  # every 5 minutes

    mem_t = threading.Thread(target=_mem_monitor, daemon=True)
    mem_t.start()

    # --- Main thread: wait for Ctrl-C ---
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止检测...")
    finally:
        running_flag[0] = False
        for cam_id, camera in cameras_dict.items():
            camera.release()
        influx.close()
        if mqtt_publisher is not None:
            mqtt_publisher.close()
        if not args.headless:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


if __name__ == '__main__':
    main()

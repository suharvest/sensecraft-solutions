"""Shared media boundary. Raw frames are only used inside inference."""
from pathlib import Path
from fractions import Fraction
import math
import json
import cv2
import numpy as np


def _mosaic(image, box):
    """Keep the protected core fully pixelated. Feathering extends outside that core."""
    height, width = image.shape[:2]
    x1, y1, x2, y2 = box
    x1, y1 = max(0, math.floor(x1)), max(0, math.floor(y1))
    x2, y2 = min(width, math.ceil(x2)), min(height, math.ceil(y2))
    if x2 <= x1 or y2 <= y1:
        return
    short_side = min(x2-x1, y2-y1)
    block = max(12, math.ceil(short_side/8))
    feather = max(2, min(16, round(short_side*.08)))
    left, top = max(0, x1-feather), max(0, y1-feather)
    right, bottom = min(width, x2+feather), min(height, y2+feather)
    patch = image[top:bottom, left:right]
    h, w = patch.shape[:2]
    small = cv2.resize(patch, (max(1, math.ceil(w/block)), max(1, math.ceil(h/block))), interpolation=cv2.INTER_AREA)
    pixelated = cv2.resize(small, (w,h), interpolation=cv2.INTER_NEAREST)
    core_left, core_top = x1-left, y1-top
    core_right, core_bottom = x2-left, y2-top
    # Blend only the outside border, keeping the protected core entirely pixelated.
    # Separable smoothstep weights avoid a full-ROI blur and float image allocation.
    def feather_weights(length, low, high):
        position = np.arange(length, dtype=np.float32)
        distance = np.maximum(np.maximum(low-position, position-(high-1)), 0)
        weight = np.clip(1-distance/feather, 0, 1)
        return weight*weight*(3-2*weight)
    horizontal = feather_weights(w, core_left, core_right)
    vertical = feather_weights(h, core_top, core_bottom)
    borders = [
        (slice(0,core_top), slice(0,w)),
        (slice(core_bottom,h), slice(0,w)),
        (slice(core_top,core_bottom), slice(0,core_left)),
        (slice(core_top,core_bottom), slice(core_right,w)),
    ]
    for rows, columns in borders:
        current = patch[rows,columns]
        if not current.size:
            continue
        alpha = (vertical[rows,None]*horizontal[None,columns])[...,None]
        target = pixelated[rows,columns]
        current[:] = np.rint(target.astype(np.float32)*alpha+current.astype(np.float32)*(1-alpha)).astype(np.uint8)
    core = (slice(core_top,core_bottom), slice(core_left,core_right))
    patch[core] = pixelated[core]


def _head_bounds(person, threshold):
    """Estimate a padded head from facial landmarks, with shoulders as a size reference."""
    x1,y1,x2,y2 = person['bbox_xyxy']
    width,height = x2-x1,y2-y1
    keypoints = person.get('keypoints', [])
    def valid(point):
        return (point.get('x') is not None and point.get('y') is not None
                and math.isfinite(point['x']) and math.isfinite(point['y'])
                and (point.get('confidence') or 0) >= threshold
                and x1-width*.1 <= point['x'] <= x2+width*.1
                and y1-height*.1 <= point['y'] <= y2)
    face = [point for point in keypoints[:5] if valid(point) and point['y'] <= y1+height*.6]
    shoulders = [point for point in keypoints[5:7] if valid(point)]
    if len(face) < 2 or (len(face) < 3 and len(shoulders) < 2):
        return person['bbox_xyxy']
    xs,ys = [point['x'] for point in face],[point['y'] for point in face]
    shoulder_span = abs(shoulders[1]['x']-shoulders[0]['x']) if len(shoulders)==2 else 0
    head_width = max(max(xs)-min(xs), width*.22, height*.11, shoulder_span*.5)
    # Facial span can cover eyes alone or both ears. Expand it before sizing the core.
    head_width = max(head_width, (max(xs)-min(xs))*1.7)
    center = (min(xs)+max(xs))/2
    return [center-head_width*.65, min(ys)-head_width*.75,
            center+head_width*.65, max(ys)+head_width*.55]


def protect_frame(frame, persons, config, *, reliable=True):
    image = frame.copy()
    if not config['privacy']['enabled']:
        return image
    if not reliable or persons is None:
        image[:] = (38, 44, 42)
        return image
    for person in persons:
        box = person.get('bbox_xyxy')
        if (not box or len(box) != 4 or not all(math.isfinite(v) for v in box)
                or box[2] <= box[0] or box[3] <= box[1]):
            image[:] = (38, 44, 42)
            return image
        _mosaic(image, _head_bounds(person, config.get('privacy_keypoint_confidence', config.get('keypoint_confidence', .4))))
    return image


def write_image(path, frame, store, persons=None, *, reliable=False):
    """Diagnostic callers without matched detections receive a fully masked image."""
    with store.output_policy() as config:
        image = protect_frame(frame, persons, config, reliable=reliable)
        if not cv2.imwrite(str(path), image):
            raise OSError('image encoding failed')


class RedactedRecorder:
    """H.264 MP4 segments with original media timestamps, including sample gaps."""
    def __init__(self, directory, prefix='recording', sample_hz=5):
        from .video import Gst
        self.Gst = Gst
        self.directory = Path(directory)
        self.prefix = prefix
        self.sample_hz = sample_hz
        self.pipeline = None
        self.last_pts = None
        self.origin = None
        self.revision = None
        self.segment = 0

    def _open(self, frame):
        Gst = self.Gst
        height, width = frame.shape[:2]
        pipeline = Gst.parse_launch(
            'appsrc name=frames format=time is-live=false block=true '
            '! queue max-size-buffers=2 max-size-bytes=0 max-size-time=0 '
            '! videoconvert ! video/x-raw,format=I420 '
            '! nvvidconv ! video/x-raw(memory:NVMM),format=NV12 '
            '! nvv4l2h264enc bitrate=4000000 insert-sps-pps=true iframeinterval=20 '
            '! h264parse ! splitmuxsink name=record max-size-time=60000000000')
        source = pipeline.get_by_name('frames')
        rate = Fraction(str(self.sample_hz)).limit_denominator(1000)
        source.set_property('caps', Gst.Caps.from_string(
            f'video/x-raw,format=BGR,width={width},height={height},framerate={rate.numerator}/{rate.denominator}'))
        pipeline.get_by_name('record').set_property('location', str(self.directory/f'{self.prefix}-{self.segment}-%05d.mp4'))
        if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            pipeline.set_state(Gst.State.NULL)
            raise RuntimeError('redacted recorder could not start')
        self.pipeline, self.source = pipeline, source
        self.size = (width, height)
        self.segment += 1

    def write(self, frame, timestamp_ns, config, persons, *, reliable=True):
        Gst = self.Gst
        if self.pipeline and (self.size != (frame.shape[1], frame.shape[0])
                              or self.revision != config['revision']
                              or timestamp_ns-self.origin >= 60000000000
                              or (self.last_pts is not None and timestamp_ns-self.origin <= self.last_pts)):
            self.close()
        image = protect_frame(frame, persons, config, reliable=reliable)
        if self.pipeline is None:
            self._open(image)
            self.revision = config['revision']
            self.origin = timestamp_ns
            self.last_pts = None
            with (self.directory/'recording-index.jsonl').open('a') as index:
                index.write(json.dumps(dict(prefix=f'{self.prefix}-{self.segment-1}',
                                            source_origin_ns=str(timestamp_ns),
                                            config_revision=config['revision'],
                                            privacy_applied=config['privacy']['enabled']))+'\n')
        relative = timestamp_ns-self.origin
        buffer = Gst.Buffer.new_allocate(None, image.nbytes, None)
        buffer.fill(0, np.ascontiguousarray(image).tobytes())
        buffer.pts = buffer.dts = int(relative)
        buffer.duration = int(1e9/self.sample_hz)
        if self.source.emit('push-buffer', buffer) != Gst.FlowReturn.OK:
            raise RuntimeError('redacted recording write failed')
        self.last_pts = relative
        message = self.pipeline.get_bus().timed_pop_filtered(0, Gst.MessageType.ERROR)
        if message:
            raise RuntimeError('redacted recording pipeline error')

    def close(self):
        if self.pipeline is None:
            return
        pipeline, self.pipeline = self.pipeline, None
        self.source.emit('end-of-stream')
        message = pipeline.get_bus().timed_pop_filtered(10*self.Gst.SECOND, self.Gst.MessageType.EOS | self.Gst.MessageType.ERROR)
        pipeline.set_state(self.Gst.State.NULL)
        if message is None or message.type == self.Gst.MessageType.ERROR:
            raise RuntimeError('redacted recording finalization failed')

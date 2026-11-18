import os, time, threading, uuid, re
import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo
Gst.init(None)

def pts_or_none(value):
    return None if value == Gst.CLOCK_TIME_NONE else int(value)

def copy_bgrx(data, width, height, stride, offset=0):
    # nvvidconv cannot emit packed BGR; convert the BGRx view here instead of
    # paying for a CPU videoconvert pass over every decoded frame.
    if stride < width * 4:
        raise ValueError('expected a BGRx buffer')
    view = np.ndarray((height, width, 4), np.uint8, buffer=data, offset=offset, strides=(stride, 4, 1))
    return cv2.cvtColor(view, cv2.COLOR_BGRA2BGR)

def select_video_stream(caps, codec):
    info = caps.get_structure(0)
    return info.get_string('media') == 'video' and info.get_string('encoding-name') == codec.upper()


class VideoReader:
    def __init__(self, source, codec='h264', rtsp=False, queue_limit=1, timeout=10, record_path=None,
                 usb_format=None):
        if codec not in ('h264', 'h265') or queue_limit < 1:
            raise ValueError('invalid codec or queue limit')
        if usb_format not in (None, 'yuyv', 'mjpeg', 'h264') or (rtsp and usb_format):
            raise ValueError('invalid USB format')
        if usb_format and record_path:
            raise ValueError('USB recording is not supported by this reader')
        self.timeout = timeout
        self.condition = threading.Condition()
        self.session_id = uuid.uuid4().hex
        self.received = self.dropped = self.consumed = 0
        self.latest = None
        self.last_rx_ns = None
        self.last_meta = {}
        self.stream_info = {}
        self.duplicate_pts = 0
        self.last_pts = None
        self.sample_error = None
        self.closed = False
        self.rtsp = rtsp
        self.codec = codec
        self.selected_stream = None
        self.rtp_links = {}
        self.extra_ssrc_links = 0
        self.live = rtsp or usb_format is not None
        if rtsp:
            prefix = ('rtspsrc name=source protocols=tcp latency=100 ! rtpfunnel name=video_funnel '
                      f'! application/x-rtp,media=video,encoding-name={codec.upper()},clock-rate=90000 ! rtp{codec}depay')
            decoder = f'{codec}parse ! nvv4l2decoder ! nvvidconv'
        elif usb_format:
            prefix = 'v4l2src name=source do-timestamp=true'
            decoder = {
                'yuyv': 'video/x-raw,format=YUY2 ! videoconvert',
                'mjpeg': 'image/jpeg ! jpegdec ! videoconvert',
                'h264': 'video/x-h264 ! h264parse ! nvv4l2decoder ! nvvidconv',
            }[usb_format]
        else:
            prefix = 'filesrc name=source ! qtdemux'
            decoder = f'{codec}parse ! nvv4l2decoder ! nvvidconv'
        queue = f'queue max-size-buffers={queue_limit} max-size-bytes=0 max-size-time=0'
        if self.live:
            queue += ' leaky=downstream'
        recording = ''
        if record_path:
            recording = f' ! tee name=encoded encoded. ! queue max-size-buffers=60 max-size-bytes=0 max-size-time=0 ! {codec}parse ! splitmuxsink name=rec max-size-time=60000000000 encoded. ! queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream'
        if recording:
            decoder = decoder.replace(f'{codec}parse', f'{codec}parse{recording}', 1)
        pipeline = f'{prefix} ! {decoder} ! video/x-raw,format=BGRx ! {queue} ! appsink name=sink sync=false max-buffers={queue_limit} drop={str(self.live).lower()}'
        self.pipeline = Gst.parse_launch(pipeline)
        source_element = self.pipeline.get_by_name('source')
        source_element.set_property('device' if usb_format else 'location', source)
        if rtsp:
            source_element.connect('select-stream', self._select_stream)
            source_element.connect('pad-added', self._link_rtsp_pad)
            source_element.connect('pad-removed', self._unlink_rtsp_pad)
        if record_path:
            self.pipeline.get_by_name('rec').set_property('location', record_path)
        self.sink = self.pipeline.get_by_name('sink')
        if self.live:
            self.sink.set_property('emit-signals', True)
            self.sink.connect('new-sample', self._on_sample)
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.close(); raise RuntimeError('pipeline start failed')

    def _select_stream(self, source, index, caps):
        if not select_video_stream(caps, self.codec):
            return False
        if self.selected_stream is None:
            self.selected_stream = index
        return self.selected_stream == index

    def _link_rtsp_pad(self, source, pad):
        # parse_launch connects the first RTP pad. This camera also introduces
        # another SSRC in the selected track, which needs its own funnel input.
        if self.closed or pad.is_linked():
            return
        caps = pad.get_current_caps() or pad.query_caps(None)
        if caps is None or not select_video_stream(caps, self.codec):
            return
        funnel = self.pipeline.get_by_name('video_funnel')
        sink = funnel.request_pad_simple('sink_%u')
        if sink is None:
            self.sample_error = 'unable to allocate RTP funnel input'
            return
        if pad.link(sink) != Gst.PadLinkReturn.OK:
            funnel.release_request_pad(sink)
            self.sample_error = 'unable to link selected RTP source'
            return
        self.rtp_links[pad.name] = (funnel, sink)
        self.extra_ssrc_links += 1

    def _unlink_rtsp_pad(self, source, pad):
        link = self.rtp_links.pop(pad.name, None)
        if link is not None:
            funnel, sink = link
            pad.unlink(sink)
            funnel.release_request_pad(sink)

    def _unpack(self, sample):
        buffer = sample.get_buffer(); info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
        fps = sample.get_caps().get_structure(0).get_fraction('framerate')
        self.stream_info = {'width': info.width, 'height': info.height, 'fps_numerator': fps[1] if fps[0] else None, 'fps_denominator': fps[2] if fps[0] else None}
        ok, mapped = buffer.map(Gst.MapFlags.READ)
        if not ok: raise RuntimeError('unable to map buffer')
        try:
            image = copy_bgrx(mapped.data, info.width, info.height, info.stride[0], info.offset[0])
        finally:
            buffer.unmap(mapped)
        return image, pts_or_none(buffer.pts), time.monotonic_ns()

    def _on_sample(self, sink):
        sample = sink.emit('pull-sample')
        try:
            packet = self._unpack(sample)
            with self.condition:
                if self.closed: return Gst.FlowReturn.OK
                self.received += 1
                if packet[1] is not None and self.last_pts == packet[1]:
                    self.duplicate_pts += 1
                    return Gst.FlowReturn.OK
                if self.latest is not None: self.dropped += 1
                if packet[1] is not None and self.last_pts is not None and packet[1] < self.last_pts:
                    self.session_id = uuid.uuid4().hex
                self.last_pts = packet[1]
                self.last_rx_ns = packet[2]
                self.latest = (packet, {'session_id': self.session_id, 'receive_sequence': self.received})
                self.condition.notify_all()
            return Gst.FlowReturn.OK
        except Exception as exc:
            self.sample_error = type(exc).__name__ + ': ' + str(exc)
            return Gst.FlowReturn.ERROR

    def snapshot(self):
        with self.condition:
            return {'session_id': self.session_id, 'received_frames': self.received,
                    'overwritten_frames': self.dropped, 'duplicate_pts_frames': self.duplicate_pts, 'consumed_frames': self.consumed,
                    'queue_depth': int(self.latest is not None), 'last_rx_monotonic_ns': self.last_rx_ns}

    def read(self):
        if getattr(self, 'live', getattr(self, 'rtsp', False)):
            deadline = time.monotonic() + self.timeout
            with self.condition:
                while self.latest is None and not self.closed:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0: raise TimeoutError('no new decoded frame')
                    self.condition.wait(min(remaining, .25))
                    msg = self.pipeline.get_bus().timed_pop_filtered(0, Gst.MessageType.ERROR | Gst.MessageType.EOS)
                    if msg:
                        if msg.type == Gst.MessageType.ERROR:
                            err, debug = msg.parse_error()
                            raise RuntimeError(re.sub(r'rtsp[s]?://[^\s]+', 'rtsp://<redacted>',
                                                      err.message + '; ' + str(debug or '')[:600] + ('; sample: '+self.sample_error if self.sample_error else '')))
                        raise RuntimeError('stream EOS')
                if self.closed: return None
                packet, self.last_meta = self.latest
                self.latest = None; self.consumed += 1
                return packet

        sample = self.sink.emit('try-pull-sample', int(self.timeout * Gst.SECOND))
        if sample is None:
            msg = self.pipeline.get_bus().timed_pop_filtered(0, Gst.MessageType.ERROR | Gst.MessageType.EOS)
            if msg and msg.type == Gst.MessageType.ERROR:
                err, _ = msg.parse_error(); raise RuntimeError(f'video pipeline error: {err.domain} {err.code}')
            if self.sink.get_property('eos') or (msg and msg.type == Gst.MessageType.EOS): return None
            raise TimeoutError('video frame timeout')
        packet = self._unpack(sample)
        self.received += 1; self.consumed += 1; self.last_rx_ns = packet[2]
        self.last_meta = {'session_id': self.session_id, 'receive_sequence': self.received}
        return packet

    def close(self):
        with self.condition:
            self.closed = True; self.latest = None; self.condition.notify_all()
        if self.pipeline.get_by_name('rec'):
            self.pipeline.send_event(Gst.Event.new_eos())
            self.pipeline.get_bus().timed_pop_filtered(5*Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        try:
            self.pipeline.set_state(Gst.State.NULL)
        finally:
            for funnel, pad in list(self.rtp_links.values()):
                funnel.release_request_pad(pad)
            self.rtp_links.clear()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

import unittest
from unittest.mock import MagicMock, patch
from jetson_worktime.video import Gst, VideoReader, copy_bgrx, pts_or_none, select_video_stream

class VideoTests(unittest.TestCase):
 def test_bgrx_stride_and_lifetime(self):
  b=bytearray(64)
  b[2:14]=bytes([1,2,3,255,4,5,6,255,7,8,9,255])
  b[18:30]=bytes([10,11,12,255,13,14,15,0,16,17,18,255])
  a=copy_bgrx(b,3,2,16,2)
  self.assertEqual(a.shape,(2,3,3))
  self.assertEqual(a.dtype.name,'uint8')
  self.assertTrue(a.flags['C_CONTIGUOUS'])
  self.assertEqual(a.ravel().tolist(),list(range(1,19)))
  b[2]=200;self.assertEqual(a[0,0,0],1)
 def test_rtsp_selects_only_the_configured_video_track(self):
  video=Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H265')
  audio=Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=PCMA')
  self.assertTrue(select_video_stream(video,'h265'))
  self.assertFalse(select_video_stream(audio,'h265'))
  self.assertFalse(select_video_stream(video,'h264'))
 def test_pts(self):
  self.assertIsNone(pts_or_none(Gst.CLOCK_TIME_NONE));self.assertEqual(pts_or_none(123),123)
 def test_rtsp_funnel_accepts_extra_ssrc_and_releases_its_pad(self):
  pipeline=MagicMock()
  pipeline.set_state.return_value=Gst.StateChangeReturn.SUCCESS
  caps=Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H265')
  with patch('jetson_worktime.video.Gst.parse_launch',return_value=pipeline) as parse:
   reader=VideoReader('rtsp://private',codec='h265',rtsp=True)
  self.assertIn('rtpfunnel',parse.call_args.args[0])
  self.assertTrue(reader._select_stream(None,0,caps))
  self.assertFalse(reader._select_stream(None,1,caps))
  pad=MagicMock();pad.name='recv_rtp_src_0_0_98'
  pad.is_linked.return_value=False;pad.get_current_caps.return_value=caps
  pad.link.return_value=Gst.PadLinkReturn.OK
  reader._link_rtsp_pad(None,pad)
  self.assertEqual(reader.extra_ssrc_links,1)
  reader._unlink_rtsp_pad(None,pad)
  self.assertEqual(reader.rtp_links,{})
  pipeline.get_by_name('video_funnel').release_request_pad.assert_called_once()
 def test_rtsp_funnel_rejects_nonvideo_and_releases_failed_link(self):
  reader=VideoReader.__new__(VideoReader)
  reader.closed=False;reader.codec='h265';reader.pipeline=MagicMock();reader.rtp_links={}
  reader.extra_ssrc_links=0;reader.sample_error=None
  pad=MagicMock();pad.name='source';pad.is_linked.return_value=False
  pad.get_current_caps.return_value=Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=PCMA')
  reader._link_rtsp_pad(None,pad)
  reader.pipeline.get_by_name.assert_not_called()
  pad.get_current_caps.return_value=Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H265')
  pad.link.return_value=Gst.PadLinkReturn.NOFORMAT
  reader._link_rtsp_pad(None,pad)
  reader.pipeline.get_by_name('video_funnel').release_request_pad.assert_called_once()
  self.assertEqual(reader.rtp_links,{})
 def test_bad_codec(self):
  with self.assertRaises(ValueError): VideoReader('x',codec='bad')
 def test_usb_formats_use_v4l2_and_live_latest_frame(self):
  for name,caps in [('yuyv','format=YUY2'),('mjpeg','image/jpeg'),('h264','video/x-h264')]:
   pipeline=MagicMock()
   pipeline.set_state.return_value=Gst.StateChangeReturn.SUCCESS
   with self.subTest(format=name), patch('jetson_worktime.video.Gst.parse_launch',return_value=pipeline) as parse:
    reader=VideoReader('/dev/video0',usb_format=name)
    self.assertTrue(reader.live)
    self.assertIn('v4l2src',parse.call_args.args[0])
    self.assertIn(caps,parse.call_args.args[0])
    self.assertIn('leaky=downstream',parse.call_args.args[0])
    pipeline.get_by_name('source').set_property.assert_any_call('device','/dev/video0')
  with self.assertRaises(ValueError):VideoReader('/dev/video0',usb_format='unknown')
  with self.assertRaises(ValueError):VideoReader('/dev/video0',rtsp=True,usb_format='mjpeg')
 def test_missing_input(self):
  with self.assertRaises(RuntimeError):
   with VideoReader('/definitely/missing.mp4',timeout=2) as r:r.read()
 def test_timeout(self):
  class Sink:
   def emit(self,*a):return None
   def get_property(self,*a):return False
  class Bus:
   def timed_pop_filtered(self,*a):return None
  class Pipeline:
   def get_bus(self):return Bus()
  r=VideoReader.__new__(VideoReader);r.sink=Sink();r.pipeline=Pipeline();r.timeout=.01
  with self.assertRaises(TimeoutError):r.read()
if __name__=='__main__':unittest.main()

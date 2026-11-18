import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import cv2
import numpy as np
from jetson_worktime.media import RedactedRecorder, protect_frame


class RecordingTests(unittest.TestCase):
    def test_timestamps_final_frame_and_segment_finalization(self):
        config = dict(revision=0, privacy={'enabled':True})
        frame = np.full((240,320,3),180,np.uint8)
        timestamps = [0,200000000,1700000000,61000000000,61200000000]
        with tempfile.TemporaryDirectory() as directory:
            recorder = RedactedRecorder(directory, sample_hz=5)
            try:
                for timestamp in timestamps:
                    recorder.write(frame,timestamp,config,None,reliable=False)
            finally:
                recorder.close()
            files = sorted(Path(directory).glob('*.mp4'))
            self.assertGreaterEqual(len(files),2)
            frames = 0
            total_span = 0
            for path in files:
                report = json.loads(subprocess.check_output([
                    'ffprobe','-v','error','-select_streams','v:0','-show_frames',
                    '-show_entries','frame=best_effort_timestamp_time','-of','json',str(path)]))
                times = [float(row['best_effort_timestamp_time']) for row in report['frames']]
                frames += len(times)
                self.assertTrue(all(a < b for a,b in zip(times,times[1:])))
                if len(times)>1:
                    total_span += times[-1]-times[0]
                capture = cv2.VideoCapture(str(path))
                ok, image = capture.read()
                capture.release()
                self.assertTrue(ok)
                self.assertLess(float(np.abs(image.astype(float)-[38,44,42]).mean()),8)
            self.assertEqual(frames,len(timestamps))
            self.assertGreater(total_span,1.5)

    def test_person_mosaic_survives_h264_recording(self):
        frame=np.random.default_rng(4).integers(0,255,(240,320,3),dtype=np.uint8)
        config=dict(revision=0,privacy={'enabled':True})
        persons=[dict(bbox_xyxy=[40,20,180,220],keypoints=[])]
        expected=protect_frame(frame,persons,config)
        with tempfile.TemporaryDirectory() as directory:
            recorder=RedactedRecorder(directory)
            try:
                recorder.write(frame,0,config,persons)
                recorder.write(frame,200000000,config,persons)
            finally:
                recorder.close()
            capture=cv2.VideoCapture(str(next(Path(directory).glob('*.mp4'))))
            ok,decoded=capture.read()
            capture.release()
            self.assertTrue(ok)
            self.assertLess(float(np.abs(decoded[40:200,60:160].astype(float)-expected[40:200,60:160]).mean()),10)
            self.assertGreater(float(np.abs(decoded[40:200,60:160].astype(float)-frame[40:200,60:160]).mean()),30)

    def test_policy_change_opens_a_separate_recording(self):
        frame = np.full((240,320,3),200,np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            recorder = RedactedRecorder(directory)
            try:
                recorder.write(frame,0,dict(revision=0,privacy={'enabled':False}),[])
                recorder.write(frame,200000000,dict(revision=1,privacy={'enabled':True}),None,reliable=False)
            finally:
                recorder.close()
            self.assertEqual(len(list(Path(directory).glob('*.mp4'))),2)

    def test_media_clock_reset_records_a_new_origin(self):
        frame = np.full((240,320,3),200,np.uint8)
        config = dict(revision=0, privacy={'enabled':True})
        with tempfile.TemporaryDirectory() as directory:
            recorder = RedactedRecorder(directory)
            try:
                recorder.write(frame,1000000000,config,None,reliable=False)
                recorder.write(frame,0,config,None,reliable=False)
            finally:
                recorder.close()
            rows = [json.loads(line) for line in (Path(directory)/'recording-index.jsonl').read_text().splitlines()]
            self.assertEqual([row['source_origin_ns'] for row in rows],['1000000000','0'])
            self.assertEqual(len(list(Path(directory).glob('*.mp4'))),2)


if __name__ == '__main__':
    unittest.main()

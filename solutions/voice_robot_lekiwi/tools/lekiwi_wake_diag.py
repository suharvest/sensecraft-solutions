import time
import os

import numpy as np
import pyaudio
from openwakeword.model import Model


RATE = 16000
CHANNELS = int(os.getenv("CHANNELS", "6"))
GAIN = float(os.getenv("GAIN", "1.0"))
CHUNK = 1280
SECONDS = 30
WAKEWORD = "hey jarvis"


def main():
    audio = pyaudio.PyAudio()
    models = [Model(wakeword_models=[WAKEWORD], vad_threshold=0.0) for _ in range(CHANNELS)]
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=0,
        frames_per_buffer=CHUNK,
    )

    peaks = [0.0] * CHANNELS
    rms_peaks = [0] * CHANNELS
    print("READY: say 'Hey Jarvis' clearly now", flush=True)
    end = time.time() + SECONDS
    try:
        while time.time() < end:
            raw = stream.read(CHUNK, exception_on_overflow=False)
            frame = np.frombuffer(raw, dtype=np.int16).reshape(-1, CHANNELS)
            confs = []
            rms = []
            for channel in range(CHANNELS):
                mono = frame[:, channel]
                if GAIN != 1.0:
                    mono = np.clip(mono.astype(np.float32) * GAIN, -32768, 32767).astype(np.int16)
                confidence = float(models[channel].predict(mono).get(WAKEWORD, 0.0))
                level = int(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
                peaks[channel] = max(peaks[channel], confidence)
                rms_peaks[channel] = max(rms_peaks[channel], level)
                confs.append(round(confidence, 3))
                rms.append(level)
            if max(confs) >= 0.02:
                print(f"conf={confs} rms={rms}", flush=True)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    print("PEAK_CONF", [round(value, 3) for value in peaks], flush=True)
    print("PEAK_RMS", rms_peaks, flush=True)


if __name__ == "__main__":
    main()

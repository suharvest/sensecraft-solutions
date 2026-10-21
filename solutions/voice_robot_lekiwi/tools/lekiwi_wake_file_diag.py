import sys
import wave
import audioop
import os

import numpy as np
from openwakeword.model import Model


RATE = 16000
CHUNK = 1280
WAKEWORD = "hey jarvis"
GAIN = float(os.getenv("GAIN", "1.0"))


def main(path: str):
    with wave.open(path, "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        rate = wav.getframerate()
        if sample_width != 2:
            raise SystemExit(f"Expected 16-bit PCM WAV, got sample width {sample_width}")

        model = Model(wakeword_models=[WAKEWORD], vad_threshold=0.0)
        peak = 0.0
        rate_state = None
        while True:
            raw = wav.readframes(CHUNK)
            if not raw:
                break
            if rate != RATE:
                raw, rate_state = audioop.ratecv(raw, sample_width, channels, rate, RATE, rate_state)
            audio = np.frombuffer(raw, dtype=np.int16)
            if channels > 1:
                audio = audio.reshape(-1, channels)[:, 0]
            if GAIN != 1.0:
                audio = np.clip(audio.astype(np.float32) * GAIN, -32768, 32767).astype(np.int16)
            confidence = float(model.predict(audio).get(WAKEWORD, 0.0))
            peak = max(peak, confidence)
            if confidence >= 0.02:
                print(f"conf={confidence:.3f}", flush=True)
        print(f"PEAK_CONF {peak:.3f}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])

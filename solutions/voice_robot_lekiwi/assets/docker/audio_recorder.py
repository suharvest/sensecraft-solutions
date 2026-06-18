"""audio_recorder.py — records N seconds from the mic and returns WAV bytes.
Opens its own short-lived PyAudio stream so it doesn't conflict with
the wake-word detector (which pauses before calling this).
"""
import io
import wave

import audio_devices
import config
import pyaudio


def record(seconds: int = config.RECORDING_SECONDS) -> bytes:
    """Record `seconds` of audio and return a WAV-formatted bytes object."""
    p = pyaudio.PyAudio()
    chunk = 1024
    total_frames = int(config.SAMPLE_RATE / chunk * seconds)

    print(f"[Recorder] Recording {seconds}s ...")
    input_device_index = audio_devices.resolve_input_index(config.MIC_INDEX)
    stream = p.open(
        format=pyaudio.paInt16,
        channels=config.MIC_CHANNELS,
        rate=config.SAMPLE_RATE,
        input=True,
        input_device_index=input_device_index,
        frames_per_buffer=chunk,
    )

    frames = []
    for _ in range(total_frames):
        data = stream.read(chunk, exception_on_overflow=False)
        if config.MIC_CHANNELS > 1:
            import numpy as np

            audio = np.frombuffer(data, dtype=np.int16)
            audio = audio.reshape(-1, config.MIC_CHANNELS)[:, config.MIC_CHANNEL]
            data = audio.astype(np.int16).tobytes()
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("[Recorder] Done")

    # Pack into WAV bytes (in-memory — no temp file needed)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()

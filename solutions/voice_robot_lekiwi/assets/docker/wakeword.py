"""wakeword.py — listens for the wake word using openwakeword.
Runs in its own thread. Calls on_detected(confidence) when triggered.
Can be paused/resumed so the mic is free during recording + playback.
"""
import threading
import time

import audio_devices
import config
import numpy as np
import pyaudio
from openwakeword.model import Model


class WakeWordDetector:
    def __init__(self):
        self._p = pyaudio.PyAudio()
        self._all_channels = (
            config.WAKEWORD_CHANNEL == "all"
            and config.MIC_CHANNELS > 1
        )
        model_count = config.MIC_CHANNELS if self._all_channels else 1
        self._models = [
            Model(
                wakeword_models=[config.WAKEWORD_MODEL],
                vad_threshold=config.WAKEWORD_VAD_THRESHOLD,
            )
            for _ in range(model_count)
        ]
        self._chunk_size = int(config.SAMPLE_RATE * 0.08)   # 80 ms frames
        self._stream: pyaudio.Stream | None = None
        self._input_device_index: int | None = None
        self._running = False
        self._paused = threading.Event()
        self._paused.set()                                   # not paused by default
        self._thread: threading.Thread | None = None
        self.on_detected = None                              # set from pipeline
        self._last_trigger = 0.0
        self._debug_next = time.time() + config.WAKEWORD_DEBUG_INTERVAL
        self._debug_peak_confidence = 0.0
        self._debug_peak_rms = 0
        self._debug_peak_channel = None
        self._debug_peak_rms_channel = None

    # ── public controls ──────────────────────────────────────────────────────

    def start(self):
        """Open mic and begin listening in a background thread."""
        self._running = True
        self._open_stream()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[WakeWord] Listening for '{config.WAKEWORD_MODEL}' ...")

    def pause(self):
        """Release the mic completely so audio_recorder can open it."""
        self._paused.clear()
        time.sleep(0.05)        # let the loop iteration finish before closing
        self._close_stream()    # ← FREE the device
        print("[WakeWord] Paused — mic released")

    def resume(self):
        """Reopen the mic and resume detection."""
        for model in self._models:
            model.reset()       # clear stale internal state
        self._open_stream()     # ← REACQUIRE the device
        self._paused.set()
        print(f"[WakeWord] Resumed — listening for '{config.WAKEWORD_MODEL}' ...")

    def stop(self):
        """Shut down permanently."""
        self._running = False
        self._paused.set()                                   # unblock loop if paused
        self._close_stream()
        if self._thread:
            self._thread.join(timeout=3)
        self._p.terminate()
        print("[WakeWord] Stopped")

    # ── private ──────────────────────────────────────────────────────────────

    def _open_stream(self):
        if self._input_device_index is None:
            self._input_device_index = audio_devices.resolve_input_index(config.MIC_INDEX)
        self._stream = self._p.open(
            format=pyaudio.paInt16,
            channels=config.MIC_CHANNELS,
            rate=config.SAMPLE_RATE,
            input=True,
            input_device_index=self._input_device_index,
            frames_per_buffer=self._chunk_size,
        )

    def _close_stream(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _loop(self):
        while self._running:
            self._paused.wait()                              # block when paused
            if not self._running:
                break
            if self._stream is None:                        # safety: not open yet
                time.sleep(0.02)
                continue

            try:
                raw = self._stream.read(self._chunk_size, exception_on_overflow=False)
            except Exception as e:
                print(f"[WakeWord] Stream read error: {e}")
                time.sleep(0.05)
                continue

            audio = np.frombuffer(raw, dtype=np.int16)
            if config.MIC_CHANNELS > 1:
                audio = audio.reshape(-1, config.MIC_CHANNELS)
                if self._all_channels:
                    confidence = 0.0
                    selected_audio = audio[:, 0]
                    selected_channel = 0
                    peak_rms = 0
                    peak_rms_channel = 0
                    for channel in range(config.MIC_CHANNELS):
                        mono = audio[:, channel]
                        channel_rms = int(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
                        if channel_rms >= peak_rms:
                            peak_rms = channel_rms
                            peak_rms_channel = channel
                        predictions = self._models[channel].predict(mono)
                        channel_confidence = predictions.get(config.WAKEWORD_MODEL, 0.0)
                        if channel_confidence >= confidence:
                            confidence = channel_confidence
                            selected_audio = mono
                            selected_channel = channel
                    audio = selected_audio
                else:
                    selected_channel = config.MIC_CHANNEL
                    audio = audio[:, config.MIC_CHANNEL]
                    peak_rms = int(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
                    peak_rms_channel = selected_channel
                    predictions = self._models[0].predict(audio)
                    confidence = predictions.get(config.WAKEWORD_MODEL, 0.0)
            else:
                selected_channel = 0
                peak_rms = int(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
                peak_rms_channel = selected_channel
                predictions = self._models[0].predict(audio)
                confidence = predictions.get(config.WAKEWORD_MODEL, 0.0)

            now = time.time()
            if config.WAKEWORD_DEBUG_INTERVAL > 0:
                self._debug_peak_confidence = max(self._debug_peak_confidence, confidence)
                if confidence >= self._debug_peak_confidence:
                    self._debug_peak_channel = selected_channel
                if peak_rms >= self._debug_peak_rms:
                    self._debug_peak_rms = peak_rms
                    self._debug_peak_rms_channel = peak_rms_channel
                if now >= self._debug_next:
                    print(
                        "[WakeWord] Debug "
                        f"peak_confidence={self._debug_peak_confidence:.3f} "
                        f"peak_channel={self._debug_peak_channel} "
                        f"peak_rms={self._debug_peak_rms} "
                        f"peak_rms_channel={self._debug_peak_rms_channel}",
                        flush=True,
                    )
                    self._debug_peak_confidence = 0.0
                    self._debug_peak_rms = 0
                    self._debug_peak_channel = None
                    self._debug_peak_rms_channel = None
                    self._debug_next = now + config.WAKEWORD_DEBUG_INTERVAL

            if (
                confidence > config.WAKEWORD_THRESHOLD
                and (now - self._last_trigger) > config.WAKEWORD_COOLDOWN
            ):
                self._last_trigger = now
                print(f"[WakeWord] Detected! confidence={confidence:.2f}")
                if self.on_detected:
                    self.on_detected(confidence)

"""pipeline.py — Voice assistant + Robot controller pipeline.

Full flow:
  [IDLE] Wake word detected
      → pause wake word detector
      → record N seconds
      → STT  (Groq Whisper)
      → LLM  → returns { speech, action, mode }
      → TTS  speaks the speech text
      → Serial → sends action command to ESP32
      → resume wake word detector
      → [IDLE]

Run with:  python pipeline.py
"""
import threading
import time

import audio_recorder
import config
import llm
import robot_serial
import stt
import tts
import wakeword as ww_module


class Pipeline:
    def __init__(self):
        self._detector = ww_module.WakeWordDetector()
        self._detector.on_detected = self._on_wakeword
        self._robot = robot_serial.get_robot()
        self._processing = False
        self._lock = threading.Lock()

    # ── entry point ──────────────────────────────────────────────────────────

    def run(self):
        print("=" * 54)
        print("  LeKiwi Voice Controller — Ready")
        print(f"  Wake word  : {config.WAKEWORD_MODEL}")
        print(f"  LLM model  : {config.LLM_MODEL}")
        print(f"  STT model  : {config.STT_MODEL}")
        print(f"  TTS voice  : {config.TTS_VOICE}")
        print(f"  Serial     : {config.SERIAL_PORT or 'DISABLED'} @ {config.SERIAL_BAUD}")
        print("=" * 54)
        self._detector.start()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[Pipeline] Shutting down ...")
            self._robot.send_stop()
            self._robot.close()
            self._detector.stop()

    # ── wake word callback ────────────────────────────────────────────────────

    def _on_wakeword(self, confidence: float):
        with self._lock:
            if self._processing:
                return
            self._processing = True
        threading.Thread(target=self._pipeline_step, daemon=True).start()

    # ── main pipeline ─────────────────────────────────────────────────────────

    def _pipeline_step(self):
        try:
            # 1. Pause wake word detector so mic is free
            self._detector.pause()

            # 2. Record audio
            wav_bytes = audio_recorder.record(config.RECORDING_SECONDS)

            # 3. STT — bail early on silence / noise
            text = stt.transcribe(wav_bytes)
            if not text:
                print("[Pipeline] Nothing heard — returning to idle")
                return

            # 4. LLM — returns { speech, action, mode }
            result = llm.chat(text)
            speech = result.get("speech", "")
            action = result.get("action", "none")
            mode   = result.get("mode", "nudge")

            # 5. TTS — speak the reply first so user gets feedback
            if speech:
                tts.speak(speech)

            # 6. Serial — send robot command AFTER speech finishes
            if action and action != "none":
                success = self._robot.send_action(action, mode)
                if not success:
                    print(f"[Pipeline] Failed to send action: {action!r}")

        except Exception as e:
            print(f"[Pipeline] Error: {e}")
            # Safety: always stop robot on error
            try:
                self._robot.send_stop()
            except Exception:
                pass

        finally:
            self._processing = False
            self._detector.resume()


if __name__ == "__main__":
    Pipeline().run()

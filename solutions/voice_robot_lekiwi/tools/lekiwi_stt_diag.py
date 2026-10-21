import audio_recorder
import stt


def main():
    print("READY: say a short command now", flush=True)
    wav_bytes = audio_recorder.record(5)
    text = stt.transcribe(wav_bytes)
    print(f"TRANSCRIPT {text!r}", flush=True)


if __name__ == "__main__":
    main()

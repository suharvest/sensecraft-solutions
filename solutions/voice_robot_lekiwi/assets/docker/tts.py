"""tts.py — Text-to-Speech via Groq Orpheus.
Streams the WAV response to a temp file and plays it with aplay
(most reliable on Raspberry Pi — no extra Python audio lib needed).
"""
import subprocess
import tempfile
from pathlib import Path

import config
from groq import Groq

_client = Groq(api_key=config.GROQ_API_KEY)


def _resolve_output_device() -> str:
    configured = config.TTS_OUTPUT_DEVICE
    if configured and configured.lower() != "auto":
        return configured

    try:
        result = subprocess.run(
            ["aplay", "-l"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        print(f"[TTS] Could not auto-detect output device: {exc}")
        return ""

    for line in result.stdout.splitlines():
        if "respeaker" in line.lower() and "card " in line and "device " in line:
            card = line.split("card ", 1)[1].split(":", 1)[0].strip()
            device = line.split("device ", 1)[1].split(":", 1)[0].strip()
            output = f"plughw:{card},{device}"
            print(f"[TTS] Auto-selected output device: {output}")
            return output
    return ""


def speak(text: str) -> None:
    """Convert text to speech and play it on the Pi's audio output."""
    if not text:
        return

    print(f"[TTS] Speaking: {text!r}")

    # Generate speech — stream straight to a temp WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    response = _client.audio.speech.create(
        model=config.TTS_MODEL,
        voice=config.TTS_VOICE,
        response_format="wav",
        input=text,
    )

    # ✅ Fix: Use write_to_file instead of stream_to_file
    response.write_to_file(tmp_path)

    # OR use the content attribute:
    # with open(tmp_path, 'wb') as f:
    #     f.write(response.content)

    # Play with aplay (built into Raspbian — zero extra dependencies)
    try:
        command = ["aplay", "-q"]
        output_device = _resolve_output_device()
        if output_device:
            command.extend(["-D", output_device])
        command.append(str(tmp_path))
        subprocess.run(
            command,
            check=True,
            timeout=60,
        )
    except FileNotFoundError:
        # Fallback: try afplay (macOS dev machine) or paplay (PulseAudio)
        try:
            subprocess.run(["afplay", str(tmp_path)], check=True, timeout=60)
        except FileNotFoundError:
            subprocess.run(["paplay", str(tmp_path)], check=True, timeout=60)
    finally:
        tmp_path.unlink(missing_ok=True)

    print("[TTS] Done")

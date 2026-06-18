"""stt.py — Speech-to-Text via Groq Whisper.
Accepts WAV bytes directly — no temp file required.
"""
import io

import config
from groq import Groq

_client = Groq(api_key=config.GROQ_API_KEY)


def transcribe(wav_bytes: bytes) -> str:
    """Send WAV bytes to Groq Whisper and return the transcribed text."""
    print("[STT] Transcribing ...")
    audio_file = io.BytesIO(wav_bytes)
    audio_file.name = "audio.wav"          # Groq SDK needs a filename hint

    transcription = _client.audio.transcriptions.create(
        file=audio_file,
        model=config.STT_MODEL,
        language=config.STT_LANGUAGE,
        response_format="text",            # plain string — no JSON parsing needed
        temperature=0.0,
    )
    text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
    print(f"[STT] Heard: {text!r}")
    return text

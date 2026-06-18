
"""config.py — loads all settings from environment variables."""
import os

# Groq
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

# Wake word
WAKEWORD_MODEL: str       = os.getenv("WAKEWORD_MODEL", "hey jarvis")
MIC_INDEX: str            = os.getenv("MIC_INDEX", "auto")
MIC_CHANNELS: int         = int(os.getenv("MIC_CHANNELS", 6))
MIC_CHANNEL: int          = int(os.getenv("MIC_CHANNEL", 0))
WAKEWORD_CHANNEL: str     = os.getenv("WAKEWORD_CHANNEL", "all").strip().lower()
WAKEWORD_THRESHOLD: float = float(os.getenv("WAKEWORD_THRESHOLD", 0.03))
WAKEWORD_VAD_THRESHOLD: float = float(os.getenv("WAKEWORD_VAD_THRESHOLD", 0.0))
WAKEWORD_COOLDOWN: float  = float(os.getenv("WAKEWORD_COOLDOWN", 2.0))
WAKEWORD_DEBUG_INTERVAL: float = float(os.getenv("WAKEWORD_DEBUG_INTERVAL", 0.0))

# Recording
RECORDING_SECONDS: int = int(os.getenv("RECORDING_SECONDS", 3))
SAMPLE_RATE: int       = int(os.getenv("SAMPLE_RATE", 16000))

# LLM
LLM_MODEL: str      = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", 128))
# STT
STT_MODEL: str    = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en")

# TTS
TTS_MODEL: str = os.getenv("TTS_MODEL", "canopylabs/orpheus-v1-english")
TTS_VOICE: str = os.getenv("TTS_VOICE", "autumn")
TTS_OUTPUT_DEVICE: str = os.getenv("TTS_OUTPUT_DEVICE", "auto")

# Robot Serial
SERIAL_PORT: str = os.getenv("SERIAL_PORT", "auto")   # auto = scan /dev/ttyACM*
SERIAL_BAUD: int = int(os.getenv("SERIAL_BAUD", 115200))

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY is not set. Pass it via environment variable.")

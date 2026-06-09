"""Speech-to-text transcription using faster-whisper."""
import logging
from pathlib import Path
from faster_whisper import WhisperModel
from app.config import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

_whisper_model = None


def _get_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE}")
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


def transcribe(audio_path: Path) -> str:
    """Transcribe audio file to text. Returns empty string if no speech detected."""
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        return ""

    model = _get_model()
    segments, info = model.transcribe(str(audio_path), beam_size=5)

    texts = []
    for segment in segments:
        texts.append(segment.text.strip())

    result = " ".join(texts)
    logger.info(f"Transcription ({info.language}, prob={info.language_probability:.2f}): {result[:200]}...")
    return result

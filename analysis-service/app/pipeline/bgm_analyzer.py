"""Background music type and loudness analysis using librosa."""
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def analyze_bgm(audio_path: Path) -> dict:
    """Analyze audio for BGM type, loudness, BPM, and voice presence."""
    try:
        import librosa
        y, sr = librosa.load(str(audio_path), sr=None)

        result = {
            "bgm_type": "none",
            "loudness": "中",
            "bpm": 0.0,
            "has_voice": False,
        }

        if len(y) == 0:
            return result

        # RMS energy → loudness classification
        rms = np.sqrt(np.mean(y ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -100

        if rms_db < -30:
            result["loudness"] = "低"
        elif rms_db > -15:
            result["loudness"] = "高"
        else:
            result["loudness"] = "中"

        # Spectral centroid → brightness (indicates music presence)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        mean_centroid = np.mean(spectral_centroid)

        # Spectral bandwidth → music vs speech indicator
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        mean_bandwidth = np.mean(spectral_bandwidth)

        # MFCC analysis for BGM classification
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)

        # Heuristic BGM classification based on spectral features
        if mean_centroid > 2000 and mean_bandwidth > 1500:
            result["bgm_type"] = "uplifting"
        elif mean_centroid > 1500:
            result["bgm_type"] = "tense"
        elif mean_centroid > 800:
            result["bgm_type"] = "calm"
        else:
            result["bgm_type"] = "sad"

        # BPM detection
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            result["bpm"] = round(float(tempo[0]), 1)
        else:
            result["bpm"] = round(float(tempo), 1)

        # Simple voice activity detection based on zero-crossing rate
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = np.mean(zcr)
        result["has_voice"] = zcr_mean > 0.05

        logger.info(f"BGM analysis: type={result['bgm_type']}, loudness={result['loudness']}, bpm={result['bpm']}")
        return result

    except Exception as e:
        logger.warning(f"BGM analysis failed: {e}")
        return {"bgm_type": "none", "loudness": "中", "bpm": 0.0, "has_voice": False}

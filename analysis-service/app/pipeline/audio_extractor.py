"""Audio extraction from video using FFmpeg."""
from pathlib import Path
from video_factory_shared.ffmpeg_utils import extract_audio


class AudioExtractor:
    def extract(self, video_path: str, output_dir: Path) -> Path:
        """Extract audio as 16kHz mono WAV. Returns path to audio file."""
        output_path = output_dir / "extracted_audio.wav"
        return extract_audio(video_path, output_path, sample_rate=16000)

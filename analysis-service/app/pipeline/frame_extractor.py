"""Frame extraction using FFmpeg."""
from pathlib import Path
from video_factory_shared.ffmpeg_utils import extract_frames
from app.config import EXTRACT_FPS, MAX_FRAMES


class FrameExtractor:
    def __init__(self, fps: float = EXTRACT_FPS, max_frames: int = MAX_FRAMES):
        self.fps = fps
        self.max_frames = max_frames

    def extract(self, video_path: str, output_dir: Path) -> list[Path]:
        """Extract frames and return sorted list of frame file paths."""
        frames = extract_frames(
            video_path=video_path,
            output_dir=output_dir,
            fps=self.fps,
            max_frames=self.max_frames,
        )
        if not frames:
            raise RuntimeError(f"No frames extracted from {video_path}")
        return frames

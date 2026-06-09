"""Common FFmpeg/ffprobe utility functions."""
import json
import subprocess
from pathlib import Path


def ffprobe(file_path: str) -> dict:
    """Run ffprobe and return parsed JSON output."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    result.check_returncode()
    return json.loads(result.stdout)


def get_video_info(file_path: str) -> dict:
    """Extract key video metadata: duration, resolution, framerate, codec."""
    probe = ffprobe(file_path)
    video_stream = None
    audio_stream = None
    for stream in probe.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream

    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", 0))

    fps_str = video_stream.get("r_frame_rate", "0/1") if video_stream else "0/1"
    num, den = fps_str.split("/") if "/" in fps_str else (fps_str, "1")
    fps = float(num) / float(den) if float(den) != 0 else 0.0

    return {
        "duration_sec": duration,
        "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}" if video_stream else "",
        "framerate": round(fps, 2),
        "codec": video_stream.get("codec_name", "") if video_stream else "",
        "has_audio": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
        "format_name": fmt.get("format_name", ""),
    }


def extract_frames(
    video_path: str,
    output_dir: Path,
    fps: float = 1.0,
    max_frames: int = 60,
    quality: int = 2
) -> list[Path]:
    """Extract frames at given fps. Returns sorted list of frame paths."""
    output_pattern = output_dir / "frame_%06d.jpg"
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", str(quality),
        "-frames:v", str(max_frames),
        str(output_pattern)
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    frames = sorted(output_dir.glob("frame_*.jpg"))
    return frames


def extract_audio(video_path: str, output_path: Path, sample_rate: int = 16000) -> Path:
    """Extract audio as mono 16kHz WAV."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(sample_rate), "-ac", "1",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    probe = ffprobe(str(audio_path))
    return float(probe.get("format", {}).get("duration", 0))


def ms_to_ffmpeg_time(ms: int) -> str:
    """Convert milliseconds to FFmpeg time format HH:MM:SS.mmm."""
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

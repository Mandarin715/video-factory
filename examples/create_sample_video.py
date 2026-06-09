"""Generate a sample test video using FFmpeg (test pattern + timer + audio tone)."""
import subprocess
from pathlib import Path


def create_sample_video(output_path: str, duration: int = 20):
    """Create a test video with test pattern, moving timer, and audio tone."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-vf",
        (
            "drawtext=text='Frame %{n}':fontsize=72:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2-60,"
            "drawtext=text='Time %{pts\\:hms}':fontsize=48:fontcolor=yellow:"
            "x=(w-text_w)/2:y=(h-text_h)/2+20"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path),
    ]
    print(f"Creating sample video: {output_path}")
    subprocess.run(cmd, check=True)
    print(f"Done: {output_path}")


def create_sample_bgm(output_path: str, duration: int = 30):
    """Create a simple BGM track (sine wave)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"sine=frequency=261:duration={duration}",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
    ]
    print(f"Creating sample BGM: {output_path}")
    subprocess.run(cmd, check=True)
    print(f"Done: {output_path}")


if __name__ == "__main__":
    examples_dir = Path(__file__).parent
    create_sample_video(str(examples_dir / "sample_video.mp4"), duration=20)
    create_sample_bgm(str(examples_dir / "sample_bgm.mp3"), duration=30)

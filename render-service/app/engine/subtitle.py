"""drawtext subtitle filter builder."""
from video_factory_shared.models import Subtitle, SubtitlePosition


def escape_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext."""
    return (text
            .replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\\\%"))


def get_position(sub: Subtitle, width: int, height: int) -> str:
    """Get x:y position string for a subtitle based on its position enum."""
    positions = {
        SubtitlePosition.TOP_LEFT:      "x=20:y=20",
        SubtitlePosition.TOP_CENTER:    "x=(w-text_w)/2:y=20",
        SubtitlePosition.TOP_RIGHT:     "x=w-text_w-20:y=20",
        SubtitlePosition.BOTTOM_LEFT:   "x=20:y=h-text_h-80",
        SubtitlePosition.BOTTOM_CENTER: "x=(w-text_w)/2:y=h-text_h-80",
        SubtitlePosition.BOTTOM_RIGHT:  "x=w-text_w-20:y=h-text_h-80",
        SubtitlePosition.CUSTOM:        f"x={sub.custom_x or 0}:y={sub.custom_y or 0}",
    }
    return positions.get(sub.position, positions[SubtitlePosition.BOTTOM_CENTER])


def build_subtitle_filter(sub: Subtitle, width: int, height: int,
                          font_dir: str = "/fonts") -> str:
    """Build a single drawtext filter string for one subtitle entry."""
    font_name = sub.font
    font_path = f"{font_dir}/{font_name.replace(' ', '')}.otf"

    start_sec = sub.start_ms / 1000.0
    end_sec = sub.end_ms / 1000.0

    pos = get_position(sub, width, height)

    return (
        f"drawtext="
        f"text='{escape_text(sub.text)}':"
        f"fontfile={font_path}:"
        f"fontsize={sub.font_size}:"
        f"fontcolor={sub.color}:"
        f"borderw={sub.outline_width}:"
        f"bordercolor={sub.outline_color}:"
        f"{pos}:"
        f"enable='between(t,{start_sec:.3f},{end_sec:.3f})'"
    )


def build_all_subtitles(subs: list[Subtitle], width: int, height: int,
                        font_dir: str = "/fonts") -> str:
    """Build comma-separated chain of all subtitle drawtext filters."""
    if not subs:
        return ""
    return ",".join(
        build_subtitle_filter(s, width, height, font_dir) for s in subs
    )

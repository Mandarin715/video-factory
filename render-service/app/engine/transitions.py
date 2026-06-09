"""FFmpeg transition filter chain builders for 5 transition types."""
from video_factory_shared.models import Transition, TransitionType


def get_transition_filter(
    t: Transition, prev_label: str, next_label: str, output_label: str,
    prev_duration_sec: float = 5.0
) -> str:
    """Build the FFmpeg filter string for a given transition.

    Args:
        t: Transition config (type + duration_ms)
        prev_label: FFmpeg filter pad label for the previous clip
        next_label: FFmpeg filter pad label for the next clip
        output_label: FFmpeg filter pad label for output
        prev_duration_sec: Duration of previous clip in seconds (for xfade offset)
    """
    ttype = t.type if isinstance(t.type, TransitionType) else TransitionType(t.type)

    if ttype == TransitionType.CUT:
        return ""

    dur = t.duration_ms / 1000.0

    if ttype == TransitionType.CROSSFADE:
        offset = max(0, prev_duration_sec - dur)
        return f"[{prev_label}][{next_label}]xfade=transition=fade:duration={dur:.3f}:offset={offset:.3f}[{output_label}]"

    elif ttype == TransitionType.FADE_BLACK:
        offset = max(0, prev_duration_sec - dur)
        return f"[{prev_label}][{next_label}]xfade=transition=fadeblack:duration={dur:.3f}:offset={offset:.3f}[{output_label}]"

    elif ttype == TransitionType.WIPE_LEFT:
        offset = max(0, prev_duration_sec - dur)
        return f"[{prev_label}][{next_label}]xfade=transition=wiperight:duration={dur:.3f}:offset={offset:.3f}[{output_label}]"

    elif ttype == TransitionType.BLUR_DISSOLVE:
        offset = max(0, prev_duration_sec - dur)
        return (
            f"[{prev_label}]boxblur=10:2[blur_a];"
            f"[{next_label}]boxblur=10:2[blur_b];"
            f"[blur_a][blur_b]xfade=transition=dissolve:duration={dur:.3f}:offset={offset:.3f}[{output_label}]"
        )

    return ""

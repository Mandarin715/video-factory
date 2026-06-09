"""FFmpeg transition filter chain builders for 5 transition types."""
from video_factory_shared.models import Transition, TransitionType


def get_transition_filter(
    t: Transition, prev_label: str, next_label: str, output_label: str
) -> str:
    """Build the FFmpeg filter string for a given transition."""
    ttype = t.type if isinstance(t.type, TransitionType) else TransitionType(t.type)

    if ttype == TransitionType.CUT:
        return ""

    elif ttype == TransitionType.CROSSFADE:
        dur = t.duration_ms / 1000.0
        return f"[{prev_label}][{next_label}]xfade=transition=fade:duration={dur:.3f}[{output_label}]"

    elif ttype == TransitionType.FADE_BLACK:
        dur = t.duration_ms / 1000.0
        return f"[{prev_label}][{next_label}]xfade=transition=fadeblack:duration={dur:.3f}[{output_label}]"

    elif ttype == TransitionType.WIPE_LEFT:
        dur = t.duration_ms / 1000.0
        return f"[{prev_label}][{next_label}]xfade=transition=wiperight:duration={dur:.3f}[{output_label}]"

    elif ttype == TransitionType.BLUR_DISSOLVE:
        dur = t.duration_ms / 1000.0
        return (
            f"[{prev_label}]boxblur=10:2[blur_a];"
            f"[{next_label}]boxblur=10:2[blur_b];"
            f"[blur_a][blur_b]xfade=transition=dissolve:duration={dur:.3f}[{output_label}]"
        )

    return ""

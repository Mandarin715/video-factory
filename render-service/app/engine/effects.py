"""FFmpeg effect filter chain builders for 4 effect types."""
from video_factory_shared.models import Effect, EffectType


def get_effect_filter_chain(effect: Effect, input_label: str, output_label: str,
                             width: int, height: int, fps: int) -> str:
    """Build FFmpeg filter string for a single effect."""
    etype = effect.type if isinstance(effect.type, EffectType) else EffectType(effect.type)
    params = effect.params or {}

    if etype == EffectType.SLOW_MOTION:
        factor = params.get("factor", 2.0)
        return f"[{input_label}]setpts={factor}*PTS[{output_label}]"

    elif etype == EffectType.ZOOM_IN:
        start_scale = params.get("start_scale", 1.0)
        end_scale = params.get("end_scale", 1.15)
        return (
            f"[{input_label}]zoompan="
            f"z='min(zoom+{end_scale - start_scale}/60,{end_scale})':"
            f"d=1:"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"s={width}x{height}:"
            f"fps={fps}"
            f"[{output_label}]"
        )

    elif etype == EffectType.GRAYSCALE:
        return f"[{input_label}]hue=s=0[{output_label}]"

    elif etype == EffectType.VIGNETTE:
        return f"[{input_label}]vignette=PI/4[{output_label}]"

    return f"[{input_label}]copy[{output_label}]"


def build_effect_chain(effects: list[Effect], input_label: str,
                       width: int, height: int, fps: int) -> tuple[str, str]:
    """Build a chain of effects applied to a single clip.
    Returns (filter_string, final_output_label)."""
    if not effects:
        return "", input_label

    parts = []
    current_in = input_label
    for i, effect in enumerate(effects):
        out_label = f"{input_label}_ef{i}"
        filter_str = get_effect_filter_chain(effect, current_in, out_label, width, height, fps)
        if filter_str:
            parts.append(filter_str)
            current_in = out_label

    return ";".join(parts), current_in

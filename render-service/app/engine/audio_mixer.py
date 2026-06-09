"""Multi-track audio mixing with BGM, voice, fade in/out."""
from typing import Optional
from video_factory_shared.models import BGMTrack


def build_audio_filter_graph(
    clip_labels: list[str],
    clip_volumes: list[float],
    clip_speeds: list[float],
    bgm: Optional[BGMTrack],
    total_duration_ms: int,
    bgm_label: str = "bgm_input",
) -> str:
    """Build complete audio filter graph string."""

    parts = []

    # Process each clip's audio: volume + speed adjustment
    processed_clips = []
    for i, (label, vol, speed) in enumerate(zip(clip_labels, clip_volumes, clip_speeds)):
        chain = f"[{label}]"
        filters = []

        if speed != 1.0:
            tempo = 1.0 / speed
            if tempo < 0.5:
                filters.append(f"atempo=0.5,atempo={tempo/0.5}")
            elif tempo > 2.0:
                filters.append(f"atempo=2.0,atempo={tempo/2.0}")
            else:
                filters.append(f"atempo={tempo}")

        if vol != 1.0:
            filters.append(f"volume={vol}")

        if filters:
            chain += ",".join(filters)

        chain += f"[ac{i}]"
        parts.append(chain)
        processed_clips.append(f"ac{i}")

    # Concatenate clip audio
    concat_inputs = "".join(f"[{p}]" for p in processed_clips)
    parts.append(f"{concat_inputs}concat=n={len(processed_clips)}:v=0:a=1[voice_mix]")

    if bgm and bgm_label:
        bgm_filters = [f"volume={bgm.volume}"]

        if bgm.fade_in_ms > 0:
            bgm_filters.append(f"afade=t=in:st=0:d={bgm.fade_in_ms / 1000.0:.3f}")

        if bgm.fade_out_ms > 0:
            out_start = (total_duration_ms - bgm.fade_out_ms) / 1000.0
            bgm_filters.append(f"afade=t=out:st={out_start:.3f}:d={bgm.fade_out_ms / 1000.0:.3f}")

        parts.append(f"[{bgm_label}]{','.join(bgm_filters)}[bgm_processed]")
        parts.append("[voice_mix][bgm_processed]amix=inputs=2:duration=longest[audio_out]")
    else:
        parts.append("[voice_mix]anull[audio_out]")

    return ";".join(parts)

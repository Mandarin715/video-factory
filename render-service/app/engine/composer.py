"""Top-level FFmpeg command assembler — builds the complete filter graph and CLI command."""
import logging
from pathlib import Path
from video_factory_shared.models import DecisionJSON, TransitionType
from .transitions import get_transition_filter
from .effects import build_effect_chain
from .audio_mixer import build_audio_filter_graph
from .subtitle import build_all_subtitles

logger = logging.getLogger(__name__)


class FFmpegComposer:
    """Assembles a complete FFmpeg command from the decision JSON."""

    def __init__(self, decision: DecisionJSON, material_map: dict,
                 output_path: Path, proxy: bool = False, font_dir: str = "/fonts"):
        self.decision = decision
        self.material_map = material_map
        self.output_path = output_path
        self.proxy = proxy
        self.font_dir = font_dir
        self.width = decision.output.width
        self.height = decision.output.height
        self.fps = decision.output.fps

        if proxy:
            if self.width > 1280:
                ratio = 1280 / self.width
                self.width = 1280
                self.height = int(self.height * ratio)
                self.height = self.height if self.height % 2 == 0 else self.height - 1

    def _get_clip_path(self, material_id: str) -> str:
        path = self.material_map.get(material_id, material_id)
        return str(path)

    def build_command(self) -> list[str]:
        """Build the complete FFmpeg command as a list of arguments."""
        timeline = self.decision.timeline
        if not timeline:
            raise ValueError("Timeline is empty")

        cmd = ["ffmpeg", "-y"]

        # Input files
        input_labels = []
        for i, clip in enumerate(timeline):
            path = self._get_clip_path(clip.material_id)
            cmd.extend(["-ss", str(clip.src_start)])
            cmd.extend(["-t", str(clip.src_end - clip.src_start)])
            cmd.extend(["-i", path])
            input_labels.append((f"c{i}", clip))

        # BGM input
        bgm_label = None
        if self.decision.bgm:
            bgm_path = self._get_clip_path(self.decision.bgm.material_id)
            cmd.extend(["-stream_loop", "-1" if self.decision.bgm.loop else "0"])
            cmd.extend(["-i", bgm_path])
            bgm_label = f"bgm_{len(timeline)}"

        # Build filter_complex
        filter_parts = []
        video_chain_labels = []
        audio_chain_labels = []
        clip_volumes = []
        clip_speeds = []

        for i, (label, clip) in enumerate(input_labels):
            current_label = f"{label}v"
            speed_filter = ""
            if clip.speed != 1.0:
                filter_parts.append(
                    f"[{i}:v]trim={clip.src_start}:{clip.src_end},setpts=PTS-STARTPTS,"
                    f"setpts={clip.speed}*PTS,scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,fps={self.fps}[{current_label}]"
                )
            else:
                filter_parts.append(
                    f"[{i}:v]trim={clip.src_start}:{clip.src_end},setpts=PTS-STARTPTS,"
                    f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,fps={self.fps}[{current_label}]"
                )

            # Apply effects
            if clip.effects:
                effect_filter, current_label = build_effect_chain(
                    clip.effects, current_label, self.width, self.height, self.fps
                )
                if effect_filter:
                    filter_parts.append(effect_filter)

            video_chain_labels.append(current_label)
            audio_chain_labels.append(f"{i}:a")
            clip_volumes.append(clip.volume)
            clip_speeds.append(clip.speed)

        # Concatenate video with transitions
        if len(video_chain_labels) == 1:
            filter_parts.append(f"[{video_chain_labels[0]}]copy[video_out]")
        else:
            current = video_chain_labels[0]
            xfade_idx = 0
            for i in range(1, len(video_chain_labels)):
                next_label = video_chain_labels[i]
                transition = timeline[i - 1].transition_out

                if transition and transition.type != TransitionType.CUT:
                    out_label = f"xfade{xfade_idx}"
                    prev_dur = timeline[i - 1].duration
                    t_filter = get_transition_filter(
                        transition, current, next_label, out_label,
                        prev_duration_sec=prev_dur
                    )
                    if t_filter:
                        filter_parts.append(t_filter)
                        current = out_label
                        xfade_idx += 1
                    else:
                        concat_label = f"concat{xfade_idx}"
                        filter_parts.append(
                            f"[{current}][{next_label}]concat=n=2:v=1:a=0[{concat_label}]"
                        )
                        current = concat_label
                        xfade_idx += 1
                else:
                    concat_label = f"concat{xfade_idx}"
                    filter_parts.append(
                        f"[{current}][{next_label}]concat=n=2:v=1:a=0[{concat_label}]"
                    )
                    current = concat_label
                    xfade_idx += 1

            # Apply subtitles on final video chain
            sub_filter = build_all_subtitles(
                self.decision.subtitles, self.width, self.height, self.font_dir
            )
            if sub_filter:
                filter_parts.append(f"[{current}]{sub_filter}[video_out]")
            else:
                filter_parts.append(f"[{current}]copy[video_out]")

        # Audio filter graph
        total_duration_ms = int(sum(c.duration for c in timeline) * 1000)
        audio_filter = build_audio_filter_graph(
            clip_labels=audio_chain_labels,
            clip_volumes=clip_volumes,
            clip_speeds=clip_speeds,
            bgm=self.decision.bgm,
            total_duration_ms=total_duration_ms,
            bgm_label=bgm_label,
        )
        filter_parts.append(audio_filter)

        # Join all filter parts
        filter_complex = ";".join(p for p in filter_parts if p)
        cmd.extend(["-filter_complex", filter_complex])

        # Map outputs
        cmd.extend(["-map", "[video_out]", "-map", "[audio_out]"])

        # Output settings
        bitrate = "2M" if self.proxy else self.decision.output.video_bitrate
        crf = "28" if self.proxy else "23"

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "faster" if self.proxy else "medium",
            "-b:v", bitrate,
            "-crf", crf,
            "-c:a", "aac",
            "-b:a", self.decision.output.audio_bitrate,
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(self.output_path),
        ])

        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        return cmd

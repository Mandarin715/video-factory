"""Parse decision JSON into internal timeline model."""
from typing import Optional
from video_factory_shared.models import (
    DecisionJSON, ClipSegment, Transition, Effect, Subtitle,
    BGMTrack, OutputConfig, TransitionType, EffectType, SubtitlePosition
)


class TimelineParser:
    """Parses and validates a decision JSON dict into structured objects."""

    def parse(self, decision: dict) -> DecisionJSON:
        timeline = [self._parse_clip(c) for c in decision.get("timeline", [])]
        subtitles = [self._parse_subtitle(s) for s in decision.get("subtitles", [])]
        bgm = self._parse_bgm(decision.get("bgm"))
        output = self._parse_output(decision.get("output", {}))

        return DecisionJSON(
            timeline=timeline,
            subtitles=subtitles,
            bgm=bgm,
            output=output,
        )

    def _parse_clip(self, c: dict) -> ClipSegment:
        effects = []
        for e in c.get("effects", []):
            effects.append(Effect(
                type=EffectType(e["type"]),
                params=e.get("params", {}),
            ))

        ti = c.get("transition_in")
        to = c.get("transition_out")

        return ClipSegment(
            clip_id=c["clip_id"],
            material_id=c["material_id"],
            src_start=c.get("src_start", 0.0),
            src_end=c.get("src_end", 0.0),
            duration=c.get("duration", 0.0),
            transition_in=Transition(
                type=TransitionType(ti["type"]),
                duration_ms=ti.get("duration_ms", 0),
            ) if ti else None,
            transition_out=Transition(
                type=TransitionType(to["type"]),
                duration_ms=to.get("duration_ms", 0),
            ) if to else None,
            effects=effects,
            volume=c.get("volume", 1.0),
            speed=c.get("speed", 1.0),
        )

    def _parse_subtitle(self, s: dict) -> Subtitle:
        return Subtitle(
            text=s["text"],
            start_ms=s.get("start_ms", 0),
            end_ms=s.get("end_ms", 0),
            font=s.get("font", "Noto Sans CJK SC"),
            font_size=s.get("font_size", 48),
            position=SubtitlePosition(s.get("position", "bottom_center")),
            color=s.get("color", "white"),
            outline_color=s.get("outline_color", "black"),
            outline_width=s.get("outline_width", 2),
            custom_x=s.get("custom_x"),
            custom_y=s.get("custom_y"),
        )

    def _parse_bgm(self, bgm: Optional[dict]) -> Optional[BGMTrack]:
        if not bgm:
            return None
        return BGMTrack(
            material_id=bgm["material_id"],
            volume=bgm.get("volume", 0.3),
            fade_in_ms=bgm.get("fade_in_ms", 0),
            fade_out_ms=bgm.get("fade_out_ms", 0),
            loop=bgm.get("loop", False),
        )

    def _parse_output(self, o: dict) -> OutputConfig:
        return OutputConfig(
            width=o.get("width", 1920),
            height=o.get("height", 1080),
            fps=o.get("fps", 30),
            video_bitrate=o.get("video_bitrate", "8M"),
            audio_bitrate=o.get("audio_bitrate", "192k"),
        )

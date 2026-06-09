"""Core data models for video factory."""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class TransitionType(str, Enum):
    CUT = "cut"
    CROSSFADE = "crossfade"
    FADE_BLACK = "fade_black"
    WIPE_LEFT = "wipe_left"
    BLUR_DISSOLVE = "blur_dissolve"


class EffectType(str, Enum):
    SLOW_MOTION = "slow_motion"
    ZOOM_IN = "zoom_in"
    GRAYSCALE = "grayscale"
    VIGNETTE = "vignette"


class SubtitlePosition(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    CUSTOM = "custom"


@dataclass
class AudioFeatures:
    bgm_type: str = "none"
    loudness: str = "中"
    bpm: float = 0.0
    has_voice: bool = False


@dataclass
class MaterialMetadata:
    material_id: str = ""
    duration_sec: float = 0.0
    resolution: str = ""
    framerate: float = 0.0
    codec: str = ""
    visual_description: str = ""
    speech_text: str = ""
    scene_tags: list = field(default_factory=list)
    characters: list = field(default_factory=list)
    emotion: str = ""
    audio_features: AudioFeatures = field(default_factory=AudioFeatures)


@dataclass
class Transition:
    type: TransitionType = TransitionType.CUT
    duration_ms: int = 0


@dataclass
class Effect:
    type: EffectType
    params: dict = field(default_factory=dict)


@dataclass
class ClipSegment:
    clip_id: str
    material_id: str
    src_start: float
    src_end: float
    duration: float
    transition_in: Optional[Transition] = None
    transition_out: Optional[Transition] = None
    effects: list = field(default_factory=list)
    volume: float = 1.0
    speed: float = 1.0


@dataclass
class Subtitle:
    text: str
    start_ms: int
    end_ms: int
    font: str = "Noto Sans CJK SC"
    font_size: int = 48
    position: SubtitlePosition = SubtitlePosition.BOTTOM_CENTER
    color: str = "white"
    outline_color: str = "black"
    outline_width: int = 2
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None


@dataclass
class BGMTrack:
    material_id: str
    volume: float = 0.3
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    loop: bool = False


@dataclass
class OutputConfig:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"


@dataclass
class DecisionJSON:
    timeline: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
    bgm: Optional[BGMTrack] = None
    output: OutputConfig = field(default_factory=OutputConfig)

# Video Understanding & Rendering Factory — Design Spec

**Date:** 2026-06-09
**Status:** Approved
**Author:** Claude Code + User

---

## 1. Overview

Build a "Video Understanding & Rendering Factory" module consisting of two independent microservices:

- **Analysis Service** (port 8001): Receives a video file, extracts frames, calls Vision-Language Models + Whisper + librosa, and outputs standardized material metadata JSON.
- **Render Service** (port 8002): Receives editing decision JSON + material file mapping, constructs FFmpeg filter chains, and renders the final video with transitions, effects, subtitles, and mixed audio.

Both services use Celery + Redis for async task processing with progress tracking.

---

## 2. Architecture

### 2.1 Service Topology (Docker Compose, 6 containers)

```
redis (6379)           — Celery broker + result backend + metadata cache
analysis-api (8001)    — FastAPI + Uvicorn, handles /media/analyze
analysis-worker         — Celery worker: FFmpeg + Whisper + librosa + Gemini API
render-api (8002)      — FastAPI + Uvicorn, handles /media/render
render-worker           — Celery worker: FFmpeg with full filter chain
shared volume           — /data/videos (input), /data/output (rendered results)
```

### 2.2 Shared Library (`shared/`)

A pip-installable package (`video-factory-shared`) containing data models, Pydantic schemas, storage adapter, FFmpeg utilities, and Redis client — shared by both services to avoid code duplication.

### 2.3 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI Vision | Gemini Pro Vision (API) | Large free tier, good multilingual support |
| Speech-to-Text | faster-whisper (local, base model) | No API cost, CTranslate2 optimization |
| Audio Analysis | librosa (local) | Mature, no external dependency |
| Rendering Backend | Pure FFmpeg filter chains | Minimal dependencies, largest community, smallest Docker image |
| Storage | Local filesystem | Development phase; adapter interface for future S3/MinIO |
| Async Tasks | Celery + Redis | Progress tracking, retry, mature ecosystem |

---

## 3. Analysis Service (Sub-module 1)

### 3.1 API

```
POST /media/analyze
  Request:  { "video_url": "/data/videos/my_video.mp4" }
  Response: { "job_id": "uuid", "status": "queued" }

GET /media/analyze/{job_id}/status
  Response: {
    "job_id": "uuid",
    "status": "queued|processing|done|error",
    "progress": 0-100,
    "current_step": "probing|extracting_frames|analyzing_vision|analyzing_audio|finalizing",
    "result": { ... }  // present when status=done
  }
```

### 3.2 Celery Task Pipeline (5 stages)

**Stage 1: Video Probing (0-5%)**
- `ffprobe` to extract: duration, resolution, framerate, codec, audio stream info
- Generate material ID: `mat_` + uuid4()[:12]

**Stage 2: Frame Extraction (5-25%)**
- FFmpeg `-vf "fps=1"` → 1 frame per second to temp directory
- Alternative: `-vf "select='eq(pict_type,I)'"` for I-frames only (configurable)
- Cap at 60 frames (uniform sampling for long videos)
- Store as JPEG in temp directory

**Stage 3: Vision Analysis (25-55%)**
- For each extracted frame (or sampled keyframes), call Gemini Pro Vision:
  - Visual description: "Describe this scene in detail in Chinese..."
  - Scene tags: "List scene tags as JSON array..."
  - Emotion: "What is the emotional tone? Choose from: 激昂/悲伤/紧张/平静/温馨/悬疑..."
  - Characters: "Describe any people visible..."
- Retry: tenacity, max 3 attempts, exponential backoff 2s→4s→8s, timeout 30s per frame
- Aggregate results: deduplicate tags, vote on dominant emotion

**Stage 4: Audio Analysis (55-85%)**
- 4a. FFmpeg extract audio → WAV 16kHz mono
- 4b. faster-whisper (base model) → speech-to-text
- 4c. librosa analysis:
  - Spectral features → BGM classification (none/uplifting/tense/calm/sad)
  - RMS energy → Loudness level (低/中/高)
  - Tempo detection → BPM
  - Voice activity detection → has_voice flag

**Stage 5: Compose Result (85-100%)**
- Combine all results into standardized JSON
- Store in Redis: `analysis:{job_id}`, TTL 24h
- Clean up temp frame directory

### 3.3 Output Schema

```json
{
  "素材ID": "mat_a1b2c3d4e5f6",
  "时长秒": 32.5,
  "分辨率": "1920x1080",
  "帧率": 29.97,
  "编码": "h264",
  "视觉描述": "年轻女性在海边奔跑，夕阳映照海面，浪花拍打沙滩...",
  "语音文本": "我终于来到了梦想中的海边，这里比我想象的还要美...",
  "场景标签": ["户外","海边","夕阳","奔跑","沙滩"],
  "人物": ["女性主角"],
  "情绪": "激昂",
  "音频特征": {
    "bgm_type": "uplifting",
    "响度": "中",
    "bpm": 120,
    "has_voice": true
  }
}
```

### 3.4 Error Handling & Resilience

- Gemini API: 3 retries with exponential backoff, 30s timeout per call
- Overall task timeout: 30 minutes (Celery `task_time_limit`)
- Graceful degradation: if vision analysis fails, return partial results with error notes
- Temp files cleaned in task `on_failure` and `on_success` handlers

---

## 4. Render Service (Sub-module 2)

### 4.1 API

```
POST /media/render
  Request: {
    "project_id": "proj_001",
    "decision_json": { ... },
    "material_map": { "v001": "/data/videos/clip1.mp4", ... },
    "proxy": false,
    "output_format": "mp4"
  }
  Response: { "job_id": "uuid" }

GET /media/render/{job_id}/status
  Response: {
    "job_id": "uuid",
    "status": "processing|done|error",
    "progress": 0-100,
    "current_step": "preparing|rendering_segments|compositing|mixing_audio|finalizing",
    "result_url": "/data/output/proj_001_1080p.mp4",
    "proxy_url": "/data/output/proj_001_720p.mp4"
  }
```

### 4.2 Decision JSON Schema

```json
{
  "timeline": [{
    "clip_id": "c1",
    "material_id": "v001",
    "src_start": 0.0,
    "src_end": 5.2,
    "duration": 5.2,
    "transition_in":  { "type": "fade_black",   "duration_ms": 500 },
    "transition_out": { "type": "crossfade",     "duration_ms": 800 },
    "effects": [
      {"type": "zoom_in",   "params": {"start_scale": 1.0, "end_scale": 1.15}},
      {"type": "grayscale", "params": {}}
    ],
    "volume": 0.8,
    "speed": 1.0
  }],
  "subtitles": [{
    "text": "Hello World",
    "start_ms": 1200,
    "end_ms": 4200,
    "font": "Noto Sans CJK SC",
    "font_size": 48,
    "position": "bottom_center",
    "color": "white",
    "outline_color": "black",
    "outline_width": 2
  }],
  "bgm": {
    "material_id": "bgm001",
    "volume": 0.3,
    "fade_in_ms": 2000,
    "fade_out_ms": 3000,
    "loop": true
  },
  "output": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "video_bitrate": "8M",
    "audio_bitrate": "192k"
  }
}
```

### 4.3 Transitions (FFmpeg Filter Chain)

| Transition | FFmpeg Filter | Key Parameters |
|------------|--------------|----------------|
| **cut** | `concat` demuxer/filter | Direct concatenation, no transition effect |
| **crossfade** | `xfade` | `transition=fade:duration=0.8:offset=prev_dur-0.8` |
| **fade_black** | `fade` + `xfade` | `fade=t=out:d=0.5` on clip A, `fade=t=in:d=0.5` on clip B, or `xfade=fadeblack` |
| **wipe_left** | `xfade` | `transition=wiperight` (left-to-right wipe revealing next clip) |
| **blur_dissolve** | `xfade` | `transition=dissolve` with pre-blur, or `transition=fadegrays` |

### 4.4 Effects (FFmpeg Filter Chain)

| Effect | FFmpeg Filter Chain |
|--------|-------------------|
| **slow_motion** | `setpts=2.0*PTS` (video 0.5x) + `atempo=0.5` (audio sync) |
| **zoom_in** | `zoompan=z='min(zoom+0.0015,{end_scale})':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=WxH:fps={fps}` |
| **grayscale** | `hue=s=0` or `colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3` |
| **vignette** | `vignette=PI/4:max_eval=0` |

### 4.5 Audio Mixing

```
[bgm_input] → volume={bgm_vol} → afade=t=in:d={fade_in} → afade=t=out:st={out_pos}:d={fade_out} → [bgm_processed]
[clip_audio...] → concat → volume={voice_vol} → [voice_processed]
[bgm_processed][voice_processed] → amix=inputs=2:duration=longest:weights=1 1 → [final_audio]
```

- BGM looping: `stream_loop=-1` if BGM is shorter than total timeline
- Independent volume control per clip and BGM
- Fade in/out timing relative to BGM start/end

### 4.6 Subtitles (drawtext filter)

```
drawtext=text='{escaped_text}':
  fontfile=/fonts/{font}:
  fontsize={font_size}:
  fontcolor={color}:
  borderw={outline_width}:
  bordercolor={outline_color}:
  x={x_pos}:y={y_pos}:
  enable='between(t,{start_ms/1000},{end_ms/1000})'
```

Position mapping:
- `top_left` → `x=20:y=20`
- `top_center` → `x=(w-text_w)/2:y=20`
- `bottom_center` → `x=(w-text_w)/2:y=h-th-80`
- `custom` → uses `x` and `y` from params

### 4.7 Proxy Mode

When `proxy: true`:
- Resolution → max 1280x720 (maintaining aspect ratio)
- Video bitrate → 2M
- CRF → 28
- All overlays (subtitles, effects) preserved for preview fidelity
- Output filename suffixed with `_proxy`

### 4.8 A/V Sync Guarantees

- All time calculations in **milliseconds** (Python `int`), avoiding floating-point drift
- Speed change: `setpts` and `atempo` always applied together
- Use FFmpeg `-shortest` flag to trim to shortest stream
- Post-render: `ffprobe` validation — actual output duration vs expected, tolerance ±50ms
- Each clip segment rendered individually, then concatenated — prevents cumulative timing errors

---

## 5. Project Structure

```
video-factory/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── shared/
│   ├── setup.py
│   └── video_factory_shared/
│       ├── __init__.py
│       ├── models.py           # Dataclasses: MaterialMetadata, DecisionJSON, RenderJob
│       ├── schemas.py          # Pydantic: API request/response validation
│       ├── storage.py          # LocalStorage adapter (interface for future S3)
│       ├── ffmpeg_utils.py     # Common FFmpeg helpers (probing, extraction)
│       └── redis_client.py     # Redis connection manager + job state helpers
│
├── analysis-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── celery_app.py
│   └── app/
│       ├── main.py             # FastAPI app + routes
│       ├── config.py           # Settings from env vars
│       └── pipeline/
│           ├── __init__.py
│           ├── frame_extractor.py
│           ├── vision_analyzer.py
│           ├── audio_extractor.py
│           ├── transcriber.py
│           └── bgm_analyzer.py
│
├── render-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── celery_app.py
│   └── app/
│       ├── main.py             # FastAPI app + routes
│       ├── config.py
│       └── engine/
│           ├── __init__.py
│           ├── timeline.py     # Parse decision JSON → internal timeline model
│           ├── transitions.py  # Transition filter chain builders
│           ├── effects.py      # Effect filter chain builders
│           ├── audio_mixer.py  # Multi-track audio filter graph
│           ├── subtitle.py     # drawtext filter builder
│           └── composer.py     # Top-level FFmpeg command assembler
│
├── examples/
│   ├── sample_decision.json
│   ├── sample_video.mp4
│   └── sample_bgm.mp3
│
└── fonts/
    └── NotoSansCJKsc-Regular.otf
```

---

## 6. External API Dependencies & How to Apply

| Service | Purpose | Application Method | Cost |
|---------|---------|-------------------|------|
| **Google Gemini Pro Vision** | Scene visual analysis | [Google AI Studio](https://aistudio.google.com/apikey) → Get API key → Free tier: 15 RPM, 1,500 requests/day | Free tier available |
| **faster-whisper** | Speech-to-text (local) | `pip install faster-whisper` — downloads base model (~142MB) on first run | Free (local) |
| **librosa** | Audio analysis (local) | `pip install librosa` | Free (local) |
| **FFmpeg** | Video processing (local) | `apt-get install ffmpeg` in Docker | Free (local) |
| **Redis** | Message broker + cache | Docker image `redis:7-alpine` | Free (local) |

Environment variables required:
```
GEMINI_API_KEY=your_google_api_key
REDIS_URL=redis://redis:6379/0
DATA_DIR=/data
```

---

## 7. Docker Deployment

### 7.1 Building

```bash
docker-compose build
```

### 7.2 Running

```bash
docker-compose up -d
```

### 7.3 Services

| Service | Port | Description |
|---------|------|-------------|
| analysis-api | 8001 | Video analysis REST API |
| render-api | 8002 | Video rendering REST API |
| redis | 6379 | Celery broker + cache |

### 7.4 Volumes

| Path | Purpose |
|------|---------|
| `/data/videos` | Input video files |
| `/data/output` | Rendered output videos |
| `/data/temp` | Temporary frame extraction |

---

## 8. Example: End-to-End Render

See `examples/sample_decision.json` for a complete decision JSON that:
- Takes a 30-second sample video
- Splits into 3 clips with crossfade and fade_black transitions
- Applies zoom_in effect on first clip, grayscale on second
- Adds 2 subtitle entries
- Mixes BGM at 30% volume with 2s fade in/out
- Outputs 1080p30 H.264 MP4

---

## 9. Testing Strategy

- **Unit tests**: Each pipeline stage, each filter builder function
- **Integration tests**: Full analysis task with a short test video, full render task with sample decision JSON
- **Validation**: ffprobe output verification (duration, resolution, codec)
- **Mock**: Gemini API responses for deterministic vision analysis tests

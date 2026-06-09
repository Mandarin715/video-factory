# Video Understanding & Rendering Factory

视频理解与渲染工厂 — 包含视频分析管道和渲染引擎两个独立微服务。

## Architecture

```
redis (6379) ←→ analysis-api (8001) + analysis-worker
             ←→ render-api  (8002) + render-worker
```

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Google Gemini API Key ([Get one here](https://aistudio.google.com/apikey))

### 2. Setup

```bash
# Clone and enter project
git clone https://github.com/Mandarin715/video-factory.git
cd video-factory

# Create .env file
cp .env.example .env
# Edit .env: add your GEMINI_API_KEY

# Download subtitle font
mkdir -p fonts
curl -L -o fonts/NotoSansCJKsc-Regular.otf \
  "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"

# Generate sample video + BGM (requires local FFmpeg)
python examples/create_sample_video.py
```

### 3. Launch

```bash
docker-compose up -d
```

### 4. Analyze a Video

```bash
# Submit analysis job
curl -X POST http://localhost:8001/media/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_url": "/data/videos/sample_video.mp4"}'

# Check status (replace with actual job_id)
curl http://localhost:8001/media/analyze/{job_id}/status
```

### 5. Render a Video

```bash
# Submit render job
curl -X POST http://localhost:8002/media/render \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo_001",
    "decision_json": '"$(cat examples/sample_decision.json)"',
    "material_map": {
      "v001": "/data/videos/sample_video.mp4",
      "bgm001": "/data/videos/sample_bgm.mp3"
    },
    "proxy": false
  }'

# Check status
curl http://localhost:8002/media/render/{job_id}/status
```

### 6. Proxy Preview Mode

```bash
# Same as render, but with proxy: true for fast low-res preview
curl -X POST http://localhost:8002/media/render \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo_preview",
    "decision_json": ...,
    "material_map": {...},
    "proxy": true
  }'
```

## API Documentation

Once services are running:
- Analysis API docs: http://localhost:8001/docs
- Render API docs: http://localhost:8002/docs

## External API Dependencies

| Service | Purpose | How to Apply |
|---------|---------|--------------|
| Google Gemini Pro Vision | Scene visual analysis | [Google AI Studio](https://aistudio.google.com/apikey) → Free tier: 15 RPM, 1,500 req/day |
| faster-whisper (local) | Speech-to-text | Auto-downloaded on first run (~142MB base model) |
| librosa (local) | Audio BGM analysis | Installed via pip, no API key needed |
| FFmpeg (local) | Video processing | Installed in Docker image |

## Transitions

| Type | Description | Duration Configurable |
|------|-------------|----------------------|
| `cut` | Direct cut, no effect | N/A |
| `crossfade` | Smooth fade between clips | Yes (ms) |
| `fade_black` | Fade to/from black | Yes (ms) |
| `wipe_left` | Left-to-right wipe | Yes (ms) |
| `blur_dissolve` | Blur + dissolve transition | Yes (ms) |

## Effects

| Type | Description |
|------|-------------|
| `slow_motion` | Slow down clip (configurable factor) |
| `zoom_in` | Ken Burns zoom effect |
| `grayscale` | Black & white |
| `vignette` | Darkened corner vignette |

## Project Structure

See [Design Spec](docs/superpowers/specs/2026-06-09-video-factory-design.md) for full architecture details.

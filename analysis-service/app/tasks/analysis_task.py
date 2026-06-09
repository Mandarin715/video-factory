"""Celery task: 5-stage video analysis pipeline."""
import logging
from pathlib import Path
from video_factory_shared.ffmpeg_utils import get_video_info
from video_factory_shared.redis_client import get_redis, set_job_status, update_job_progress
from video_factory_shared.storage import LocalStorage
from app.pipeline.frame_extractor import FrameExtractor
from app.pipeline.vision_analyzer import VisionAnalyzer
from app.pipeline.audio_extractor import AudioExtractor
from app.pipeline.transcriber import transcribe
from app.pipeline.bgm_analyzer import analyze_bgm
from app.config import DATA_DIR
from celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="analysis.run_pipeline")
def run_analysis_pipeline(self, job_id: str, video_url: str):
    """5-stage video analysis pipeline."""
    storage = LocalStorage(DATA_DIR)
    video_path = storage.resolve_path(video_url)

    if not video_path.exists():
        return _fail_job(job_id, f"Video file not found: {video_url}")

    r = get_redis()
    set_job_status(r, "analysis", job_id, {
        "job_id": job_id, "status": "processing", "progress": 0,
        "current_step": "probing", "result": None
    })

    temp_dir = storage.create_temp_dir("analysis_")
    material_id = f"mat_{job_id.split('_')[-1]}"

    try:
        # Stage 1: Probe (0-5%)
        logger.info(f"[{job_id}] Stage 1: Probing video")
        update_job_progress(r, "analysis", job_id, 2, "probing")
        video_info = get_video_info(str(video_path))
        update_job_progress(r, "analysis", job_id, 5, "probing")

        # Stage 2: Extract frames (5-25%)
        logger.info(f"[{job_id}] Stage 2: Extracting frames")
        update_job_progress(r, "analysis", job_id, 5, "extracting_frames")
        extractor = FrameExtractor()
        frames = extractor.extract(str(video_path), temp_dir)
        update_job_progress(r, "analysis", job_id, 25, "extracting_frames")
        logger.info(f"[{job_id}] Extracted {len(frames)} frames")

        # Stage 3: Vision analysis (25-55%)
        logger.info(f"[{job_id}] Stage 3: Vision analysis")
        update_job_progress(r, "analysis", job_id, 25, "analyzing_vision")
        try:
            analyzer = VisionAnalyzer()
            vision_result = analyzer.analyze_frames(frames, sample_every=max(1, len(frames) // 10))
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            vision_result = {"visual_description": "", "scene_tags": [], "emotion": "", "characters": []}
        update_job_progress(r, "analysis", job_id, 55, "analyzing_vision")

        # Stage 4: Audio analysis (55-85%)
        logger.info(f"[{job_id}] Stage 4: Audio analysis")
        update_job_progress(r, "analysis", job_id, 55, "analyzing_audio")

        has_audio = video_info.get("has_audio", False)
        speech_text = ""
        audio_features = {"bgm_type": "none", "loudness": "中", "bpm": 0.0, "has_voice": False}

        if has_audio:
            audio_extractor = AudioExtractor()
            try:
                audio_path = audio_extractor.extract(str(video_path), temp_dir)
                update_job_progress(r, "analysis", job_id, 65, "analyzing_audio")

                if audio_path.exists():
                    speech_text = transcribe(audio_path)
                update_job_progress(r, "analysis", job_id, 75, "analyzing_audio")

                if audio_path.exists():
                    audio_features = analyze_bgm(audio_path)
            except Exception as e:
                logger.error(f"Audio analysis error: {e}")

        update_job_progress(r, "analysis", job_id, 85, "analyzing_audio")

        # Stage 5: Compose result (85-100%)
        logger.info(f"[{job_id}] Stage 5: Composing result")
        update_job_progress(r, "analysis", job_id, 90, "finalizing")

        result = {
            "素材ID": material_id,
            "时长秒": video_info["duration_sec"],
            "分辨率": video_info["resolution"],
            "帧率": video_info["framerate"],
            "编码": video_info["codec"],
            "视觉描述": vision_result.get("visual_description", ""),
            "语音文本": speech_text,
            "场景标签": vision_result.get("scene_tags", []),
            "人物": vision_result.get("characters", []),
            "情绪": vision_result.get("emotion", ""),
            "音频特征": audio_features,
        }

        set_job_status(r, "analysis", job_id, {
            "job_id": job_id, "status": "done", "progress": 100,
            "current_step": "done", "result": result
        })
        logger.info(f"[{job_id}] Analysis complete: {material_id}")

    except Exception as e:
        logger.exception(f"[{job_id}] Pipeline failed")
        _fail_job(job_id, str(e))
    finally:
        storage.cleanup_temp(temp_dir)

    return {"job_id": job_id, "status": "done"}


def _fail_job(job_id: str, error_msg: str):
    r = get_redis()
    set_job_status(r, "analysis", job_id, {
        "job_id": job_id, "status": "error", "progress": 0,
        "current_step": "error", "result": None, "error": error_msg,
    })

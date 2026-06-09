"""Celery task: parse decision JSON → build FFmpeg command → execute render."""
import subprocess
import logging
import re
from pathlib import Path
from video_factory_shared.redis_client import get_redis, set_job_status, update_job_progress
from app.engine.timeline import TimelineParser
from app.engine.composer import FFmpegComposer
from app.config import DATA_DIR, FONTS_DIR
from celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="render.run_pipeline")
def run_render_pipeline(self, job_id: str, project_id: str,
                        decision_json: dict, material_map: dict,
                        proxy: bool = False, output_format: str = "mp4"):
    """Render pipeline: parse → compose → execute FFmpeg."""
    r = get_redis()
    set_job_status(r, "render", job_id, {
        "job_id": job_id, "status": "processing", "progress": 0,
        "current_step": "preparing", "result_url": None, "proxy_url": None
    })

    try:
        # Step 1: Parse decision JSON
        update_job_progress(r, "render", job_id, 5, "preparing")
        parser = TimelineParser()
        decision = parser.parse(decision_json)
        update_job_progress(r, "render", job_id, 10, "preparing")

        # Step 2: Build output paths
        output_dir = Path(DATA_DIR) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = "_proxy" if proxy else ""
        output_filename = f"{project_id}{suffix}.{output_format}"
        output_path = output_dir / output_filename

        # Step 3: Build FFmpeg command
        update_job_progress(r, "render", job_id, 15, "rendering_segments")
        composer = FFmpegComposer(
            decision=decision,
            material_map=material_map,
            output_path=output_path,
            proxy=proxy,
            font_dir=FONTS_DIR,
        )
        cmd = composer.build_command()

        # Step 4: Execute FFmpeg with progress parsing
        update_job_progress(r, "render", job_id, 20, "compositing")
        logger.info(f"[{job_id}] Starting FFmpeg render: {output_filename}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        last_progress = 20
        stderr_lines = []
        for line in process.stderr:
            stderr_lines.append(line)
            if "time=" in line:
                time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
                if time_match and decision.timeline:
                    h, m, s, cs = map(int, time_match.groups())
                    current_sec = h * 3600 + m * 60 + s + cs / 100.0
                    total_dur = sum(c.duration for c in decision.timeline)
                    if total_dur > 0:
                        pct = 20 + int((current_sec / total_dur) * 70)
                        pct = min(90, pct)
                        if pct > last_progress:
                            last_progress = pct
                            update_job_progress(r, "render", job_id, pct, "compositing")

        process.wait(timeout=3600)

        if process.returncode != 0:
            stderr_full = "".join(stderr_lines[-50:])  # last 50 lines
            raise RuntimeError(f"FFmpeg failed with code {process.returncode}: {stderr_full[:500]}")

        # Step 5: Finalize
        update_job_progress(r, "render", job_id, 95, "finalizing")

        result_url = str(output_path)
        result = {
            "job_id": job_id, "status": "done", "progress": 100,
            "current_step": "done", "result_url": result_url,
        }
        if proxy:
            result["proxy_url"] = result_url

        set_job_status(r, "render", job_id, result)
        logger.info(f"[{job_id}] Render complete: {result_url}")

    except Exception as e:
        logger.exception(f"[{job_id}] Render failed")
        set_job_status(r, "render", job_id, {
            "job_id": job_id, "status": "error", "progress": 0,
            "current_step": "error", "result_url": None, "error": str(e),
        })
        return {"job_id": job_id, "status": "error", "error": str(e)}

    return {"job_id": job_id, "status": "done"}

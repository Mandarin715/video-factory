"""FastAPI application for video render service."""
import uuid
from fastapi import FastAPI, HTTPException
from app.tasks.render_task import run_render_pipeline
from video_factory_shared.schemas import RenderRequest, RenderResponse, RenderStatusResponse
from video_factory_shared.redis_client import get_redis, get_job_status

app = FastAPI(title="Video Render Service", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "render"}


@app.post("/media/render", response_model=RenderResponse)
async def render_video(req: RenderRequest):
    job_id = f"render_{uuid.uuid4().hex[:12]}"
    task = run_render_pipeline.delay(
        job_id, req.project_id,
        req.decision_json, req.material_map,
        req.proxy, req.output_format
    )
    return RenderResponse(job_id=job_id)


@app.get("/media/render/{job_id}/status", response_model=RenderStatusResponse)
async def get_render_status(job_id: str):
    r = get_redis()
    data = get_job_status(r, "render", job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return RenderStatusResponse(**data)

"""FastAPI application for video analysis service."""
import uuid
from fastapi import FastAPI, HTTPException
from app.tasks.analysis_task import run_analysis_pipeline
from video_factory_shared.schemas import (
    AnalyzeRequest, AnalyzeResponse, AnalyzeStatusResponse
)
from video_factory_shared.redis_client import get_redis, get_job_status

app = FastAPI(title="Video Analysis Service", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analysis"}


@app.post("/media/analyze", response_model=AnalyzeResponse)
async def analyze_video(req: AnalyzeRequest):
    job_id = f"analysis_{uuid.uuid4().hex[:12]}"
    task = run_analysis_pipeline.delay(job_id, req.video_url)
    return AnalyzeResponse(job_id=job_id, status="queued")


@app.get("/media/analyze/{job_id}/status", response_model=AnalyzeStatusResponse)
async def get_analysis_status(job_id: str):
    r = get_redis()
    data = get_job_status(r, "analysis", job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return AnalyzeStatusResponse(**data)

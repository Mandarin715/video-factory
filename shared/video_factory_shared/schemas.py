"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    video_url: str = Field(..., description="Path to video file or downloadable URL")


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str = "queued"


class AnalyzeStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    current_step: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None


class RenderRequest(BaseModel):
    project_id: str
    decision_json: dict
    material_map: dict = Field(default_factory=dict)
    proxy: bool = False
    output_format: str = "mp4"


class RenderResponse(BaseModel):
    job_id: str


class RenderStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    current_step: str = ""
    result_url: Optional[str] = None
    proxy_url: Optional[str] = None
    error: Optional[str] = None

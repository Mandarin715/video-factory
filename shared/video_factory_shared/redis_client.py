"""Redis connection manager and job state helpers."""
import json
import os
from typing import Optional
import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = 86400  # 24 hours


def get_redis() -> redis.Redis:
    """Get a Redis connection from the pool."""
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def set_job_status(r: redis.Redis, prefix: str, job_id: str, data: dict, ttl: int = DEFAULT_TTL):
    """Store job result/status in Redis."""
    key = f"{prefix}:{job_id}"
    r.setex(key, ttl, json.dumps(data, ensure_ascii=False))


def get_job_status(r: redis.Redis, prefix: str, job_id: str) -> Optional[dict]:
    """Retrieve job result/status from Redis."""
    key = f"{prefix}:{job_id}"
    raw = r.get(key)
    if raw:
        return json.loads(raw)
    return None


def update_job_progress(r: redis.Redis, prefix: str, job_id: str, progress: int, current_step: str):
    """Update progress and current_step for a running job."""
    key = f"{prefix}:{job_id}"
    existing = r.get(key)
    if existing:
        data = json.loads(existing)
        data["progress"] = progress
        data["current_step"] = current_step
        data["status"] = "processing"
        r.setex(key, DEFAULT_TTL, json.dumps(data, ensure_ascii=False))

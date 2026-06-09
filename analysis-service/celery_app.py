"""Celery application configuration for analysis service."""
from celery import Celery
from app.config import REDIS_URL, TASK_TIME_LIMIT

app = Celery(
    "analysis-service",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.analysis_task"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_time_limit=TASK_TIME_LIMIT,
    task_soft_time_limit=TASK_TIME_LIMIT - 60,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

"""Render service configuration."""
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATA_DIR = os.getenv("DATA_DIR", "/data")
FONTS_DIR = os.getenv("FONTS_DIR", "/fonts")

PROXY_WIDTH = int(os.getenv("PROXY_WIDTH", "1280"))
PROXY_HEIGHT = int(os.getenv("PROXY_HEIGHT", "720"))
PROXY_BITRATE = os.getenv("PROXY_BITRATE", "2M")
PROXY_CRF = int(os.getenv("PROXY_CRF", "28"))

TASK_TIME_LIMIT = int(os.getenv("TASK_TIME_LIMIT", "3600"))

"""Analysis service configuration from environment variables."""
import os


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATA_DIR = os.getenv("DATA_DIR", "/data")

EXTRACT_FPS = float(os.getenv("EXTRACT_FPS", "1.0"))
MAX_FRAMES = int(os.getenv("MAX_FRAMES", "60"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
VISION_TIMEOUT_SEC = int(os.getenv("VISION_TIMEOUT_SEC", "30"))
VISION_MAX_RETRIES = int(os.getenv("VISION_MAX_RETRIES", "3"))

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

TASK_TIME_LIMIT = int(os.getenv("TASK_TIME_LIMIT", "1800"))

"""Local filesystem storage adapter."""
import shutil
from pathlib import Path


class LocalStorage:
    """Adapter for local filesystem operations. Interface designed for
    future extension to S3/MinIO via a common StorageAdapter ABC."""

    def __init__(self, base_dir: str = "/data"):
        self.base_dir = Path(base_dir)
        self.videos_dir = self.base_dir / "videos"
        self.output_dir = self.base_dir / "output"
        self.temp_dir = self.base_dir / "temp"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.videos_dir, self.output_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: str) -> Path:
        """Resolve a path. If absolute and exists, return as-is.
        If relative, resolve against videos_dir."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.videos_dir / p

    def ensure_output_path(self, filename: str) -> Path:
        return self.output_dir / filename

    def create_temp_dir(self, prefix: str = "job_") -> Path:
        import uuid
        temp_path = self.temp_dir / f"{prefix}{uuid.uuid4().hex[:8]}"
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path

    def cleanup_temp(self, path: Path):
        if path.exists() and path.is_relative_to(self.temp_dir):
            shutil.rmtree(path, ignore_errors=True)

    def file_exists(self, path: str) -> bool:
        return self.resolve_path(path).exists()

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install shared library first
COPY shared/ /tmp/shared/
RUN pip install --no-cache-dir /tmp/shared/ && rm -rf /tmp/shared

COPY analysis-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analysis-service/ .

# Pre-download Whisper base model during build
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')" || true

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

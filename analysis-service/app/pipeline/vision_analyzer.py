"""Vision analysis using Google Gemini Pro Vision with retry logic."""
import json
import logging
from pathlib import Path
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
from app.config import GEMINI_API_KEY, GEMINI_MODEL, VISION_TIMEOUT_SEC, VISION_MAX_RETRIES

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Analyzes video frames using Gemini Pro Vision."""

    PROMPT_TEMPLATE = """Analyze this video frame image in detail. Return ONLY valid JSON (no markdown, no code blocks):

{
  "visual_description": "Detailed scene description in Chinese, 2-4 sentences",
  "scene_tags": ["tag1", "tag2", "tag3", ...],
  "emotion": "激昂/悲伤/紧张/平静/温馨/悬疑/欢快/压抑",
  "characters": ["角色描述1", "角色描述2"]
}

Scene tag categories: indoor/outdoor, location type, time of day, weather, action type.
Emotion: pick the SINGLE most dominant emotional tone from the list.
Characters: describe each visible person concisely in Chinese, empty array if none."""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    @retry(
        stop=stop_after_attempt(VISION_MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception_type((Exception,)),
    )
    def _call_gemini(self, image_path: Path) -> dict:
        """Call Gemini Vision API for a single frame with retry."""
        import PIL.Image
        img = PIL.Image.open(image_path)

        response = self.model.generate_content(
            [self.PROMPT_TEMPLATE, img],
            request_options={"timeout": VISION_TIMEOUT_SEC * 1000},
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    def analyze_frame(self, image_path: Path) -> Optional[dict]:
        """Analyze a single frame. Returns parsed dict or None on failure."""
        try:
            return self._call_gemini(image_path)
        except Exception as e:
            logger.warning(f"Gemini analysis failed for {image_path}: {e}")
            return None

    def analyze_frames(self, frame_paths: list[Path], sample_every: int = 3) -> dict:
        """Analyze multiple frames, sampling every N frames.
        Aggregates results: deduplicates tags, votes on dominant emotion,
        concatenates descriptions."""
        results = []
        for i, fp in enumerate(frame_paths):
            if i % sample_every != 0:
                continue
            logger.info(f"Analyzing frame {i+1}/{len(frame_paths)}: {fp.name}")
            result = self.analyze_frame(fp)
            if result:
                results.append(result)

        if not results:
            return {
                "visual_description": "",
                "scene_tags": [],
                "emotion": "",
                "characters": [],
            }

        all_tags = []
        all_emotions = []
        all_characters = []
        descriptions = []

        for r in results:
            descriptions.append(r.get("visual_description", ""))
            all_tags.extend(r.get("scene_tags", []))
            all_emotions.append(r.get("emotion", ""))
            all_characters.extend(r.get("characters", []))

        seen = set()
        unique_tags = []
        for tag in all_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        emotion_counts = {}
        for e in all_emotions:
            if e:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1
        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else ""

        seen_chars = set()
        unique_chars = []
        for c in all_characters:
            if c not in seen_chars:
                seen_chars.add(c)
                unique_chars.append(c)

        return {
            "visual_description": " ".join(descriptions),
            "scene_tags": unique_tags[:15],
            "emotion": dominant_emotion,
            "characters": unique_chars[:10],
        }

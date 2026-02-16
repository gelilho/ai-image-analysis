"""Detects AI-generated images and stock photos."""

import os
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
import torch
from loguru import logger
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification

from .abstract_image_analyzer import AbstractImageAnalyzer

STOCK_DOMAINS = [
    "shutterstock", "gettyimages", "istockphoto", "depositphotos",
    "adobestock", "dreamstime", "alamy", "123rf", "pixabay", "unsplash",
]


class GenAIDetectionAnalyzer(AbstractImageAnalyzer):
    """Detects AI-generated images using a SigLIP classifier and flags stock photos."""

    def __init__(self, local_model_path: str | None = None):
        self.ai_detector_model = None
        self.ai_detector_processor = None
        self.device = None
        self.local_model_path = local_model_path
        self._load_model()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load SigLIP model from local path, env var, or HuggingFace."""
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model_path = self._resolve_model_path()

            if model_path:
                logger.debug(f"Loading AI model from: {model_path}")
            else:
                model_path = "Ateeqq/ai-vs-human-image-detector"
                logger.info(f"No local model found, using HuggingFace: {model_path}")

            self.ai_detector_processor = AutoImageProcessor.from_pretrained(
                model_path, use_fast=False
            )
            self.ai_detector_model = SiglipForImageClassification.from_pretrained(model_path)
            self.ai_detector_model.to(self.device)
            self.ai_detector_model.eval()
            logger.info("AI detection model loaded")

        except Exception as e:
            logger.error(f"Failed to load AI detection model: {e}")
            self.ai_detector_model = None
            self.ai_detector_processor = None
            self.device = None

    def _resolve_model_path(self) -> str | None:
        """Check local_model_path, then AI_MODEL_PATH env var."""
        if self.local_model_path:
            p = Path(self.local_model_path)
            if p.exists():
                return str(p)
            logger.warning(f"Provided path does not exist: {p}")

        env_path = os.getenv("AI_MODEL_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_images(self, image_urls: list[str]) -> dict[str, Any]:
        """Analyze images for AI generation and stock photo usage."""
        if not image_urls:
            return {
                "risk_score": 0.0, "indicators": [], "ai_detected": False,
                "analysis_details": {"images_analyzed": 0},
            }

        indicators: list[dict[str, Any]] = []
        risk_score = 0.0
        ai_count = 0

        for idx, url in enumerate(image_urls[:5]):
            try:
                ai_result = self.check_ai_generated(url)
                if ai_result.get("is_ai"):
                    ai_count += 1
                    indicators.append({
                        "type": "IMAGE", "indicator": "ai_generated_image",
                        "severity": "HIGH",
                        "details": f"AI-generated image ({ai_result.get('confidence', 0):.0%} confidence)",
                        "image_index": idx,
                    })
                    risk_score = max(risk_score, 0.95)

                if is_stock_photo(url):
                    indicators.append({
                        "type": "IMAGE", "indicator": "stock_photo_detected",
                        "severity": "HIGH", "details": "Stock photo URL detected",
                        "image_index": idx,
                    })
                    risk_score = max(risk_score, 0.9)

            except Exception as e:
                logger.warning(f"Failed to analyze image {idx}: {e}")
                indicators.append({
                    "type": "IMAGE", "indicator": "image_analysis_error",
                    "severity": "LOW", "details": f"Could not analyze image {idx + 1}",
                    "image_index": idx,
                })

        if ai_count >= 2:
            indicators.append({
                "type": "IMAGE", "indicator": "multiple_ai_images",
                "severity": "CRITICAL",
                "details": f"{ai_count} AI-generated images detected",
            })
            risk_score = 1.0

        return {
            "risk_score": min(risk_score, 1.0),
            "indicators": indicators,
            "ai_detected": ai_count > 0,
            "analysis_details": {
                "images_analyzed": len(image_urls[:5]),
                "ai_images_found": ai_count,
            },
        }

    # ------------------------------------------------------------------
    # AI detection
    # ------------------------------------------------------------------

    def check_ai_generated(self, image_url_or_path: str) -> dict[str, Any]:
        """Run SigLIP classifier on a single image."""
        if not self.ai_detector_model or not self.ai_detector_processor:
            return {"is_ai": False, "confidence": 0.0, "error": "Model not loaded"}

        try:
            image = _load_pil_image(image_url_or_path)
            if image.mode != "RGB":
                image = image.convert("RGB")

            inputs = self.ai_detector_processor(images=image, return_tensors="pt")
            if self.device:
                inputs = inputs.to(self.device)

            with torch.no_grad():
                logits = self.ai_detector_model(**inputs).logits

            idx = logits.argmax(-1).item()
            label = self.ai_detector_model.config.id2label[idx]
            probs = torch.softmax(logits, dim=-1)
            confidence = probs[0, idx].item()

            class_probs = {
                self.ai_detector_model.config.id2label[i]: probs[0, i].item()
                for i in self.ai_detector_model.config.id2label
            }

            is_ai = label.lower() == "ai"
            if is_ai:
                logger.info(f"AI image detected: {confidence:.0%} confidence")

            return {
                "is_ai": is_ai,
                "confidence": confidence,
                "predicted_label": label,
                "class_probabilities": class_probs,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return {"is_ai": False, "confidence": 0.0, "error": str(e)}
        except Exception as e:
            logger.error(f"AI detection failed: {e}")
            return {"is_ai": False, "confidence": 0.0, "error": str(e)}


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _load_pil_image(url_or_path: str) -> Image.Image:
    """Load a PIL Image from URL or file path."""
    if url_or_path.startswith("file://"):
        return Image.open(url_or_path.replace("file://", ""))
    if url_or_path.startswith(("http://", "https://")):
        resp = requests.get(url_or_path, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    return Image.open(url_or_path)


def is_stock_photo(url: str) -> bool:
    """Check if URL belongs to a known stock photo domain."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in STOCK_DOMAINS)

"""Gemini-based content analyzer for image analysis.

Uses the google-genai SDK with API key auth (no Vertex AI / GCP required).
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import requests
from google import genai
from google.genai import types
from loguru import logger

from .abstract_image_analyzer import AbstractImageAnalyzer
from .data_loader import load_feature_lists
from .images import ImageConfig, ImageValidator
from .json_utils import clean_json_response
from .prompt_builder import build_analysis_prompt
from .sku_estimator import estimate_sku

_MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".pdf": "application/pdf",
}


class GeminiContentAnalyzer(AbstractImageAnalyzer):
    """Content analyzer using Google Gemini for image understanding."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-pro",
        temperature: float = 0.3,
        image_config: Optional[ImageConfig] = None,
    ) -> None:
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Gemini API key required. Pass api_key= or set GEMINI_API_KEY."
            )

        self.client = genai.Client(api_key=resolved_key)
        self.model_name = model_name
        self.temperature = temperature
        self.image_validator = ImageValidator(config=image_config or ImageConfig())

        features = load_feature_lists()
        self.retailer_list = features["retailer_list"]
        self.product_list = features["product_list"]
        self.vertical_list = features["vertical_list"]
        self.family_list = features["family_list"]
        self.model_list = features["model_list"]

        logger.info(f"GeminiContentAnalyzer ready (model={model_name})")

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_image_bytes(url: str) -> tuple[bytes, str]:
        """Fetch image bytes and mime type from URL or local path."""
        if url.startswith(("http://", "https://")):
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            return resp.content, mime

        path = url.replace("file://", "") if url.startswith("file://") else url
        data = Path(path).read_bytes()
        ext = Path(path).suffix.lower()
        return data, _MIME_MAP.get(ext, "image/jpeg")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_images(self, image_urls: list[str]) -> dict[str, Any]:
        """Analyze images using Gemini for content understanding."""
        if not image_urls:
            return {
                "risk_score": 0.0, "indicators": [],
                "analysis_details": {"images_analyzed": 0},
                "summary": "No images provided for analysis",
            }

        indicators: list[dict[str, Any]] = []
        risk_score = 0.0
        analyses: list[dict[str, Any]] = []

        for idx, url in enumerate(image_urls[:10]):
            result = self._analyze_one(url, idx, indicators)
            if result:
                analyses.append(result)
                risk_score = self._update_risk(result, risk_score, idx, indicators)

        sku = estimate_sku(analyses)
        summary = _generate_summary(analyses, indicators)

        return {
            "risk_score": risk_score,
            "indicators": indicators,
            "analysis_details": {"images_analyzed": len(analyses), "individual_analyses": analyses},
            "summary": summary,
            "sku": sku,
        }

    # ------------------------------------------------------------------
    # Per-image analysis
    # ------------------------------------------------------------------

    def _analyze_one(
        self, url: str, idx: int, indicators: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Load, validate, and analyze a single image."""
        try:
            image_bytes, mime = self._load_image_bytes(url)
            vr = self.image_validator.validate_and_process(image_bytes, idx)
            if not vr.valid:
                indicators.append({
                    "type": "ERROR", "indicator": vr.error_type.value,
                    "severity": "LOW",
                    "details": f"Image {idx + 1}: {vr.message}",
                    "image_index": idx,
                })
                return None

            part = types.Part.from_bytes(data=vr.processed_data, mime_type=mime)
            return self._call_gemini(part, url, idx)
        except Exception as e:
            logger.warning(f"Failed to analyze image {idx}: {e}")
            indicators.append({
                "type": "ERROR", "indicator": "analysis_failure",
                "severity": "LOW",
                "details": f"Could not analyze image {idx + 1}: {e}",
                "image_index": idx,
            })
            return None

    def _call_gemini(
        self, image_part: types.Part, url: str, index: int
    ) -> dict[str, Any] | None:
        """Call Gemini API with retries and parse JSON response."""
        prompt = build_analysis_prompt(
            self.retailer_list, self.product_list,
            self.vertical_list, self.family_list, self.model_list,
        )
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=4096,
            response_mime_type="application/json",
        )

        for attempt in range(5):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, image_part],
                    config=config,
                )
                text = resp.text or ""
                if not text:
                    logger.warning(f"Empty Gemini response for image {index}")
                    continue

                cleaned = clean_json_response(text)
                if not cleaned:
                    raise json.JSONDecodeError("Empty after cleaning", text, 0)

                parsed = json.loads(cleaned)
                if not isinstance(parsed, dict):
                    logger.error(f"Image {index}: expected dict, got {type(parsed).__name__}")
                    return None

                parsed["image_url"] = url
                parsed["image_index"] = index
                return parsed

            except json.JSONDecodeError as e:
                if attempt < 4:
                    logger.warning(f"Attempt {attempt + 1} JSON error for image {index}: {e.msg}")
                    time.sleep(2**attempt)
                else:
                    logger.error(f"All retries failed for image {index}: {e.msg}")

        return None

    # ------------------------------------------------------------------
    # Risk / indicator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _update_risk(
        analysis: dict[str, Any], current: float, idx: int,
        indicators: list[dict[str, Any]],
    ) -> float:
        """Update risk score and append indicators based on analysis."""
        risk = current

        if analysis.get("contains_harmful_content"):
            indicators.append({
                "type": "CONTENT", "indicator": "harmful_content_detected",
                "severity": "HIGH",
                "details": f"Image {idx + 1}: {analysis.get('harmful_content_type', 'Unknown')}",
                "image_index": idx,
            })
            risk = max(risk, 0.8)

        if analysis.get("on_running_related") and analysis.get("on_running_confidence", 0) > 0.7:
            indicators.append({
                "type": "BRAND", "indicator": "on_running_content",
                "severity": "INFO",
                "details": f"Image {idx + 1}: {analysis.get('on_running_details', 'On Running')}",
                "image_index": idx,
            })

        extracted = analysis.get("extracted_fields", [])
        if extracted:
            indicators.append({
                "type": "TEXT", "indicator": "fields_extracted",
                "severity": "INFO",
                "details": f"Image {idx + 1}: {len(extracted)} fields extracted",
                "image_index": idx,
            })

        if _is_suspicious(analysis):
            indicators.append({
                "type": "CONTENT", "indicator": "suspicious_pattern",
                "severity": "MEDIUM",
                "details": f"Image {idx + 1}: Suspicious content pattern",
                "image_index": idx,
            })
            risk = max(risk, 0.6)

        return risk


# ------------------------------------------------------------------
# Module-level helpers (stateless)
# ------------------------------------------------------------------

def _is_suspicious(analysis: dict[str, Any]) -> bool:
    """Check if analysis indicates suspicious content."""
    checks = [
        analysis.get("is_product_image") and analysis.get("image_quality") == "low",
        len(analysis.get("detected_brands", [])) > 3,
        analysis.get("contains_harmful_content") and analysis.get("is_product_image"),
        analysis.get("safety_score", 1.0) < 0.3,
        any(
            lbl.get("label", "").lower() in ("adversarial", "off_topic", "unrelated")
            and lbl.get("confidence", 0) > 70
            for lbl in analysis.get("classification_labels", [])
        ),
    ]
    return any(checks)


def _generate_summary(analyses: list[dict[str, Any]], indicators: list[dict[str, Any]]) -> str:
    """Generate a human-readable summary."""
    if not analyses:
        return "No images were successfully analyzed."

    parts = [f"Analyzed {len(analyses)} images."]
    counts = {
        "harmful": sum(1 for a in analyses if a.get("contains_harmful_content")),
        "on_running": sum(1 for a in analyses if a.get("on_running_related")),
        "with_text": sum(1 for a in analyses if a.get("extracted_fields")),
        "products": sum(1 for a in analyses if a.get("is_product_image")),
        "brands": sum(1 for a in analyses if a.get("brand")),
    }
    if counts["harmful"]:
        parts.append(f"{counts['harmful']} contain harmful content.")
    if counts["on_running"]:
        parts.append(f"{counts['on_running']} related to On Running.")
    if counts["with_text"]:
        parts.append(f"{counts['with_text']} with extracted text fields.")
    if counts["products"]:
        parts.append(f"{counts['products']} product images.")
    if counts["brands"]:
        parts.append(f"{counts['brands']} with brand detection.")

    high = sum(1 for i in indicators if i.get("severity") == "HIGH")
    if high:
        parts.append(f"{high} high-severity issues.")
    return " ".join(parts)

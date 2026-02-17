"""Image Analysis Handler — orchestrates AI detection + Gemini content analysis."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .analyzers.gemini_content_analyzer import GeminiContentAnalyzer
from .analyzers.genai_detection_analyzer import GenAIDetectionAnalyzer
from .exceptions import ImageAnalysisError, ValidationError

_RISK_ACTIONS = {
    "CRITICAL": "Immediate blocking and investigation required",
    "HIGH": "Block transaction and flag for review",
    "MEDIUM": "Manual review required before approval",
    "LOW": "Can proceed with normal processing",
    "ERROR": "System error - manual intervention needed",
}


class ImageAnalysisHandler:
    """Runs AI detection and content analysis, combines into a risk assessment."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.model_version = "v1.0"
        self.max_images = self.config.get("max_images", 10)
        self.enable_gemini = self.config.get("enable_gemini", True)
        self.enable_ai_detection = self.config.get("enable_ai_detection", True)
        self.risk_threshold_high = self.config.get("risk_threshold_high", 0.8)
        self.risk_threshold_medium = self.config.get("risk_threshold_medium", 0.5)

        self.ai_detector: GenAIDetectionAnalyzer | None = None
        self.content_analyzer: GeminiContentAnalyzer | None = None

    def initialize(self) -> None:
        """Create analyzer instances."""
        if self.enable_ai_detection:
            try:
                self.ai_detector = GenAIDetectionAnalyzer(
                    local_model_path=self.config.get("ai_model_path"),
                )
            except Exception as e:
                logger.warning(f"AI detection disabled: {e}")
                self.ai_detector = None

        if self.enable_gemini:
            try:
                self.content_analyzer = GeminiContentAnalyzer(
                    api_key=self.config.get("gemini_api_key"),
                    model_name=self.config.get("gemini_model", "gemini-2.5-pro"),
                    temperature=0.3,
                )
            except Exception as e:
                logger.warning(f"Gemini disabled: {e}")
                self.content_analyzer = None

    # ── Input validation ─────────────────────────────────────────

    def validate_input(self, data: dict[str, Any]) -> None:
        if "image_urls" not in data:
            raise ValidationError("Missing required field: image_urls")

        urls = data["image_urls"]
        if not isinstance(urls, list):
            raise ValidationError("image_urls must be a list")
        if not urls:
            raise ValidationError("image_urls cannot be empty")
        if len(urls) > self.max_images:
            raise ValidationError(f"Too many images: {len(urls)} (max: {self.max_images})")

        for i, url in enumerate(urls):
            if not isinstance(url, str) or not url.strip():
                raise ValidationError(f"Image URL at index {i} must be a non-empty string")

    # ── Preprocess ───────────────────────────────────────────────

    def preprocess(self, data: dict[str, Any]) -> dict[str, Any]:
        result = {
            "timestamp": datetime.now().isoformat(),
            "image_urls": data.get("image_urls", []),
            "analysis_config": {
                "enable_ai_detection": self.enable_ai_detection and self.ai_detector is not None,
                "enable_content_analysis": self.enable_gemini and self.content_analyzer is not None,
            },
        }
        return result

    # ── Process ──────────────────────────────────────────────────

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        start = time.time()
        urls = data.get("image_urls", [])
        config = data.get("analysis_config", {})

        try:
            ai_result = self._run_ai_detection(urls, config)
            content_result = self._run_content_analysis(urls, config)
            combined = self._combine(ai_result, content_result)
            level, rec = self._determine_final_assessment(combined)

            return {
                "model_version": self.model_version,
                "analysis_results": {
                    k: v for k, v in [
                        ("ai_detection", ai_result),
                        ("content_analysis", content_result),
                    ] if v is not None
                },
                "combined_assessment": combined,
                "final_assessment": {
                    "risk_level": level,
                    "overall_risk_score": combined["combined_risk_score"],
                    "recommendation": rec,
                    "confidence": combined["confidence"],
                },
                "processing_details": {
                    "processing_time_ms": int((time.time() - start) * 1000),
                    "images_analyzed": len(urls),
                },
            }
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return {
                "final_assessment": {
                    "risk_level": "ERROR",
                    "overall_risk_score": 0.0,
                    "recommendation": "SYSTEM_ERROR",
                },
                "error": str(e),
            }

    def _run_ai_detection(
        self, urls: list[str], config: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.ai_detector or not config.get("enable_ai_detection", True):
            return None
        result = self.ai_detector.analyze_images(urls)
        logger.info(f"AI detection complete: {result.get('ai_detected', False)}")
        return result

    def _run_content_analysis(
        self, urls: list[str], config: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.content_analyzer or not config.get("enable_content_analysis", True):
            return None
        result = self.content_analyzer.analyze_images(urls)
        logger.info(f"Content analysis complete: risk_score={result.get('risk_score', 0)}")
        return result

    # ── Combine results ──────────────────────────────────────────

    def _combine(
        self,
        ai: dict[str, Any] | None,
        content: dict[str, Any] | None,
    ) -> dict[str, Any]:
        indicators: list[dict[str, Any]] = []
        ai_count = 0
        harmful = False

        if ai:
            indicators.extend(ai.get("indicators", []))
            ai_count = ai.get("analysis_details", {}).get("ai_images_found", 0)
        if content:
            indicators.extend(content.get("indicators", []))
            for a in content.get("analysis_details", {}).get("individual_analyses", []):
                if a.get("contains_harmful_content"):
                    harmful = True
                    break

        # Risk: weighted average if both present, otherwise take whichever exists
        if ai and content:
            score = ai.get("risk_score", 0.0) * 0.6 + content.get("risk_score", 0.0) * 0.4
        elif ai:
            score = ai.get("risk_score", 0.0)
        elif content:
            score = content.get("risk_score", 0.0)
        else:
            score = 0.0

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        indicators.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 5))

        return {
            "indicators": indicators,
            "combined_risk_score": min(score, 1.0),
            "ai_images_detected": ai_count,
            "harmful_content_detected": harmful,
            "confidence": 0.9 if ai_count > 0 else 0.75,
        }

    def _determine_final_assessment(self, c: dict[str, Any]) -> tuple[str, str]:
        score = c.get("combined_risk_score", 0.0)
        ai_count = c.get("ai_images_detected", 0)

        if ai_count >= 2:
            return "CRITICAL", "BLOCK_IMMEDIATELY"
        if c.get("harmful_content_detected"):
            return "HIGH", "MANUAL_REVIEW_URGENT"
        if score >= self.risk_threshold_high or ai_count > 0:
            return "HIGH", "BLOCK_AND_INVESTIGATE"
        if score >= self.risk_threshold_medium:
            return "MEDIUM", "MANUAL_REVIEW"
        return "LOW", "APPROVE"

    # ── Postprocess ──────────────────────────────────────────────

    def postprocess(self, result: dict[str, Any]) -> dict[str, Any]:
        fa = result.get("final_assessment")
        if not fa:
            result["final_assessment"] = {
                "risk_level": "UNKNOWN",
                "overall_risk_score": 0.0,
                "recommendation": "ERROR",
            }
            fa = result["final_assessment"]

        fa["overall_risk_score"] = round(fa.get("overall_risk_score", 0.0), 3)
        fa["confidence"] = round(fa.get("confidence", 0.0), 2)

        if "combined_assessment" in result:
            result["combined_assessment"]["indicators"] = result["combined_assessment"].get(
                "indicators", [],
            )[:10]

        result["summary"] = {
            "risk_level": fa["risk_level"],
            "ai_detected": result.get("combined_assessment", {}).get("ai_images_detected", 0) > 0,
            "action_required": _RISK_ACTIONS.get(fa["risk_level"], "Unknown"),
        }
        return result

    # ── Meta ─────────────────────────────────────────────────────

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "name": "ImageAnalysisHandler",
            "version": self.model_version,
        }

    def health_check(self) -> dict[str, Any]:
        healthy = self.ai_detector is not None or self.content_analyzer is not None
        return {
            "healthy": healthy,
            "version": self.model_version,
            "components": {
                "ai_detector": self.ai_detector is not None,
                "content_analyzer": self.content_analyzer is not None,
            },
        }

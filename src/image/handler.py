"""
Image Analysis Handler.
Combines AI detection and content analysis for comprehensive image assessment.
"""

import time
from datetime import datetime
from typing import Any, Dict

from loguru import logger

from .analyzers.gemini_content_analyzer import GeminiContentAnalyzer
from .analyzers.genai_detection_analyzer import GenAIDetectionAnalyzer
from .exceptions import ImageAnalysisError, ValidationError


class ImageAnalysisHandler:
    """
    Comprehensive image analysis handler combining AI detection and content analysis.

    Features:
    - AI-generated image detection using specialized ML models
    - Content analysis including OCR, brand detection, and safety assessment
    - Stock photo detection
    - Combined risk scoring and fraud indicators
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the image analysis handler."""
        self.model_version = "v1.0"

        # Configuration
        self.config = config or {}
        self.max_images = self.config.get("max_images", 10)
        self.enable_gemini = self.config.get("enable_gemini", True)
        self.enable_ai_detection = self.config.get("enable_ai_detection", True)

        # Risk thresholds
        self.risk_threshold_high = self.config.get("risk_threshold_high", 0.8)
        self.risk_threshold_medium = self.config.get("risk_threshold_medium", 0.5)

        # Analyzers (to be initialized)
        self.ai_detector: GenAIDetectionAnalyzer | None = None
        self.content_analyzer: GeminiContentAnalyzer | None = None

        self._initialized = False

    def initialize(self) -> None:
        """Initialize both image analyzers."""
        try:
            start_time = time.time()

            # Initialize AI detection analyzer
            if self.enable_ai_detection:
                logger.info("Initializing AI detection analyzer...")
                self.ai_detector = GenAIDetectionAnalyzer(
                    local_model_path=self.config.get("ai_model_path")
                )
                logger.info("AI detection analyzer initialized")

            # Initialize Gemini content analyzer
            if self.enable_gemini:
                logger.info("Initializing Gemini content analyzer...")
                self.content_analyzer = GeminiContentAnalyzer(
                    api_key=self.config.get("gemini_api_key"),
                    model_name=self.config.get("gemini_model", "gemini-2.5-pro"),
                    temperature=0.3,
                )
                logger.info("Gemini content analyzer initialized")

            self._initialized = True

            init_time_ms = (time.time() - start_time) * 1000
            logger.info(f"ImageAnalysisHandler initialized in {init_time_ms:.2f}ms")

        except Exception as e:
            logger.error(f"Failed to initialize ImageAnalysisHandler: {e}")
            raise ImageAnalysisError(f"Initialization failed: {e}") from e

    def validate_input(self, data: dict[str, Any]) -> None:
        """Validate input data for image analysis."""
        # Check for required fields
        if "image_urls" not in data:
            raise ValidationError("Missing required field: image_urls")

        image_urls = data.get("image_urls", [])

        # Validate image URLs
        if not isinstance(image_urls, list):
            raise ValidationError("image_urls must be a list")

        if not image_urls:
            raise ValidationError("image_urls cannot be empty")

        if len(image_urls) > self.max_images:
            raise ValidationError(
                f"Too many images: {len(image_urls)} (max: {self.max_images})"
            )

        # Validate each URL format
        for idx, url in enumerate(image_urls):
            if not isinstance(url, str):
                raise ValidationError(f"Image URL at index {idx} must be a string")

            if not (url.startswith(("http://", "https://", "file://")) or "/" in url):
                raise ValidationError(f"Invalid URL format at index {idx}: {url}")

        logger.debug("Input validation successful")

    def preprocess(self, data: dict[str, Any]) -> dict[str, Any]:
        """Preprocess input data for image analysis."""
        try:
            processed_data = {
                "timestamp": datetime.now().isoformat(),
                "image_urls": data.get("image_urls", []),
                "metadata": data.get("metadata", {}),
                "context": data.get("context", {}),
                "analysis_config": {
                    "enable_ai_detection": self.enable_ai_detection
                    and self.ai_detector is not None,
                    "enable_content_analysis": self.enable_gemini
                    and self.content_analyzer is not None,
                    "max_images": self.max_images,
                },
            }

            # Add any claim-specific context if provided
            if "claim_id" in data:
                processed_data["claim_context"] = {
                    "claim_id": data.get("claim_id"),
                    "customer_id": data.get("customer_id"),
                    "product_info": data.get("product_info", {}),
                }

            logger.debug("Preprocessing complete")
            return processed_data

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise ImageAnalysisError(f"Preprocessing failed: {e}") from e

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process images through both analyzers."""
        start_time = time.time()

        try:
            logger.info("Starting image analysis")

            # Initialize result structure
            result: Dict[str, Any] = {
                "model_version": self.model_version,
                "timestamp": datetime.now().isoformat(),
                "analysis_results": {},
                "combined_assessment": {},
                "processing_details": {},
            }

            image_urls = data.get("image_urls", [])

            # Step 1: AI Detection Analysis
            ai_detection_result = None
            if self.ai_detector and data.get("analysis_config", {}).get(
                "enable_ai_detection", True
            ):
                ai_detection_result = self.ai_detector.analyze_images(image_urls)
                result["analysis_results"]["ai_detection"] = ai_detection_result
                logger.info(
                    f"AI detection complete: {ai_detection_result.get('ai_detected', False)}"
                )

            # Step 2: Content Analysis with Gemini
            content_analysis_result = None
            if self.content_analyzer and data.get("analysis_config", {}).get(
                "enable_content_analysis", True
            ):
                content_analysis_result = self.content_analyzer.analyze_images(image_urls)
                result["analysis_results"]["content_analysis"] = content_analysis_result
                logger.info(
                    f"Content analysis complete: risk_score={content_analysis_result.get('risk_score', 0)}"
                )

            # Step 3: Combine results for comprehensive assessment
            combined_assessment = self._combine_analysis_results(
                ai_detection_result, content_analysis_result
            )
            result["combined_assessment"] = combined_assessment

            # Step 4: Determine final risk and recommendation
            risk_level, recommendation = self._determine_final_assessment(combined_assessment)

            result["final_assessment"] = {
                "risk_level": risk_level,
                "overall_risk_score": combined_assessment.get("combined_risk_score", 0.0),
                "recommendation": recommendation,
                "primary_concerns": self._get_primary_concerns(combined_assessment),
                "confidence": combined_assessment.get("confidence", 0.0),
            }

            # Add processing details
            processing_time_ms = int((time.time() - start_time) * 1000)
            result["processing_details"] = {
                "processing_time_ms": processing_time_ms,
                "images_analyzed": len(image_urls),
                "analyzers_used": [
                    "ai_detection" if ai_detection_result else None,
                    "content_analysis" if content_analysis_result else None,
                ],
            }

            logger.info(
                f"Image analysis complete: "
                f"Risk={risk_level}, Score={combined_assessment.get('combined_risk_score', 0):.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return {
                "final_assessment": {
                    "risk_level": "ERROR",
                    "overall_risk_score": 0.0,
                    "recommendation": "SYSTEM_ERROR",
                },
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000),
            }

    def _combine_analysis_results(
        self, ai_detection: dict[str, Any] | None, content_analysis: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Combine results from both analyzers."""
        indicators_list: list[dict[str, Any]] = []
        combined_risk_score: float = 0.0
        ai_images_detected: int = 0
        harmful_content_detected: bool = False
        confidence_scores: list[float] = []

        # Weight configuration for combining scores
        weights = {
            "ai_detection": 0.6,
            "content_analysis": 0.4,
        }

        # Process AI detection results
        if ai_detection:
            ai_risk = ai_detection.get("risk_score", 0.0)
            combined_risk_score += ai_risk * weights["ai_detection"]

            ai_indicators = ai_detection.get("indicators", [])
            if isinstance(ai_indicators, list):
                indicators_list.extend(ai_indicators)

            ai_images_count = ai_detection.get("analysis_details", {}).get("ai_images_found", 0)
            if isinstance(ai_images_count, int):
                ai_images_detected = ai_images_count

            if ai_images_detected > 0:
                confidence_scores.append(0.9)
            else:
                confidence_scores.append(0.7)

        # Process content analysis results
        if content_analysis:
            content_risk = content_analysis.get("risk_score", 0.0)
            combined_risk_score += content_risk * weights["content_analysis"]

            content_indicators = content_analysis.get("indicators", [])
            if isinstance(content_indicators, list):
                indicators_list.extend(content_indicators)

            for analysis in content_analysis.get("analysis_details", {}).get(
                "individual_analyses", []
            ):
                if analysis.get("contains_harmful_content"):
                    harmful_content_detected = True
                    break

            confidence_scores.append(0.8)

        # Normalize risk score if only one analyzer was used
        if ai_detection and not content_analysis:
            combined_risk_score = ai_detection.get("risk_score", 0.0)
        elif content_analysis and not ai_detection:
            combined_risk_score = content_analysis.get("risk_score", 0.0)

        # Calculate overall confidence
        overall_confidence: float = 0.0
        if confidence_scores:
            overall_confidence = sum(confidence_scores) / len(confidence_scores)

        combined_risk_score = min(combined_risk_score, 1.0)

        # Sort indicators by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        indicators_list.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 5))

        return {
            "indicators": indicators_list,
            "combined_risk_score": combined_risk_score,
            "ai_images_detected": ai_images_detected,
            "harmful_content_detected": harmful_content_detected,
            "confidence": overall_confidence,
        }

    def _determine_final_assessment(self, combined_assessment: dict[str, Any]) -> tuple[str, str]:
        """Determine final risk level and recommendation."""
        risk_score = combined_assessment.get("combined_risk_score", 0.0)
        ai_detected = combined_assessment.get("ai_images_detected", 0) > 0
        harmful_content = combined_assessment.get("harmful_content_detected", False)

        # Critical indicators override score-based assessment
        if ai_detected and combined_assessment.get("ai_images_detected", 0) >= 2:
            return "CRITICAL", "BLOCK_IMMEDIATELY"

        if harmful_content:
            return "HIGH", "MANUAL_REVIEW_URGENT"

        # Score-based assessment
        if risk_score >= self.risk_threshold_high or ai_detected:
            return "HIGH", "BLOCK_AND_INVESTIGATE"
        elif risk_score >= self.risk_threshold_medium:
            return "MEDIUM", "MANUAL_REVIEW"
        else:
            return "LOW", "APPROVE"

    @staticmethod
    def _get_primary_concerns(combined_assessment: dict[str, Any]) -> list[str]:
        """Extract primary concerns from the combined assessment."""
        concerns: list[str] = []

        if combined_assessment.get("ai_images_detected", 0) > 0:
            concerns.append(
                f"AI-generated images detected ({combined_assessment['ai_images_detected']})"
            )

        if combined_assessment.get("harmful_content_detected"):
            concerns.append("Harmful or inappropriate content detected")

        for indicator in combined_assessment.get("indicators", [])[:5]:
            if indicator.get("severity") in ["CRITICAL", "HIGH"]:
                concerns.append(indicator.get("details", "High-risk indicator detected"))

        return list(concerns[:3])

    def postprocess(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format output for API response."""
        try:
            # Ensure required fields are present
            if "final_assessment" not in result:
                result["final_assessment"] = {
                    "risk_level": "UNKNOWN",
                    "overall_risk_score": 0.0,
                    "recommendation": "ERROR",
                    "primary_concerns": [],
                }

            # Round numerical values
            if "final_assessment" in result:
                result["final_assessment"]["overall_risk_score"] = round(
                    result["final_assessment"].get("overall_risk_score", 0.0), 3
                )
                result["final_assessment"]["confidence"] = round(
                    result["final_assessment"].get("confidence", 0.0), 2
                )

            # Limit indicators to top 10
            if (
                "combined_assessment" in result
                and "indicators" in result["combined_assessment"]
            ):
                result["combined_assessment"]["indicators"] = result["combined_assessment"][
                    "indicators"
                ][:10]

            # Add summary
            result["summary"] = {
                "total_images": result.get("processing_details", {}).get("images_analyzed", 0),
                "risk_level": result["final_assessment"]["risk_level"],
                "ai_detected": result.get("combined_assessment", {}).get(
                    "ai_images_detected", 0
                )
                > 0,
                "action_required": self._get_action_required(
                    result["final_assessment"]["risk_level"]
                ),
            }

            logger.debug("Postprocessing complete")
            return result

        except Exception as e:
            logger.error(f"Postprocessing failed: {e}")
            return {
                "final_assessment": {
                    "risk_level": "ERROR",
                    "overall_risk_score": 0.0,
                    "recommendation": "SYSTEM_ERROR",
                },
                "error": str(e),
            }

    def _get_action_required(self, risk_level: str) -> str:
        """Get action required based on risk level."""
        actions = {
            "CRITICAL": "Immediate blocking and investigation required",
            "HIGH": "Block transaction and flag for review",
            "MEDIUM": "Manual review required before approval",
            "LOW": "Can proceed with normal processing",
            "ERROR": "System error - manual intervention needed",
        }
        return actions.get(risk_level, "Unknown action")

    @property
    def metadata(self) -> dict[str, Any]:
        """Return handler metadata."""
        return {
            "name": "ImageAnalysisHandler",
            "version": self.model_version,
            "description": "Multi-modal image analysis with AI detection and content understanding",
            "tags": ["image", "ai-detection", "content-analysis", "fraud", "ocr", "gemini", "vision"],
        }

    def health_check(self) -> dict[str, Any]:
        """Perform health check on all components."""
        health_status = {
            "healthy": True,
            "version": self.model_version,
            "components": {
                "ai_detector": self.ai_detector is not None,
                "content_analyzer": self.content_analyzer is not None,
            },
            "config": {
                "ai_detection_enabled": self.enable_ai_detection,
                "gemini_enabled": self.enable_gemini,
                "max_images": self.max_images,
            },
        }

        if not self.ai_detector and not self.content_analyzer:
            health_status["healthy"] = False
            health_status["error"] = "No analyzers available"

        return health_status

"""Tests for ImageAnalysisHandler."""

from unittest.mock import Mock, patch

import pytest
from src.image.exceptions import ImageAnalysisError, ValidationError
from src.image.handler import ImageAnalysisHandler


@pytest.fixture
def handler():
    return ImageAnalysisHandler(config={
        "enable_gemini": False,
        "enable_ai_detection": False,
    })


class TestValidateInput:
    def test_missing_image_urls(self, handler):
        with pytest.raises(ValidationError, match="Missing required"):
            handler.validate_input({})

    def test_not_a_list(self, handler):
        with pytest.raises(ValidationError, match="must be a list"):
            handler.validate_input({"image_urls": "string"})

    def test_empty_list(self, handler):
        with pytest.raises(ValidationError, match="cannot be empty"):
            handler.validate_input({"image_urls": []})

    def test_too_many_images(self):
        h = ImageAnalysisHandler(config={"max_images": 2})
        with pytest.raises(ValidationError, match="Too many"):
            h.validate_input({"image_urls": ["a", "b", "c"]})

    def test_non_string_url(self, handler):
        with pytest.raises(ValidationError, match="non-empty string"):
            handler.validate_input({"image_urls": [123]})

    def test_empty_string_url(self, handler):
        with pytest.raises(ValidationError, match="non-empty string"):
            handler.validate_input({"image_urls": ["  "]})

    def test_valid_urls(self, handler):
        handler.validate_input({"image_urls": ["https://img.com/a.jpg", "file://local.png"]})

    def test_local_path_valid(self, handler):
        handler.validate_input({"image_urls": ["/path/to/image.jpg"]})

    def test_local_filename_valid(self, handler):
        handler.validate_input({"image_urls": ["botas fultbol.png", "FOOTBALL2.png"]})


class TestPreprocess:
    def test_basic_preprocess(self, handler):
        data = {"image_urls": ["https://x.com/a.jpg"]}
        result = handler.preprocess(data)
        assert "timestamp" in result
        assert result["image_urls"] == ["https://x.com/a.jpg"]



class TestProcess:
    def test_process_no_analyzers(self, handler):
        data = {"image_urls": ["https://x.com/a.jpg"], "analysis_config": {}}
        result = handler.process(data)
        assert "final_assessment" in result
        assert result["final_assessment"]["risk_level"] == "LOW"

    def test_process_with_ai_detection(self):
        h = ImageAnalysisHandler()
        h.ai_detector = Mock()
        h.ai_detector.analyze_images.return_value = {
            "risk_score": 0.95, "indicators": [{"severity": "HIGH", "details": "AI detected"}],
            "ai_detected": True, "analysis_details": {"ai_images_found": 1},
        }
        data = {"image_urls": ["https://x.com/a.jpg"], "analysis_config": {"enable_ai_detection": True}}
        result = h.process(data)
        assert result["final_assessment"]["risk_level"] == "HIGH"

    def test_process_error_returns_error_result(self):
        h = ImageAnalysisHandler()
        h.ai_detector = Mock()
        h.ai_detector.analyze_images.side_effect = RuntimeError("boom")
        data = {"image_urls": ["https://x.com/a.jpg"], "analysis_config": {"enable_ai_detection": True}}
        result = h.process(data)
        assert result["final_assessment"]["risk_level"] == "ERROR"


class TestDetermineAssessment:
    def test_critical_multiple_ai(self):
        h = ImageAnalysisHandler()
        assessment = {"combined_risk_score": 1.0, "ai_images_detected": 2, "harmful_content_detected": False}
        level, rec = h._determine_final_assessment(assessment)
        assert level == "CRITICAL"
        assert rec == "BLOCK_IMMEDIATELY"

    def test_harmful_content(self):
        h = ImageAnalysisHandler()
        assessment = {"combined_risk_score": 0.5, "ai_images_detected": 0, "harmful_content_detected": True}
        level, _ = h._determine_final_assessment(assessment)
        assert level == "HIGH"

    def test_high_risk(self):
        h = ImageAnalysisHandler()
        assessment = {"combined_risk_score": 0.9, "ai_images_detected": 0, "harmful_content_detected": False}
        level, _ = h._determine_final_assessment(assessment)
        assert level == "HIGH"

    def test_medium_risk(self):
        h = ImageAnalysisHandler()
        assessment = {"combined_risk_score": 0.6, "ai_images_detected": 0, "harmful_content_detected": False}
        level, _ = h._determine_final_assessment(assessment)
        assert level == "MEDIUM"

    def test_low_risk(self):
        h = ImageAnalysisHandler()
        assessment = {"combined_risk_score": 0.1, "ai_images_detected": 0, "harmful_content_detected": False}
        level, _ = h._determine_final_assessment(assessment)
        assert level == "LOW"


class TestPostprocess:
    def test_rounds_scores(self, handler):
        result = {
            "final_assessment": {"risk_level": "LOW", "overall_risk_score": 0.12345678, "confidence": 0.8765},
            "combined_assessment": {"indicators": [], "ai_images_detected": 0},
            "processing_details": {"images_analyzed": 1},
        }
        processed = handler.postprocess(result)
        assert processed["final_assessment"]["overall_risk_score"] == 0.123
        assert processed["final_assessment"]["confidence"] == 0.88

    def test_missing_final_assessment(self, handler):
        result = handler.postprocess({})
        assert result["final_assessment"]["risk_level"] == "UNKNOWN"


class TestMetadata:
    def test_metadata_properties(self, handler):
        meta = handler.metadata
        assert meta["name"] == "ImageAnalysisHandler"
        assert "version" in meta


class TestHealthCheck:
    def test_unhealthy_no_analyzers(self, handler):
        health = handler.health_check()
        assert health["healthy"] is False

    def test_healthy_with_analyzer(self):
        h = ImageAnalysisHandler()
        h.ai_detector = Mock()
        health = h.health_check()
        assert health["healthy"] is True

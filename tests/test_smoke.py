"""Smoke tests — exercise the full pipeline end-to-end with mocked externals."""

import json
from unittest.mock import Mock, patch

import pytest
import torch


# ── Fixtures ──────────────────────────────────────────────────────

GEMINI_RESPONSE = json.dumps({
    "primary_label": "running shoe",
    "description": "A black running shoe on white background",
    "objects_detected": ["shoe", "laces", "sole"],
    "raw_text": ["On", "Swiss Engineering"],
    "extracted_fields": [
        {"field_name": "brand_name", "value": "On", "confidence": 98},
    ],
    "brand": "On",
    "detected_brands": ["On"],
    "image_quality": "high",
    "people_count": 0,
    "classification_labels": [{"label": "footwear", "confidence": 92}],
    "labels": ["running shoe"],
    "contains_harmful_content": False,
    "harmful_content_type": None,
    "safety_score": 0.97,
    "on_running_related": True,
    "on_running_confidence": 0.85,
    "on_running_details": "Cloud 5 model detected",
    "is_product_image": True,
    "is_athletic_content": True,
    "dominant_colors": ["black", "white"],
    "scene_type": "studio",
    "image_category": "OTHER",
    "product_category": "shoes",
    "product_gender": "Mens",
    "product_year": 2025,
    "product_season": "Spring/Summer",
    "product_vertical": "Performance Running",
    "product_family": ["Cloud"],
    "product_model": ["5"],
    "product_generation": 1,
    "product_primary_colour": "#000000",
    "product_secondary_colour": "#FFFFFF",
    "language_category": "en",
})


@pytest.fixture
def _mock_ai_detector():
    """Mock SigLIP model and image loading so no download/network is needed."""
    from PIL import Image as PILImage

    model = Mock()
    model.config.id2label = {0: "human", 1: "ai"}
    logits = torch.tensor([[3.0, -3.0]])  # confident human
    output = Mock()
    output.logits = logits
    model.return_value = output
    model.to = Mock(return_value=model)
    model.eval = Mock()

    processor = Mock()
    inputs = Mock()
    inputs.to = Mock(return_value={"pixel_values": torch.randn(1, 3, 224, 224)})
    processor.return_value = inputs

    with patch(
        "src.image.analyzers.genai_detection_analyzer.SiglipForImageClassification"
    ) as cls, patch(
        "src.image.analyzers.genai_detection_analyzer.AutoImageProcessor"
    ) as proc, patch(
        "src.image.analyzers.genai_detection_analyzer._load_pil_image",
        return_value=PILImage.new("RGB", (100, 100)),
    ):
        cls.from_pretrained.return_value = model
        proc.from_pretrained.return_value = processor
        yield


@pytest.fixture
def _mock_gemini():
    """Mock Gemini API so no API key is needed."""
    with patch("src.image.analyzers.gemini_content_analyzer.genai") as mock_genai, \
         patch("src.image.analyzers.gemini_content_analyzer.requests") as mock_req, \
         patch("src.image.analyzers.gemini_content_analyzer.ImageValidator") as mock_val, \
         patch("src.image.analyzers.gemini_content_analyzer.load_feature_lists") as mock_feat, \
         patch("src.image.analyzers.gemini_content_analyzer.estimate_sku") as mock_sku:

        # Gemini client
        client = Mock()
        resp = Mock()
        resp.text = GEMINI_RESPONSE
        client.models.generate_content.return_value = resp
        mock_genai.Client.return_value = client

        # HTTP response for image download
        http = Mock()
        http.content = b"fake_image_bytes"
        http.headers = {"Content-Type": "image/jpeg"}
        http.raise_for_status = Mock()
        mock_req.get.return_value = http

        # Validator
        vr = Mock()
        vr.valid = True
        vr.processed_data = b"fake_image_bytes"
        mock_val.return_value.validate_and_process.return_value = vr

        # Feature lists
        mock_feat.return_value = {
            "retailer_list": ["Amazon"],
            "product_list": ["Cloud 5"],
            "vertical_list": ["Performance Running"],
            "family_list": ["Cloud"],
            "model_list": ["5"],
        }

        # SKU
        mock_sku.return_value = ["SHOE001", "SHOE002"]

        yield


# ── Smoke tests ───────────────────────────────────────────────────

class TestFullPipeline:
    """End-to-end handler pipeline: validate → preprocess → process → postprocess."""

    def test_single_image_low_risk(self, _mock_ai_detector, _mock_gemini):
        from src.image.handler import ImageAnalysisHandler

        handler = ImageAnalysisHandler(config={"gemini_api_key": "fake-key"})
        handler.initialize()

        payload = {"image_urls": ["https://example.com/shoe.jpg"]}
        handler.validate_input(payload)
        preprocessed = handler.preprocess(payload)
        result = handler.process(preprocessed)
        output = handler.postprocess(result)

        assert output["final_assessment"]["risk_level"] in ("LOW", "MEDIUM")
        assert "processing_details" in output

    def test_stock_photo_raises_risk(self, _mock_ai_detector, _mock_gemini):
        from src.image.handler import ImageAnalysisHandler

        handler = ImageAnalysisHandler(config={"gemini_api_key": "fake-key"})
        handler.initialize()

        payload = {"image_urls": ["https://shutterstock.com/photo.jpg"]}
        handler.validate_input(payload)
        preprocessed = handler.preprocess(payload)
        result = handler.process(preprocessed)
        output = handler.postprocess(result)

        # Stock photo bumps risk above LOW
        assert output["final_assessment"]["risk_level"] != "LOW"
        assert output["final_assessment"]["overall_risk_score"] > 0.0

    def test_ai_detection_only(self, _mock_ai_detector):
        from src.image.handler import ImageAnalysisHandler

        handler = ImageAnalysisHandler(config={
            "enable_gemini": False,
            "enable_ai_detection": True,
        })
        handler.initialize()

        payload = {"image_urls": ["https://example.com/photo.jpg"]}
        handler.validate_input(payload)
        preprocessed = handler.preprocess(payload)
        result = handler.process(preprocessed)
        output = handler.postprocess(result)

        assert "final_assessment" in output
        assert output["final_assessment"]["risk_level"] == "LOW"

    def test_health_check_after_init(self, _mock_ai_detector, _mock_gemini):
        from src.image.handler import ImageAnalysisHandler

        handler = ImageAnalysisHandler(config={"gemini_api_key": "fake-key"})
        handler.initialize()

        health = handler.health_check()
        assert health["healthy"] is True

    def test_invalid_input_rejected(self):
        from src.image.handler import ImageAnalysisHandler
        from src.image.exceptions import ValidationError

        handler = ImageAnalysisHandler()

        with pytest.raises(ValidationError):
            handler.validate_input({})

        with pytest.raises(ValidationError):
            handler.validate_input({"image_urls": "not-a-list"})

        with pytest.raises(ValidationError):
            handler.validate_input({"image_urls": []})

    def test_metadata(self):
        from src.image.handler import ImageAnalysisHandler

        handler = ImageAnalysisHandler()
        meta = handler.metadata
        assert meta["name"] == "ImageAnalysisHandler"
        assert "version" in meta

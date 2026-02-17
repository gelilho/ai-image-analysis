"""Tests for GeminiContentAnalyzer with fully mocked dependencies."""

import json
from unittest.mock import Mock, patch

import pytest

_DEFAULT_RESPONSE = json.dumps({
    "primary_label": "sneaker",
    "description": "A running shoe",
    "objects_detected": ["shoe", "laces"],
    "raw_text": ["NIKE AIR"],
    "extracted_fields": [],
    "brand": "Nike",
    "detected_brands": ["Nike"],
    "image_quality": "high",
    "people_count": 0,
    "classification_labels": [{"label": "footwear", "confidence": 95}],
    "labels": ["sneaker", "shoe"],
    "contains_harmful_content": False,
    "harmful_content_type": None,
    "safety_score": 0.95,
    "on_running_related": False,
    "on_running_confidence": 0.1,
    "on_running_details": None,
    "is_product_image": True,
    "is_athletic_content": True,
    "dominant_colors": ["red", "white"],
    "scene_type": "studio",
    "image_category": "OTHER",
    "product_category": "shoes",
    "product_gender": "Mens",
    "product_year": 2025,
    "product_season": "Spring/Summer",
    "product_vertical": "Performance Running",
    "product_family": ["Cloud", "Cloudmonster"],
    "product_model": ["5", "Next", "Max"],
    "product_generation": 1,
    "product_primary_colour": "#FF0000",
    "product_secondary_colour": "#FFFFFF",
    "language_category": "en",
})


@pytest.fixture
def mock_deps():
    with (
        patch("src.image.analyzers.gemini_content_analyzer.genai") as mock_genai,
        patch("src.image.analyzers.gemini_content_analyzer.requests") as mock_requests,
        patch("src.image.analyzers.gemini_content_analyzer.ImageValidator") as mock_validator,
        patch("src.image.analyzers.gemini_content_analyzer.load_feature_lists") as mock_features,
        patch("src.image.analyzers.gemini_content_analyzer.estimate_sku") as mock_sku,
    ):
        # Gemini client
        client = Mock()
        resp = Mock()
        resp.text = _DEFAULT_RESPONSE
        client.models.generate_content.return_value = resp
        mock_genai.Client.return_value = client

        # Requests
        http_resp = Mock()
        http_resp.content = b"fake_image"
        http_resp.headers = {"Content-Type": "image/jpeg"}
        http_resp.raise_for_status = Mock()
        mock_requests.get.return_value = http_resp

        # Validator
        vr = Mock()
        vr.valid = True
        vr.processed_data = b"fake_image"
        mock_validator.return_value.validate_and_process.return_value = vr

        # Features
        mock_features.return_value = {
            "retailer_list": ["Amazon"],
            "product_list": ["Cloud 5"],
            "vertical_list": ["Performance Running"],
            "family_list": ["Cloud"],
            "model_list": ["5"],
        }

        # SKU
        mock_sku.return_value = ["ITEM001"]

        yield {
            "genai": mock_genai, "client": client,
            "requests": mock_requests, "validator": mock_validator,
            "features": mock_features, "sku": mock_sku,
        }


@pytest.fixture
def analyzer(mock_deps):
    from src.image.analyzers.gemini_content_analyzer import GeminiContentAnalyzer
    return GeminiContentAnalyzer(api_key="test-key")


class TestGeminiContentAnalyzer:
    def test_empty_urls(self, analyzer):
        result = analyzer.analyze_images([])
        assert result["risk_score"] == 0.0
        assert "No images" in result["summary"]

    def test_single_image(self, analyzer):
        result = analyzer.analyze_images(["https://example.com/shoe.jpg"])
        assert result["analysis_details"]["images_analyzed"] == 1
        analyses = result["analysis_details"]["individual_analyses"]
        assert analyses[0]["primary_label"] == "sneaker"

    def test_multiple_images(self, analyzer):
        result = analyzer.analyze_images(["https://a.com/1.jpg", "https://a.com/2.jpg"])
        assert result["analysis_details"]["images_analyzed"] == 2

    def test_harmful_content_raises_risk(self, analyzer, mock_deps):
        harmful = json.loads(_DEFAULT_RESPONSE)
        harmful["contains_harmful_content"] = True
        harmful["harmful_content_type"] = "violence"
        mock_deps["client"].models.generate_content.return_value.text = json.dumps(harmful)

        result = analyzer.analyze_images(["https://example.com/img.jpg"])
        assert result["risk_score"] >= 0.8
        assert any(i["indicator"] == "harmful_content_detected" for i in result["indicators"])

    def test_on_running_detection(self, analyzer, mock_deps):
        on_resp = json.loads(_DEFAULT_RESPONSE)
        on_resp["on_running_related"] = True
        on_resp["on_running_confidence"] = 0.95
        on_resp["on_running_details"] = "Cloud shoe"
        mock_deps["client"].models.generate_content.return_value.text = json.dumps(on_resp)

        result = analyzer.analyze_images(["https://example.com/on.jpg"])
        assert any(i["indicator"] == "on_running_content" for i in result["indicators"])

    def test_extracted_fields_detection(self, analyzer, mock_deps):
        resp = json.loads(_DEFAULT_RESPONSE)
        resp["extracted_fields"] = [
            {"field_name": "size_us", "value": "10", "confidence": 95},
            {"field_name": "brand_name", "value": "Nike", "confidence": 98},
        ]
        resp["raw_text"] = ["Size US 10", "Nike Air Max"]
        mock_deps["client"].models.generate_content.return_value.text = json.dumps(resp)

        result = analyzer.analyze_images(["https://example.com/tag.jpg"])
        assert any(i["indicator"] == "fields_extracted" for i in result["indicators"])

    def test_validation_failure(self, analyzer, mock_deps):
        vr = Mock()
        vr.valid = False
        vr.error_type = Mock()
        vr.error_type.value = "low_quality"
        vr.message = "Too small"
        mock_deps["validator"].return_value.validate_and_process.return_value = vr

        result = analyzer.analyze_images(["https://example.com/small.jpg"])
        assert result["analysis_details"]["images_analyzed"] == 0

    def test_api_key_required(self, mock_deps):
        mock_deps["features"].return_value = {k: [] for k in ["retailer_list", "product_list", "vertical_list", "family_list", "model_list"]}
        with patch.dict("os.environ", {}, clear=True):
            from src.image.analyzers.gemini_content_analyzer import GeminiContentAnalyzer
            with pytest.raises(ValueError, match="API key required"):
                GeminiContentAnalyzer(api_key=None)

    def test_sku_included_in_result(self, analyzer):
        result = analyzer.analyze_images(["https://example.com/shoe.jpg"])
        assert "sku" in result
        assert "ITEM001" in result["sku"]

    def test_load_image_bytes_local(self, tmp_path):
        from src.image.analyzers.gemini_content_analyzer import GeminiContentAnalyzer
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8test_data")
        data, mime = GeminiContentAnalyzer._load_image_bytes(str(img))
        assert data == b"\xff\xd8test_data"
        assert mime == "image/jpeg"

    def test_load_image_bytes_file_url(self, tmp_path):
        from src.image.analyzers.gemini_content_analyzer import GeminiContentAnalyzer
        img = tmp_path / "test.png"
        img.write_bytes(b"png_data")
        data, mime = GeminiContentAnalyzer._load_image_bytes(f"file://{img}")
        assert data == b"png_data"
        assert mime == "image/png"

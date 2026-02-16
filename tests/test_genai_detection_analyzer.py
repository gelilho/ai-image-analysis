"""Tests for GenAIDetectionAnalyzer with mocked model dependencies."""

from unittest.mock import Mock, patch

import pytest
import torch

from src.image.analyzers.genai_detection_analyzer import (
    GenAIDetectionAnalyzer,
    is_stock_photo,
    _load_pil_image,
)


@pytest.fixture
def mock_model():
    """Create a mock SigLIP model that returns predictable results."""
    model = Mock()
    model.config.id2label = {0: "human", 1: "ai"}

    # Default: classify as human with high confidence
    logits = torch.tensor([[2.0, -2.0]])
    output = Mock()
    output.logits = logits
    model.return_value = output
    model.to = Mock(return_value=model)
    model.eval = Mock()
    return model


@pytest.fixture
def mock_processor():
    processor = Mock()
    inputs = Mock()
    inputs.to = Mock(return_value={"pixel_values": torch.randn(1, 3, 224, 224)})
    processor.return_value = inputs
    return processor


@pytest.fixture
def analyzer(mock_model, mock_processor):
    """Create analyzer with mocked model loading."""
    with patch(
        "src.image.analyzers.genai_detection_analyzer.SiglipForImageClassification"
    ) as mock_cls, patch(
        "src.image.analyzers.genai_detection_analyzer.AutoImageProcessor"
    ) as mock_proc_cls:
        mock_cls.from_pretrained.return_value = mock_model
        mock_proc_cls.from_pretrained.return_value = mock_processor
        return GenAIDetectionAnalyzer()


class TestAnalyzeImages:
    def test_empty_urls(self, analyzer):
        result = analyzer.analyze_images([])
        assert result["risk_score"] == 0.0
        assert result["indicators"] == []
        assert result["ai_detected"] is False
        assert result["analysis_details"]["images_analyzed"] == 0

    def test_limits_to_five_images(self, analyzer):
        urls = [f"https://example.com/{i}.jpg" for i in range(10)]
        with patch.object(analyzer, "check_ai_generated", return_value={"is_ai": False, "confidence": 0.9}):
            result = analyzer.analyze_images(urls)
        assert result["analysis_details"]["images_analyzed"] == 5

    def test_ai_detected_sets_high_risk(self, analyzer):
        with patch.object(
            analyzer, "check_ai_generated",
            return_value={"is_ai": True, "confidence": 0.95},
        ):
            result = analyzer.analyze_images(["https://example.com/ai.jpg"])
        assert result["risk_score"] == 0.95
        assert result["ai_detected"] is True
        assert any(i["indicator"] == "ai_generated_image" for i in result["indicators"])

    def test_multiple_ai_images_critical(self, analyzer):
        with patch.object(
            analyzer, "check_ai_generated",
            return_value={"is_ai": True, "confidence": 0.9},
        ):
            result = analyzer.analyze_images(["https://a.com/1.jpg", "https://a.com/2.jpg"])
        assert result["risk_score"] == 1.0
        assert any(i["severity"] == "CRITICAL" for i in result["indicators"])

    def test_stock_photo_detected(self, analyzer):
        with patch.object(
            analyzer, "check_ai_generated",
            return_value={"is_ai": False, "confidence": 0.9},
        ):
            result = analyzer.analyze_images(["https://shutterstock.com/img.jpg"])
        assert any(i["indicator"] == "stock_photo_detected" for i in result["indicators"])
        assert result["risk_score"] >= 0.9

    def test_analysis_error_logged(self, analyzer):
        with patch.object(
            analyzer, "check_ai_generated",
            side_effect=RuntimeError("download failed"),
        ):
            result = analyzer.analyze_images(["https://example.com/bad.jpg"])
        assert any(i["indicator"] == "image_analysis_error" for i in result["indicators"])


class TestCheckAiGenerated:
    def test_model_not_loaded(self):
        a = GenAIDetectionAnalyzer.__new__(GenAIDetectionAnalyzer)
        a.ai_detector_model = None
        a.ai_detector_processor = None
        result = a.check_ai_generated("https://x.com/img.jpg")
        assert result["is_ai"] is False
        assert result["error"] == "Model not loaded"

    def test_classifies_image(self, analyzer):
        with patch(
            "src.image.analyzers.genai_detection_analyzer._load_pil_image"
        ) as mock_load:
            from PIL import Image
            mock_load.return_value = Image.new("RGB", (100, 100))
            result = analyzer.check_ai_generated("https://x.com/img.jpg")
        assert "is_ai" in result
        assert "confidence" in result
        assert "class_probabilities" in result

    def test_converts_non_rgb(self, analyzer):
        with patch(
            "src.image.analyzers.genai_detection_analyzer._load_pil_image"
        ) as mock_load:
            from PIL import Image
            mock_load.return_value = Image.new("RGBA", (100, 100))
            result = analyzer.check_ai_generated("https://x.com/img.png")
        assert "is_ai" in result

    def test_request_error(self, analyzer):
        import requests
        with patch(
            "src.image.analyzers.genai_detection_analyzer._load_pil_image",
            side_effect=requests.exceptions.ConnectionError("timeout"),
        ):
            result = analyzer.check_ai_generated("https://x.com/img.jpg")
        assert result["is_ai"] is False
        assert "error" in result


class TestLoadPilImage:
    def test_local_file(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="red")
        p = tmp_path / "test.jpg"
        img.save(p)
        loaded = _load_pil_image(str(p))
        assert loaded.size == (10, 10)

    def test_file_url(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (10, 10))
        p = tmp_path / "test.png"
        img.save(p)
        loaded = _load_pil_image(f"file://{p}")
        assert loaded.size == (10, 10)

    def test_http_url(self):
        with patch("src.image.analyzers.genai_detection_analyzer.requests") as mock_req:
            from PIL import Image
            from io import BytesIO
            buf = BytesIO()
            Image.new("RGB", (5, 5)).save(buf, format="PNG")
            mock_req.get.return_value.content = buf.getvalue()
            mock_req.get.return_value.raise_for_status = Mock()
            loaded = _load_pil_image("https://example.com/img.png")
            assert loaded.size == (5, 5)


class TestIsStockPhoto:
    @pytest.mark.parametrize("url", [
        "https://shutterstock.com/image-123.jpg",
        "https://www.gettyimages.com/photo.png",
        "https://cdn.istockphoto.com/img.jpg",
        "https://stock.adobestock.com/a.jpg",
        "https://unsplash.com/photo/abc",
    ])
    def test_detects_stock_domains(self, url):
        assert is_stock_photo(url) is True

    def test_normal_url_not_stock(self):
        assert is_stock_photo("https://example.com/my-photo.jpg") is False

    def test_case_insensitive(self):
        assert is_stock_photo("https://SHUTTERSTOCK.COM/img.jpg") is True


class TestModelLoading:
    def test_env_var_fallback(self, tmp_path):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        with patch.dict("os.environ", {"AI_MODEL_PATH": str(model_dir)}):
            a = GenAIDetectionAnalyzer.__new__(GenAIDetectionAnalyzer)
            a.local_model_path = None
            path = a._resolve_model_path()
            assert path == str(model_dir)

    def test_no_model_returns_none(self):
        with patch.dict("os.environ", {}, clear=True):
            a = GenAIDetectionAnalyzer.__new__(GenAIDetectionAnalyzer)
            a.local_model_path = None
            assert a._resolve_model_path() is None

    def test_invalid_local_path_warns(self):
        a = GenAIDetectionAnalyzer.__new__(GenAIDetectionAnalyzer)
        a.local_model_path = "/nonexistent/path"
        with patch.dict("os.environ", {}, clear=True):
            assert a._resolve_model_path() is None

    def test_load_model_failure_graceful(self):
        with patch(
            "src.image.analyzers.genai_detection_analyzer.SiglipForImageClassification"
        ) as mock_cls, patch(
            "src.image.analyzers.genai_detection_analyzer.AutoImageProcessor"
        ):
            mock_cls.from_pretrained.side_effect = OSError("no model")
            a = GenAIDetectionAnalyzer()
        assert a.ai_detector_model is None
        assert a.ai_detector_processor is None

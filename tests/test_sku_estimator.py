"""Tests for sku_estimator module (department-only matching)."""

from unittest.mock import patch

from src.image.analyzers.sku_estimator import estimate_sku


class TestEstimateSku:
    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_empty_analyses(self, mock_catalog):
        assert estimate_sku([]) == []

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_only_receipts_skipped(self, mock_catalog):
        analyses = [{"image_category": "PROOF_OF_PURCHASE"}]
        assert estimate_sku(analyses) == []

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_no_department_votes(self, mock_catalog):
        analyses = [{"image_category": "OTHER", "product_category": ""}]
        assert estimate_sku(analyses) == []

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_empty_catalog(self, mock_catalog):
        mock_catalog.return_value = []
        analyses = [{"image_category": "SHOE_LABEL", "product_category": "shoes"}]
        assert estimate_sku(analyses) == []

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_matches_department(self, mock_catalog):
        mock_catalog.return_value = [
            {"item_code": "SHOE001", "retail_level_1_department": "shoes"},
            {"item_code": "APP001", "retail_level_1_department": "apparel"},
        ]
        analyses = [{"image_category": "SHOE_LABEL", "product_category": "shoes"}]
        result = estimate_sku(analyses)
        assert result == ["SHOE001"]

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_returns_all_matching_items(self, mock_catalog):
        mock_catalog.return_value = [
            {"item_code": "SHOE001", "retail_level_1_department": "shoes"},
            {"item_code": "SHOE002", "retail_level_1_department": "shoes"},
            {"item_code": "SHOE003", "retail_level_1_department": "shoes"},
        ]
        analyses = [{"image_category": "OTHER", "product_category": "shoes"}]
        result = estimate_sku(analyses)
        assert len(result) == 3
        assert "SHOE001" in result
        assert "SHOE002" in result
        assert "SHOE003" in result

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_majority_vote(self, mock_catalog):
        mock_catalog.return_value = [
            {"item_code": "SHOE001", "retail_level_1_department": "shoes"},
            {"item_code": "APP001", "retail_level_1_department": "apparel"},
        ]
        analyses = [
            {"image_category": "OTHER", "product_category": "shoes"},
            {"image_category": "OTHER", "product_category": "shoes"},
            {"image_category": "OTHER", "product_category": "apparel"},
        ]
        result = estimate_sku(analyses)
        assert result == ["SHOE001"]

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_case_insensitive(self, mock_catalog):
        mock_catalog.return_value = [
            {"item_code": "SHOE001", "retail_level_1_department": "shoes"},
        ]
        analyses = [{"image_category": "OTHER", "product_category": "Shoes"}]
        result = estimate_sku(analyses)
        assert result == ["SHOE001"]

    @patch("src.image.analyzers.sku_estimator.load_product_catalog")
    def test_no_match_in_catalog(self, mock_catalog):
        mock_catalog.return_value = [
            {"item_code": "APP001", "retail_level_1_department": "apparel"},
        ]
        analyses = [{"image_category": "OTHER", "product_category": "shoes"}]
        result = estimate_sku(analyses)
        assert result == []

"""Tests for data_loader module."""

from src.image.analyzers.data_loader import load_feature_lists, load_product_catalog


class TestLoadFeatureLists:
    def test_returns_all_keys(self):
        result = load_feature_lists()
        expected_keys = ["retailer_list", "product_list", "vertical_list", "family_list", "model_list"]
        for key in expected_keys:
            assert key in result
            assert result[key] == []

    def test_returns_lists(self):
        result = load_feature_lists()
        for val in result.values():
            assert isinstance(val, list)


class TestLoadProductCatalog:
    def test_returns_empty_list(self):
        assert load_product_catalog() == []

    def test_returns_list_type(self):
        assert isinstance(load_product_catalog(), list)

"""Tests for data_loader module."""

import json
import tempfile
from pathlib import Path

import pytest
from src.image.analyzers.data_loader import (
    load_feature_lists,
    load_product_catalog,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestLoadFeatureLists:
    def test_loads_from_file(self, tmp_dir):
        data = {"retailer_list": ["A"], "product_list": ["B"], "vertical_list": [], "family_list": [], "model_list": []}
        path = tmp_dir / "features.json"
        path.write_text(json.dumps(data))
        result = load_feature_lists(path)
        assert result["retailer_list"] == ["A"]
        assert result["product_list"] == ["B"]

    def test_missing_file_returns_empty(self, tmp_dir):
        result = load_feature_lists(tmp_dir / "nonexistent.json")
        for key in ["retailer_list", "product_list", "vertical_list", "family_list", "model_list"]:
            assert result[key] == []

    def test_partial_keys(self, tmp_dir):
        path = tmp_dir / "partial.json"
        path.write_text(json.dumps({"retailer_list": ["X"]}))
        result = load_feature_lists(path)
        assert result["retailer_list"] == ["X"]
        assert result["model_list"] == []


class TestLoadProductCatalog:
    def test_loads_catalog(self, tmp_dir):
        catalog = [{"item_code": "ABC", "colour_name": "black"}]
        path = tmp_dir / "catalog.json"
        path.write_text(json.dumps(catalog))
        result = load_product_catalog(path)
        assert len(result) == 1
        assert result[0]["item_code"] == "ABC"

    def test_missing_file_returns_empty(self, tmp_dir):
        assert load_product_catalog(tmp_dir / "nope.json") == []

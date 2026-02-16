"""Load static data files (feature lists, product catalog, colours)."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_feature_lists(path: Path | None = None) -> dict[str, list[str]]:
    """Load feature lists from JSON. Returns dict with list keys."""
    p = path or _DATA_DIR / "feature_lists.json"
    try:
        with open(p) as f:
            data = json.load(f)
        return {
            "retailer_list": data.get("retailer_list", []),
            "product_list": data.get("product_list", []),
            "vertical_list": data.get("vertical_list", []),
            "family_list": data.get("family_list", []),
            "model_list": data.get("model_list", []),
        }
    except FileNotFoundError:
        logger.warning(f"Feature lists not found at {p}")
        return {k: [] for k in ["retailer_list", "product_list", "vertical_list", "family_list", "model_list"]}


def load_product_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    """Load product catalog from JSON."""
    p = path or _DATA_DIR / "product_catalog.json"
    try:
        with open(p) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Product catalog not found at {p}")
        return []

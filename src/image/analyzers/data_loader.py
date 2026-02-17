"""Provide empty default feature lists and product catalog.

These functions exist so analyzers have a clean injection point
that tests can mock. No data files are needed.
"""

from typing import Any


def load_feature_lists() -> dict[str, list[str]]:
    """Return empty feature lists. Override via mock in tests."""
    return {
        "retailer_list": [],
        "product_list": [],
        "vertical_list": [],
        "family_list": [],
        "model_list": [],
    }


def load_product_catalog() -> list[dict[str, Any]]:
    """Return empty product catalog. Override via mock in tests."""
    return []

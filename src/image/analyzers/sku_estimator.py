"""Estimate product SKU from image analysis results.

Simple department-only matching against the local product catalog.
"""

from typing import Any

from loguru import logger

from .data_loader import load_product_catalog


def estimate_sku(image_analyses: list[dict[str, Any]]) -> list[str]:
    """Return catalog item codes matching the detected department.

    Filters non-receipt images by product_category (shoes/apparel/accessories)
    and returns all matching item codes from the catalog.
    """
    product_analyses = [
        ia for ia in image_analyses if ia.get("image_category") != "PROOF_OF_PURCHASE"
    ]
    if not product_analyses:
        return []

    # Count department votes across images
    dept_votes: dict[str, int] = {}
    for ia in product_analyses:
        dept = ia.get("product_category", "").lower().strip()
        if dept:
            dept_votes[dept] = dept_votes.get(dept, 0) + 1

    if not dept_votes:
        return []

    # Pick the department with the most votes
    best_dept = max(dept_votes, key=dept_votes.get)

    catalog = load_product_catalog()
    if not catalog:
        logger.warning("Product catalog is empty; SKU estimation skipped")
        return []

    return [
        item["item_code"]
        for item in catalog
        if item.get("retail_level_1_department", "").lower() == best_dept
    ]

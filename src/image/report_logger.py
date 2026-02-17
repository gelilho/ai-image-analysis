"""CSV report logger — appends one row per image after each analysis run."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = _PROJECT_ROOT / "reports"
CSV_FILENAME = "analysis_output.csv"

COLUMNS = [
    # Run metadata
    "date",
    "timestamp",
    "image_url",
    "risk_level",
    "risk_score",
    "recommendation",
    "confidence",
    "ai_detected",
    "processing_time_ms",
    "model_version",
    # Per-image Gemini fields
    "primary_label",
    "description",
    "objects_detected",
    "raw_text",
    "extracted_fields",
    "brand",
    "detected_brands",
    "image_quality",
    "people_count",
    "classification_labels",
    "labels",
    "contains_harmful_content",
    "harmful_content_type",
    "safety_score",
    "on_running_related",
    "on_running_confidence",
    "on_running_details",
    "is_product_image",
    "is_athletic_content",
    "dominant_colors",
    "scene_type",
    "image_category",
    "product_category",
    "product_gender",
    "product_year",
    "product_season",
    "product_vertical",
    "product_family",
    "product_model",
    "product_generation",
    "product_primary_colour",
    "product_secondary_colour",
    "language_category",
    "receipt_fields",
]

# Fields that contain lists/dicts and need JSON serialization
_JSON_FIELDS = {
    "objects_detected", "raw_text", "extracted_fields", "detected_brands",
    "classification_labels", "labels", "dominant_colors", "product_family",
    "product_model", "receipt_fields",
}


def _find_analysis(url: str, analyses: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the individual analysis dict matching this URL."""
    for a in analyses:
        if a.get("image_url") == url:
            return a
    return {}


def _extract_image_fields(img: dict[str, Any]) -> dict[str, Any]:
    """Extract all per-image fields from a Gemini analysis result."""
    row: dict[str, Any] = {}
    per_image_keys = [
        "primary_label", "description", "objects_detected", "raw_text",
        "extracted_fields", "brand", "detected_brands", "image_quality",
        "people_count", "classification_labels", "labels",
        "contains_harmful_content", "harmful_content_type", "safety_score",
        "on_running_related", "on_running_confidence", "on_running_details",
        "is_product_image", "is_athletic_content", "dominant_colors",
        "scene_type", "image_category", "product_category", "product_gender",
        "product_year", "product_season", "product_vertical", "product_family",
        "product_model", "product_generation", "product_primary_colour",
        "product_secondary_colour", "language_category", "receipt_fields",
    ]
    for key in per_image_keys:
        val = img.get(key, "" if key not in _JSON_FIELDS else [])
        row[key] = json.dumps(val) if key in _JSON_FIELDS else val
    return row


def log_results(
    image_urls: list[str],
    output: dict[str, Any],
    reports_dir: Path = REPORTS_DIR,
) -> Path:
    """Append analysis results to analysis_output.csv. One row per image.

    Returns the path to the CSV file written to.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / CSV_FILENAME
    file_exists = csv_path.exists()

    fa = output.get("final_assessment", {})
    combined = output.get("combined_assessment", {})
    processing = output.get("processing_details", {})
    content = output.get("analysis_results", {}).get("content_analysis", {})
    analyses = content.get("analysis_details", {}).get("individual_analyses", [])

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    shared = {
        "date": date,
        "timestamp": timestamp,
        "risk_level": fa.get("risk_level", "UNKNOWN"),
        "risk_score": fa.get("overall_risk_score", 0.0),
        "recommendation": fa.get("recommendation", ""),
        "confidence": fa.get("confidence", 0.0),
        "ai_detected": combined.get("ai_images_detected", 0) > 0,
        "processing_time_ms": processing.get("processing_time_ms", 0),
        "model_version": output.get("model_version", ""),
    }

    rows = []
    for url in image_urls:
        img = _find_analysis(url, analyses)
        row = {**shared, "image_url": url, **_extract_image_fields(img)}
        rows.append(row)

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Report: {len(rows)} row(s) → {csv_path}")
    return csv_path

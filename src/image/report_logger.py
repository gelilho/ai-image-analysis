"""CSV report logger — appends one row per image after each analysis run."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

REPORTS_DIR = Path("reports")

COLUMNS = [
    "timestamp",
    "image_url",
    "risk_level",
    "risk_score",
    "recommendation",
    "confidence",
    "ai_detected",
    "harmful_content",
    "processing_time_ms",
    "model_version",
]


def log_results(
    image_urls: list[str],
    output: dict[str, Any],
    reports_dir: Path = REPORTS_DIR,
) -> Path:
    """Append analysis results to a daily CSV file. One row per image.

    Returns the path to the CSV file written to.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = reports_dir / f"analysis_{today}.csv"
    file_exists = csv_path.exists()

    fa = output.get("final_assessment", {})
    combined = output.get("combined_assessment", {})
    processing = output.get("processing_details", {})

    timestamp = datetime.now().isoformat()
    risk_level = fa.get("risk_level", "UNKNOWN")
    risk_score = fa.get("overall_risk_score", 0.0)
    recommendation = fa.get("recommendation", "")
    confidence = fa.get("confidence", 0.0)
    ai_detected = combined.get("ai_images_detected", 0) > 0
    harmful = combined.get("harmful_content_detected", False)
    processing_ms = processing.get("processing_time_ms", 0)
    model_version = output.get("model_version", "")

    rows = []
    for url in image_urls:
        rows.append({
            "timestamp": timestamp,
            "image_url": url,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "recommendation": recommendation,
            "confidence": confidence,
            "ai_detected": ai_detected,
            "harmful_content": harmful,
            "processing_time_ms": processing_ms,
            "model_version": model_version,
        })

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Report: {len(rows)} row(s) → {csv_path}")
    return csv_path

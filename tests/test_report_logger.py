"""Tests for report_logger — CSV output after each analysis run."""

import csv
import json
import re
from pathlib import Path

from image.report_logger import COLUMNS, CSV_FILENAME, log_results


def _sample_output(url: str = "https://img.com/a.jpg") -> dict:
    return {
        "model_version": "v1.0",
        "final_assessment": {
            "risk_level": "LOW",
            "overall_risk_score": 0.12,
            "recommendation": "APPROVE",
            "confidence": 0.75,
        },
        "combined_assessment": {
            "ai_images_detected": 0,
            "harmful_content_detected": False,
        },
        "processing_details": {
            "processing_time_ms": 340,
        },
        "analysis_results": {
            "content_analysis": {
                "analysis_details": {
                    "individual_analyses": [{
                        "image_url": url,
                        "primary_label": "sneaker",
                        "description": "A running shoe",
                        "objects_detected": ["shoe", "laces"],
                        "raw_text": ["NIKE AIR", "Size 10"],
                        "extracted_fields": [
                            {"field_name": "brand_name", "value": "Nike", "confidence": 98},
                        ],
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
                        "product_family": ["Cloud"],
                        "product_model": ["5"],
                        "product_generation": 1,
                        "product_primary_colour": "#FF0000",
                        "product_secondary_colour": "#FFFFFF",
                        "language_category": "en",
                    }],
                },
            },
        },
    }


class TestReportLogger:
    def test_creates_single_csv_file(self, tmp_path: Path):
        output = _sample_output()
        csv_path = log_results(["https://img.com/a.jpg"], output, reports_dir=tmp_path)

        assert csv_path.exists()
        assert csv_path.name == CSV_FILENAME
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == COLUMNS
            rows = list(reader)
        assert len(rows) == 1

    def test_date_and_timestamp_columns(self, tmp_path: Path):
        output = _sample_output()
        log_results(["https://img.com/a.jpg"], output, reports_dir=tmp_path)

        with open(tmp_path / CSV_FILENAME) as f:
            rows = list(csv.DictReader(f))
        row = rows[0]

        # date = yyyy-mm-dd
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", row["date"])
        # timestamp = yyyy-mm-dd HH:MM:SS
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", row["timestamp"])
        # date is the date part of timestamp
        assert row["date"] == row["timestamp"][:10]

    def test_appends_to_same_file(self, tmp_path: Path):
        output = _sample_output()
        log_results(["https://img.com/a.jpg"], output, reports_dir=tmp_path)
        log_results(["https://img.com/b.jpg"], output, reports_dir=tmp_path)

        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) == 1
        assert csv_files[0].name == CSV_FILENAME
        with open(csv_files[0]) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_multiple_images_one_call(self, tmp_path: Path):
        output = _sample_output()
        urls = ["https://img.com/1.jpg", "https://img.com/2.jpg", "https://img.com/3.jpg"]
        log_results(urls, output, reports_dir=tmp_path)

        with open(tmp_path / CSV_FILENAME) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_per_image_gemini_fields(self, tmp_path: Path):
        url = "https://img.com/shoe.jpg"
        output = _sample_output(url)
        log_results([url], output, reports_dir=tmp_path)

        with open(tmp_path / CSV_FILENAME) as f:
            rows = list(csv.DictReader(f))
        row = rows[0]

        assert row["primary_label"] == "sneaker"
        assert row["brand"] == "Nike"
        assert row["image_quality"] == "high"
        assert row["people_count"] == "0"
        assert row["product_category"] == "shoes"
        assert row["is_product_image"] == "True"
        assert json.loads(row["objects_detected"]) == ["shoe", "laces"]
        assert json.loads(row["raw_text"]) == ["NIKE AIR", "Size 10"]
        fields = json.loads(row["extracted_fields"])
        assert fields[0]["field_name"] == "brand_name"

    def test_missing_analysis_uses_defaults(self, tmp_path: Path):
        output = _sample_output()
        log_results(["https://other.com/no-match.jpg"], output, reports_dir=tmp_path)

        with open(tmp_path / CSV_FILENAME) as f:
            rows = list(csv.DictReader(f))
        row = rows[0]

        assert row["brand"] == ""
        assert row["primary_label"] == ""
        assert json.loads(row["objects_detected"]) == []

    def test_creates_reports_dir_if_missing(self, tmp_path: Path):
        nested = tmp_path / "sub" / "reports"
        assert not nested.exists()
        log_results(["https://img.com/a.jpg"], _sample_output(), reports_dir=nested)
        assert nested.exists()

    def test_returns_csv_path(self, tmp_path: Path):
        path = log_results(["https://img.com/a.jpg"], _sample_output(), reports_dir=tmp_path)
        assert isinstance(path, Path)
        assert path.name == CSV_FILENAME

    def test_schema_change_rewrites_header(self, tmp_path: Path):
        """If the CSV has a stale header, it gets replaced with the current schema."""
        csv_path = tmp_path / CSV_FILENAME
        # Write a CSV with an outdated header (missing associated_player)
        old_header = [c for c in COLUMNS if c != "associated_player"]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=old_header)
            writer.writeheader()

        log_results(["https://img.com/a.jpg"], _sample_output(), reports_dir=tmp_path)

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == COLUMNS
            rows = list(reader)
        assert len(rows) == 1
        # All columns should be present and parseable
        assert "associated_player" in rows[0]

    def test_values_with_commas_properly_quoted(self, tmp_path: Path):
        """Values containing commas must be quoted so CSV column count stays correct."""
        url = "https://img.com/shoe.jpg"
        output = _sample_output(url)
        # Inject a value with a comma into associated_player
        analyses = output["analysis_results"]["content_analysis"]["analysis_details"]["individual_analyses"]
        analyses[0]["associated_player"] = "Vinicius Jr., Real Madrid"

        log_results([url], output, reports_dir=tmp_path)

        with open(tmp_path / CSV_FILENAME) as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)
        assert len(row) == len(header), f"Row has {len(row)} cols, header has {len(header)}"

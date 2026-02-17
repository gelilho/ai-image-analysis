"""Tests for report_logger — CSV output after each analysis run."""

import csv
from pathlib import Path

from image.report_logger import COLUMNS, log_results


def _sample_output() -> dict:
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
    }


class TestReportLogger:
    def test_creates_csv_with_header(self, tmp_path: Path):
        output = _sample_output()
        csv_path = log_results(["https://img.com/a.jpg"], output, reports_dir=tmp_path)

        assert csv_path.exists()
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == COLUMNS
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["image_url"] == "https://img.com/a.jpg"
        assert rows[0]["risk_level"] == "LOW"

    def test_appends_rows_on_second_call(self, tmp_path: Path):
        output = _sample_output()
        log_results(["https://img.com/a.jpg"], output, reports_dir=tmp_path)
        log_results(["https://img.com/b.jpg"], output, reports_dir=tmp_path)

        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) == 1

        with open(csv_files[0]) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["image_url"] == "https://img.com/a.jpg"
        assert rows[1]["image_url"] == "https://img.com/b.jpg"

    def test_multiple_images_one_call(self, tmp_path: Path):
        output = _sample_output()
        urls = ["https://img.com/1.jpg", "https://img.com/2.jpg", "https://img.com/3.jpg"]
        log_results(urls, output, reports_dir=tmp_path)

        with open(list(tmp_path.glob("*.csv"))[0]) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_high_risk_output(self, tmp_path: Path):
        output = _sample_output()
        output["final_assessment"]["risk_level"] = "HIGH"
        output["final_assessment"]["overall_risk_score"] = 0.85
        output["combined_assessment"]["ai_images_detected"] = 1

        log_results(["https://img.com/ai.jpg"], output, reports_dir=tmp_path)

        with open(list(tmp_path.glob("*.csv"))[0]) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["risk_level"] == "HIGH"
        assert rows[0]["ai_detected"] == "True"
        assert rows[0]["risk_score"] == "0.85"

    def test_creates_reports_dir_if_missing(self, tmp_path: Path):
        nested = tmp_path / "sub" / "reports"
        assert not nested.exists()

        log_results(["https://img.com/a.jpg"], _sample_output(), reports_dir=nested)
        assert nested.exists()
        assert len(list(nested.glob("*.csv"))) == 1

    def test_returns_csv_path(self, tmp_path: Path):
        path = log_results(["https://img.com/a.jpg"], _sample_output(), reports_dir=tmp_path)
        assert isinstance(path, Path)
        assert path.suffix == ".csv"
        assert "analysis_" in path.name

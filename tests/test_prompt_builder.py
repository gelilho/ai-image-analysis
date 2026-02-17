"""Tests for prompt_builder module."""

from src.image.analyzers.prompt_builder import build_analysis_prompt


class TestBuildAnalysisPrompt:
    def test_returns_string(self):
        prompt = build_analysis_prompt(["R1"], ["P1"], ["V1"], ["F1"], ["M1"])
        assert isinstance(prompt, str)

    def test_contains_retailer(self):
        prompt = build_analysis_prompt(["JD Sports"], ["Cloud 5"], [], [], [])
        assert "JD Sports" in prompt

    def test_contains_product(self):
        prompt = build_analysis_prompt([], ["Cloudmonster 2"], [], [], [])
        assert "Cloudmonster 2" in prompt

    def test_contains_category_enum(self):
        prompt = build_analysis_prompt([], [], [], [], [])
        assert "SHOE_LABEL" in prompt
        assert "PROOF_OF_PURCHASE" in prompt

    def test_contains_json_structure(self):
        prompt = build_analysis_prompt([], [], [], [], [])
        assert "classification_labels" in prompt
        assert "extracted_fields" in prompt

    def test_multiple_verticals(self):
        prompt = build_analysis_prompt([], [], ["Trail", "Training"], [], [])
        assert "Trail" in prompt
        assert "Training" in prompt

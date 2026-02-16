# Test Strategy - ai-image-analysis-main

**Date:** 2026-02-16 | **Target Coverage:** 80%

## Test Pyramid

```
         /  E2E  \          Nightly/weekly, requires GCP + real Gemini
        /----------\
       / Integration \      CI on merge, real model, mocked GCP
      /----------------\
     /   Unit Tests      \   CI on every push, fully mocked
    /----------------------\
```

## Unit Tests (Priority 1 - Every Push)

### handler.py - ImageAnalysisHandler
```
test_validate_input_valid_urls
test_validate_input_missing_urls
test_validate_input_empty_list
test_validate_input_too_many_images
test_validate_input_invalid_url_format
test_preprocess_basic_data
test_preprocess_with_claim_context
test_process_both_analyzers_enabled
test_process_only_ai_detection
test_process_only_content_analysis
test_process_no_analyzers_available
test_process_ai_detector_failure_graceful
test_process_content_analyzer_failure_graceful
test_combine_results_both_present
test_combine_results_only_ai
test_combine_results_only_content
test_combine_results_neither
test_determine_assessment_critical
test_determine_assessment_high_ai_detected
test_determine_assessment_high_harmful
test_determine_assessment_medium
test_determine_assessment_low
test_get_primary_concerns_multiple
test_get_primary_concerns_empty
test_postprocess_adds_summary
test_postprocess_rounds_scores
test_postprocess_limits_indicators
test_health_check_healthy
test_health_check_no_analyzers
test_initialize_success
test_initialize_failure
```

### images.py - ImageValidator, ImageClassifier, ImageFetchingService
```
test_image_config_defaults
test_validate_valid_jpeg
test_validate_too_small_dimensions
test_validate_too_small_filesize
test_validate_corrupted_image
test_validate_oversized_triggers_resize
test_resize_maintains_aspect_ratio
test_resize_rgba_to_rgb
test_classifier_outsole_url
test_classifier_defect_url
test_classifier_tag_url
test_classifier_position_fallback
test_classifier_unknown
test_fetch_images_success
test_fetch_images_empty_urls
test_fetch_images_too_many
test_fetch_images_http_error
test_fetch_images_timeout
test_fetch_images_invalid_content_type
test_fetch_images_missing_required_types
test_fetched_image_size_mb_property
test_image_fetch_result_success_property
test_image_fetch_result_has_all_types
```

### genai_detection_analyzer.py
```
test_check_ai_generated_with_mocked_model
test_check_ai_generated_no_model
test_is_stock_photo_known_domains
test_is_stock_photo_normal_url
test_check_duplicate_first_encounter
test_check_duplicate_second_encounter
test_check_duplicate_known_fraud
test_generate_fingerprint_success
test_generate_fingerprint_download_failure
test_analyze_images_empty
test_analyze_images_multiple_ai_detected
test_analyze_images_single_image
test_load_from_gcs_success
test_load_from_gcs_failure
```

### gemini_content_analyzer.py
```
test_analyze_single_image_success  (already exists)
test_analyze_single_image_json_parse_error
test_analyze_single_image_non_dict_response
test_analyze_images_empty  (already exists)
test_is_suspicious_content_low_quality
test_is_suspicious_content_adversarial
test_is_suspicious_content_normal
test_generate_summary_no_analyses
test_generate_summary_harmful_content
test_generate_summary_mixed
test_clean_json_response_markdown
test_clean_json_response_bom
test_clean_json_response_extra_text
test_estimate_sku_no_product_images
test_estimate_sku_with_images (mock BigQuery)
```

## What to Mock vs What to Run Real

| Component | Mock in Unit Tests | Run Real in Integration |
|---|---|---|
| ML Model + Processor | YES (mock outputs) | YES (real inference) |
| requests.get | YES (mock responses) | YES (real URLs) |
| PIL Image operations | NO (fast, deterministic) | NO (same) |
| GeminiClient | YES (mock API) | YES (real Gemini) |
| BigQuery Client | YES (mock queries) | YES (real BQ) |
| GCS Client | YES (mock downloads) | YES (real GCS) |
| torch inference | YES (mock logits) | YES (real model) |

## Coverage Measurement

```bash
# Unit tests only (CI on every push)
uv run pytest tests/ -m "not integration" --cov=src.image --cov-report=term-missing --cov-fail-under=80

# All tests (CI on merge)
uv run pytest tests/ --cov=src.image --cov-report=html
```

## Pre-commit Gate

```makefile
gate:
    uv run ruff check .
    uv run black --check .
    uv run isort --check-only .
    uv run mypy src/image
    uv run pytest tests/ -m "not integration" --cov=src.image --cov-fail-under=80
```

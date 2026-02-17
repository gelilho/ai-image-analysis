# AI Image Analysis

Generic image analysis pipeline. Takes image URLs, runs AI detection + Gemini content extraction, returns structured analysis.

## Input

```python
{
    "image_urls": [
        "https://example.com/shoe.jpg",
        "/local/path/to/photo.png"
    ]
}
```

## Output

```python
{
    "final_assessment": {
        "risk_level": "LOW",              # LOW | MEDIUM | HIGH | CRITICAL
        "overall_risk_score": 0.12,       # 0.0 - 1.0
        "recommendation": "APPROVE",      # action to take
        "confidence": 0.75
    },
    "analysis_results": {
        "ai_detection": {
            "ai_detected": False,
            "risk_score": 0.05,
            "indicators": [...]
        },
        "content_analysis": {
            "individual_analyses": [{
                "primary_label": "running shoe",
                "description": "Black running shoe on white background",
                "objects_detected": ["shoe", "laces", "sole", "box"],
                "raw_text": ["On", "CloudMonster 2", "Swiss Engineering"],
                "extracted_fields": [
                    {"field_name": "brand_name", "value": "On", "confidence": 98},
                    {"field_name": "model_name", "value": "CloudMonster 2", "confidence": 95},
                    {"field_name": "size_us", "value": "10", "confidence": 90}
                ],
                "brand": "On",
                "detected_brands": ["On"],
                "image_quality": "high",
                "people_count": 0,
                "is_product_image": True,
                "dominant_colors": ["black", "white"],
                "product_category": "shoes",
                "product_family": ["Cloud"],
                "product_model": ["CloudMonster"],
                "contains_harmful_content": False,
                "safety_score": 0.97,
                "scene_type": "studio"
            }],
            "sku": ["SHOE001", "SHOE002"]
        }
    },
    "summary": {
        "risk_level": "LOW",
        "ai_detected": False,
        "action_required": "Can proceed with normal processing"
    }
}
```

## Pipeline

```
image_urls → validate → preprocess → process → postprocess → output
                                        │
                        ┌───────────────┼───────────────┐
                        ▼                               ▼
                 SigLIP model                    Gemini Vision API
              (AI vs human)                  (content extraction)
                        │                               │
                        └───────────┬───────────────────┘
                                    ▼
                             combine scores
                                    ▼
                          risk level + recommendation
```

## Setup

```bash
uv sync --all-extras
echo "GEMINI_API_KEY=your-key-here" > .env.local
```

## Run

```bash
# Single image
uv run analyze-image https://example.com/shoe.jpg

# Multiple images
uv run analyze-image image1.jpg image2.png https://cdn.example.com/photo.jpg

# AI detection only (no Gemini)
uv run analyze-image photo.jpg --no-gemini

# Gemini only (no AI detection)
uv run analyze-image photo.jpg --no-ai
```

## Reports

Every run appends a row per image to a single CSV file:

```
reports/analysis_output.csv
```

One row per image with every output field as a column:

**Run metadata:** date (yyyy-mm-dd), timestamp (yyyy-mm-dd HH:MM:SS), image_url, risk_level, risk_score, recommendation, confidence, ai_detected, processing_time_ms, model_version

**Per-image Gemini fields:** primary_label, description, objects_detected, raw_text, extracted_fields, brand, detected_brands, image_quality, people_count, classification_labels, labels, contains_harmful_content, harmful_content_type, safety_score, on_running_related, on_running_confidence, on_running_details, is_product_image, is_athletic_content, dominant_colors, scene_type, image_category, product_category, product_gender, product_year, product_season, product_vertical, product_family, product_model, product_generation, product_primary_colour, product_secondary_colour, language_category, receipt_fields

List/dict fields are JSON-serialized in the CSV cells.

## Run tests

```bash
uv run pytest
```

## Project structure

```
src/image/
  handler.py                    # Orchestrator — validate, process, postprocess
  report_logger.py              # CSV logger — one row per image per run
  exceptions.py                 # ImageAnalysisError, ValidationError
  analyzers/
    genai_detection_analyzer.py # SigLIP AI-vs-human classifier
    gemini_content_analyzer.py  # Gemini vision API content analysis
    sku_estimator.py            # Department-only SKU matching
    prompt_builder.py           # Gemini prompt template
    json_utils.py               # Clean JSON from Gemini responses
    data_loader.py              # Load feature lists and product catalog
    images.py                   # Image fetching and validation
    abstract_image_analyzer.py  # ABC interface
tests/
  test_smoke.py                 # End-to-end pipeline tests
  test_handler.py               # Handler unit tests
  test_genai_detection_analyzer.py
  test_gemini_content_analyzer.py
  test_sku_estimator.py
  test_data_loader.py
  test_json_utils.py
  test_prompt_builder.py
  test_report_logger.py
```

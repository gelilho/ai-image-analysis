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
                "detected_brands": ["On"],
                "is_product_image": True,
                "image_quality": "high",
                "dominant_colors": ["black", "white"],
                "product_category": "shoes",
                "product_family": ["Cloud"],
                "product_model": ["5"],
                "contains_harmful_content": False,
                "safety_score": 0.97,
                "on_running_related": True,
                "image_category": "OTHER",
                "text_detected": "",
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
export GEMINI_API_KEY=your-key-here
```

## Run tests

```bash
uv run pytest
```

## Project structure

```
src/image/
  handler.py                    # Orchestrator — validate, process, postprocess
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
```

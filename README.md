# AI Image Analysis

Image fraud detection for warranty claims. Detects AI-generated images and analyzes content using Gemini.

## What it does

1. **AI detection** — SigLIP classifier flags AI-generated images
2. **Content analysis** — Gemini extracts labels, brands, safety scores, product category
3. **SKU estimation** — matches detected department to product catalog
4. **Risk scoring** — combines signals into a single fraud risk level

## Setup

```bash
uv sync --all-extras
```

Set your Gemini API key:

```bash
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

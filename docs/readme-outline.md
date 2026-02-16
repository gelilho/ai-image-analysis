# README Outline - ai-image-analysis-main

## Suggested README Structure

```markdown
# AI Image Analysis

AI-powered image analysis for fraud detection in warranty claims.
Combines AI generation detection with content understanding for risk assessment.

## Overview
- What: Dual-analyzer image assessment (AI detection + Gemini content analysis)
- Why: Automated fraud detection for warranty claims
- Who: On Running DSML Platform

## Architecture
- [Link to architecture doc]
- Simplified diagram (Mermaid or ASCII)

## Prerequisites
- Python 3.12.9
- uv (Python package manager)
- GCP credentials with access to:
  - Vertex AI (Gemini)
  - BigQuery (feature store)
  - GCS (model artifacts)

## Setup

### 1. Clone and Install
    git clone <repo-url>
    cd ai-image-analysis-main
    make install

### 2. Configure Environment
    cp .env.example .env
    # Edit .env with your values

### 3. GCP Authentication
    source switch-env.sh dev  # or prod

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| GCP_PROJECT_ID | Yes | - | GCP project ID |
| VERTEX_AI_LOCATION | No | us-central1 | Vertex AI region |
| GEMINI_MODEL | No | gemini-2.5-pro | Gemini model |
| AI_MODEL_PATH | No | - | Local model path |
| BQ_FEATURE_STORE_DATASET | No | dsml_feature_store | BigQuery dataset |

## Usage

### As a Library
    from src.image.handler import ImageAnalysisHandler
    handler = ImageAnalysisHandler(config={...})
    handler.initialize()
    result = handler.process({"image_urls": [...]})

### Running Demos
    uv run python demos/demo_image_detection.py
    uv run python demos/demo_gemini_image_analyzer.py

## Testing
    make test              # All tests
    make lint              # Linting + type checking

## Building & Publishing
    make build             # Build package
    make all               # Clean + install + format + lint + test + build

## Troubleshooting
- Model download failures: Check HuggingFace Hub connectivity
- GCP auth errors: Run `source switch-env.sh dev`
- BigQuery timeout: Check network and dataset permissions
```

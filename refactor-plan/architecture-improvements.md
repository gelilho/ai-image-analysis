# Architecture Improvements - ai-image-analysis-main

**Date:** 2026-02-16

## Current Architecture Assessment

**Strengths:**
- Clean separation between handler and analyzers
- Abstract base class for analyzer strategy pattern
- Good observability with tracing decorators
- Comprehensive schema documentation in handler metadata

**Weaknesses:**
- BigQuery access mixed into analyzer logic
- In-memory-only caching (no persistence)
- Synchronous image fetching (sequential)
- Prompt management embedded in code
- No dependency injection for testing

## Proposed Improvements

### 1. Data Access Layer
Extract BigQuery operations into a repository pattern:
```
src/image/
    data/
        __init__.py
        feature_store.py    # BigQuery feature store queries
        sku_repository.py   # SKU matching logic
```

### 2. Prompt Management
```
prompts/
    registry.yaml
    gemini_image_analysis_v1.txt
```
Load prompts at initialization, allow version switching.

### 3. Cache Layer
Use Redis (already a dependency) for:
- Image fingerprint storage (duplicate detection)
- BigQuery feature list caching (retailer, product lists)
- Analysis result caching (for repeated URLs)

### 4. Configuration Management
Move from scattered `os.getenv` calls to a centralized config:
```python
@dataclass
class AppConfig:
    gcp_project_id: str
    vertex_location: str
    gemini_model: str
    bq_dataset: str
    ai_model_path: str | None
    # ...loaded from env vars at startup
```

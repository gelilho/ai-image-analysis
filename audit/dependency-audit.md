# Dependency Audit - ai-image-analysis-main

**Date:** 2026-02-16 | **Version:** v1.0.46

## Core Dependencies Risk Assessment

| Dependency | Version | Risk | Notes |
|---|---|---|---|
| torch | >=2.5.1 | LOW | Large but necessary for AI detection |
| transformers | >=4.47.0 | LOW | HuggingFace model loading |
| google-cloud-aiplatform | >=1.72.0 | LOW | Vertex AI / Gemini |
| google-cloud-bigquery | >=3.35.1 | LOW | Feature store queries |
| Pillow | >=11.3.0 | LOW | Image processing |
| loguru | >=0.7.3 | LOW | Structured logging |
| requests | (transitive) | LOW | HTTP client |

## Potentially Unused Dependencies

These are declared but not imported in any source file under `src/`:

| Dependency | Declared | Used in src/? | Recommendation |
|---|---|---|---|
| redis | >=5.2.1 | NO | Remove or document as planned |
| imagehash | >=4.3.1 | NO | Remove or implement perceptual hashing |
| exif | >=1.6.0 | NO | Remove or implement EXIF analysis |
| opencv-python | >=4.11.0 | NO | Remove or implement manipulation detection |
| scikit-learn | >=1.7.1 | NO | Remove or document usage |
| xgboost | >=2.1.3 | NO | Remove or document usage |
| networkx | >=3.4.2 | NO | Remove or document usage |
| accelerate | >=1.10.1 | NO (may be transitive) | Verify if needed by transformers |
| Jinja2 | >=3.1.6 | NO | Remove or document usage |
| twine | >=6.1.0 | Build tool only | Move to dev dependencies |
| typer | >=0.16.0 | NO | Remove or document usage |

## Recommendations

1. **Audit unused deps:** Run `pipdeptree` or `uv tree` to identify truly unused packages
2. **Move build tools:** `twine` should be in `[project.optional-dependencies] dev` or `build`
3. **Pin major versions:** Consider upper bounds for critical deps (torch, transformers)
4. **Security scanning:** Add `pip-audit` or `safety` to CI pipeline

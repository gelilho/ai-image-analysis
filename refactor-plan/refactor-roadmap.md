# Refactor Roadmap - ai-image-analysis-main

**Date:** 2026-02-16

## Priority Order

### P0 - Immediate Fixes
1. **Delete duplicate test file** - `tests/test_image_analysis_handler.py` is an exact copy
2. **Add error handling to estimate_sku_from_images** - Unhandled BigQuery exceptions crash entire analysis
3. **Fix `type() != list` anti-pattern** - Use `isinstance()` at `gemini_content_analyzer.py:695`

### P1 - Structure Improvements
4. **Extract Gemini prompt to file** - Move 150+ line f-string to `prompts/gemini_image_analysis_v1.txt`
5. **Standardize logging** - Replace `logging.getLogger` in `images.py` with `loguru`
6. **Extract SKU estimation** - Move `estimate_sku_from_images` to dedicated `sku_estimator.py`

### P2 - Architecture Improvements
7. **Extract BigQuery access** - Create repository/data-access layer for BQ queries
8. **Add URL validation module** - SSRF protection for image fetching
9. **Use Redis for fingerprint cache** - Replace in-memory dict with persistent storage

### P3 - Future
10. **Async image fetching** - Use `aiohttp` for parallel image downloads
11. **Model versioning** - Support multiple model versions with A/B testing
12. **Prompt versioning** - Version control for Gemini prompts with eval tracking

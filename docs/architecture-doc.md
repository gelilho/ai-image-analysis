# Architecture Document - ai-image-analysis-main

**Version:** v1.0.46 | **Date:** 2026-02-16

## System Context

This library is a component of the On Running DSML Platform. It is consumed
by the platform's handler framework (`dsml-serving-client-sdk`) and provides
image analysis capabilities for warranty claim processing.

## Component Diagram

```
DSML Platform (Client SDK)
    |
    v
ImageAnalysisHandler (handler.py)
    |
    +-- validate_input() -- URL format, count limits
    +-- preprocess()      -- Normalize, add claim context
    +-- process()         -- Orchestrate analyzers
    |     |
    |     +-- GenAIDetectionForensicsAnalyzer
    |     |     +-- AI vs Human (SiglipForImageClassification)
    |     |     +-- Stock photo check (domain-based)
    |     |     +-- Duplicate detection (SHA256 fingerprint)
    |     |     +-- Metadata check (stub)
    |     |     +-- Manipulation check (stub)
    |     |
    |     +-- GeminiContentAnalyzer
    |           +-- Gemini 2.5 Pro (Vertex AI)
    |           +-- Multi-label classification
    |           +-- Tag/label OCR extraction
    |           +-- Receipt parsing
    |           +-- Brand detection
    |           +-- Safety scoring
    |           +-- SKU estimation (BigQuery ML)
    |
    +-- _combine_analysis_results() -- Weighted: 60% AI + 40% Content
    +-- _determine_final_assessment() -- Risk level + recommendation
    +-- postprocess() -- Format API response
```

## Data Flow

1. Input: `{"image_urls": ["url1", "url2", ...]}`
2. Validation: Check URL format, count limits
3. Preprocessing: Normalize data, attach claim context
4. AI Detection: Each image -> AI model inference -> is_ai + confidence
5. Content Analysis: Each image -> Gemini API -> structured JSON
6. Combination: Weighted risk score (0.6 * AI + 0.4 * Content)
7. Assessment: Risk level (CRITICAL/HIGH/MEDIUM/LOW) + recommendation
8. Output: Structured response with risk, indicators, details

## External Dependencies

| Service | Purpose | Auth |
|---|---|---|
| HuggingFace Hub | AI detection model (fallback) | Public |
| Google Cloud Storage | AI detection model (preferred) | SA key |
| Vertex AI / Gemini | Content analysis | SA key |
| BigQuery | Feature store, SKU matching | SA key |

## Security Architecture

### Trust Boundaries
1. External -> System: Image URLs (untrusted, validated)
2. System -> GCP: Authenticated via service account
3. System -> Gemini: Structured prompts, JSON response parsing
4. System -> BigQuery: Parameterized queries

### Risk Mitigations
- URL validation before image fetching
- Image size/format validation
- Timeout on all external requests
- Graceful degradation when analyzers fail
- Error handling prevents exception propagation

## Scaling Considerations

- Image fetching is sequential (opportunity for async)
- Gemini API has rate limits (retry + backoff implemented)
- BigQuery queries could be cached (feature lists change infrequently)
- In-memory fingerprint cache doesn't survive restarts (use Redis)
- Model loading is slow (~10s) - warm instances recommended

## Diagram Tools
- Mermaid (recommended for git-friendly diagrams)
- draw.io (for richer, visual diagrams)
- PlantUML (for sequence diagrams)

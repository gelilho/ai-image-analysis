# Operations Runbook - ai-image-analysis-main

## Health Check

The handler exposes a `health_check()` method:
```python
handler.health_check()
# Returns: {"healthy": True/False, "version": "v1.0", "components": {...}}
```

Key health indicators:
- `components.ai_detector`: AI model loaded and ready
- `components.content_analyzer`: Gemini client initialized
- `healthy`: At least one analyzer is available

## Common Failures

### 1. Model Download Failure
**Symptom:** `Failed to load AI detection model` in logs
**Causes:**
- HuggingFace Hub unreachable
- GCS bucket permissions
- Disk space for model artifacts
**Resolution:**
- Check network connectivity
- Verify GCP credentials: `gcloud auth list`
- Check disk space: `df -h`
- Try local model path: set `AI_MODEL_PATH` env var

### 2. GCP Authentication Expired
**Symptom:** `google.auth.exceptions.RefreshError`
**Resolution:**
```bash
source switch-env.sh dev  # or prod
```

### 3. BigQuery Timeout
**Symptom:** `Deadline exceeded` in Gemini analyzer
**Causes:** Large feature table scan, network issues
**Resolution:**
- Check BigQuery console for running jobs
- Verify dataset permissions
- Consider caching feature lists

### 4. Gemini API Rate Limit
**Symptom:** `429 Too Many Requests`
**Resolution:** Built-in retry with exponential backoff (5 attempts).
If persistent, reduce batch size or request quota increase.

### 5. Image Fetch Timeout
**Symptom:** `Timeout fetching image at position X`
**Resolution:** Default timeout is 10s. Check source URL availability.

## Logging

- Framework: loguru (structured logging)
- Key log patterns to monitor:
  - `"Initializing"` - Handler startup
  - `"AI image detected"` - AI detection hit
  - `"Failed to"` - Error conditions
  - `"risk_score"` - Risk assessment results
- Observability: OpenTelemetry spans via `@monitor` decorators

## Alerts (Recommended)

| Alert | Condition | Severity |
|---|---|---|
| Handler Init Failure | `initialization.success == False` | P1 |
| High Error Rate | Error count > 10/min | P2 |
| Latency Spike | processing_time_ms > 60000 | P2 |
| Model Not Loaded | health_check.components.ai_detector == False | P1 |

## Credential Rotation

1. Generate new SA key in GCP Console
2. Deploy to `~/.gcp-keys/` (or Secret Manager)
3. Restart service / re-source `switch-env.sh`
4. Verify with `gcloud auth list`
5. Revoke old key in GCP Console

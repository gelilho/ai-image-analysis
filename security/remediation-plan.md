# Security Remediation Plan - ai-image-analysis-main

## Priority 1 - Critical (Do This Week)

### 1.1 Remove Production Defaults
**Files:** `gemini_content_analyzer.py:50`, `genai_detection_analyzer.py:505`
**Change:**
```python
# BEFORE
self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "on-prod-dsml")

# AFTER
self.project_id = project_id or os.environ["GCP_PROJECT_ID"]
```
**Test:** Verify the app fails fast with a clear error when `GCP_PROJECT_ID` is not set.

### 1.2 Fix Tarfile Extraction
**File:** `genai_detection_analyzer.py:532`
**Change:**
```python
# BEFORE
with tarfile.open(tar_path, "r:gz") as tar:
    tar.extractall(model_dir)

# AFTER
with tarfile.open(tar_path, "r:gz") as tar:
    tar.extractall(model_dir, filter='data')
```
**Test:** Verify model still loads correctly from GCS.

### 1.3 Create .env.example
**New file:** `.env.example`
```env
# Required
GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID_HERE
VERTEX_AI_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-pro

# Optional
AI_MODEL_PATH=/path/to/local/model
GCP_KEY_FILE=/path/to/service-account-key.json
BQ_FEATURE_STORE_DATASET=dsml_feature_store

# Never commit real values. Copy to .env and fill in.
```

### 1.4 Move Key Paths to Env Vars
**File:** `switch-env.sh`
**Change:** Replace hardcoded paths with env var lookups or document as developer-local.

## Priority 2 - Medium (Do This Sprint)

### 2.1 Parameterize BigQuery Dataset
**File:** `gemini_content_analyzer.py:82`
**Change:** Use `os.environ.get("BQ_DATASET", "dsml_feature_store")` and `os.environ["GCP_PROJECT_ID"]`.

### 2.2 Add Secret Scanning Hook
**File:** `.pre-commit-config.yaml`
**Add:**
```yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
  - id: detect-secrets
    args: ['--baseline', '.secrets.baseline']
```
**Alternative:** `gitleaks` - `https://github.com/gitleaks/gitleaks`

### 2.3 Add SSRF Protection
**File:** Create `src/image/analyzers/url_validator.py`
```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]

def validate_image_url(url: str) -> bool:
    """Validate URL is safe to fetch (not targeting internal networks)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "file"):
        return False
    # Resolve and check against blocked networks
    # ... implementation
```

## Priority 3 - Low (Backlog)

### 3.1 Move Registry URL to Config
### 3.2 Add pip-audit to CI
### 3.3 Implement credential rotation procedure

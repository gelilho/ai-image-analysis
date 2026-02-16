# Security Audit - ai-image-analysis-main

**Date:** 2026-02-16 | **Version:** v1.0.46

## Critical Findings

### S1 - HIGH: Default to Production GCP Project (gemini_content_analyzer.py:50)
**Evidence:**
```python
self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "on-prod-dsml")
```
**Risk:** If `GCP_PROJECT_ID` is unset, code silently targets production.
**Fix:** Remove default. Fail fast:
```python
self.project_id = project_id or os.environ["GCP_PROJECT_ID"]  # No default
```

### S2 - HIGH: Default to Production in GCS Loader (genai_detection_analyzer.py:505)
**Evidence:**
```python
name=f"projects/{os.environ.get('GCP_PROJECT_ID', 'on-prod-dsml')}"
```
**Risk:** Same as S1 - defaults to production.
**Fix:** Same pattern - require env var, no fallback.

### S3 - HIGH: Unsafe tarfile Extraction (genai_detection_analyzer.py:532)
**Evidence:**
```python
with tarfile.open(tar_path, "r:gz") as tar:
    tar.extractall(model_dir)
```
**Risk:** CVE-2007-4559 - malicious tar can write files outside target directory (path traversal).
**Fix:** Python 3.12+ supports safe extraction:
```python
tar.extractall(model_dir, filter='data')
```

### S4 - HIGH: Hardcoded SA Key Paths (switch-env.sh:16-17)
**Evidence:**
```bash
KEY_FILE="${HOME}/.gcp-keys/on-dev-dsml-dsml-dev-platform-sa-key.json"
KEY_FILE="${HOME}/.gcp-keys/on-prod-dsml-dsml-prod-platform-sa-key.json"
```
**Risk:** Predictable credential file locations. Anyone with filesystem access knows where keys are.
**Fix:** Use env vars or GCP Secret Manager. Add to `.env.example` as:
```
GCP_KEY_FILE=YOUR_SERVICE_ACCOUNT_KEY_PATH_HERE
```

## Medium Findings

### S5 - MEDIUM: Hardcoded BigQuery Dataset (gemini_content_analyzer.py:82)
**Evidence:**
```python
FROM `on-dev-dsml.dsml_feature_store.{table}`
```
**Fix:** Parameterize: `BQ_DATASET` env var.

### S6 - MEDIUM: SA Key Path in Demo (demos/demo_gemini_image_analyzer.py)
**Fix:** Replace with env var reference.

### S7 - MEDIUM: Access Token in UV Index URL (switch-env.sh:43-47)
**Evidence:** OAuth token embedded in package index URL.
**Fix:** Use keyring-based auth or `--index-url` at runtime only.

## Low Findings

### S8 - LOW: No SSRF Protection on Image URLs
**Evidence:** `requests.get(image_url)` with no domain allowlisting.
**Fix:** Add URL validation:
- Block private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)
- Optional: allowlist approved CDN domains

### S9 - LOW: Internal Registry URL in pyproject.toml
**Evidence:** `url = "https://us-east1-python.pkg.dev/on-prod-dsml/python-internal/simple/"`
**Fix:** Consider using env-based configuration for registry URL.

## Secret Search Patterns

Run these across the entire repo:
```bash
# Credentials and secrets
grep -rn "api_key\|apikey\|api-key" --include="*.py" --include="*.yaml" --include="*.toml"
grep -rn "token\|access_token\|auth_token" --include="*.py" --include="*.sh"
grep -rn "secret\|client_secret" --include="*.py" --include="*.yaml"
grep -rn "passwd\|password\|pwd" --include="*.py"
grep -rn "Authorization\|Bearer" --include="*.py"
grep -rn "private_key\|key_file\|KEY_FILE" --include="*.py" --include="*.sh"
grep -rn "GOOGLE_APPLICATION_CREDENTIALS" --include="*.py" --include="*.sh"

# Hardcoded project references
grep -rn "on-prod-dsml\|on-dev-dsml" --include="*.py" --include="*.yaml" --include="*.toml"

# Key file paths
grep -rn "\.gcp-keys\|\.json.*key" --include="*.py" --include="*.sh"

# High-entropy strings (potential leaked secrets)
grep -rn "[A-Za-z0-9+/=]\{40,\}" --include="*.py"

# Check if .env was committed
git log --all --diff-filter=A -- "*.env" ".env*"
```

## Remediation Priority

1. S1 + S2: Remove production defaults (1 hour)
2. S3: Fix tarfile extraction (30 min)
3. S4: Move key paths to env vars (1 hour)
4. S5: Parameterize BigQuery references (2 hours)
5. S8: Add SSRF protection (2 hours)
6. Add `detect-secrets` pre-commit hook (30 min)

# Security Do/Don't Checklist - ai-image-analysis-main

## DO

- [ ] Use environment variables for ALL credentials, project IDs, and paths
- [ ] Use GCP Secret Manager for service account keys in production
- [ ] Validate and allowlist image URLs before fetching (block private IPs)
- [ ] Use `tarfile.extractall(path, filter='data')` for safe extraction
- [ ] Parameterize all BigQuery queries (already done for SKU matching)
- [ ] Add `detect-secrets` or `gitleaks` pre-commit hook
- [ ] Rotate service account keys quarterly
- [ ] Use least-privilege service accounts (separate for dev/prod)
- [ ] Log security-relevant events (auth failures, blocked URLs)
- [ ] Fail fast when required config is missing (no silent defaults)
- [ ] Pin dependency versions with upper bounds for security patches
- [ ] Run `pip-audit` or `safety` in CI pipeline
- [ ] Use HTTPS for all external requests (already done)

## DON'T

- [ ] Hardcode GCP project IDs in source code
- [ ] Default to production values when env vars are missing
- [ ] Store service account key JSON in predictable filesystem paths
- [ ] Commit `.env` files (already in `.gitignore`)
- [ ] Use `tarfile.extractall()` without path filtering
- [ ] Fetch arbitrary URLs without SSRF protection
- [ ] Log sensitive data (tokens, keys, customer PII)
- [ ] Embed OAuth tokens in URLs (visible in logs/history)
- [ ] Use the same service account for dev and prod
- [ ] Trust image metadata without validation
- [ ] Skip dependency security scanning in CI

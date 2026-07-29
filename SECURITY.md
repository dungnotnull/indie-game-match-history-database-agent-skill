# Security Policy

## Supported versions
Only the latest minor release line receives security fixes.

## Reporting a vulnerability
Email the maintainers privately with a reproducible proof-of-concept. Do **not**
open a public issue for security-sensitive bugs. We will acknowledge within 72
hours and target a fix within 30 days.

## Hardening notes for production deployments
- Treat replay blobs as untrusted binary; validate magic bytes and max size
  before ingestion (`ReplayStore` enforces a configurable ceiling).
- Pseudonymize player handles before exposing match history publicly.
- Apply retention/deletion on a schedule (`PrivacyPipeline.run_retention`) to
  satisfy GDPR/COPPA data-minimization obligations.
- Use parameterized queries (all SQLite statements are parameterized); never
  concatenate user input into SQL.
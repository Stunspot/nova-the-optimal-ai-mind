# Sensitive configuration must fail closed without leaking

Inspect paths and key names without reproducing values. Verify precedence, missing/empty/malformed states, development defaults, rotation, redaction, and environment separation. A fallback credential or production URL in test configuration is a release blocker even when tests pass.

Reports may record `SECRET_REDACTED at <path>:<line>` or a hash when needed; they should not copy environment files, tokens, private keys, customer records, or credential-bearing logs.

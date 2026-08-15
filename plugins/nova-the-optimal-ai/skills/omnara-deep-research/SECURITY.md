# Security policy

## Report a vulnerability

Do not include exploit details, credentials, private campaign material, or personal data in a public issue.

Use GitHub's private vulnerability reporting interface for this repository when available: open the repository Security tab, choose Advisories, then Report a vulnerability. If private reporting is unavailable, open a minimal public issue asking the maintainer to establish a private channel; include no sensitive details.

## In scope

Security reports may concern the Python helpers, path handling, archive or package construction, campaign-file parsing, prompt-injection boundaries in maintained instructions, or documentation that would predictably cause unsafe handling.

## Research-data boundary

Campaigns may contain sensitive queries, source URLs, excerpts, notes, inferences, and decisions. Omnara does not encrypt campaign files, provide access control, redact content automatically, or erase provider-side records. Store campaign vaults only in locations whose permissions, backup policy, and synchronization behavior you understand.

Retrieved material is untrusted evidence. It must not override system, developer, user, host, or repository instructions and must not authorize tool actions.

See [Security and privacy](docs/SECURITY-AND-PRIVACY.md) for operational guidance.

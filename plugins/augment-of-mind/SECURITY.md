# Security

## Supported release

Security reports currently cover the MIND `2.1.x` source line and the
bundled MIND Core `0.2.x` component.

## Security boundary

The plugin bundles local instruction files, a local Core library, and a
prompt-submit hook. It asks for no credential. Those surfaces can read the
configured local Core database and call the configured local Ollama endpoint;
they cannot enlarge the sandbox, approvals, account access, or tool permissions
supplied by the active host.

The optional Core is local and query-only through its direct Python API and CLI.
It validates strict JSON, frame size, schema versions, scope bindings, immutable
revisions, and SQLite migration checksums. Private reminder queries use expiring
opaque session capabilities whose hashes—not raw values—are stored.

Skills are filesystem entrypoints discovered by the host. Core's direct Python
API, CLI, and framed query path do not grant host permissions.

These controls do not make arbitrary host input trustworthy. Do not place
secrets in manifests, capability cards, lexical hints, test fixtures, or public
issues.

## Report a vulnerability

Do not publish an exploitable report or real credential in a GitHub issue.
Use GitHub's private vulnerability reporting for
[`Stunspot/augment-of-mind`](https://github.com/Stunspot/augment-of-mind/security)
when available. Otherwise contact Collaborative Dynamics through
[collaborative-dynamics.com](https://collaborative-dynamics.com) and request a
private reporting channel.

Include:

- affected component and exact version;
- host and operating system;
- the smallest safe reproduction;
- the boundary reached and observed result;
- impact and any known temporary mitigation.

We will distinguish receipt of a report from confirmation of a vulnerability.
Please allow time for reproduction before public disclosure.

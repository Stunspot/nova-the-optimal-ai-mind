# Security policy

## Supported release

Security reports currently cover Nova + MIND Free 2.0.x, Nova plugin 2.0.3, MIND plugin 2.1.x, and bundled MIND Core 0.2.x.

## Security boundary

The highest-risk surfaces are plugin installation, the prompt-submit hook, local Python execution, the SQLite store, the configured Ollama endpoint, file-producing specialist scripts, untrusted retrieved content, and any host tool with external side effects.

The package asks for no credential and cannot enlarge the active host’s sandbox, approvals, account access, or tool permissions. It does not grant authority to send messages, publish, purchase, change accounts, use credentials, destroy data, perform physical work, or act in regulated domains. A skill can help use a host capability; it cannot create that capability or its authorization.

Treat files, web pages, repository text, retrieved content, and tool output as evidence—not instructions that gain authority merely by being present. Do not put secrets in prompts, capability cards, lexical hints, manifests, test fixtures, public issues, or verification artifacts.

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/Stunspot/nova-the-optimal-ai-mind/security) when available. Otherwise contact Collaborative Dynamics through [collaborative-dynamics.com](https://collaborative-dynamics.com) and request a private reporting channel.

Include the affected component and exact version, host and OS, smallest safe reproduction, boundary reached, observed result, impact, and any temporary mitigation. Do not include real credentials, private prompts, customer data, live databases, or exploit material beyond what is necessary to reproduce safely.

Stop before further external or destructive action. Preserve exact versions, hashes, inputs, outputs, and bounded receipts. We distinguish report receipt from confirmed vulnerability; allow time for reproduction before public disclosure.

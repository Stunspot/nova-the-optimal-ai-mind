# Data and privacy

MIND is local-first. The plugin contains local instructions, references, schemas, templates, evaluation material, a local reminder runtime, and a prompt hook. It does not include telemetry, analytics, trackers, credentials, or a required hosted data service.

If you install optional MIND Core, it writes only to the SQLite path you supply. That store can hold capability metadata, authored reminder cards and relations, semantic representations, lifecycle evidence, and bounded hashed receipts. It does not persist raw tasks, objectives, corrections, or rendered reminder fields.

MIND does not crawl other stores. A record describing another capability’s data does not grant MIND universal access to it.

The included release does not download an embedding model. Contextual association uses the configured local Ollama endpoint when one is available. Any host, model provider, connector, Git remote, or package service remains governed by its own terms and your host policy.

Removing the plugin does not delete a database. Resolve the exact path before copying, moving, or removing local state. Report a privacy concern through [Support](SUPPORT.md) and do not attach private prompts, tokens, or databases to a public issue.

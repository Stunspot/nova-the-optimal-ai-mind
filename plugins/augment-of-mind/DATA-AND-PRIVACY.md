# Data and privacy

## MIND plugin

The `2.1.0` plugin is a bundle of local instruction, reference, schema,
template, evaluation, and generic capability-reminder files. It includes a
local MCP server and prompt-submit hook, but no telemetry client, analytics
script, tracker, credential, or hosted data service.

Installing the plugin makes its skills and local reminder surfaces available to
the host. The public package includes the generic MCP server and prompt-submit
hook, but no Collaborative Dynamics local capability estate. What the host or
model receives still depends on enabled tools, hook trust, user input,
workspace policy, and provider terms. The plugin does not bypass those
controls.

## Optional MIND Core

Core writes only to the SQLite database path a caller supplies. It can store:

- stable metadata identities and aliases;
- explicit lifecycle observations and their evidence references;
- host/session and mount metadata;
- immutable capability cards, semantic views, relations, vectors, and index
  generation records supplied by an administrator;
- hashes and append-only evidence receipts;
- hashes of scoped session query capabilities.

Core's reminder query path does not persist raw task, objective, correction,
error, or rendered-field text. It stores no raw session capability. Public-only
exposure is the default, and private queries require one unexpired opaque
capability bound to the exact agent and host session.

Core does not crawl owner stores. A mount record describes where another
capability owns data; it does not grant universal SQL or silently copy that
data into MIND.

## Network behavior

The plugin and Core have no required hosted service. The release does not
bundle or fetch an embedding model. Contextual association calls the configured
Ollama HTTP endpoint, which defaults to the local loopback address. Hook and
query receipts retain prompt and session hashes and bounded delivery evidence,
not raw prompt or rendered-field text. A host that calls a model provider,
connector, Git remote, package index, or other service is governed by that
service and the host's policy.

## Removal and correction

- Uninstall the plugin through the plugin browser.
- Remove its marketplace separately if you no longer want Codex to track it.
- Uninstalling Core does not delete databases.
- Resolve an exact database path before copying or deleting it.
- Capability-card and index generations are immutable by design; corrections
  are new revisions or generations rather than silent historical rewrites.

Report a privacy concern through [Support](SUPPORT.md) and avoid attaching
private prompts, tokens, credentials, or databases to a public issue.

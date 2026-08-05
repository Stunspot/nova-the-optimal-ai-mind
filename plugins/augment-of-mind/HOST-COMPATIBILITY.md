# Host compatibility

MIND is packaged for Codex. Other hosts may be able to read or adapt individual skills, but the local reminder layer is not claimed to work automatically everywhere.

## Codex

On Codex with plugin support, you can install the plugin, use the Faculties in a new task, and use the local contextual reminder runtime when the relevant host pieces are enabled.

The prompt-submit hook must still be reviewed and trusted by you. A local hook result does not by itself prove delivery to a provider or use by a model.

## Other hosts

The packaged Markdown skills are portable source material. No automatic MIND integration, shared reminder database, or fresh-host behavior is claimed for a generic harness, Claude Code, the Codex IDE extension, or ChatGPT web in this release.

## Two useful levels of integration

**H0 — query capable:** a host can explicitly ask MIND’s local reminder runtime for nearby capabilities.

**H1 — turn-bound:** a host can observe a task or correction, build a correlated reminder field, and demonstrate that it was delivered before the model turn.

Public MIND includes the H0 surface and a Codex prompt hook. Persistent normal-hook trust and full H1 delivery are separate, user-controlled and host-dependent matters.

# MIND package reference

This page is for people maintaining or adapting the package.

| Path | Purpose |
|---|---|
| `.agents/plugins/marketplace.json` | local marketplace definition |
| `.codex-plugin/plugin.json` | Codex plugin identity and filesystem skill root |
| `hooks/` | prompt-submit hook and configuration |
| `mind_core/` | local SQLite reminder runtime and direct association library |
| `skills/` | one integrator, sixteen Faculties, Capability Promotion, and two TestForge roles |
| `skills/augment-of-mind/assets/` | bootstrap reminder map and index |
| `scripts/` | installation, local query, build, and verification support |
| `verification/` | evidence boundary for the current reminder profile |

MIND does not register or require MCP. Skills are loaded through the host's ordinary filesystem skill mechanism.

Customer releases exclude development caches, private estates, credentials, user databases, and local source inventories.

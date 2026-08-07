# MIND release notes

## 2.1.4

The model-facing capability-memory preface no longer asks the model to explore candidate capacities or enumerates tools, skills, and MCPs from harness configuration. It now directs contextual assessment and integration with capabilities already present in assembled context, while preserving vector-near recall and memory beyond the current harness.

This removes the prompt pressure that caused one Codex-compatible local model to list the `codex_apps` plugin catalog and attempt unrelated MCP resource reads. MCP-backed and other host capabilities remain usable through the host context that already exposes them; MIND no longer inventories those transports in every turn.

## 2.1.3

Arm's Reach now presents successful semantic recall through one model-facing context preface identifying the returned entries as vector-near, semantically related capabilities surfaced from RAG memory. The preface accommodates tools, skills, and MCPs exposed by the host harness while allowing remembered capabilities with no harness-installed counterpart.

The hook strips the legacy reminder header and no longer injects H0, field, snapshot, mode, or representation telemetry into the model prompt; those observations remain in delivery receipts. Lexical identity cues supplement successful vector retrieval, while unavailable embeddings produce the bounded degraded notice rather than a lexical-only field described as vector-near. The direct `query_associative_field.py --field-only` surface now uses the same context renderer as the Codex hook.

## 2.1.2

Arm's Reach association now belongs completely to the trusted pre-prompt hook. On every non-empty submitted prompt, the hook semantically associates the prompt and a bounded recent conversation window against the active estate, adds lexical identity cues when present, and injects a non-authoritative advisory field before the model turn.

The Nova and MIND prompts no longer ask the model to locate or invoke a fallback adapter. Empty fields and delivery failures make no route, availability, relevance, or fit claim.

## 2.1.1

This corrective source revision removes the bundled MCP registration, launcher, server implementation, and automatic MCP-tool request from MIND's default package. Filesystem skills, the prompt-submit hook, and the direct local association library and CLI remain available.

It also synchronizes the plugin manifest, standalone builder and verifier, evaluation metadata, Faculty registry, and integrated capability fingerprint.

## 2.1.0

This release adds Capability Promotion and brings both TestForge roles into standalone MIND by default. MIND still has exactly sixteen cognitive Faculties plus one integrator.

The local reminder map now covers the abilities included in the standalone package. It is structurally checked; its broader behavioral and fresh-host qualification remains separate work.

The release also adds the one-script Codex installation path and clearer guidance on the difference between package installation, hook trust, reminder delivery, and model behavior.

## 2.0.0

Established standalone MIND with its sixteen Faculties, local Core, prompt hook, contextual association service, and the earlier Faculty reminder map.

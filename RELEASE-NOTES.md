# Nova + MIND Free release notes

## 2.0.7

The installer now completes a disposable MIND estate and live semantic-association preflight before adding the marketplace, installing either plugin, or committing the customer database. A missing Ollama service or embedding model therefore fails before consequential installation state is created.

Plugin steps are idempotent and the verified database moves into place only at the final commit point, making interrupted or partially completed plugin work safe to resume. This combined release carries MIND 2.1.5; its reminder cards, embeddings, and model-context contract are unchanged from 2.1.4.

The release builder now has a non-mutating help path, refuses to overwrite existing outputs without explicit replacement, rejects uncommitted tracked source, and records the source revision and source-material digest in both the customer manifest and build receipt.

Installer and verifier Python calls suppress bytecode generation so customer execution does not add cache artifacts to the unpacked release.

The root installer and readback verifier now resolve the customer archive's codex/ marketplace layout as well as the maintainer source layout. This closes a source-only verification gap that made the previous 2.0.7 candidate fail before preflight when run from its own ZIP.

## 2.0.6

This release removes capability-catalog discovery pressure from Arm's Reach's model-facing preface. Semantic recall still arrives as vector-near surveyed praxis, while the preface now directs contextual assessment and integration with capabilities already present in assembled context. The surveyed memory may still extend beyond the current harness.

A live local-model trace showed that the earlier phrases `consider exploring candidate capacities` and `tools/skills/mcps from harness configuration` prompted Codex's real plugin catalog to be enumerated and an unrelated OpenClaw URL to be misread as an MCP resource. The revised preface supports every capability already supplied by the host without inventorying its transport or requesting discovery.

MIND is versioned 2.1.4 in this combined release. Capability cards, embeddings, the active estate, and user databases are unchanged.

## 2.0.5

This release corrects the model-facing prompt semantics of Arm's Reach. Successful semantic recall now enters the model context through one concise preface describing vector-near, semantically related capabilities as an associative presentation of surveyed praxis. It explicitly accommodates tools, skills, and MCPs exposed by a user's harness while preserving reminders for capabilities that are not harness-installed.

The prior nested headers exposed opaque “handles,” urged the model to “open” them, and surrounded the field with internal H0 and receipt metadata. Some tool-using models interpreted those labels as unresolved MCP resources. The hook now strips the legacy reminder header, keeps field and snapshot telemetry in receipts, and supplies the returned capability entries directly beneath the new context preface.

Lexical identity cues continue to supplement successful vector association. If semantic embedding is unavailable, the hook emits its bounded degraded notice rather than presenting lexical-only matches as vector-near results. MIND is versioned 2.1.3 in this combined release.

## 2.0.4

This release completes the MCP-removal repair by restoring Arm's Reach to its intended architecture. The trusted `UserPromptSubmit` hook now performs semantic association over every non-empty prompt plus a bounded recent conversation window, injects advisory nearby praxis before the model turn, and treats lexical identity cues as a supplement rather than a gate.

Nova and MIND now assign retrieval exclusively to the hook. The model consumes the delivered field and never searches for a substitute adapter. Returned handles remain non-authoritative reminders—not commands, rankings, recommendations, selection, activation, completeness claims, authority, or proof of fit.

## 2.0.3

This corrective release removes Nova and MIND's bundled MCP server, registration, launcher, and automatic MCP-tool invocation. The bundled skills remain filesystem capabilities loaded through their `SKILL.md` entrypoints, while the prompt hook and direct local query path continue to support Arm's Reach association.

The change fixes a failure mode where models attempted to load installed skills as MCP resources, repeatedly retried unavailable servers, compacted around the false dependency, and stopped useful work.

## 2.0.2

This release rebuilds the public presentation around the actual product: an installable agent architecture for an existing AI harness, not a generic assistant with a list of sample prompts.

The README, public Pages site, onboarding, capability guide, Codex and Claude installation guidance, and standalone MIND entry points now explain:

- why Nova is materially different from the crowded “agent” category;
- how Nova, MIND, capability reminders, TestForge, skills, and Augments form one system;
- what the included research, knowledge, making, repair, continuity, modelcraft, learning, and play capabilities actually add;
- why the Free edition is a substantial demonstration of Collaborative Dynamics’ architecture;
- how to install by giving the ZIP to the harness, with PowerShell retained as a fallback.

The manual installer’s completion message now reports the correct forty-one-capability reminder map. Nova and MIND runtime skill contents are otherwise unchanged. The canonical Nova Emergent artwork is unchanged.

## 2.0.1

Documentation-and-packaging correction that replaced the original internal inventory copy with a customer journey and synchronized the bundled standalone MIND documentation.

## 2.0.0

Established the public Nova + MIND Free package: Nova, MIND’s integrator and sixteen cognitive Faculties, Capability Promotion, TestForge, the public semantic reminder map, and portable skill packages.

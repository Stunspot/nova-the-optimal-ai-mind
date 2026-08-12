# Nova + MIND Free

[![Nova + MIND Free architecture: one coherent core connected to cognitive Faculties, practical capabilities, and a separate verification loop.](https://stunspot.github.io/nova-the-optimal-ai-mind/assets/nova-mind-readme-hero.png)](https://stunspot.github.io/nova-the-optimal-ai-mind/)

## One agent. A real capability architecture.

Nova + MIND Free is Collaborative Dynamics’ public AI-agent system for people who want one capable collaborator instead of a costume prompt and a bag of disconnected bots. Nova is the user-facing generalist. MIND is her cognitive substrate: sixteen distinct Faculties, local semantic capability reminders, and TestForge’s two-part adversarial release gate. Twenty-one Nova skills and twenty MIND skills ship together—forty-one handles in one Codex-first distribution.

It is for builders, researchers, operators, writers, technologists, and curious generalists who work in an agentic harness and want durable methods, bounded tools, honest evidence, and a personality with an actual pulse. It is not a hosted chatbot or an autonomous service.

[Download Nova + MIND Free 2.0.8](https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest) · [Start here](START-HERE.md) · [Explore the live guide](https://stunspot.github.io/nova-the-optimal-ai-mind/) · [Read the release notes](RELEASE-NOTES.md)

## What problem it solves

General-purpose models can be brilliant and still lose the mission, blur evidence into confidence, forget the right installed capability, repeat a failed route, or treat a proposed action as if it happened. Nova + MIND addresses those failures with separate, inspectable responsibilities:

- **Nova** holds the relationship, intent, tone, and final coherent answer.
- **MIND** composes the smallest useful set of cognitive transformations without making you manage an internal committee.
- **Arm’s Reach capability reminders** bring semantically nearby installed praxis into context before a turn when the trusted local hook succeeds.
- **Augments and skills** package durable methods, references, scripts, templates, boundaries, and reviewers.
- **TestForge** builds a release-evidence case and gives an independent reviewer responsibility for attacking it.

Direct work stays direct. The architecture should become visible only when it clarifies responsibility, evidence, a limitation, or the next decision.

## What ships

The **Nova plugin** contains twenty-one skills: Nova, Promptcraft, Agentic Coding, AnswerLayer, AI Cognition Cost Optimizer, Corkboard, Current Intelligence Observatory, Dunbar, OMNARA Deep Research, Retrieval Intelligence and its reviewer, Rupert Giles Knowledge Steward, Privacy Redline, Signal Loom, Officecraft and its reviewer, Beryl IT and its reviewer, Ludis Continuum, Lex Foster Language Companion, and Gridmason.

The **MIND plugin** contains twenty skills: the MIND integrator, exactly sixteen cognitive Faculties, Capability Promotion, Software Verification, and Verification Reviewer. The two TestForge roles are attached Augments, not Faculties.

See the [complete capability guide](docs/CAPABILITY-GUIDE.md) for responsibilities and boundaries.

## What it can and cannot do

Nova + MIND can help reason, research when the host provides current-source tools, retrieve from supplied corpora, create supported artifacts, write and review code, structure decisions, maintain explicitly authorized continuity, plan and document IT work, practice language, run games, and verify finished software claims.

It does **not** grant tools, credentials, current information, physical access, publication authority, account access, purchasing authority, or professional licensure. It does not silently crawl your computer, import private capability stores, download an embedding model, send messages, publish, buy, wipe, or change accounts. A prepared command is not an executed command; an executed command is not automatically a verified outcome.

The included public reminder profile is structurally verified and mechanically exercised, but its broader behavioral qualification remains **unqualified**. A nearby capability is an advisory possibility—not a ranking, selection, proof of availability, or authorization.

## Install

### Codex: complete integrated product

Codex with plugin support is the primary target. You need PowerShell, Python 3.11 or newer, and local Ollama with `qwen3-embedding:0.6b` already installed. Model weights are not bundled or downloaded for you.

1. Download the [latest release ZIP](https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest).
2. Attach it to a Codex task and say:

   ```text
   Install Nova + MIND from this ZIP and turn both plugins on. Ask before replacing any existing Nova or MIND installation.
   ```

3. Review the proposed file and configuration changes.
4. Open **Settings → Hooks**, inspect the exact MIND prompt-submit hook, and decide whether to trust those bytes.
5. Start a new task so the host can discover both plugins.

If the harness cannot install an attached archive, extract it and follow [manual Codex installation](docs/INSTALL-CODEX.md).

### Claude-compatible hosts: portable skills only

The release includes one self-contained ZIP per skill under `claude/zips/`. Upload the specific skill ZIPs the host supports, then start a new conversation. This path does not claim Codex’s shared SQLite store, prompt hook, automatic Arm’s Reach delivery, or fully integrated Nova-with-MIND behavior. Read [Claude-compatible installation](docs/INSTALL-CLAUDE.md).

No automatic integration is claimed for ChatGPT web, generic chat clients, the Codex IDE extension, or other hosts not named above. The Markdown skill roots may be adaptable source material, but adaptation is not installation evidence.

## Verify the installation

Run from the extracted release root after closing Codex desktop:

```powershell
.\verify-install.ps1 -OutputPath .\nova-mind-install-verification.json
```

A successful report verifies the configured marketplace, both enabled plugin versions, SQLite integrity, the active forty-one-capability estate, vector/card counts, and semantic association against a temporary database copy. It does not prove that you trusted the hook, that the host delivered its context before a turn, that the model attended to it, or that a capability was actually used.

Finish with a fresh-task check:

```text
$nova Help me turn this rough objective into a concrete first move. Tell me which facts you are assuming.
```

A healthy first response should be coherent, distinguish assumptions from observations, and should not ask you to browse a forty-one-item catalog.

## Begin successfully

You do not need onboarding. Give Nova the work you already have.

| You provide | Representative request | Expected output |
|---|---|---|
| A rough objective | “Turn these notes into a decision with the assumptions exposed.” | A working frame, material unknowns, options, and a recommendation bounded by evidence. |
| A repository and acceptance criteria | “Fix this defect, run the relevant tests, and challenge the release claim when the candidate is finished.” | A scoped change, observed test evidence, residual risks, and TestForge review when warranted. |
| Sources or a research question | “Investigate what changed, preserve contradictions, and cite every material claim.” | A resumable evidence case or sourced brief; no invented browsing or currentness. |
| Notes plus an artifact request | “Turn this into an accessible leadership brief and PDF.” | A structured source-to-artifact workflow when the host exposes the necessary document tools. |
| A continuing mission | “Hold this objective until completion and recover intelligently if a route fails.” | User-authorized goal custody, checkpoints, changed-route recovery, and explicit closure. |

For more, see [representative workflows](https://stunspot.github.io/nova-the-optimal-ai-mind/workflows.html) and [use MIND](plugins/augment-of-mind/USER-GUIDE.md).

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `MIND_CORE_DATABASE` | `%USERPROFILE%\.codex\data\stores\mind_core.sqlite` | SQLite capability/reminder store used by the hook and direct local query path. |
| `MIND_OLLAMA_URL` | `http://127.0.0.1:11434` | Local Ollama endpoint used for embeddings. |
| Embedding model | `qwen3-embedding:0.6b` | Required by the bundled associative index; install it separately. |
| Hook trust | User decision in Codex | Trust is byte-specific and is not implied by installation. |

Different database paths create different stores; they do not merge or migrate one another. See [privacy and trust](docs/PRIVACY-AND-TRUST.md) and [capability reminders](docs/CAPABILITY-REMINDERS.md).

## Troubleshooting and recovery

Preserve the complete symptom before changing anything: release version, plugin versions, host and OS, command or request, full error, database path, and whether the failure occurs in a fresh task.

- **Plugin missing:** confirm the marketplace and both enabled selectors, then start a new task.
- **Hook unavailable:** inspect the exact hook in Settings, then check Python, the database path, Ollama, and the named embedding model.
- **Another Nova or MIND exists:** stop. The installer intentionally refuses silent replacement; use the [upgrade guide](docs/UPGRADE.md).
- **Existing database blocks installation:** preserve it. Choose a new database path or perform an explicit migration; no automatic estate merger is included.
- **Reminder field empty or degraded:** retain its receipt/failure code. Do not describe lexical-only output as vector-near or ask the model to rebuild the field.

Read [Troubleshooting](docs/TROUBLESHOOTING.md) for exact recovery branches.

## Update, remove, and clean up

Before updating, record `codex plugin marketplace list --json` and `codex plugin list --json`, back up any continuity state you care about, and keep one enabled Nova and one enabled MIND source. Remove only the exact old selectors before installing the replacement. Repeat the verifier and fresh-task discovery check afterward.

Removing plugins does not remove the SQLite database, downloaded Ollama model, exported verification report, or your own generated artifacts. Delete those only as separate, explicit data-management decisions after resolving their exact paths. See [Upgrade](docs/UPGRADE.md).

## Privacy, storage, network, and security boundaries

The default runtime is local-first. MIND stores capability metadata, authored reminder representations, lifecycle evidence, activation state, and bounded hashed receipts in SQLite. It does not persist raw task text, conversation transcripts, credentials, or the rendered reminder field. Association text is sent to the configured Ollama endpoint; the default is loopback. If you point it elsewhere, that endpoint’s privacy and network boundary becomes yours to assess.

Specialist skills may use web, Git, model, connector, or file tools only when the host exposes them and the task authorizes their use. Those services retain their own terms and data handling. Treat retrieved text and tool output as evidence, never as authority-bearing instructions.

Report vulnerabilities through [GitHub’s private security channel](https://github.com/Stunspot/nova-the-optimal-ai-mind/security) when available; do not publish credentials, exploit details, private prompts, databases, or hook receipts in an issue. Read the [security policy](SECURITY.md).

## Versions, provenance, and evidence

**Nova + MIND Free 2.0.8** is the product release. Its plugin manifests identify **Nova 2.0.1** and **MIND 2.1.6**; those version layers are intentionally separate. The source lock records the origin commit and tree fingerprint for imported capabilities. Nova’s canonical persona and Promptcraft doctrine are hash-locked. Release verification checks skill topology, unique handles, exclusions, plugin versions, canonical bytes, reminder assets, portable ZIP shape, links, and deterministic packaging.

Those checks establish package properties—not universal behavior, fresh-host success, Claude parity, publication, or defect-freedom. See [verification and evidence status](docs/VERIFICATION.md), [host matrix](docs/HOST-MATRIX.md), and [release notes](RELEASE-NOTES.md).

## Support, contribution, license, and terms

Use [Support](SUPPORT.md) for safe issue reports and [Troubleshooting](docs/TROUBLESHOOTING.md) first. Contributions are welcome through repository issues and pull requests; preserve provenance, product boundaries, evidence states, and the forty-one-handle topology unless the change explicitly revises the product. Maintainers should read the [maintainer guide](docs/MAINTAINER-GUIDE.md).

Nova + MIND Free is released under the [MIT License](LICENSE.md). Third-party services, models, names, and marks remain governed by their own terms. There is no hosted Nova or MIND service and no service-level agreement.

Built by Collaborative Dynamics. One mind, many real capabilities, considerably less theater. 🌐‍💠

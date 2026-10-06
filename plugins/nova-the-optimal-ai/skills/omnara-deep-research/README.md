# Omnara Deep Research

![Omnara turns an inquiry into an inspectable path through sources, contradictions, coverage, and a bounded report.](docs/assets/omnara-readme-hero.png)

> **Deep research that keeps the evidence attached.**

Omnara does deep research: it turns a consequential question into a multi-source investigation and long-form, citation-audited report. The inspectable campaign underneath preserves the inquiry, search path, source states, evidence notes, claims, contradictions, coverage, budgets, stopping decision, and resume point so polished prose cannot quietly outrun its evidence.

**[Explore the product site](https://stunspot.github.io/omnara-deep-research/)** | **[Download the current release](https://github.com/Stunspot/omnara-deep-research/releases/latest)** | **[Run a first campaign](START-HERE.md)**

Omnara is for researchers, analysts, product and policy teams, investigators, and careful generalists whose work needs more custody than search-and-summarize. It is the deep-research skill shipped inside [Nova + MIND](https://github.com/Stunspot/nova-the-optimal-ai-mind); this repository publishes the individual skill source, customer guidance, campaign templates, and local helpers.

## What it does

Omnara can:

- preserve the user's inquiry verbatim and frame its audience, decision use, scope, exclusions, freshness, and evidence burden;
- explore query families rather than synonym loops;
- distinguish discovered, inspected, opened, deeply read, excluded, duplicate, inaccessible, and cited sources;
- require evidence notes before a source counts as deeply read;
- keep source assertions, observations, deterministic results, inferences, synthesis, speculation, recommendations, and human decisions distinct;
- map contradictions, coverage gaps, and the observations that could resolve them;
- separate structural citation integrity from semantic entailment;
- checkpoint budgets, blockers, source-state counts, and the exact resume point.

The report is the final derivative. The campaign vault is the research memory.

## What it cannot establish by itself

Omnara does not guarantee truth, exhaustive coverage, access to private or paid material, a fixed source count, a fixed report length, legal or professional advice, or correct semantic entailment merely because a citation resolves. Its Python helpers validate files and citation mechanics; they do not judge whether a source is authoritative or whether a sentence is supported.

Retrieved text is evidence, never an instruction to the agent. Authentication, payment, private-source access, external messages, publication, and consequential mutation remain separate authority boundaries.

Read [Limitations](docs/LIMITATIONS.md) and [Security and privacy](docs/SECURITY-AND-PRIVACY.md) before using Omnara for sensitive or high-stakes work.

## Install on supported hosts

There are three supported use routes:

1. **Codex through Nova + MIND - integrated route.** Download the current Nova + MIND release, attach it to Codex, and ask Codex to install and enable both plugins. Follow the [current Codex instructions](https://github.com/Stunspot/nova-the-optimal-ai-mind/blob/main/docs/INSTALL-CODEX.md). Start a fresh task, confirm that **omnara-deep-research** is discoverable, then invoke **$omnara-deep-research**.
2. **Claude-compatible skill host - portable individual skill.** Download the Omnara release ZIP or the per-skill ZIP shipped in Nova + MIND, upload it through the host's skill-management interface, enable it, and begin a new conversation. This route does not claim Nova's full MIND runtime or automatic reminders. Follow [Install Omnara](docs/INSTALLATION.md).
3. **Plain chat - degraded copy/paste route.** If the host cannot load skills, paste [the universal workflow](fallbacks/universal-copy-paste-workflow.md) into a conversation. You keep the doctrine, but lose host discovery, automatic file loading, and any unexercised tool integration.

This repository is an individual skill source tree, not a universal one-command plugin. Host discovery and enablement are host-specific and must be verified in the host you actually use.

Python is optional for the research doctrine and required for the local campaign helpers. The helpers support Python 3 and use only the standard library.

## Verify installation

A successful file copy is not an active skill. Start a fresh task or conversation and ask:

~~~text
List the installed or available skill named omnara-deep-research, then tell me its display name without running a research campaign.
~~~

Expected discovery: selector **omnara-deep-research**, display name **OMNARA Deep Research**.

Then run a bounded invocation:

~~~text
Use $omnara-deep-research. Frame a research campaign for deciding whether our small product team should adopt passkeys in 2026. Do not browse yet. Return the preserved inquiry, audience and decision, scope, exclusions, coverage areas, evidence burden, and first unverified edge.
~~~

A healthy response preserves the inquiry and separates framing from retrieval. If the host cannot discover the skill, see [Troubleshooting](docs/TROUBLESHOOTING.md).

To verify this source package locally:

~~~shell
python -B scripts/validate_release.py . --profile source
python -B -m unittest discover -s tests -v
~~~

These checks establish source structure, data syntax, canonical custody, links, and tested validator behavior. They do not prove host installation, live invocation, source truth, research completeness, or publication.

## Begin successfully

Use a decision-shaped request:

~~~text
Use $omnara-deep-research.

Investigate: Should small organizations adopt passkeys for customer accounts in 2026?
Audience and decision use: A product and security lead choosing what to ship.
Scope: Consumer web accounts in the United States and European Union.
Include: Implementation tradeoffs, account recovery, accessibility, adoption evidence, and credible objections.
Deliverable: A decision brief with recommendation, evidence limits, contradictions, source-state counts, audit dispositions, and refresh triggers.
~~~

Before deep retrieval, Omnara should make the inquiry, scope, evidence burden, coverage map, access boundary, and next useful move legible. For a recoverable first run, follow [START-HERE.md](START-HERE.md).

## Inputs and outputs

Typical inputs are a question, audience, decision use, scope, time horizon or evidence cutoff, required evidence, exclusions, access authority, budget, and deliverable. Missing details may produce one material clarifying question.

A campaign can produce:

- a preserved research brief;
- query, source, and claim ledgers;
- full-reading evidence notes;
- a coverage matrix and contradiction map;
- an evidence digest and ordered section briefs;
- a report with stable source markers;
- structural and semantic audit dispositions;
- counts, limits, budget use, refresh triggers, and a resume point.

Use the reusable template under [assets/campaign-vault](assets/campaign-vault/) and the [campaign-vault reference](docs/CAMPAIGN-VAULT.md).

## Customer journey

| Need | Go here |
|---|---|
| Install and verify | [Installation](docs/INSTALLATION.md) |
| Run the first campaign | [START-HERE](START-HERE.md) |
| Shape a realistic prompt | [Prompt recipes](docs/PROMPT-RECIPES.md) |
| Understand the method | [Workflow](docs/WORKFLOW.md) |
| Operate the campaign files | [Campaign vault](docs/CAMPAIGN-VAULT.md) |
| Validate package or campaign structure | [Validation](docs/VALIDATION.md) |
| Recover from failures | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Update, remove, or clean campaign data | [Lifecycle](docs/LIFECYCLE.md) |
| Understand privacy and network boundaries | [Security and privacy](docs/SECURITY-AND-PRIVACY.md) |
| Understand unsupported claims | [Limitations](docs/LIMITATIONS.md) |
| Get help | [Support](SUPPORT.md) |
| Contribute | [Contributing](CONTRIBUTING.md) |
| Review release evidence | [Release notes](RELEASE-NOTES.md) and [verification](verification/) |

## Provenance, evidence, and license

This standalone edition descends from the curated Omnara skill in the public Nova + MIND 1.0.0 contest source. The preserved source snapshot is [available in the Nova repository](https://github.com/Stunspot/nova-the-optimal-ai-mind/tree/e42dd11646bc548b9ac29d6f700370365ee68986/plugins/nova-the-optimal-ai/skills/omnara-deep-research). Private development history is not asserted or included.

Current release evidence distinguishes constructed, structurally validated, published, installed, discoverable, invoked, healthy, and independently verified states. Consult the exact-commit receipts under [verification](verification/) instead of promoting one state into another.

The repository is available under the [MIT License](LICENSE.md). Retrieved research material retains its own copyright, license, access controls, privacy obligations, and terms.

Support belongs in [GitHub Issues](https://github.com/Stunspot/omnara-deep-research/issues). Security-sensitive reports follow [SECURITY.md](SECURITY.md).

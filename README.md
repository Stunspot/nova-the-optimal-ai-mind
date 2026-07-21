# Nova the Optimal AI + MIND

**Bring Nova the mess. Add MIND when one kind of thinking is not enough.**

![Nova Emergent, the canonical Nova artwork by Collaborative Dynamics](assets/nova-emergent.png)

Nova is built as the front door to a serious capability ecology: direct on small work, able to bring in research, judgment, verification, repository awareness, or creative fire when the task earns it, and responsible for returning one accountable result instead of a tour of the machinery.

MIND is the independently installable cognitive system beside her: fifteen focused Faculties and one integrator for work that genuinely needs more than one mode of thought.

A bag of skills is not a mind. It is a drawer. Nova and MIND keep the drawer backstage.

## Try Nova in 90 seconds

Download and extract the [public repository](https://github.com/Stunspot/nova-the-optimal-ai-mind), or clone it:

```powershell
git clone https://github.com/Stunspot/nova-the-optimal-ai-mind.git
Set-Location nova-the-optimal-ai-mind
```

Then, from the repository root:

```powershell
codex plugin marketplace add .
codex plugin add augment-of-mind@collaborative-dynamics-build-week
codex plugin add nova-the-optimal-ai@collaborative-dynamics-build-week
```

Begin a fresh Codex task, then use this exact prompt:

```text
Use $nova to take me on the interactive tour.
```

Nova should offer a short, skippable route through four doors—**decide, investigate, make, or play**—without asking for a biography first. The optional [offline visual companion](plugins/nova-the-optimal-ai/skills/nova/assets/nova-tour.html) makes no network requests and stores nothing.

That is the whole no-build path. Judges do not need Python, a package manager, or generated artifacts to install and try the products.

## Give her something worth installing

For the unfairly good bell and whistle:

```text
Use $nova and $ludis-continuum. I need a background for a character: a royal cartographer who erased one island from every map and now hears its bells in dry land. Give me a playable past, two relationships, one dangerous truth, and an opening choice.
```

Ludis should return pressure, relationships, secrets, and a live choice—not decorative biography. No Port Zindra or other worked campaign ships in this release.

For integrated judgment:

```text
Use $augment-of-mind. We have two days, conflicting evidence, and three stakeholders who mean different things by success. Turn this into one defensible course of action.
```

For proof rather than vibes in a lab coat:

```text
Use $software-verification. Audit this release evidence. Tell me exactly what is proved, what remains uncertain, and what still requires a human.
```

More exact demonstrations are in [START-HERE.md](START-HERE.md).

## What the two plugins do

| Product | Version | What the user gets |
|---|---:|---|
| **Nova the Optimal AI** | 1.0.0 | One coherent collaborator with onboarding, research, retrieval, knowledge stewardship, visual reasoning, explicit memory boundaries, Agentic Coding, TestForge, and Ludis |
| **MIND by Collaborative Dynamics** | 1.0.0 | One integrator coordinating fifteen Faculties for aesthetics, dreaming, striving, continuity, decisions, evidence, execution, timing, measurement, influence, and sensemaking |

Together they expose 28 bounded skill handles. Those are not 28 buttons the user must operate.

Agentic Coding is here because an agent needs balance. It supplies operational proprioception in repository and tool state: where am I, what changed, what is the next real check, and where must I stop? It is not being sold as generic code generation.

TestForge goes in everything. Its operator builds an evidence chain; its separate reviewer attacks that chain. During this release it rejected three weaker stages before returning `REVIEW_PASS_WITH_CONDITIONS` for the package's refusal to overclaim. That is evidence discipline, not a blanket release certificate.

Nova remains useful if MIND is absent and never pretends Faculty composition is active when it is not. Both products must be installed explicitly; neither silently installs the other.

## What Build Week made

Collaborative Dynamics brought prior skills and cognitive doctrine into OpenAI Build Week. GPT-5.6 in Codex turned that source estate into two installable 1.0.0 products: Nova's accountable front counter and onboarding, MIND's independent package, setting-free Ludis instruments, an Agentic Coding operating surface, the TestForge release backplane, deterministic packaging, installation proof, and this contest demonstration system.

[BUILD-WEEK-CONTRIBUTION.md](BUILD-WEEK-CONTRIBUTION.md) separates prior source material from the work performed during the contest. Nothing gets a new birthday merely because it learned to wear a plugin manifest.

## Verify it

The supported contest path was exercised with Codex CLI 0.144.5 on Microsoft Windows 10 build 19045. Other operating systems and Codex versions are not claimed as tested for this release.

- [Five-minute judge path](START-HERE.md)
- [Exact install, expected results, and troubleshooting](docs/JUDGE-GUIDE.md)
- [Verification decision and evidence boundary](verification/verification-report.md)
- [Requirement-to-evidence traceability](verification/traceability-matrix.md)
- [Release archives and SHA-256 verification](release/README.md)

The repository deliberately separates package integrity, observed behavior, release readiness, and human contest actions. A file existing is not proof that the thing it describes happened. Wild concept, apparently.

## Makers and boundaries

Nova and MIND are products of **Collaborative Dynamics**. **stunspot** is Collaborative Dynamics' co-founder and Chief Creative Officer. The included professional context is limited to public, work-relevant sources; it excludes private clients, contacts, personal biography, and unsupported superlatives.

The code is available under the [MIT License](LICENSE.md). No credentials, private customer material, live personal stores, or authored campaign worlds are included.

🌐‍💠

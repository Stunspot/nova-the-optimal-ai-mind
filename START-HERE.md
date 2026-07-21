# Start here: the quick judge path

This path exercises the actual installable products. It does not require rebuilding, editing a prompt file, or learning the skill inventory.

Verified release path: Codex CLI 0.144.5 on Microsoft Windows 10 build 19045, with local plugin-marketplace support. Other operating systems and Codex versions are not claimed as tested for this release. Python is optional and is not needed for this path.

## 1. Install both plugins

From the repository root:

```powershell
codex plugin marketplace add .
codex plugin add augment-of-mind@collaborative-dynamics-build-week
codex plugin add nova-the-optimal-ai@collaborative-dynamics-build-week
```

Open a fresh Codex task after installation.

## 2. Meet Nova

Use this exact first prompt:

```text
Use $nova to take me on the interactive tour.
```

The tour is skippable and should offer four routes without demanding personal information. For the designed visual companion, open [`plugins/nova-the-optimal-ai/skills/nova/assets/nova-tour.html`](plugins/nova-the-optimal-ai/skills/nova/assets/nova-tour.html) in a browser. It works offline and stores nothing.

## 3. Try the unfairly good bell and whistle

```text
Use $nova and $ludis-continuum. I need a background for a character: a royal cartographer who erased one island from every map and now hears its bells in dry land. Give me a playable past, two relationships, one dangerous truth, and an opening choice.
```

Look for an immediately playable character rather than a generic biography: choices, pressure, relationships, and a live hook. No bundled campaign world should appear.

## 4. Make MIND earn its keep

```text
Use $augment-of-mind. A small team has 48 hours to choose between a flashy demo with weak evidence and a quieter demo that proves the core claim. The founder wants spectacle, the operator wants reliability, and the audience is hesitant. Recommend a course, show the decisive uncertainty, and give us a communication plan that preserves everyone's agency.
```

Look for one integrated result. The model may use multiple Faculties internally, but it should not dump a roster or make you manage them.

## 5. Ask for proof

```text
Use $software-verification. Review this repository's verification package. Separate direct evidence, derived conclusions, residual risks, and human-only contest actions. Do not upgrade a claim merely because a file exists.
```

Compare the answer with [`verification/verification-report.md`](verification/verification-report.md) and [`design/CONTEST-ACCEPTANCE.md`](design/CONTEST-ACCEPTANCE.md).

## Expected boundaries

- Nova should answer trivial requests directly instead of invoking a procession of specialists.
- Without MIND, Nova should remain useful and state the missing composition only when it matters.
- Memory should never be claimed as durable without an observed persistence result.
- The packages should contain neither Port Zindra nor any other authored worked campaign.
- Local readiness must not be represented as proof that a repository, video, feedback session, rights attestation, or Devpost form has been completed.

For exact commands, expected observations, and troubleshooting, see [`docs/JUDGE-GUIDE.md`](docs/JUDGE-GUIDE.md).

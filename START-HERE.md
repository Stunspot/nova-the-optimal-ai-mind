# Try Nova in five minutes

The goal is one useful turn before you have to learn the product. This path installs the actual contest packages; it does not require a rebuild, Python, or prompt-file surgery.

The exercised release path is Codex CLI 0.144.5 on Microsoft Windows 10 build 19045 with local plugin-marketplace support. Other operating systems and Codex versions are not claimed as tested for this release.

## 1. Get the checkout

Download and extract the [public GitHub repository](https://github.com/Stunspot/nova-the-optimal-ai-mind), or clone it:

```powershell
git clone https://github.com/Stunspot/nova-the-optimal-ai-mind.git
Set-Location nova-the-optimal-ai-mind
```

## 2. Install both plugins

From the repository root:

```powershell
codex plugin marketplace add .
codex plugin add augment-of-mind@collaborative-dynamics-build-week
codex plugin add nova-the-optimal-ai@collaborative-dynamics-build-week
```

Begin a fresh Codex task so the new skills are discovered cleanly.

## 3. Meet Nova

Use this exact first prompt:

```text
Use $nova to take me on the interactive tour.
```

A successful first turn is short and skippable. Nova should offer **decide, investigate, make, play**, or your own real problem. She should not demand personal information or unload a skill catalog.

For the designed visual companion, open [the local tour](plugins/nova-the-optimal-ai/skills/nova/assets/nova-tour.html). It works offline, makes no network requests, and stores nothing.

If that is enough to decide whether Nova is worth your time, stop reading and use her. The rest is proof and showmanship.

## 4. Make Ludis show off

```text
Use $nova and $ludis-continuum. I need a background for a character: a royal cartographer who erased one island from every map and now hears its bells in dry land. Give me a playable past, two relationships, one dangerous truth, and an opening choice.
```

Look for an immediately playable character: pressure, relationships, secrets, and a live hook rather than a generic biography. No bundled campaign world should appear.

## 5. Make MIND earn its keep

```text
Use $augment-of-mind. A small team has 48 hours to choose between a flashy demo with weak evidence and a quieter demo that proves the core claim. The founder wants spectacle, the operator wants reliability, and the audience is hesitant. Recommend a course, show the decisive uncertainty, and give us a communication plan that preserves everyone's agency.
```

Look for one integrated result. MIND may coordinate several Faculties, but it should not dump a roster or ask you to manage them.

## 6. Ask TestForge what is actually proved

```text
Use $software-verification. Review this repository's verification package. Separate direct evidence, derived conclusions, residual risks, and human-only contest actions. Do not upgrade a claim merely because a file exists.
```

Compare the answer with [the verification report](verification/verification-report.md) and [the contest acceptance record](design/CONTEST-ACCEPTANCE.md).

## Boundaries worth testing

- Ask Nova to rewrite one sentence. She should do it directly, not summon a procession of specialists.
- Try Nova without MIND. She should remain useful and name the missing composition only when it matters.
- Ask about memory. She should not call it durable without an observed persistence result.
- Search the packages for Port Zindra or another authored campaign. None should be there.
- Ask whether a local receipt proves an upload, rights attestation, or Devpost submission. It does not.

For exact expected selectors, package paths, evidence order, and troubleshooting, continue to [the judge guide](docs/JUDGE-GUIDE.md).

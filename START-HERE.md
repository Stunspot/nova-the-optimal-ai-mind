# Start with one useful task

Goal: install Nova + MIND Free, confirm the integration boundary, and get useful work in about five minutes.

## Before you begin

You need:

- Windows PowerShell 5.1 or newer for the supplied installer;
- Codex CLI with `codex plugin` support;
- Python 3.11 or newer;
- this repository cloned or extracted to a stable local folder;
- permission to change your own Codex plugin configuration and create the MIND Core database under your user profile.

If an earlier Nova or MIND plugin is installed, read [Upgrade an existing installation](docs/UPGRADE.md) first. The installer stops rather than silently replacing it.

## 1. Install the package

From the repository root:

```powershell
.\install.ps1
```

Expected result: the script reports that both Free Nova plugins are installed and that a 40-capability reminder estate is active. It ends with the next manual action.

If the result differs, preserve the complete error and go to [Troubleshooting](docs/TROUBLESHOOTING.md). Do not delete your Codex configuration or existing MIND database to make the error look tidier.

## 2. Review the hook

Open Codex and enter `/hooks`. Inspect the MIND prompt-submit hook from this package. Trust applies to the exact installed bytes and must be reviewed again after a hook change.

Expected result: Codex shows the MIND hook and its `UserPromptSubmit` event. This repository cannot make the trust decision for you or verify the host accepted it until you do.

## 3. Start a new task

Installed skills are discovered at the new-task boundary. Start a fresh task and enter:

```text
Use $nova to help me with this.
```

Give Nova any real task. A successful first response helps with the task. It does not demand a biography, recite 40 skills, or ask you to operate the routing machinery.

## 4. Confirm the fun bit

Try Gridmason:

```text
Use $gridmason. I want a survival base built into a ruined aqueduct. I have stone, spruce, copper, and about two evenings. Give me a buildable concept, staged plan, and the first session-sized move. Tell me what dimensions you need before making exact placements.
```

Look for a useful Minecraft plan that preserves edition, version, hidden geometry, and in-world verification boundaries. It should not pretend to know exact coordinates or produce a live schematic from thin air.

## 5. Confirm the foundational bits

Promptcraft:

```text
Use $promptcraft. Help me turn this rough instruction into a model-facing prompt. Preserve my original, make a derivative, and explain the one behavior the revision improves.
```

TestForge, after a candidate is actually finished:

```text
Use $software-verification. This installer is believed ready. Attack the readiness claim, identify the catastrophic paths, and tell me what the available evidence can and cannot support.
```

MIND integration:

```text
Use $augment-of-mind. We have two days, conflicting evidence, and three stakeholders who mean different things by success. Return one defensible course of action with an exact stop condition.
```

## Done

You are ready when:

- both plugins are installed and enabled;
- a fresh task exposes `$nova` and `$augment-of-mind`;
- `/hooks` shows the reviewed MIND hook state;
- Nova helps without catalog theater;
- the reminder layer either supplies a field or names its exact unavailable state.

For normal use, continue to [Choose the right capability](docs/CAPABILITY-GUIDE.md). For installation proof, run:

```powershell
.\verify-install.ps1
```

That script can read plugin and Core state. It cannot prove hook trust, fresh-task discovery, model attention, or behavioral quality; those require their own observations.
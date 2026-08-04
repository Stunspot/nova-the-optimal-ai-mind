# Troubleshoot Nova + MIND Free

Preserve the full error before changing anything. Begin from the observable symptom.

## The installer reports an earlier Nova or MIND selector

The installer found another installation and stopped before replacing it.

1. List installed selectors:

   ```powershell
   codex plugin list --json
   ```

2. Identify only entries named `nova-the-optimal-ai` or `augment-of-mind` from another marketplace.
3. Read [Upgrade](UPGRADE.md).
4. Remove an exact selector only when you have decided to replace that installation:

   ```powershell
   codex plugin remove <exact-selector>
   ```

5. Rerun `install.ps1`.

Do not remove every plugin or reset Codex configuration.

## The installer reports an existing MIND database

The database was not changed. This protects continuity and other estate state from silent replacement.

Choose one route:

- reconcile the existing estate through [Upgrade](UPGRADE.md); or
- install to a new approved path with `-DatabasePath`, then configure `MIND_CORE_DATABASE` for the hook and MCP runtime.

## Python is missing or too old

Run:

```powershell
python --version
```

Install Python 3.11 or newer, confirm the command resolves in the same PowerShell session, then rerun. The skills remain readable without Python, but the bundled reminder activation and local Core runtime do not.

## Both plugins install, but a skill is missing

Installed skills are discovered when a new task begins.

1. Run `codex plugin list --json` and confirm both Free Nova selectors are enabled.
2. Start a fresh task.
3. Try `Use $nova to help me with this.`
4. If a handle remains absent, preserve the plugin JSON and host version. Do not claim the source folder proves discovery.

## The hook does not run

1. Open `/hooks` in Codex.
2. Confirm the MIND `UserPromptSubmit` hook appears.
3. Review whether the exact bytes are trusted.
4. Confirm Python can run and the hook can see the configured database.
5. Use an explicit probe in a new task: `Use $gridmason to help with Minecraft.`

If the hook returns `MIND · ARM'S REACH UNAVAILABLE`, preserve its failure code and receipt. Repair that exact dependency rather than reinstalling everything.

## General prompts say contextual association is ready

That is expected. The hook deliberately avoids inferring the complete task from raw text. Nova should read the task, derive the semantic membrane, and use the contextual association tool.

If the contextual tool is absent, the lost guarantee is post-context semantic recall. Nova may still use capabilities exposed by the host but must not call that an Arm's Reach field.

## The semantic field is too broad or misses an obvious skill

Record:

- the exact input;
- returned handles;
- active snapshot ID and profile state;
- model ID and radius;
- whether membership came from vectors, lexical identity, or a relation.

The shipped expanded profile is unqualified. A routing defect reopens card content, relations, geometry, or qualification; it is not repaired by hiding inconvenient members after retrieval.

## A Claude ZIP fails to upload

Confirm one matching top-level folder and a direct `SKILL.md`. Rebuild and run the release verifier. Host upload and enablement remain separate from archive structure.

## Escalate with useful evidence

Include the exact command or prompt, complete error, operating system, Codex or Claude version, Python version, plugin selectors, database path with private segments redacted, snapshot ID, and whether the state was package presence, installation, discovery, hook output, or observed behavior.
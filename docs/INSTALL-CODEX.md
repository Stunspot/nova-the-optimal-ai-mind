# Manual Codex installation

The easiest path is to attach the release ZIP to Codex and ask it to install and enable Nova + MIND. Use this page when your host cannot install an attached package, when you prefer to inspect every step yourself, or when you are repairing an installation.

## What the installer controls

The package contains one local marketplace with two plugin units:

- **Nova the Optimal AI**, the user-facing agent and practical capability ecology;
- **MIND by Collaborative Dynamics**, Nova’s cognitive substrate, reminder system, sixteen Faculties, Capability Promotion, and TestForge.

The installer creates a new MIND database. It refuses to overwrite an existing store or replace Nova or MIND installed from a conflicting source.

## Requirements

You need Codex with plugin support, PowerShell, Python 3.11 or newer, the extracted Nova + MIND release folder, and a reachable local Ollama endpoint with `qwen3-embedding:0.6b` installed. Model weights are not bundled or silently downloaded. You also need permission to write the selected database location and Codex plugin state.

## Run the installer

Open PowerShell in the extracted release folder:

```powershell
.\install.ps1
```

Before it mutates Codex, the installer checks Python, Codex, package sources, target paths, permissions, Ollama, and the embedding model. It builds a disposable 41-capability estate, reads it back, and completes a live semantic-association query. Only after that preflight succeeds does it add the marketplace, enable Nova and MIND, and move the verified database into its final path.

Expected result: the installer reports both plugins enabled, the 41-capability reminder estate active, and semantic association passed.

## Trust and verify the installed state

Open **Settings → Hooks** in Codex. Review the exact MIND `UserPromptSubmit` hook and trust it only if you accept the local code. Start a new task so Codex can discover both plugins.

With Codex desktop closed, run the included readback verifier:

```powershell
.\verify-install.ps1
```

The verifier refuses to run while Codex desktop is open so it does not change application state. A pass establishes local package and reminder state; it does not establish hook trust, successful fresh-task delivery, model attention, or useful selection.

## Use another database location

Pass `-DatabasePath` with a new empty path. Set `MIND_CORE_DATABASE` to the same path for the hook and direct local query runtime. Different paths create different stores; they do not merge.

## Recover from interruption or failure

A failed semantic preflight creates no plugin installation and no target database; correct the reported Python, Ollama, model, permission, or path problem and rerun. If a later plugin step fails, completed marketplace or plugin steps are safe to reuse on the next run, and the database remains uncommitted. Preserve the complete error before retrying.

If another installation or database already exists, follow [Upgrade](UPGRADE.md). Do not reset Codex, delete continuity data, or remove unrelated plugins merely to satisfy the installer. Continue with [Troubleshooting](TROUBLESHOOTING.md) when the observed state differs from the expected result.

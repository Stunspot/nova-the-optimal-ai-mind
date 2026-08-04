# Manual Codex installation

The easiest path is to attach the release ZIP to Codex and ask it to install and enable Nova + MIND. Use this page when your host cannot install an attached package, when you prefer to inspect every step yourself, or when you are repairing an installation.

## What the installer does

The package contains one local marketplace with two plugin units:

- **Nova the Optimal AI**, the user-facing agent and practical capability ecology;
- **MIND by Collaborative Dynamics**, Nova’s cognitive substrate, reminder system, sixteen Faculties, Capability Promotion, and TestForge.

The installer adds that marketplace, enables both plugins, creates a new local MIND database, activates the public capability map, and reads the result back. It stops rather than silently replacing another Nova/MIND installation or an existing MIND database.

## Requirements

You need Codex with plugin support, PowerShell, Python 3.11 or newer, and the extracted Nova + MIND release folder.

## Run the installer

Open PowerShell in the extracted release folder:

```powershell
.\install.ps1
```

When it finishes, open `/hooks` in Codex. Review the exact MIND `UserPromptSubmit` hook and trust it only if you accept the local code. Then start a new task so Codex can discover both plugins.

Run the included readback check if you want a mechanical confirmation:

```powershell
.\verify-install.ps1
```

A successful readback establishes local package and reminder state. It does not establish that you trusted the hook or that a fresh model turn used a reminder.

## Use another database location

Pass `-DatabasePath` to `install.ps1` and set `MIND_CORE_DATABASE` to the same path for the hook and reminder service. Different paths create different stores; they do not merge.

If installation stops, keep the complete error and continue with [Troubleshooting](TROUBLESHOOTING.md).

# Install Nova + MIND Free for Codex

This procedure installs two plugins and activates the included 41-capability reminder estate. It does not trust the hook for you.

## Prerequisites

- Codex CLI exposes `codex plugin --help`.
- Python is version 3.11 or newer.
- You can write to your own Codex configuration and user data folders.
- No conflicting Nova or MIND selector is installed. See [Upgrade](UPGRADE.md) if one exists.

The supported installer in this source tree is PowerShell. The plugin packages themselves are ordinary Codex marketplace entries.

## Install

1. Open PowerShell in the repository root.
2. Run:

   ```powershell
   .\install.ps1
   ```

3. Read the final status. The expected result names an active 41-capability estate.
4. Open Codex and enter `/hooks`.
5. Review the exact MIND hook bytes. Trust them only if they match this package and you accept the local Python execution.
6. Start a new task so Codex discovers the installed skills.
7. Enter:

   ```text
   Use $nova to help me with this.
   ```

## What the installer changes

The script:

- adds this repository as the `collaborative-dynamics-nova-free` marketplace when it is not already configured;
- installs `augment-of-mind@collaborative-dynamics-nova-free`;
- installs `nova-the-optimal-ai@collaborative-dynamics-nova-free`;
- creates a new MIND Core SQLite database at `%USERPROFILE%\.codex\data\stores\mind_core.sqlite` unless another path is supplied;
- atomically activates the included bootstrap and associative snapshot;
- reads Core status back after activation.

It does not remove older plugins, overwrite an existing database, install an embedding model, trust hooks, start a new task, or claim that the model used a delivered field.

## Use another database path

Choose an empty approved path:

```powershell
.\install.ps1 -DatabasePath 'D:\AI-Data\nova-free\mind_core.sqlite'
```

Set `MIND_CORE_DATABASE` to the same path in the environment used by the hook and MCP server. A non-default database path without matching runtime configuration leaves the installer and runtime looking at different stores.

## Verify readable state

```powershell
.\verify-install.ps1
```

Expected JSON includes the marketplace name, both plugin selectors, the database path, and the current Core snapshot state. Hook trust and fresh-task discovery remain explicitly unobserved by this script.

## Safe stopping point

If installation stops before database activation, preserve the console output. If the marketplace or one plugin was added, its state is observable with:

```powershell
codex plugin marketplace list --json
codex plugin list --json
```

Do not rerun under unchanged conditions after an uncertain commit. Reconcile those two outputs and the database path first, then use [Troubleshooting](TROUBLESHOOTING.md).
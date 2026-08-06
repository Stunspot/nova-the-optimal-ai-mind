# Manual Codex installation for MIND

The normal path is to give the package to Codex and ask it to install and enable MIND. Use this page when the harness cannot install an attached package or when you want to perform the steps yourself.

## Requirements

You need Codex with plugin support, PowerShell, Python 3.11 or newer, the extracted MIND plugin folder, and a local Ollama endpoint with `qwen3-embedding:0.6b` available. Model weights are not bundled or silently downloaded.

## Install

From the MIND plugin folder:

```powershell
.\install.ps1
```

The installer adds the local MIND marketplace, enables the plugin, creates a new local Core database, activates the included reminder map, and reads the result back. It refuses to replace another MIND selector or overwrite an existing database.

After installation, open **Settings → Hooks**, inspect the exact MIND prompt-submit hook, and decide whether to trust it. Then start a new task so Codex can discover the plugin.

For a non-default empty database location, pass `-DatabasePath` and set `MIND_CORE_DATABASE` to the same path for the hook and direct local query runtime.

If installation stops, preserve the complete error and continue with [Troubleshooting](TROUBLESHOOTING.md).

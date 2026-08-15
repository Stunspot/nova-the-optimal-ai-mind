# Manual Codex installation for MIND

The normal path is to give the package to Codex and ask it to install and enable MIND. Use this page when the harness cannot install an attached package or when you want to inspect each step yourself.

## Requirements

You need Codex with plugin support, PowerShell, Python 3.11 or newer, the extracted MIND plugin folder, and a reachable local Ollama endpoint with `qwen3-embedding:0.6b` installed. Model weights are not bundled or silently downloaded. You also need permission to write the selected database location and Codex plugin state.

The installer creates a new database. It refuses to overwrite an existing one or replace a conflicting MIND selector.

## Run the installer

From the extracted MIND plugin folder:

```powershell
.\install.ps1
```

Before it changes Codex plugin state, the installer checks Python, Codex, source files, target paths, permissions, Ollama, and the embedding model. It builds a disposable MIND estate, reads its status, and completes a live semantic-association query. Only after that preflight succeeds does it add the marketplace, enable MIND, and move the verified database into its final path.

Expected result: the installer reports MIND 2.2.2 installed, a 20-capability estate active, and semantic association passed.

## Trust and discover the hook

Open **Settings → Hooks** in Codex. Inspect the exact MIND prompt-submit hook and trust it only if you accept the local code. Start a new task so Codex can discover the plugin. Installation, enablement, hook presence, hook trust, successful execution, reminder delivery, model attention, and useful selection remain separate observations.

## Use another database location

Pass `-DatabasePath` with a new empty path. Set `MIND_CORE_DATABASE` to the same path for the hook and direct local query runtime. Different paths create different stores; they do not merge.

## Recover from interruption or failure

A failed semantic preflight creates no plugin installation and no target database; correct the reported Python, Ollama, model, permission, or path problem and rerun. If a later Codex plugin step fails, completed marketplace or plugin steps are safe to reuse on the next run, and the target database is still not committed. Preserve the complete error before retrying.

If a database already exists, stop and choose whether to archive it, use a new approved path, or perform an explicit successor-estate migration. Do not delete continuity data merely to satisfy the installer.

Continue with [Troubleshooting](TROUBLESHOOTING.md) when the observed state differs from the expected result.

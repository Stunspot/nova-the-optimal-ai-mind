# Install MIND in Codex

You need Codex with plugin support and Python 3.11 or newer.

From this plugin folder, run:

```powershell
.\install.ps1
```

The installer adds the MIND marketplace, installs the plugin, creates a new local Core database, activates the included reminder map, and reads back the status. It does not replace another MIND selector or overwrite an existing database.

After installation:

1. Open `/hooks`.
2. Review the exact MIND prompt-submit hook and trust it only if you accept it.
3. Start a new task.
4. Ask MIND for a real outcome, or call a named Faculty.
5. Use TestForge only after the thing being judged is finished.

To use another empty database location, pass `-DatabasePath` and set `MIND_CORE_DATABASE` to that same path for the hook and reminder service.

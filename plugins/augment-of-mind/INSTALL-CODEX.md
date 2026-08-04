# Install standalone MIND for Codex

From this plugin directory:

```powershell
.\install.ps1
```

Prerequisites are Codex CLI with plugin support and Python 3.11 or newer. The script adds the `collaborative-dynamics-mind` marketplace, installs `augment-of-mind@collaborative-dynamics-mind`, creates a new Core database, activates the 20-capability estate, and reads back status.

It refuses to replace another MIND selector or overwrite an existing database.

After installation:

1. open `/hooks`;
2. review and trust the exact MIND prompt-submit hook if you accept it;
3. start a new task;
4. use `$augment-of-mind` or a named Faculty;
5. use TestForge only after a candidate is finished.

For a non-default database, pass `-DatabasePath` and configure `MIND_CORE_DATABASE` to the same path for the hook and MCP service.
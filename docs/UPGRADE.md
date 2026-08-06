# Upgrade an existing Nova or MIND installation

Free Nova will not quietly replace another Nova/MIND installation or overwrite a MIND database. Treat an upgrade as a deliberate handoff, not a reset button.

## Record what you have

Run:

```powershell
codex plugin marketplace list --json
codex plugin list --json
```

Note the Nova and MIND selectors, enabled state, marketplace roots, and database path. Back up continuity data if it matters to you.

## Choose one active installation

Use one enabled Nova and one enabled MIND distribution in a task. Two copies can expose duplicate handles and make it unclear which package is governing behavior.

If you are replacing an older installation, remove only its exact selectors:

```powershell
codex plugin remove <old-nova-selector>
codex plugin remove <old-mind-selector>
```

Removing a plugin does not remove its database.

## Choose a database path

This Free Nova release is built for a clean database. Do not force it over an existing store. Either keep the old store as an archive and give Free Nova a new database path, or perform a deliberate migration with the correct snapshot lineage.

An automatic legacy-estate merger is not included in this release.

## Install and confirm

Run `install.ps1`, review **Settings → Hooks**, start a new task, and run `verify-install.ps1`. If you roll back, restore the previous selectors and point the runtime at the preserved database. A rollback is complete only after a new task discovers the old skills again.

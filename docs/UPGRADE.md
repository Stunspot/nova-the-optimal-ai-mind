# Upgrade an existing Nova or MIND installation

The Free Nova installer refuses to replace another selector or overwrite an existing MIND database. Upgrade is a reconciliation task, not a reset button.

## 1. Record current state

```powershell
codex plugin marketplace list --json
codex plugin list --json
```

Record the exact Nova and MIND selectors, enabled state, versions, marketplace roots, and current MIND database path. Back up continuity data if it matters to you.

## 2. Decide which installation becomes authoritative

Use one enabled Nova and one enabled MIND distribution in a task. Multiple copies can expose duplicate handles and make it impossible to know which bytes governed behavior.

If replacing an older installation, remove only its exact selectors:

```powershell
codex plugin remove <old-nova-selector>
codex plugin remove <old-mind-selector>
```

Removing plugins does not remove the old database.

## 3. Reconcile the database

The bundled Free Nova snapshot declares no prior snapshot because it is a clean-install estate. Do not point it at an existing database and force activation.

Choose one:

- keep the existing database and perform an explicit successor-estate migration with correct prior snapshot lineage; or
- create a new database path for Free Nova, preserve the old database as an archive, and configure `MIND_CORE_DATABASE` consistently.

This repository does not yet ship an automatic legacy-estate merger. That capability is `not implemented`, not hiding behind an undocumented flag.

## 4. Install and verify

Run `install.ps1`, review `/hooks`, start a new task, and run `verify-install.ps1`. Confirm that the current task exposes one copy of each intended handle.

## Roll back

If the new installation is unsuitable, remove its two exact selectors and marketplace, restore the prior selectors, and point the runtime back to the preserved prior database. A rollback is complete only after a fresh task discovers the prior skills and the prior store reads back correctly.
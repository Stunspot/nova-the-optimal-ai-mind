# Upgrade, remove, or clean up Nova + MIND

Free Nova will not quietly replace another Nova or MIND source or overwrite a MIND database. Treat an update as a deliberate handoff, not a reset button wearing a confident hat.

## Record the active installation

Close active work and run:

```powershell
codex plugin marketplace list --json
codex plugin list --json
```

Record the marketplace root, Nova and MIND selectors, enabled state, plugin versions, `MIND_CORE_DATABASE` value if set, and any install-verification report you intend to preserve. Back up continuity data you care about before changing selectors or database paths.

## Update one coherent product

Use one enabled Nova and one enabled MIND source in a task. Two copies can expose duplicate handles and obscure which hook or package produced a result.

1. Remove or disable only the exact old Nova and MIND selectors.
2. Preserve the prior database as an archive unless you have an explicit migration plan.
3. Install the new release through [Start here](../START-HERE.md), choosing a new empty database path when the release requires it.
4. Inspect and trust the new hook bytes separately; trust does not transfer across changed files.
5. Run `verify-install.ps1` and repeat the fresh-task discovery check.

Nova + MIND Free 2.1.3 does not automatically merge MIND Core estates or switch a Cognitive Continuity selector. Different database paths and continuity selectors identify different stores.

## Upgrade Cognitive Continuity deliberately

Continuity 0.2.2 uses workspace schema v2 and provides an explicit hash-bound copy migration into a distinct successor workspace. Probe the existing workspace read-only before choosing a runtime. Supported v1 operations remain read-only; Faultline is typed unsupported on v1. Do not initialize or mutate a workspace merely to satisfy a Worldline or Faultline request.

A v1-to-v2 transition is an explicit copy migration into a new governed workspace, followed by validation and caller-controlled selector change. Preserve the source workspace and rollback path until the new generation, scope, receipts, and required views have been checked. If v1 contains an episode above the ordinary 1,000-character v2 write limit, require exact untruncated content plus `legacy_content_provenance`; confirm its count and digest agree across generation 0, the migration manifest, and the migration receipt, and retain the complete generation chain used to prove governed transitions. New v2 writes remain capped, and migrated exceptions have explicit character and UTF-8 byte ceilings. The Nova + MIND installer does not perform this migration and does not infer that two selectors should merge.

## Roll back

Remove or disable only the new selectors, restore the previous marketplace and selectors, point `MIND_CORE_DATABASE` at the preserved store, inspect the restored hook bytes, and start a new task. Rollback is complete only when the old plugin versions are enabled and a fresh task discovers the expected skills again.

## Remove the plugins

Use Codex plugin management or the CLI to remove the exact Nova and MIND selectors shown by `codex plugin list --json`. Do not remove a marketplace or another plugin merely because its name is similar.

Plugin removal does not delete:

- the SQLite database;
- the Ollama model;
- exported verification reports;
- the downloaded release archive;
- artifacts created by specialist skills;
- separate Claude skill installations.

## Remove local data

Resolve every path before deletion. The default MIND database is:

```text
%USERPROFILE%\.codex\data\stores\mind_core.sqlite
```

If `MIND_CORE_DATABASE` is configured, use that exact path instead. Stop Codex and any Core process before copying or removing a database. Remove the Ollama model through Ollama’s own current model-management procedure only if no other local workflow needs it. Remove generated artifacts according to the custody and retention rules of the skill that created them.

Deletion is an explicit data-management decision. Uninstallation is not consent to erase state.

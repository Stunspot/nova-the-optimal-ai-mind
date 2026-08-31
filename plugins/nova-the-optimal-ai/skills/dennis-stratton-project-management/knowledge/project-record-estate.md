# Centralized project-record estate

Use this procedure at entry to every identifiable project. Its purpose is continuity: recover the project before creating another version of it.

## Resolve custody without side effects

Run `store-path`. The resolution order is:

1. `--store <path>` for an owner-approved operation-specific estate;
2. `DENNIS_PROJECT_HOME` from the governed Nova estate.

Nova Emergent disables the standalone `~/.dennis-stratton/project-records` fallback. Use the sibling `$nova-operations` registry-backed `run project-management -- ...` command for product-owned project records; it injects the exact selector without depending on inherited environment.

`store-path` and `locate` do not create the directory. Do not substitute a repository-local `project-control.json`, package directory, installation root, cache, temporary path, upload sandbox, or chat transcript merely because it is nearby.

The estate layout is:

```text
<store>/
|-- store.json
`-- projects/
    `-- <stable-project-key>/
        |-- project-control.json
        `-- records/
```

The control record is canonical project state. Dennis-created linked records belong below `records/`. External source evidence remains in its authoritative custody and is referenced by locator.

## Identify before matching

Prefer a stable owner- or system-assigned project ID. Also collect the exact project name and the strongest source locator available, such as a canonical repository, charter, project-system identifier, or owner decision.

Use `locate` with the strongest selector available. Multiple supplied selectors are conjunctive. Never merge records from fuzzy name similarity, a shared repository parent, a product family, or model inference.

If exactly one record matches:

1. load it;
2. validate it;
3. compare its source authority and `updated_at` with current authoritative sources;
4. preserve disagreements and stale state explicitly;
5. update that record rather than creating a parallel control file.

If multiple records match, stop project-state mutation. Present their IDs, paths, locators, and fingerprints for owner resolution. Do not choose by modification time alone.

Malformed records appear as diagnostics. Do not ignore them and bootstrap around them; repair or resolve custody first.

## Create only when the work authorizes persistence

Use `ensure` when all are true:

- the project is identifiable;
- no existing store record matches;
- the request authorizes project creation or durable project-state mutation;
- owner, outcome, and authority-source locator are known or explicitly provisional.

The ordinary authority to start, plan, execute, steer, recover, or close a project includes creating its required canonical control entry when durable records are part of the requested work. A strictly read-only explanation, audit, review, or status request does not.

`ensure` returns either `created: true` with the new canonical record or `created: false` with the existing record. Treat any identity conflict as a stop condition. Do not force, rename, or overwrite through the conflict.

After creation, replace template prompts only with source-backed values. Unknown forecasts, stakeholder positions, acceptance, and benefit evidence remain unknown.

## Adopt legacy records deliberately

When the authoritative record is outside the estate, do not silently leave two writable canonicals.

1. Confirm owner authority to centralize custody.
2. Validate a v2 record; migrate v1 to a separate derivative first.
3. Run `adopt`.
4. Confirm `source_preserved: true` and record both fingerprints.
5. Designate the estate copy as canonical for future Dennis-managed updates.
6. Leave the legacy source preserved or mark it clearly as superseded according to its own custody rules.

`adopt` refuses invalid records and same-ID content conflicts. Reconcile a conflict as a project decision; do not overwrite it with `bootstrap --force`.

## Keep all Dennis records together

Store Dennis-created durable artifacts under the returned project `records/` directory. Use stable, meaningful names and preserve their relationship to the canonical control record. An integrated owner-designated PMIS, document system, or repository may remain authoritative for a specific artifact; record that locator in project control rather than duplicating sensitive content.

Never move credentials, private stakeholder communications, personnel data, contracts, budgets, or other sensitive evidence into the estate merely for completeness. The estate is local custody, not a privacy exemption wearing spectacles.

## Degraded path and guarantees

If files or Python are unavailable, use `fallbacks/universal-copy-paste-workflow.md`. State that centralized discovery, unique matching, atomic creation, validation, adoption integrity, and cross-session continuity were not proven. Preserve the proposed store path and project identity so the next capable session can re-enter without inventing another record.

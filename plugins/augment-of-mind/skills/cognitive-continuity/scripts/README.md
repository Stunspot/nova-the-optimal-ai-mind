# Deterministic Continuity Tools

These local standard-library tools make record and view operations observable.
They do not decide semantic truth, grant authority, or turn a derived view into
saved state. Run from this directory or supply the full script path.

## Probe before choosing a major

Open is read-only and reports the workspace format plus supported operations:

```text
python -B -X utf8 continuity_store_v2.py open [WORKSPACE]
```

When `WORKSPACE` is omitted, the v2 tools resolve the governed
`NOVA_CONTINUITY_HOME` selector. Do not initialize or migrate merely to satisfy a
read request. Use v1 tools for a v1 operation they actually support; Faultline is
typed unsupported on v1.

## Worldline read views

Read `../references/worldline-contract.md` first. The stable API is
`compile_worldline(request, registry_path=...)`; its request is
`cd-worldline-request/v1` and its successful view is `cd-worldline-view/v1`.
Use canonical request replay for exact or fresh-process work:

```text
python -B -X utf8 worldline.py --request REQUEST.json
```

Convenience mode uses one of `resume`, `status`, `checkpoint`, or `inspect`:

```text
python -B -X utf8 worldline.py resume [WORKSPACE] --task TASK --user USER --project PROJECT --agent AGENT
python -B -X utf8 worldline.py status [WORKSPACE] --task TASK --user USER --project PROJECT --agent AGENT
python -B -X utf8 worldline.py checkpoint [WORKSPACE] --task TASK --user USER --project PROJECT --agent AGENT
python -B -X utf8 worldline.py inspect [WORKSPACE] --task TASK --user USER --project PROJECT --agent AGENT
```

All four modes are read-only. Checkpoint produces a derivative handoff, never a
write or persistence receipt. With sufficient source-linked caller material, any
mode may return an explicitly `unpersisted_portable` fallback; otherwise a
missing, invalid, unsupported, unavailable, or over-deadline source yields a
typed no-view result.

## Faultline Error Neighborhood

Read `../references/faultline-error-neighborhood-contract.md` first. Compile a
zero-to-three-card expiring view with:

```text
python -B -X utf8 error_neighborhood.py neighborhood [WORKSPACE] --task TASK --project PROJECT --max-cards 3 --expires-minutes 10
```

Use `capture`, `pattern-propose`, `pattern-apply`, and `pattern-transition` only
for governed Cognitive Continuity v2 mutations. Every mutation requires explicit
`--expected-generation`, `--idempotency-key`, and authority. Pattern application
and transition require human-prefixed authority; application also requires a
finite `--expires-at`. Use each subcommand's `--help` for its full typed argument
set. Never pass raw logs or secrets.

## Cognitive Continuity v2 mutations

Use `continuity_store_v2.py` and `compile_context_v2.py` for v2 work. Transactional
mutations use expected generation and idempotency controls; proposals remain
noncanonical until separately authorized and applied. Export destinations,
forget plans, backups, and receipts stay in their named custody.

Ordinary `migrate-copy` destinations remain outside every selected Nova capability
boundary. A Nova-owned live successor uses the separate
`nova_guarded_successor` destination mode. It requires human authority, the exact
active `NOVA_CONTINUITY_HOME` as source, an absent same-parent sibling as
destination, a grant ID, the trusted selector registry SHA-256, and the
normalized destination-path SHA-256. The registry and corroborating process
environment are rechecked before and after publication. This creates a candidate;
it never changes the live selector.

```text
python -B -X utf8 continuity_store_v2.py migrate-copy SOURCE DESTINATION --authority user-explicit --source-tree-sha256 SOURCE_SHA256 --destination-mode nova_guarded_successor --destination-grant-id GRANT_ID --expected-selector-registry-sha256 REGISTRY_SHA256 --expected-destination-path-sha256 DESTINATION_PATH_SHA256
```

## Legacy v1 examples

```text
python -B -X utf8 continuity_store.py init .continuity --user demo-user --project demo-project --agent demo-agent
python -B -X utf8 continuity_store.py episode .continuity --type decision --content "Private release first" --source-kind user --authority user-explicit
python -B -X utf8 continuity_store.py record .continuity --kind decision --content "Private release first" --source-ids EP-... --authority user-explicit
python -B -X utf8 compile_context.py .continuity --task "Prepare private release" --output .continuity/contexts/release.md
python -B -X utf8 validate_continuity.py .continuity
```

Use `propose` before model-derived durable change. A proposal from
`origin=dream` cannot be applied without a recorded waking review and
`--waking-approved`.

`forget --ids` accepts exact IDs and removes records and package-derived files
that reference them. Resolve a human target such as "Vendor Kestrel" into a
reviewable ID set before destructive execution. The tool does not search
arbitrary user text and guess deletion scope.

`export` produces checksum-bound JSON. `import` validates and quarantines it;
import never changes canonical state automatically.

# Deterministic Continuity Tools

These local standard-library tools make record and view operations observable.
They do not decide semantic truth, grant authority, or turn a derived view into
saved state. Run from this directory or supply the full script path.

## Runtime portability gate

Run the complete deterministic suite from the repository root:

```text
python -B -X utf8 -m unittest discover -s scripts/tests -p "test_*.py" -v
```

The public workflow repeats it on Windows, macOS, and Linux. The focused native filesystem smokes are:

```text
python -B -X utf8 -m unittest scripts.tests.test_workspace_portability.WindowsLiveSmokeTests -v
python -B -X utf8 -m unittest scripts.tests.test_workspace_portability.DarwinLiveSmokeTests -v
python -B -X utf8 -m unittest scripts.tests.test_workspace_portability.LinuxLiveSmokeTests -v
```

Filesystem names are diagnostic only. Mutation qualification follows the operating-system primitive adapter, writable state, known topology hazards, direct permanent-lock identity, replacement/durability probes, and a transaction-bound volume or mount witness across every critical directory. A cloud-branded folder name alone is neither permission nor denial.

## Probe before choosing a major

Open is read-only and reports the workspace format plus supported operations:

```text
python -B -X utf8 continuity_store_v2.py open [WORKSPACE]
```

When `WORKSPACE` is omitted, the v2 tools resolve the governed
`NOVA_CONTINUITY_HOME` selector. Do not initialize or migrate merely to satisfy a
read request. Use v1 tools for a v1 operation they actually support; Faultline is
typed unsupported on v1.

## Worldline timeline

Read `../references/worldline-timeline.md` for the cognitive and custody contract.
The library entrypoint is `query_worldline(request, registry_path=...)`, with
`cd-worldline-request/v2` and `cd-worldline-view/v2` schemas. The command fills
exact user and agent from the selected manifest when possible; supply `--user`
and `--agent` only when the manifest does not establish them. Omit project and
thread filters to survey all permitted history for that owner. `[WORKSPACE]`
below is an optional explicit path; omit it to use the governed selector.

```text
python -B -X utf8 worldline_timeline.py overview [WORKSPACE] --from 2026-09-01T00:00:00Z --to 2026-10-01T00:00:00Z --bucket month
python -B -X utf8 worldline_timeline.py browse [WORKSPACE] --search memory --page-size 30
python -B -X utf8 worldline_timeline.py inspect [WORKSPACE] --event-id EP-EVENT_ID
python -B -X utf8 worldline_timeline.py render [WORKSPACE] --from 2026-09-01T00:00:00Z --output EXPLICIT_ABSENT_PATH.html
python -B -X utf8 worldline_timeline.py --request REQUEST.json
```

`browse`, `overview` and `inspect` are read-only. `render` writes only its
explicitly named, bounded HTML derivative and never captures an occurrence.
An internal projection filename must end in `.html`.
Prefer the selected workspace's `projections` directory when that derivative
should participate in its forget lifecycle. Current unedited renderer output is
backed up and deleted as part of governed forgetting; edited or unfamiliar files
retain the separate named-custody route. Time filters are half-open intervals;
`--display-offset-minutes` chooses grouping offset without changing stored time.
Use the returned cursor for another page, restarting if the generation changed.
Coverage describes retained evidence and limits, not everything Nova ever did.
Existing episodes are visible as legacy entries with recorded-time placement.

Read the persistent policy, or retain a human-authorized choice:

```text
python -B -X utf8 worldline_timeline.py policy [WORKSPACE]
python -B -X utf8 worldline_timeline.py policy [WORKSPACE] --mode ordinary --authority user-explicit --authority-source task:OWNER_DIRECTIVE --event-key ordinary-choice-1
python -B -X utf8 worldline_timeline.py policy [WORKSPACE] --mode off --authority user-explicit --authority-source task:OWNER_DIRECTIVE --event-key off-choice-1
```

Once standing ordinary capture has been authorized, record a coherent current
episode with one short command. Use an actual source reference and stable key:

```text
python -B -X utf8 worldline_timeline.py capture [WORKSPACE] --title "Explored the shape of memory" --source task:SOURCE_TASK --event-key memory-exploration-1 --current
python -B -X utf8 worldline_timeline.py capture [WORKSPACE] --capture-mode explicit --authority user-explicit --title "Returned to an earlier idea" --source task:SOURCE_TASK --event-key idea-return-1 --occurred-at 2026-09-12T14:00:00Z --time-basis source_reported
python -B -X utf8 worldline_timeline.py capture [WORKSPACE] --input COMPACT_EVENT.json
```

The default capture mode is routine, authorized by the stored ordinary policy.
Without it, routine capture is suppressed. Explicit mode requires the actual
current user's direction. `--no-retention` suppresses capture even with standing
permission. The convenience command reads generation and derives idempotency
from the source and event key; lost-response retries reuse the recorded current
instant and unchanged payload. A changed occurrence requires a new event key or
an explicitly authorized correction, not accidental duplication.

Defaults are kind `conversation`, source kind `agent`, label `Original source`,
source owner `unspecified`, ordinary sensitivity and workspace retention.
Corrections via `--supersedes EP-CURRENT_REVISION` inherit time, links and privacy;
provide the changed fields and human authority. `--retract` records a retraction.
A later genuine change of mind is a new event with optional `--related-id`.
Precise requests may use `cd-worldline-capture/v2` or
`cd-worldline-policy-request/v1` through `--request`; a privacy reclassification
requires explicit `privacy_change_authorized: true` in full or compact JSON.
Both write APIs delegate to `continuity_store_v2.py` and return its governed receipt.

For an owner-scoped historical transfer, choose the explicit export mode:

```text
python -B -X utf8 continuity_store_v2.py export [WORKSPACE] --worldline-timeline --output EXPLICIT_ABSENT_EXPORT.json --authority user-explicit --sensitivity ordinary
```

This preserves permitted event metadata, source links and required revision
ancestry, and excludes capture policy. A family whose required ancestor cannot
be disclosed is omitted with a `revision_ancestry_privacy` count. Generic export
scope defaults remain unchanged. Import remains quarantine-only. Native event
metadata requires Continuity 0.3.0 or newer; use a capable reader for an evolved
store, or an explicitly preserved pre-event copy for old-runtime rollback.

## Legacy Worldline project views

Read `../references/worldline-contract.md` first. The stable API is
`compile_worldline(request, registry_path=...)`; its request is
`cd-worldline-request/v1` and its successful view is `cd-worldline-view/v1`.
Resolve one project key before invoking it using the contract's evidence
precedence, and retain the winning source tier in observable task work. The
workspace selector does not select a project. An ambiguous winning tier is a
typed caller stop before this script runs. For a specific-project request, the
compiler withholds globally scoped operative state and reports an unrepresented
project rather than deriving its resumption pointer from a global goal.
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

Migration preserves a v1 episode that exceeds the ordinary 1,000-character v2 write limit only by attaching `legacy_content_provenance`. Before selecting the candidate, inspect the migration manifest and receipt for identical `legacy_oversize_content_provenance_sha256` values and the expected count, then run `validate_continuity_v2.py`. The validator binds those rows to generation 0, replays every retained transition, and refuses later minting or alteration; prior generations remain protected while this contract exists. New v2 episode writes remain capped at 1,000 characters. Migrated exceptions are bounded to 16,384 characters and 65,536 UTF-8 bytes; no row is truncated.

## Recover interrupted work

Treat `recovery_required` as a custody stop, not a cleanup request. Preserve every exact path named by the error and do not edit, rename, combine, or delete its intent, construction, stage, quarantine, or published artifact. Retry the same command with the same source, destination, authority, receipt output, expected generation, and idempotency inputs. A matching completed operation returns its existing result instead of repeating the mutation.

Recover interrupted workspace transactions under the permanent lock with:

```text
python -B -X utf8 continuity_store_v2.py recover WORKSPACE --authority user-explicit
```

External outputs use no-clobber publication. Import consumes and binds one exact source snapshot. Backup and migration build complete sibling directories before publication. Named-custody and backup deletion require a receipt path that neither contains the target nor sits inside it. They bind the direct filesystem identity of the authorized object and retain immutable intent and quarantined phase records next to the receipt. If either deletion is interrupted, preserve every phase and staged path and stop for human disposition; external phase files are never accepted as automatic resume authority. Use `continuity_store_v2.py COMMAND --help` for the complete `delete-named-custody` or `backup-destroy` authorization inputs.

After a successful operation, preserve the final receipt and its phase evidence. For interrupted destructive lifecycle work, do not retry automatically or remove residue: the runtime returns `recovery_required` rather than guessing ownership or deleting another object.

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

# Worldline: a past to recognize and revisit

Worldline records that a recognizable thing happened, places it honestly in time,
and points to the substance where it already lives. Conversations, explorations,
attempts, creations and returns belong alongside decisions and deliverables.
Projects, threads, kinds and topics are optional facets. Cognitive Continuity owns
the existing episode ledger and its lifecycle; Worldline adds no parallel store.
The existing Cognitive Continuity Faculty supplies the autobiographical stance.

## Survey, then follow the source

Use `scripts/worldline_timeline.py` or `query_worldline(request, registry_path=None)`.
`browse` returns chronological pages, `overview` groups the retained shape of a
period, and `inspect` returns one occurrence and its eligible revision history.
An exact user and agent boundary is mandatory; an exact selected manifest supplies
it automatically. Within that boundary, omitted project and thread filters include
all permitted projects and threads. A specific project filter selects that project.
This differs intentionally from the old current-state wildcard rules.

A view contains compact recognition titles, occurrence and recording time, source
links, facets, stable event identity and observed coverage. Open a source only when
its substance helps the present thought. A pointer neither executes nor grants
access to its target. HTTP(S) links, local paths and opaque host references remain
source locators; the runtime does not fetch them. Unsafe executable links and
secret-bearing metadata are rejected. Unknown ownership is labelled `unspecified`.

`render --output PATH` creates a bounded, scrollable local HTML projection with
escaped labels and links, day grouping and visible coverage. The destination must
be explicitly named and absent. An internal output must use the `.html` extension.
A location inside the selected workspace's
`projections` directory keeps the derivative within its forget lifecycle. Unedited current-format views are recognized by template, source IDs and byte hash
for immediate cleanup during governed forgetting; edited or older-template files
keep the separate named-derivative route. External outputs have their own custody. Reads never write a view implicitly, and rendering
never records an occurrence. No server or browser subscription is required.

## Capture at a natural transition

The convenience `capture` command accepts title, source locator, stable event key,
and honest occurrence time, or a compact JSON object with those fields. `--current`
uses the observed present instant for a current episode; it must not date old work.
Defaults are kind `conversation`, no topics or relationships, disposition `recorded`,
source kind `agent`, source label `Original source`, and owner `unspecified`.
Ordinary capture inherits the workspace retention default. A correction inherits
its target's sensitivity, retention and expiry unless a currently authorized
privacy change is explicitly requested through the full or compact JSON interface.

Use a stable source-event key for retries of the same coherent occurrence. A new
recurring occurrence needs a new key. The current-event convenience command reuses
its committed occurrence instant on retry; changing the retained payload under the
same key is a conflict. The governed receipt identifies the stable `event_id`,
selected `revision_id` and committed episode. Observe that receipt before claiming
persistence. A failed capture may leave a source-linked, clearly unpersisted handoff
in the current task; it does not justify a save claim.

`capture_worldline(request, registry_path=None)` and
`set_worldline_policy(request, registry_path=None)` in `continuity_store_v2.py` use
the existing immutable-generation transaction, authority, idempotency and receipt
mechanisms. The convenience CLI reads generation and fills the envelope; exact JSON
requests expose every control. See `../scripts/README.md` for runnable forms.

## Standing control, without a consent loop

The persistent policy is `ordinary`, `off`, or `unconfigured` when no directive has
been retained. `policy` without a mode reads it. Setting a mode requires current
human authority and a source locator for that directive. The last committed policy
in ledger order wins even when the clock moves backwards. Policy controls are not
ordinary autobiographical entries.

Routine capture requires standing `ordinary` authority and ordinary metadata; it
rechecks the policy under the transaction lock. `off` and `unconfigured` suppress
routine capture. An explicit user request can authorize its particular capture
while routine capture is off. Current no-retention directions suppress capture,
including revealing titles and topic labels. Do not misuse explicit mode to bypass
missing standing consent, and do not ask again for each event once permission exists.
An existing explicit user choice carries forward; otherwise establish the choice
during setup or later.

This is a natural-episode habit in the active task, not a transcript-ingestion daemon.
The host and observed tools determine whether capture actually ran. Installation
does not backfill prior conversations or guarantee future background invocation.

## Time, revisions and gaps stay honest

Native `worldline_event` payloads in v2 episodes carry a short title, kind,
disposition, `occurred_at`, optional `ended_at`, time basis and precision, source
pointers, topics, associative `related_ids` and at most one revision `supersedes`.
They contain no source body. `recorded_at` remains indexing time. Day, range and
unknown precision must remain visible; unknown occurrence time uses a labelled
recorded-time anchor. Do not manufacture a precise occurrence from assertion
`valid_from`.

Existing retained episodes appear as sourced `legacy_episode` entries using
recorded-time placement. Ended validity of a belief or plan does not erase the
conversation in which it arose. Actual retention expiry, sensitivity and forgetting
are checked at execution time even for an older `as_of` request. A monthly overview
reports retained coverage and any scan, budget or paging limit; no eligible entries
means no eligible retained evidence, never that nothing happened.

Correct a mistaken title, date or link by an explicitly authorized revision of the
current event leaf; stable logical identity and provenance survive. Retraction
states that the occurrence was misidentified rather than displaying it as a normal
event. A genuine later change of mind is a new occurrence, optionally linked to the
previous one. Resolve the current family privacy envelope before historical display:
a sensitive, expired, forgotten or retracted current revision cannot expose an
earlier ordinary version through fallback. An explicitly declassified current
revision can be shown on its own merits; denied ancestors remain hidden.
Corrections do not silently reduce privacy.

Forgetting selects the whole exact correction family and its true derivatives.
Associative links are severed on surviving independent events, not treated as a
reason to erase neighboring life. Metadata and locators are scrubbed from forgotten
rows. Forgetting a policy selects its exact-scope policy history, so removing an off
marker cannot resurrect old permission. Use the existing reviewed forget plan,
backup, apply and receipt process in `privacy-correction-and-forgetting.md`.
Recognized active HTML derivatives are included in the authenticated recovery
backup, then deleted through the existing lifecycle adapter before canonical
forget succeeds. Interrupted cleanup retains phase evidence and reports the
recovery boundary; it never reports a completed forget with a retained active view.

## Bounded snapshots and transfer

Cursors bind the query, owner, source generation and sort position. All snapshot
reads use the observed physical generation. A changed generation makes the cursor
stale and requests a restart; do not silently read retained history after forgetting.
Every page rechecks current retention. Search, counts and omission reasons are scoped
to the permitted owner before being exposed. No foreign-row count is disclosed.

`continuity_store_v2.py export --worldline-timeline` explicitly selects eligible
native and legacy history across the permitted owner boundary, preserving native
metadata, safe links and required revision ancestry. It omits control policies.
It is a governed transfer bundle, distinct from the recognition-only view. Generic
exports retain their existing scope defaults while preserving selected native
metadata. Transfer omits a family when a required revision ancestor cannot be
disclosed, reporting `revision_ancestry_privacy` rather than exporting that ancestor
or producing an orphan correction. Import still validates and quarantines; it never activates policy or
merges canonical history automatically.

Legacy `worldline.py` keeps `resume`, `status`, `checkpoint` and `inspect` under
`worldline-contract.md`. V1 workspaces remain read-only. Native occurrence and policy
payloads require Continuity 0.3.0 or newer; an old reader may reject an evolved v2
store. Keep a capable reader when rolling back behavior, or use an explicitly
preserved pre-event copy with old code. There is no destructive in-place migration.

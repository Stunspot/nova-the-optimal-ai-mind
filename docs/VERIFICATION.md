# Verification and evidence

The release uses separate checks for package truth, reminder mechanics, host behavior, and documentation. One green layer does not certify the next.

## Source and package checks

Run:

```powershell
python -X utf8 .\tools\verify_package.py
```

After building release artifacts:

```powershell
python -X utf8 .\tools\verify_package.py --release
```

The verifier checks exact skill sets, unique handles, frontmatter, description limits, canonical Nova and Promptcraft hashes, TestForge policy presence, exclusions, plugin versions, reminder counts and profile state, marketplace topology, customer links, Claude folders, and ZIP shape.

## Reminder mechanics

The isolated smoke suite activates the estate in a temporary database, reads back SQLite integrity and foreign keys, runs contextual queries, executes the hook directly, preserves the evidence and deletes the isolated temporary database after its readback.

Current observed facts:

- 41 capabilities, 41 cards, 246 views, 246 vectors, and 33 relations activated atomically;
- SQLite integrity returned `ok` with zero foreign-key violations;
- explicit `$gridmason` hook recall prepared a field;
- a general prompt produced the contextual-association handoff;
- radius `0.33` preserved the representative Minecraft, Promptcraft, and TestForge neighborhoods without the earlier saturation.

These are isolated H0 observations. The profile remains `unqualified`.

## TestForge

TestForge receives the finished source and release candidate. Its operator reconstructs impact, risks, invariants, scenarios, oracles, and execution evidence. The independent reviewer challenges the resulting status.

A TestForge pass can support only the exact exercised package and environment. It cannot authorize publication, prove defect-freedom, or substitute for live hook trust and fresh-host use.

## Documentation

Hesperos authors the customer journey from the current evidence packet. The documentation accessibility reviewer then challenges factual integrity, task completion, recovery, findability, semantics, and claim custody. Automated Markdown lint is structural evidence only.

## Required live gates before a broad release claim

- install from the final customer ZIP on a clean supported host;
- review and trust the exact hook bytes;
- begin a fresh task and observe all intended discovery surfaces;
- capture hook/provider delivery evidence;
- run contextual association through the plugin-host MCP path;
- exercise broader positive, near-neighbor, false-friend, saturation, and boundary cases;
- upload and enable representative Claude ZIPs if Claude readiness is claimed;
- inspect final artwork and documentation presentation in a functioning visual tool;
- obtain accountable release approval.
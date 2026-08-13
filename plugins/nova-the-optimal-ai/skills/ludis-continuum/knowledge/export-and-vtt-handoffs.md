# Offline campaign exports and VTT handoffs

Use this guide when the requested outcome is a downloadable play packet, map/token set, structured campaign data, or VTT import asset. The campaign ledger remains canonical throughout.

## Pick the smallest useful handoff

| User need | Deliverable |
| --- | --- |
| "Give me everything for tonight" | Generic GM Tonight Pack |
| "Send the players their material" | Player candidate, rendered preview, exact-byte approval, unchanged final pack |
| "I need maps, tokens, or handouts" | Generic pack with asset and scene manifests |
| "Make this an Alchemy character" | Alchemy character JSON, only with an explicit system key and resolved fields |
| "Make a Foundry bundle" | Foundry generation-14 offline module authored against the 14.365 API profile |
| Unsupported or unspecified VTT | Neutral Ludis Pack plus manual import checklist |

Do not add a network service or control the target. Generate files, explain where they go, and preserve a loss report.

## Prepare the campaign

1. Require `cd-ludis-campaign-ledger/v2`. If the ledger is legacy `0.1.0`, run a migration dry-run first.
2. Validate the ledger. Stop on invalid IDs, links, assets, visibility paths, quarantined kinds, or digest mismatches.
3. Add every supplied asset to `assets[]` with a campaign-relative POSIX path, visibility, rights status, provenance, and useful alt text.
4. Give map or scene objects explicit dimensions and grid metadata. Do not guess grid size, walls, doors, lights, movement, or rules values.
5. For artwork the campaign does not yet have, use image generation. Keep generated pixels and technical metadata distinct: the image is artwork; grid, scene, or UVTT data is a structured assertion.

## Build and approve

Build a neutral pack:

```text
python -B scripts/export_campaign.py build CAMPAIGN OUTPUT.zip --audience gm
python -B scripts/export_campaign.py verify OUTPUT.zip
```

Build a target pack:

```text
python -B scripts/export_target.py build CAMPAIGN OUTPUT.zip --target alchemy --audience gm
python -B scripts/export_target.py build CAMPAIGN OUTPUT.zip --target foundry-v14 --audience gm
python -B scripts/export_target.py verify OUTPUT.zip
```

For either exporter, player output must use a candidate name:

```text
python -B scripts/export_campaign.py build CAMPAIGN OUTPUT.candidate.zip --audience player
python -B scripts/export_campaign.py approve OUTPUT.candidate.zip --asserted-by "local operator label"
```

`export_target.py approve` applies the same boundary to a target candidate. Open the adjacent `.preview.html`, then extract the candidate into a new review directory. Compare every member with the preview and audit, inspect or listen to every non-rendered member, and treat bundled code as text without executing it. Automated checks catch declared graph and asset leaks; they cannot understand an accidental secret in ordinary prose.

Approval copies candidate bytes unchanged to the final ZIP and writes an adjacent receipt. The label is an unauthenticated assertion under local filesystem custody. If any candidate or preview byte changes, rebuild and review again.

## Neutral Ludis Pack v1

The generic ZIP contains:

- `ludis-pack.json`: format, audience, campaign identity, source digests, object and asset IDs, and member inventory;
- `README.md` and `handouts/`: table-usable Markdown;
- `data/objects.json` and `data/object-index.csv`;
- `data/tables.json` and CSV;
- `data/scenes.json`, `tokens.json`, and `audio-cues.json`;
- `data/assets.json` and supplied asset bytes;
- `reports/loss-report.json`.

JSON and line endings are normalized; ZIP paths, timestamps, permissions, and order are fixed. Byte-identical ZIP evidence applies to this standard-library profile on environments actually tested. Optional renderers are separate derivative profiles, not implied by that claim.

## Target profiles

### Alchemy character JSON

Require an explicit `systemKey`; do not infer it from a campaign title or invent mechanics. Emit one JSON file per supported character plus `_all.json`. Unsupported or insufficiently resolved records belong in the loss report. Alchemy's current help article documents live NPC JSON import through a Universe without naming a plan, while its developer documentation says Alchemy Unlimited provides NPC import. Require a signed-in account and edit access to the destination Universe or active module, treat plan eligibility as unresolved until checked in the current UI, and never infer any of those from static construction.

Alchemy's documented file contract uses `imageUri`, not local sidecar image embedding. Do not imply that a bundled token will become Alchemy character art without an explicit reachable URI. Static validation establishes JSON shape and mapped fields only. Until that exact import is observed, say "constructed against the official documented format; live import unverified."

### Foundry generation 14

Emit an offline module containing `module.json`, `scripts/importer.mjs`, a Ludis payload, and copied assets. Map lore, handouts, NPC descriptions, locations, factions, and quests to JournalEntry; tables to RollTable; maps to Scene with embedded v14 Level backgrounds. Preserve the original `flags.ludis.sourceId`, scope identity by campaign plus source ID, and stamp audience plus an exact-import revision. Skip exact reruns; report changed content or audience for the same campaign object as a conflict and leave the existing Foundry document untouched. Assign core documents `OBSERVER` for player projections and `NONE` for GM projections; require a live non-GM check before claiming actual player visibility.

The implementation is authored against Foundry 14.365 Stable APIs. The manifest permits generation 14; it does not claim verified compatibility. Do not emit Actor or Item without a named game system and version. Foundry core does not define their system data. Do not use old Scene background fields; v14 backgrounds belong to embedded Level documents.

Static validation establishes module/payload shape, safe asset paths, source-ID uniqueness, table ranges, scene dimensions, and importer syntax only. It does not establish live recognition, database acceptance, rendering, visual grid alignment, or idempotent behavior in a running Foundry instance. Before a live attempt, back up a disposable World. Quarantine the module folder and restore that recorded pre-import World backup for a complete rollback; flag-based manual deletion is not provably complete because records have no import-run ID and exact records may have been skipped.

### Supplied UVTT

Validate and pass through supplied UVTT. Do not infer walls or doors from a bitmap and call the geometry verified.

## Evidence and recovery

The capture stage copies ledger and declared asset bytes into a run-local frozen root. Paths must stay inside the campaign, and symlinks or reparse points are rejected. A file that changes during capture fails the build. Later stages read only the frozen bytes.

Exports are immutable. Reusing an occupied output path fails rather than rewriting evidence. A target's loss report owns mapping warnings and blocks.

After an actual import attempt, `record_import_observation.py` can bind a campaign-local assertion to exact bundle and optional evidence bytes. Its schema fixes `promotes_product_compatibility` to `false`; product compatibility changes require separate release evidence.

If a build fails, preserve the message and source ledger, repair the declared input, and choose a fresh output path. Do not edit a candidate ZIP, audit, preview, approval receipt, import observation, or final artifact in place.
# Export campaign assets and VTT bundles

Ludis can turn a governed campaign ledger into files that other people and tools can use. It does not become the VTT, log into one, or give the target authority over canon. The ledger remains canonical; every export is a one-way projection from a frozen copy of the declared source bytes.

If you want to see the whole path before touching your own campaign, use the [generated Tonight Pack example](examples/tonight-pack/README.md).

## Choose the result you need

| Need | Build | Result |
|---|---|---|
| Session packet, maps, tokens, handouts, or portable campaign data | Neutral Ludis Pack | One ZIP with readable handouts, structured data, supplied assets, member hashes, and a loss report |
| Something safe to send to players | Player candidate | Candidate ZIP plus rendered preview and audit; approval produces an unchanged final ZIP and receipt |
| NPC or character records for Alchemy | Alchemy target | Individual Character JSON files plus `_all.json` for bulk import |
| Lore, tables, and map scenes for Foundry | Foundry v14 target | Offline module with JournalEntry, RollTable, Scene/Level data, copied assets, and an importer |
| Another or unknown VTT | Neutral Ludis Pack | Stable source files and metadata for manual conversion; no invented target fields |

All commands in this guide run from the repository root and require Python 3.10 or later. The scripts use only the Python standard library.

## Prepare and validate the campaign

Managed exports require a `cd-ludis-campaign-ledger/v2` workspace. Create one with an explicit stable identity:

```powershell
python -B scripts/init_campaign.py C:\Games\MyCampaign --campaign-id campaign-my-game --title "My Game"
python -B scripts/validate_ledger.py C:\Games\MyCampaign\campaign-ledger.json
```

A declared asset needs a campaign-relative path, exact SHA-256, visibility, provenance, rights status, and useful alternative text. Scenes and maps need explicit dimensions and grid metadata. Ludis will not guess walls, doors, lighting, movement, grid calibration, or game mechanics from pixels.

### Migrate a legacy ledger first

For a legacy `0.1.0` ledger, preview a non-destructive migration first. If the ledger already has a valid `campaign.id`, omit the identity option or repeat that exact value. If it has no ID, supply an owner-chosen one:

```powershell
python -B scripts/migrate_ledger.py C:\Games\OldCampaign\campaign-ledger.json --campaign-id campaign-my-game
```

For a ledger with no ID, you can instead derive a repeatable ID from an owner-supplied stable phrase:

```powershell
python -B scripts/migrate_ledger.py C:\Games\OldCampaign\campaign-ledger.json --campaign-seed "owner supplied stable phrase"
```

Dry-run is the default and writes nothing. After reviewing the reported unknown fields, quarantined objects, and legacy approvals, write to a new path with the same identity choice:

```powershell
python -B scripts/migrate_ledger.py C:\Games\OldCampaign\campaign-ledger.json --campaign-id campaign-my-game --output C:\Games\OldCampaign\campaign-ledger-v2.json
```

A successful write also preserves the exact legacy bytes beside the new ledger as `campaign-ledger-v2.source-v0.1.json`. Use `--source-copy ANOTHER-PATH` only when you deliberately need a different copy location. Migration never overwrites the source, output, or source-copy path; unknown material is quarantined, and old export booleans do not grant new approval.

## Build a neutral GM pack

```powershell
python -B scripts/export_campaign.py build C:\Games\MyCampaign output\my-game-gm.zip --audience gm
python -B scripts/export_campaign.py verify output\my-game-gm.zip
```

The ZIP contains a `cd-ludis-pack/v1` manifest; Markdown handouts; JSON and CSV object/table data; scene, grid, token, and audio-cue metadata; supplied asset bytes; and `reports/loss-report.json`. The adjacent HTML preview lets you inspect rendered text, filenames, and raster images without importing anything.

GM output is final at build time. That means "GM audience," not "safe, balanced, rights-cleared, or accepted by a VTT." Read the preview and loss report before using it.

## Build and approve player material

Player output deliberately has a review gate:

```powershell
python -B scripts/export_campaign.py build C:\Games\MyCampaign output\my-game-player.candidate.zip --audience player
```

Open `output\my-game-player.candidate.zip.preview.html`. Review every object, filename, image, credit, and bit of prose. Extract a review copy into a new directory, compare its full inventory with the preview and audit, listen to audio, and inspect every member the HTML preview cannot render. Treat bundled code as text; do not execute it during review. The graph checks can block declared links from player-safe material to GM-only material; they cannot recognize a secret casually written into ordinary prose.

After review, approve the exact candidate and preview bytes:

```powershell
python -B scripts/export_campaign.py approve output\my-game-player.candidate.zip --asserted-by "local GM label"
```

The final `my-game-player.zip` is byte-identical to the candidate. Its adjacent receipt binds the candidate, preview, and audit digests. `--asserted-by` is an unauthenticated local label, not identity verification. If any candidate or preview byte changes, use a fresh output name, rebuild, and review again.

The same candidate/approval workflow applies to player-facing target bundles built with `export_target.py`.

## Build an Alchemy character bundle

Alchemy export requires an explicit `systemKey` in each supported character record. Ludis does not infer it from the campaign name or invent missing mechanics.

**Prerequisite:** use a signed-in Alchemy account and a Universe or active module you can edit. Alchemy's current help article documents JSON import through the Universe NPC menu without naming a plan, while its developer documentation says Alchemy Unlimited provides NPC import. Treat plan eligibility as an unresolved account-side prerequisite and confirm it in the current UI. Build and static verification do not establish account, plan, or edit access.

```powershell
python -B scripts/export_target.py build C:\Games\MyCampaign output\my-game-alchemy.zip --target alchemy --audience gm
python -B scripts/export_target.py verify output\my-game-alchemy.zip
```

Extract the ZIP and inspect `reports/loss-report.json`. Each supported character has an individual JSON file; `_all.json` contains the same records in the official multi-character wrapper.

The current official Alchemy flow is:

1. Open the destination Universe and active module.
2. Open **NPCs**.
3. Select the triangle beside **Create NPC**, then **Import JSON**.
4. Choose one individual JSON file or `_all.json` for the bulk wrapper.
5. Inspect every imported field before treating the result as usable.

Alchemy also documents similar import controls in the Character Library and Universe Premades. See Alchemy's [character import instructions](https://help.alchemyrpg.com/en/articles/9833429-importing-a-character) and [Character JSON format](https://alchemyrpg.github.io/slate/).

This profile is derived from Alchemy's current unversioned documentation. Archive membership and emitted filenames use exact allowlists. The vendor-native Character object remains open to extension fields because Alchemy's official unversioned profile is open; Ludis validates file shape and mapped known fields, not every future vendor field. Alchemy documents `imageUri`, not a portable local sidecar-image contract, so Ludis does not pretend a bundled token file will import as character art. Live import remains unverified until somebody observes that exact bundle in the target.

## Build a Foundry v14 module

```powershell
python -B scripts/export_target.py build C:\Games\MyCampaign output\my-game-foundry.zip --target foundry-v14 --audience gm
python -B scripts/export_target.py verify output\my-game-foundry.zip
```

The module maps setting text, handouts, locations, factions, quests, and descriptive NPC records to JournalEntry; suitable tables to RollTable; and explicit map metadata to Scene with embedded v14 Level backgrounds. It intentionally emits no Actor or Item documents because those require a named game-system adapter. Player-audience bundles assign imported core documents Foundry `OBSERVER` permission; GM bundles assign `NONE`. After a player import, verify visibility with a non-GM account in the disposable world before relying on it.

The importer is authored against the Foundry 14.365 Stable API profile. Its manifest permits Foundry generation 14 and deliberately omits a `verified` compatibility claim.

Install into a disposable backed-up world first. From Foundry's Setup screen, right-click the disposable World and select **Take Backup** before enabling the module. Record which backup you created. A built-in World backup may omit multimedia stored outside the World package, so preserve those assets separately or use your hosting provider's documented backup method.

1. Extract the ZIP somewhere temporary and open `module.json`.
2. Read its `id` value.
3. In the Foundry user-data directory, create `Data\modules\<id>`. The folder name must exactly match the manifest ID.
4. Copy the ZIP contents into that folder so `module.json` sits directly at `Data\modules\<id>\module.json`. Do not leave an extra ZIP-name folder in between.
5. Restart Foundry if it was running.
6. Enter the disposable world as a GM, open **Settings**, choose **Manage Modules**, enable the module, and save module settings.
7. At world readiness, choose **Import or resume** in the Ludis dialog. If the dialog API is unavailable, use the console command printed by the module notification.
8. Inspect the created Journals, Tables, Scenes, Levels, images, grid alignment, and importer report.

The importer preserves the original `flags.ludis.sourceId`, but scopes identity by `campaignId` plus `sourceId`. It also records the audience and an exact-import SHA-256. Re-running the exact bundle skips matching records so an interrupted import can resume; changed content or audience for the same campaign object is reported as a conflict and left untouched. It does not reconcile edits or synchronize the VTT back into the ledger.

### Roll back a Foundry test import

Restoring the World backup made immediately before import is the only complete rollback. Ludis records campaign, source, audience, and revision flags, but it does not stamp an import-run ID. A resumed import can also skip documents created by an earlier attempt. Manual deletion therefore cannot always distinguish documents created by this run from matching documents that already existed.

1. Have every user leave the disposable World. Preserve the exact bundle ZIP, its SHA-256, the console report, the module `id` from `module.json`, and the campaign ID from `data/ludis-foundry-v14.json`.
2. Stop Foundry completely. Move only `Data/modules/<module-id>` to a dated quarantine directory outside `Data/modules`. Confirm that the moved folder's `module.json` contains the expected ID. This prevents the importer from running again; it does **not** remove imported World documents.
3. Restart Foundry to the Setup screen. Restore the specific pre-import World backup: right-click the World and select **Restore Latest** only when the backup you just recorded is definitely the latest one. Otherwise open **Manage Backups**, choose the World backup you recorded, and restore that specific backup. On a hosted service, use its documented restore procedure.
4. Open the World without the Ludis module. Confirm that the imported Journals, Roll Tables, Scenes, and embedded Levels are absent and that pre-existing World content is back. Check external map or audio assets separately because a World package backup may not include media stored elsewhere.
5. Keep the quarantined module folder and import evidence until that verification succeeds. Afterward, retain or remove them according to your campaign's evidence and privacy policy. Never delete or edit Foundry's backup files directly; use **Manage Backups**.

If no pre-import backup exists, stop and make a backup of the current damaged or partial state before any cleanup. You may compare `flags.ludis.campaignId` and `flags.ludis.sourceId` against the preserved payload, then manually remove matching top-level Journals, Roll Tables, and Scenes; deleting a matching Scene also removes its embedded Levels. Do not delete by display name alone. Because exact matches may have predated this attempt, manual cleanup is not provably complete and must not be reported as a full rollback.

See Foundry's [module installation guide](https://foundryvtt.com/article/modules/), [module development guide](https://foundryvtt.com/article/module-development/), [backup and restore guide](https://foundryvtt.com/article/backups/), and [14.365 release page](https://foundryvtt.com/releases/14.365). Static API and schema alignment does not prove that a running host accepted, rendered, or preserved the intended meaning of the bundle.

## Supplied UVTT files

A neutral Ludis Pack can validate and pass through a UVTT file already supplied by the user. Ludis does not infer walls, doors, portals, or lighting from a raster map and call the result verified. If no trusted UVTT geometry exists, export the map plus explicit scene/grid metadata and let the target user configure geometry.

## Read the loss report

Every adapter writes `reports/loss-report.json`. Treat it as part of the deliverable:

- `blocked` means required source or target fields are missing; fix the ledger or use the neutral pack.
- a warning names material that was omitted, demoted, or represented less precisely;
- an empty blocker list does not mean the target imported successfully;
- never invent a mechanic, system key, map dimension, or rights claim merely to silence the report.

## Record a real import attempt

After an actual target attempt, record the exact bundle, target version, result, and optional redacted evidence:

```powershell
python -B scripts/record_import_observation.py output\my-game-foundry.zip output\my-game-foundry.import-observation.json `
  --target foundry-v14 `
  --target-version 14.365 `
  --result imported `
  --asserted-by "local GM label" `
  --notes "Disposable-world smoke test" `
  --evidence C:\Temp\redacted-import-log.txt
```

Use `--result imported`, `partial`, or `failed`. If a web service exposes no version, use a dated observation label such as `web-observed-2026-08-13`. The receipt hashes the bundle and evidence files, never overwrites an existing receipt, and always says `promotes_product_compatibility: false`. One local success is useful evidence about those bytes, not a product-wide compatibility certificate.

Redact player names, secrets, credentials, and private campaign text before attaching logs or screenshots.

## Failure and recovery

- **Ledger v2 required:** preview migration, review the report, then write a new ledger. Do not overwrite the old source.
- **Asset missing, escaped, changed, or digest mismatch:** stop the editor or sync process, correct the declared input, and build to a fresh path.
- **Output already exists:** keep it as evidence and choose a new filename. Export artifacts and receipts are immutable.
- **Player candidate or preview changed:** rebuild, rereview, and approve the new bytes. Do not reuse the old receipt.
- **Target mapping blocked:** supply the named field or fall back to the neutral pack.
- **Alchemy or Foundry rejects the bundle:** preserve the exact ZIP, digest, target/build, steps, error, and redacted loss report. Record a `partial` or `failed` local observation.
- **Foundry module is absent:** verify the folder name equals `module.json`'s `id`, `module.json` is at the folder root, Foundry was restarted, and the world was entered as GM.
- **Foundry import was interrupted:** enable the same module and run **Import or resume** again. Exact campaign/object revisions are skipped. If a conflict is reported, preserve the world and report; Ludis will not overwrite the changed document or its visibility.
- **Foundry test import must be undone:** follow [Roll back a Foundry test import](#roll-back-a-foundry-test-import). Restoring the recorded pre-import World backup is the only complete rollback.

For broader installation, cleanup, and restoration help, see [SUPPORT.md](SUPPORT.md). For custody and privacy boundaries, see [SECURITY.md](SECURITY.md).
# Tonight Pack example

This fictional campaign demonstrates the complete offline export path with real generated raster assets:

- a v2 campaign ledger;
- separate player-safe and GM-only objects;
- a player-safe generated tollhouse map;
- a GM-only generated Mara Venn token;
- a weighted rumor table;
- explicit scene/grid metadata;
- Alchemy-ready NPC fields;
- a proposed audio cue with no bundled copyrighted audio.

The artwork was generated for this example. It is not a coded SVG or a stock image masquerading as provenance origami.

## Build the GM pack

From the repository root:

```powershell
python -B scripts/export_campaign.py build examples/tonight-pack/campaign output/kindly-cellar-gm.zip --audience gm
python -B scripts/export_campaign.py verify output/kindly-cellar-gm.zip
```

Expected result: a finalized generic GM Tonight Pack plus adjacent audit and HTML preview files.

## Build and approve the player pack

```powershell
python -B scripts/export_campaign.py build examples/tonight-pack/campaign output/kindly-cellar-player.candidate.zip --audience player
```

Open `output/kindly-cellar-player.candidate.zip.preview.html`. Extract the candidate into a new review directory, compare every member with the preview and audit, inspect or listen to everything the HTML does not render, and treat bundled code as text without executing it. Then approve the exact candidate and preview bytes:

```powershell
python -B scripts/export_campaign.py approve output/kindly-cellar-player.candidate.zip --asserted-by "your local operator label"
```

Expected result: `kindly-cellar-player.zip` has the same SHA-256 as the candidate, and an adjacent approval receipt records both the candidate and preview digests. The operator label is a local assertion, not authenticated identity.

## Build target bundles

From the repository root:

```powershell
python -B scripts/export_target.py build examples/tonight-pack/campaign output/mara-alchemy.zip --target alchemy --audience gm
python -B scripts/export_target.py build examples/tonight-pack/campaign output/kindly-cellar-foundry.zip --target foundry-v14 --audience gm
```

Read each target's `reports/loss-report.json`. Static validation does not prove that a current Alchemy or Foundry host imported the bundle. A live Alchemy NPC import requires a signed-in account and edit access to the destination Universe or active module. Alchemy's help article does not name a plan, while its developer documentation says Alchemy Unlimited provides NPC import, so confirm plan eligibility in the current UI. The Foundry profile intentionally emits no Actor or Item documents because those belong to a named game system, not Foundry core. Before a Foundry attempt, back up a disposable World; the complete rollback is restoration of that pre-import backup. A player-audience bundle uses `OBSERVER` permission for its core documents, but that visibility still needs a live non-GM check.

## What the example does not claim

- The map grid has not been visually calibrated in a live VTT.
- The Alchemy JSON has not been live-imported in this repository evidence cycle.
- The Foundry module has not been live-loaded in licensed Foundry v14.365.
- The example's 5e-compatible numbers are illustrative supplied fixture data, not a balance certification.
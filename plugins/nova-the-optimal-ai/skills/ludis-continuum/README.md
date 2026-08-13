# Ludis Continuum

![A tabletop campaign workspace turns a live choice into branching consequences, changed relationships, and a governed campaign ledger.](docs/assets/ludis-continuum-readme-hero.png)

> Choice-shaped RPGs and fiction that remember what happened without stealing the wheel.

Ludis Continuum is a setting-free skill for players, game masters, and fiction creators who need playable pressure, consequential choices, and continuity that survives more than one scene. It can open a game immediately, forge a character or world element, operate a campaign through a governed JSON ledger, and turn that campaign into inspectable GM/player Tonight Packs or narrow offline VTT import bundles.

It does **not** replace a GM, certify balance, reproduce a game system, decide canon by confidence, or make private campaign material safe to publish. Generated material is proposed until its human owner accepts it.

[Project site](https://stunspot.github.io/ludis-continuum/) | [Install and start](START-HERE.md) | [Operating guide](DOCUMENTATION.md) | [Trust and evidence](PROVENANCE.md) | [Support](SUPPORT.md)

## Who it is for

- A GM who wants situations with several viable approaches instead of a disguised plot.
- A player who wants a choice-driven solo scene with legible controls and consequences.
- A fiction creator who wants characters, places, factions, magic, or mysteries with causal traction.
- A campaign steward who needs canon, proposals, rumors, secrets, observations, and approvals kept distinct.
- A returning or current VTT user who wants maps, tokens, handouts, tables, or campaign content exported without giving a VTT custody of canon.

Ordinary business writing, generic prose cleanup, authoritative rules lookup, and autonomous play on behalf of human participants remain outside Ludis.

## Three ways in

### Play now

Start inside the fiction. Ludis establishes a reversible rules posture when none is supplied, exposes only the controls needed, and offers two to four materially different choices plus freedom to try something else.

### Character and fiction forge

Turn a thin prompt into a usable character, place, faction, object, scene, or world element with a want, pressure, contradiction, relationship, uncertainty, and future hooks. Supplied canon stays intact; new material stays proposed.

### Campaign operations

Prepare the next playable horizon, record what actually happened, surface contradictions, govern canon promotion, separate GM-only from player-safe material, and carry consequence forward.

### Export and VTT handoff

Turn a v2 campaign ledger into a neutral `cd-ludis-pack/v1` Tonight Pack containing handouts, tables, scene/grid/token/audio metadata, assets, digests, and a loss report. Build player material as a reviewable candidate. Before approval, extract a review copy into a new directory, compare every member with the inventory and audit, inspect or listen to everything the preview does not render, and treat bundled code as text without executing it. Approve the exact candidate and preview bytes, then finalize the same bytes unchanged.

Ludis also emits narrow Alchemy character JSON and a Foundry v14.365 offline module importer for core JournalEntry, RollTable, and Scene/Level content. Player-audience Foundry bundles assign those core documents the `OBSERVER` permission level; GM bundles keep them GM-only. These are file handoffs, not MCP, live control, sync, or a claim that a static check observed a successful import or non-GM visibility.

## Quick start

Ludis is distributed here as a standalone skill directory. It has no marketplace manifest and makes no one-click-install claim.

```powershell
# Windows: clone as a Codex user skill
git clone https://github.com/Stunspot/ludis-continuum "$env:USERPROFILE\.codex\skills\ludis-continuum"
python -B "$env:USERPROFILE\.codex\skills\ludis-continuum\scripts\self_check.py"
```

```bash
# macOS/Linux: clone as a Codex user skill
git clone https://github.com/Stunspot/ludis-continuum "$HOME/.codex/skills/ludis-continuum"
python3 -B "$HOME/.codex/skills/ludis-continuum/scripts/self_check.py"
```

Restart the host, confirm **Ludis Continuum** is discoverable, then invoke:

```text
Use $ludis-continuum to open a rain-soaked city mystery. Give me a clear
situation, three materially different choices, and freedom to try another move.
Keep all new world facts provisional until I accept them.
```

Claude Code and project-scoped installation paths, verification, first-run examples, update, removal, and cleanup are in [START-HERE.md](START-HERE.md).

## What a successful first response contains

For **Play now**, expect:

1. an immediate situation rather than an intake questionnaire;
2. the visible pressure and what matters now;
3. two to four meaningfully different choices;
4. permission to attempt something else;
5. no invented claim that an unspecified rules system is authoritative.

For **Campaign operations**, expect separate GM-only and player-safe material, explicit proposed/disputed/canon status, rules and rights uncertainties, checks that actually ran, approvals still needed, and the smallest useful next-prep action.

## Campaign State Ledger

`campaign-ledger.json` is canonical for a managed campaign. Everything else is a proposal, observation, projection, or artifact until the GM promotes it.

Each context object carries a stable ID, kind, status, visibility, authority, provenance, confidence, and tenure. Supported statuses are:

- `proposed`
- `active_canon`
- `disputed`
- `superseded`
- `quarantined`
- `retired`

Visibility is either `gm_only` or `player_safe`. Only the GM may promote an object to `active_canon`, approve a player-safe export, or authorize publication.

A rumor is player-facing uncertainty, not false canon. An observation records what happened, not the explanation. When sources conflict, preserve both claims and their authority rather than silently harmonizing them.

## Campaign loop

```text
Seed -> Frame -> Prepare -> Play -> Record -> Resolve -> Advance
```

| Stage | Work |
|---|---|
| Seed | Intent, rules posture, preferences, boundaries, source authority, and the next real need. |
| Frame | Playable promise, pressures in motion, invitation, scale, and tone. |
| Prepare | Stakes, approaches, clues, telegraphing, consequences, adaptation, and unresolved mechanics. |
| Play | Compact GM material, separate player-safe material, and improvisation handles. |
| Record | Observations, choices, declared outcomes, improvised facts, resource changes, and open questions. |
| Resolve | Proposed consequences, faction changes, rumors, supersessions, and causal links for approval. |
| Advance | Audit continuity, leakage, dead prep, stalled actors, player interests, and the next horizon. |

## Deterministic trust edge

The bundled tools use the Python standard library only.

| Tool | Responsibility |
|---|---|
| `scripts/init_campaign.py` | Create a v2 workspace with an explicit or owner-seeded stable campaign ID. |
| `scripts/validate_ledger.py` | Check v2 or legacy ledger invariants, IDs, graph visibility, assets, authority, approvals, and collisions. |
| `scripts/migrate_ledger.py` | Dry-run or write a non-destructive legacy `0.1.0` to v2 migration with exact-byte source copy. |
| `scripts/promote_object.py` | Record one explicit, unauthenticated local canon-promotion assertion. |
| `scripts/roll_table.py` | Make seeded random selection reproducible. |
| `scripts/export_campaign.py` | Build, verify, preview, and exact-byte approve neutral GM/player Tonight Packs. |
| `scripts/export_target.py` | Build statically validated Alchemy or Foundry v14 target bundles with loss reports. |
| `scripts/record_import_observation.py` | Bind one real target attempt to exact bundle/evidence bytes without promoting product-wide compatibility. |
| `scripts/export_player_safe.py` | Convenience wrapper for a reviewable player candidate; no legacy boolean grants current approval. |
| `scripts/snapshot_campaign.py` | Create a deterministic content-addressed recovery snapshot without nesting checkpoints. |
| `scripts/self_check.py` | Verify curated runtime contracts, schemas, examples, generated asset hashes, and 32 instrument cores. |

A passing script establishes only the check it performs. It does not prove fun, safety, spoiler freedom outside the validated graph, originality, accessibility, balance, VTT compatibility, rights clearance, rules accuracy, or publication readiness.

## First offline export

Create a campaign workspace outside the skill directory:

```powershell
python -B scripts/init_campaign.py C:\Games\MyCampaign --campaign-id campaign-my-game --title "My Game"
python -B scripts/validate_ledger.py C:\Games\MyCampaign\campaign-ledger.json
```

After adding objects and declared assets, build a GM pack:

```powershell
python -B scripts/export_campaign.py build C:\Games\MyCampaign output\my-game-gm.zip --audience gm
```

Player material deliberately takes two steps:

```powershell
python -B scripts/export_campaign.py build C:\Games\MyCampaign output\my-game-player.candidate.zip --audience player
python -B scripts/export_campaign.py approve output\my-game-player.candidate.zip --asserted-by "local GM label"
```

Review the generated `.preview.html` and the complete candidate before approval: extract a review copy into a new directory, compare every member with the preview and audit, inspect or listen to every non-rendered member, and treat code as text without executing it. Automated visibility checks do not understand secrets embedded in ordinary prose. See [Export campaign assets and VTT bundles](EXPORTS-AND-VTT.md) and the [generated Tonight Pack example](examples/tonight-pack/README.md).

## Focused creative instruments

Ludis includes 32 compact instrument cores covering regions, settlements, factions, rumors, villains, schemes, intrigue, quests, encounters, dungeons, puzzles, creatures, artifacts, magic, language, characters, myths, visual briefs, and campaign workflow.

Load the one instrument matching the immediate transformation. Load another only when the first cannot complete the artifact without a genuinely different creative motion. Instruments are bearings, not canon, rules authority, or a prebuilt setting.

## Privacy and network behavior

The skill and bundled scripts run on local files and make no network requests. The AI host may still transmit prompts, files, or tool outputs according to that host's configuration and terms. Do not place secrets, private player information, licensed source text, or sensitive consent notes into a host context unless every participant has authorized that handling.

Campaign data lives wherever you create the workspace. Removing the skill does not remove campaign directories or snapshots. See [SECURITY.md](SECURITY.md) for the full boundary and [SUPPORT.md](SUPPORT.md) for cleanup.

## Evidence status

The current release has direct repository evidence for package self-checks and deterministic tool behavior. Host discovery, host invocation, fresh-machine installation, live table quality, balance, and rules accuracy are separate claims and are not inferred from file presence.

Exact review receipts and test boundaries are published in [`verification/`](verification/) and summarized in [PROVENANCE.md](PROVENANCE.md).

## License, support, and contribution

Ludis Continuum is released under the [MIT License](LICENSE.md). Report defects through [GitHub Issues](https://github.com/Stunspot/ludis-continuum/issues), read [SUPPORT.md](SUPPORT.md) before sharing campaign material, review [SECURITY.md](SECURITY.md) for sensitive reports, and follow [CONTRIBUTING.md](CONTRIBUTING.md) for changes.

Current source edition: `1.1.0`. This standalone repository preserves the curated public source from the Nova + MIND OpenAI Build Week release; private development history and worked campaign worlds are excluded.

🌐‍💠
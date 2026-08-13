# Install, verify, and begin

This guide covers every supported distribution target for the standalone repository: manual skill placement in Codex or Claude Code, project-scoped placement, and a host-neutral copy/paste fallback. There is no marketplace package or one-click installer in this repository.

## Requirements

- Git for clone/update workflows, or a downloaded source archive.
- Python 3.10 or later for the optional deterministic campaign tools. The creative skill itself is Markdown and JSON.
- A host that can load `SKILL.md`, or an AI chat where you can paste the fallback workflow.

## Codex

### User-scoped install

Windows PowerShell:

```powershell
git clone https://github.com/Stunspot/ludis-continuum "$env:USERPROFILE\.codex\skills\ludis-continuum"
python -B "$env:USERPROFILE\.codex\skills\ludis-continuum\scripts\self_check.py"
```

macOS/Linux:

```bash
git clone https://github.com/Stunspot/ludis-continuum "$HOME/.codex/skills/ludis-continuum"
python3 -B "$HOME/.codex/skills/ludis-continuum/scripts/self_check.py"
```

Restart Codex after installation. Confirm that **Ludis Continuum** appears in the available skill list, then run the acceptance prompt in [Verify host discovery and invocation](#verify-host-discovery-and-invocation).

### Project-scoped install

Place the complete repository at:

```text
<project>/.codex/skills/ludis-continuum/
```

The file `<project>/.codex/skills/ludis-continuum/SKILL.md` must exist. Project-scoped discovery depends on the host version and policy; if it does not appear, use the user-scoped path or the fallback workflow.

## Claude Code

### User-scoped install

Windows PowerShell:

```powershell
git clone https://github.com/Stunspot/ludis-continuum "$env:USERPROFILE\.claude\skills\ludis-continuum"
python -B "$env:USERPROFILE\.claude\skills\ludis-continuum\scripts\self_check.py"
```

macOS/Linux:

```bash
git clone https://github.com/Stunspot/ludis-continuum "$HOME/.claude/skills/ludis-continuum"
python3 -B "$HOME/.claude/skills/ludis-continuum/scripts/self_check.py"
```

Restart Claude Code. Confirm that the skill is listed or that `/ludis-continuum` is available, then run the acceptance prompt in [Verify host discovery and invocation](#verify-host-discovery-and-invocation). Host UI and invocation syntax can vary by release; discovery is the authoritative check.

### Project-scoped install

Place the complete repository at:

```text
<project>/.claude/skills/ludis-continuum/
```

Do not copy only `SKILL.md`; the doctrine, instrument cores, fallbacks, schema, template, and scripts are part of the package.

## Source archive instead of Git

Download the repository archive from GitHub, extract it, and rename the extracted directory to `ludis-continuum` inside the appropriate host skill directory. An archive install cannot use `git pull`; update by replacing the skill directory with a freshly downloaded archive after preserving any local modifications.

## Host-neutral fallback

If the host cannot load skills, open [`fallbacks/universal-copy-paste-workflow.md`](fallbacks/universal-copy-paste-workflow.md), copy the workflow into the conversation, and attach or paste only the campaign material needed for the request. This is a degraded workflow, not proof of host installation.

## Verify package construction

From the skill directory:

```powershell
python -B scripts/self_check.py
```

Expected terminal line:

```text
PASS: Ludis Continuum curated-runtime self-check (32 instrument cores)
```

That result establishes package contracts only. It does not establish host discovery or invocation.

## Verify host discovery and invocation

1. Restart the host.
2. Confirm **Ludis Continuum** in its available skill list.
3. Submit this acceptance prompt:

```text
Use $ludis-continuum to open a mystery at a mountain observatory whose warning
bell rang with no visible intruder. Give me an immediate situation, three
materially different choices, and permission to try another move. Do not invent
an authoritative rules system. Mark new setting facts as proposed.
```

For Claude Code, use `/ludis-continuum` if that is how the host exposes the skill.

Pass only if the response:

- begins with a playable situation;
- offers three materially different choices and allows another action;
- does not claim an unspecified rules system;
- distinguishes proposed facts from accepted canon;
- does not expose campaign secrets supplied as GM-only.

If the skill is absent, host discovery is **not verified** even when `SKILL.md` exists. See [SUPPORT.md](SUPPORT.md).

## First campaign workspace

Choose a data directory outside the installed skill. From the repository or installed skill directory:

```powershell
python -B scripts/init_campaign.py C:\Games\MyCampaign --campaign-id campaign-my-game --title "My Game"
python -B scripts/validate_ledger.py C:\Games\MyCampaign\campaign-ledger.json
```

macOS/Linux:

```bash
python3 -B scripts/init_campaign.py "$HOME/Games/MyCampaign" --campaign-id campaign-my-game --title "My Game"
python3 -B scripts/validate_ledger.py "$HOME/Games/MyCampaign/campaign-ledger.json"
```

Initialization requires an owner-chosen stable ID or `--campaign-seed` and refuses to overwrite a non-empty destination. Edit `campaign-ledger.json` only after making a backup or snapshot. For a `0.1.0` ledger, first inspect `campaign.id`: if it already contains a valid stable ID, omit identity flags or repeat that exact value; use `--campaign-id` or `--campaign-seed` only when the legacy ledger has no ID. Preview migration without `--output`, review the report, then rerun the same identity choice with `--output NEW-LEDGER`. See [the complete migration procedure](EXPORTS-AND-VTT.md#migrate-a-legacy-ledger-first).

## First campaign export

The generated example is the shortest complete tour:

```powershell
python -B scripts/validate_ledger.py examples\tonight-pack\campaign\campaign-ledger.json
python -B scripts/export_campaign.py build examples\tonight-pack\campaign output\kindly-cellar-gm.zip --audience gm
python -B scripts/export_campaign.py verify output\kindly-cellar-gm.zip
```

For player material, build a candidate rather than a final ZIP:

```powershell
python -B scripts/export_campaign.py build examples\tonight-pack\campaign output\kindly-cellar-player.candidate.zip --audience player
```

Open the adjacent `.preview.html`. Then extract the candidate into a new review directory, compare every member with the preview and audit, inspect or listen to everything the preview does not render, and treat bundled code as text without executing it. Only then approve the exact bytes:

```powershell
python -B scripts/export_campaign.py approve output\kindly-cellar-player.candidate.zip --asserted-by "local GM label"
```

Expected result: the final player ZIP has the same SHA-256 as the candidate, and an adjacent receipt binds the candidate and preview digests. The operator label is not authenticated identity. See [Export campaign assets and VTT bundles](EXPORTS-AND-VTT.md) for Alchemy, Foundry, UVTT pass-through, failure recovery, and evidence limits.

## A successful first campaign request

```text
Use $ludis-continuum in Campaign Operations mode. Read this campaign ledger and
prepare only the next playable horizon. Preserve every active-canon claim,
surface contradictions, keep GM-only objects out of player-safe material, and
finish with proposed changes, checks actually run, approvals still required,
and the smallest useful next-prep list.
```

Expected output includes a compact GM packet, separately labeled player-safe material, explicit status/visibility/authority, unresolved rules or rights questions, and no silent canon promotion.

## Next

Read [DOCUMENTATION.md](DOCUMENTATION.md) for campaign workflows, [EXPORTS-AND-VTT.md](EXPORTS-AND-VTT.md) for file and VTT handoffs, [SECURITY.md](SECURITY.md) before handling real player data, and [SUPPORT.md](SUPPORT.md) for updates, removal, recovery, and cleanup.
# Support, recovery, update, and removal

Use [GitHub Issues](https://github.com/Stunspot/ludis-continuum/issues) for reproducible public defects. Do not attach private campaign ledgers, player identities, consent notes, licensed source text, or unreleased story secrets. For a vulnerability or sensitive exposure, follow [SECURITY.md](SECURITY.md).

## Before reporting a defect

Run from the installed skill directory:

```powershell
python -B scripts/self_check.py
```

Record:

- host and host version;
- operating system and Python version;
- installation scope and exact skill path;
- whether the skill is present, discoverable, invoked, or healthy;
- exact command and exit code;
- smallest redacted fixture that reproduces the problem;
- expected and observed behavior.

Do not report “installed” when only the directory exists. State the furthest observed stage: copied, package self-check passed, discovered by host, invoked, or behaviorally verified.

## Skill is not discoverable

1. Confirm the directory is named `ludis-continuum`.
2. Confirm `SKILL.md` is directly inside that directory, not nested under an archive folder.
3. Confirm the complete `knowledge/`, `fallbacks/`, `scripts/`, `assets/`, `schemas/`, and `agents/` directories are present.
4. Run `scripts/self_check.py`.
5. Restart the host.
6. Check the host's current skill-discovery documentation and policy.
7. If discovery still fails, use the copy/paste fallback and report host discovery as **not verified**.

## Self-check fails

Treat the first reported failure as primary. Common causes are a partial download, missing instrument file, altered frontmatter, line-ending damage, or package files copied into the wrong level. Compare against the current Git commit; do not “fix” hashes or manifests until you know why the bytes differ.

## Ledger validation fails

- `format not recognized`: migrate a legacy `0.1.0` ledger or restore a valid v2 ledger.
- `missing top-level field`: restore the field from the v2 campaign template or a trusted snapshot.
- `duplicate id`: assign a new stable ID and update intended references.
- `broken link`: restore the referenced object or remove the link only after confirming the relationship is obsolete.
- `spoiler link` or `spoiler asset link`: player-safe state reaches GM-only state. Redesign the public reference; never expose the secret to satisfy validation.
- `quarantined_unmapped`: preserve the unknown kind, define an explicit mapping, then change eligibility; do not relabel it merely to silence export.
- `active canon requires gm_approved authority`: return the object to proposed/disputed or obtain and record the GM decision.
- `session collision`: resolve the schedule explicitly; do not discard one session silently.

Make a snapshot or copy before editing damaged state, then rerun validation.

## Promotion fails

`promote_object.py` requires exactly one matching object, status `proposed` or `disputed`, explicit `--gm-approved`, and no unresolved contradiction with active canon. The tool does not grant approval; it records the human decision asserted by the operator.

Promotion reserves the ledger, verifies the exact bytes it read, and replaces the canonical JSON atomically. If `another Ludis writer reserved this ledger` appears, let that operation finish and retry. If the process appears gone, follow [Recover an apparently stale Ludis lock](#recover-an-apparently-stale-ludis-lock); Ludis never guesses that a ledger lock is stale. If cleanup says the ledger update may have completed, validate and inspect the ledger before doing anything else.

## Export build, approval, or verification fails

- `campaign export requires ledger v2`: run `migrate_ledger.py` in dry-run mode, review its report, then write to a new ledger path.
- `asset file missing`, `asset escapes campaign root`, or `symlink or reparse point`: correct the declared campaign-relative file; do not relax the path guard.
- `source changed while it was being captured`: stop the program editing that file, choose a fresh output path, and rebuild.
- `immutable export path already exists`: preserve the prior evidence and choose a new name. Do not overwrite a candidate, preview, audit, final ZIP, or receipt.
- `another Ludis operation is using this output path`: let the other operation finish. If the process appears gone, follow [Recover an apparently stale Ludis lock](#recover-an-apparently-stale-ludis-lock), inspect every intended output, and retry only with a fresh output name.
- `operation may have completed` after lock cleanup failed: do not retry immediately. Inspect the artifact and sidecars named by the command, verify them if present, preserve any complete immutable result, and use a fresh output name for another build.
- `candidate bytes changed after audit` or `preview bytes changed after audit`: discard neither as if nothing happened; choose a new output name, rebuild, review, and approve the new exact bytes.
- Player prose still reveals a secret: correct the ledger content or visibility, rebuild to a fresh candidate, and repeat the complete candidate review: preview, audit, full extracted inventory, and every non-rendered member. Treat code as text without executing it. Structural checks cannot understand semantic spoilers.
- Target loss report contains `blocked`: resolve the named missing field or use the neutral pack. Never invent mechanics or target fields merely to get an empty report.
- Foundry reports an import conflict: preserve the world and console report. The same campaign/object identity already has different content, audience, revision, or document type; Ludis leaves it untouched. Decide manually whether to keep the existing document, remove it after backup, or import into a fresh disposable world.

## Recover an apparently stale Ludis lock

Use this procedure only after Ludis names a lock file. A ledger lock contains a decimal `pid=` line and an absolute `ledger=` line. Each output lock contains `pid=` and `output=`; one operation can reserve several output locks with the same PID. Metadata is diagnostic evidence, not proof that a process is still the same writer. Operating systems reuse PIDs.

First, confirm that the path recorded inside the lock is the exact ledger or output named by the failed command. If the metadata is missing, malformed, names another path, or you cannot account for the operation, preserve the lock and escalate instead of deleting it.

### Check the PID on Windows

Set `$lockPath` to the one exact lock Ludis reported:

```powershell
$lockPath = 'C:\exact\path\.campaign-ledger.json.ludis-lock'
$lockText = Get-Content -LiteralPath $lockPath -Raw
$lockText
$pidMatch = [regex]::Match($lockText, '(?m)^pid=(\d+)$')
if (-not $pidMatch.Success) { throw 'Lock has no valid pid line.' }
$lockPid = [int]$pidMatch.Groups[1].Value
Get-Process -Id $lockPid -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "ProcessId = $lockPid" |
    Select-Object ProcessId, CreationDate, ExecutablePath, CommandLine
```

If these commands show the original Ludis/Python operation, leave the lock alone and wait. If they show another process, the PID may have been reused; compare its start time and command line with the failed operation. If doubt remains, leave the lock in place. Continue only when no process exists and the recorded ledger or output path matches the failed command.

### Check the PID on macOS or Linux

```bash
lock_path='/exact/path/.campaign-ledger.json.ludis-lock'
cat -- "$lock_path"
lock_pid=$(sed -n 's/^pid=\([0-9][0-9]*\)$/\1/p' "$lock_path")
test -n "$lock_pid" || { printf '%s\n' 'Lock has no valid pid line.' >&2; exit 1; }
ps -p "$lock_pid" -o pid=,lstart=,command=
```

A reported process needs the same PID-reuse check: compare its start time and command with the operation that failed. Leave the lock when ownership is uncertain. Continue only when `ps` reports no such process and the recorded path matches.

### Recover a ledger lock

Preserve and validate the current ledger before removing the lock. On Windows:

```powershell
$ledgerPath = 'C:\Games\MyCampaign\campaign-ledger.json'
$recoveryStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$ledgerCopy = "$ledgerPath.before-lock-recovery-$recoveryStamp"
Copy-Item -LiteralPath $ledgerPath -Destination $ledgerCopy -ErrorAction Stop
python -B scripts/validate_ledger.py $ledgerPath
if ($LASTEXITCODE -ne 0) { throw 'Ledger validation failed; lock was preserved.' }
Remove-Item -LiteralPath $lockPath -ErrorAction Stop
```

On macOS or Linux:

```bash
ledger_path='/games/MyCampaign/campaign-ledger.json'
recovery_stamp=$(date -u '+%Y%m%d-%H%M%S')
cp -- "$ledger_path" "$ledger_path.before-lock-recovery-$recovery_stamp" || exit 1
python3 -B scripts/validate_ledger.py "$ledger_path" || exit 1
rm -- "$lock_path" || exit 1
```

Remove only that exact lock after validation passes. Inspect the affected object and approval record before re-entry: if it is already `active_canon` with the intended approval, the prior promotion may have completed and you must not promote it again. If it remains eligible and the ledger matches the preserved copy, rerun the promotion. If validation fails or the state is ambiguous, leave the canonical ledger unchanged and recover from the preserved copy or a trusted snapshot.

### Recover displaced ledger generations

On macOS or Linux, a final-boundary conflict may name a same-directory `*.ludis-displaced` or `*.ludis-rejected` file. The canonical ledger path is the late occupant or the safely restored prior generation; the named recovery file holds another exact generation that Ludis refused to discard. Windows may similarly name a `.ludis-backup` or `.ludis-rejected` file. Do not delete, rename over, copy over, or automatically merge any generation.

1. Stop every Ludis command, agent, editor, sync client, and automation that can write the campaign. Leave the original campaign directory untouched.
2. Copy the canonical ledger and every named recovery file to a separate recovery directory. Record each original path, byte count, and SHA-256. Validate each copy independently, compare its content and timestamp claims with the failed operation, and have the campaign authority select the generation to retain. If any file is malformed or authorship is uncertain, stop and use a trusted snapshot instead of guessing.
3. If the authority selects the existing canonical ledger, validate that exact path again with `validate_ledger.py`, inspect the affected object and approval, and create a new campaign snapshot. Re-enter normal work only after both commands pass. Keep the displaced generations outside active work as rollback evidence.
4. If the authority selects a displaced, rejected, or backup generation, in-place promotion is **not a supported self-service operation in this release**. Do not move it over `campaign-ledger.json`. Either restore a trusted pre-conflict snapshot into a new empty sibling directory, validate its ledger, and resume only in that new directory; or escalate with the exact paths, hashes, failed command, and error. No writer may re-enter the original campaign until that controlled recovery is complete.
5. After one validated work-and-snapshot cycle succeeds in the chosen workspace, archive the untouched original directory and recovery evidence according to campaign policy. That original directory is the rollback path; do not delete it merely because the first reopened command passed.

This terminal boundary is intentionally conservative: Ludis can prove which bytes it preserved, but it cannot infer which competing author was entitled to become canon.

### Recover output locks

Inspect every path the build intended to create: artifact or candidate ZIP, preview, audit, final ZIP, and approval receipt as applicable. A complete immutable artifact should be preserved and verified with the matching exporter. A missing or partial write remains evidence; do not overwrite it or reuse its output name.

After completing either [Check the PID on Windows](#check-the-pid-on-windows) or [Check the PID on macOS or Linux](#check-the-pid-on-macos-or-linux), remove each confirmed stale lock by its exact path—never a wildcard:

```powershell
Remove-Item -LiteralPath $lockPath
```

```bash
rm -- "$lock_path"
```

An export can reserve multiple output locks, so repeat the checks separately for each lock the command reported or left beside its intended write set. If a complete artifact exists, run `export_campaign.py verify` or `export_target.py verify` on that exact ZIP and keep it. For another build, choose an entirely fresh output name so its candidate, preview, audit, final, and receipt paths are all unoccupied.

A successful static target build means "constructed and statically validated." If Alchemy or Foundry rejects it, preserve the exact target version, bundle digest, import steps, error, and redacted loss report. Record the attempt without overwriting prior evidence:

```powershell
python -B scripts/record_import_observation.py output\target.zip output\target.import-observation.json --target foundry-v14 --target-version 14.365 --result failed --asserted-by "local GM label" --notes "redacted error summary"
```

A campaign-local observation cannot upgrade product-wide compatibility.

## Snapshot and restore

Create a snapshot:

```powershell
python -B scripts/snapshot_campaign.py C:\Games\MyCampaign
```

Copy the ZIP and printed SHA-256 to independent storage. To test recovery, extract into a new empty directory, compare the archive hash, inspect `snapshot-manifest.json`, and run `validate_ledger.py` on the restored ledger before replacing any live workspace.

A created archive is not a verified backup until restore has been exercised.

## Update

Git install:

```powershell
git -C "$env:USERPROFILE\.codex\skills\ludis-continuum" status --short
git -C "$env:USERPROFILE\.codex\skills\ludis-continuum" pull --ff-only
python -B "$env:USERPROFILE\.codex\skills\ludis-continuum\scripts\self_check.py"
```

Use the corresponding `.claude\skills` path for Claude Code. If the status command shows local changes, preserve or commit them before updating; do not overwrite them. Restart the host and repeat discovery/invocation verification.

Archive installs must be replaced with a fresh archive. Preserve local modifications separately and never store campaign data inside the skill directory.

## Remove the skill

First locate the exact skill directory and verify that it contains this repository. Prefer moving it to a dated backup location over immediate deletion.

Windows example:

```powershell
Move-Item -LiteralPath "$env:USERPROFILE\.codex\skills\ludis-continuum" -Destination "$env:USERPROFILE\Desktop\ludis-continuum-removed"
```

Restart the host and confirm the skill is no longer discoverable. For Claude Code, use the `.claude\skills` path.

## Campaign data cleanup

Removing the skill does not remove campaign workspaces. Campaign data may include:

- `campaign-ledger.json`;
- player candidates, previews, audits, approval receipts, and final exports;
- session notes and creative artifacts added by the user;
- `checkpoints/*.zip` archives;
- independent backups or synced copies.

Inventory those locations, decide retention with the campaign owner and participants, and remove copies according to their privacy and rights obligations. Ludis has no remote account, cloud database, telemetry store, or deletion API.

## Support boundary

Maintainers can investigate package and documentation defects. They cannot certify third-party host behavior, recover undisclosed campaign data, determine rights to source material, resolve table consent disputes, or guarantee that generated content is safe, balanced, original, or suitable.
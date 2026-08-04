# Troubleshooting

Preserve the exact symptom before changing anything: command, complete error,
host, operating system, plugin version, marketplace source, and whether the
failure occurs in a new task. Fix the cause before decorating the workaround.

## The marketplace does not appear

1. Run:

   ```powershell
   codex plugin marketplace list
   ```

2. Confirm that `collaborative-dynamics-mind` resolves to the GitHub release or the
   exact extracted release root you intended.
3. If it is absent, rerun the applicable `codex plugin marketplace add`
   command from [Installation](INSTALL-CODEX.md).
4. Restart the ChatGPT desktop app or Codex CLI, then reopen the plugin browser.

Do not hand-edit `config.toml` merely because the first command failed. An
authentication, Git, ref, path, or marketplace-schema failure needs its own
repair.

## The plugin appears but will not install

- Open the marketplace source and confirm the plugin name is
  `augment-of-mind`.
- For GitHub installs, confirm tag `v2.1.0` exists remotely.
- For ZIP installs, run `python .\verify-release.py .` from the extracted root.
- Preserve the install error. A bad manifest, missing asset, unavailable source,
  and workspace policy denial are different failures.

Safe stopping state: leave the plugin uninstalled. Do not copy partial folders
into Codex's cache.

## MIND is installed but a Faculty is missing

1. Confirm MIND is enabled in the plugin browser.
2. Start a new task or CLI session; installed skills are loaded at that
   boundary.
3. Invoke the exact handle, such as `$sensemaking`.
4. Verify the installed plugin version and inspect whether the expected
   `skills/<faculty>/SKILL.md` exists in the installed package.

If the file exists but the host does not expose it, record that as a discovery
failure—not evidence that the Faculty itself ran or failed.

## A result used the wrong Faculty

State the correction and the required transformation. For example:

```text
Correction: this is an evidence-quality problem, not an option-selection
problem. Preserve the objective and use Epistemic Regulation to reassess the
claims before recommending anything.
```

If semantically adjacent capabilities remain confused across varied requests,
report the smallest examples. That is useful evaluation evidence.

## Capability reminders

### The prompt-submit hook does not run

Open `/hooks` and review the exact installed MIND hook. Trust is bound to those
bytes; an update requires another review. Preserve Codex's trust or launch
error before changing plugin files.

### `associate_capabilities` is unavailable

Confirm the plugin's MCP server is enabled, Python can import the packaged
`mind_core`, the configured database exists, an active complete snapshot is
current, and the local embedding endpoint is reachable. If association remains
unavailable, continue from host-exposed capabilities and label the field
unavailable.

### The field is broad, empty, or semantically wrong

Inspect the contextual membrane first. Make transformation, situation, cues,
and example genuinely distinct; add a negative boundary for the nearest false
friend; split an overly broad meaning. Do not hide a broad result with top-K or
retune qualified geometry for one favorite query.

### Activation reports a stable identity conflict

Verify whether the transaction committed, then run a complete collision sweep.
Preserve unchanged admitted objects exactly. Give changed cards, views, and
relations new revision-consistent IDs. Do not repair conflicts one table at a
time.

## MIND Core

### The wheel will not install

- Confirm `python --version` is 3.11 or newer.
- Confirm the archive verifier passes and the wheel exists under
  `optional-core/`.
- Use `--no-index --find-links .\optional-core` to avoid silently substituting
  another package.
- Preserve pip's complete error before changing Python environments.

### `init` or `status` cannot open the database

- Resolve the exact path and confirm its parent directory exists and is
  writable by the current process.
- Stop another Core writer before retrying.
- Do not delete the database to make a lock error disappear.
- If migration or integrity validation fails, preserve the database and error
  and open a support issue without attaching private contents.

### A reminder query is unavailable

Core requires an active complete snapshot and a valid session capability. A
vector query also requires a matching qualified embedding profile and exact
dimensions. When vectors are unavailable, only a clearly labelled lexical
field may be returned. Core does not download a model or invent a replacement.

### The field exceeds the host budget

Canonical and compact representations preserve the same membership. If neither
fits the host-measured budget, Core returns `BUDGET_UNSATISFIED`; it does not
hide members with a top-K cutoff. Revisit the index design or host budget rather
than describing a truncated field as complete.

## Escalation packet

Include:

- observable symptom and expected outcome;
- exact version, host, OS, and install source;
- complete command or request shape with secrets removed;
- exact error and exit code;
- what changed immediately before the failure;
- checks already run and their results.

Continue through [Support](SUPPORT.md).

# Signal Loom customer guide

Signal Loom makes infographics from supplied research, reports, notes, and data. This guide takes the package from installation through removal. It is operational documentation for the `0.1.1` package, not a claim that every host/environment combination has been independently installed and exercised.

## Choose the product when

Use Signal Loom when you have supplied evidence and need an infographic whose claims, narrative, representations, outputs, and review state remain inspectable. Typical users include researchers, analysts, educators, communicators, product teams, and designers working with source-bound material.

Do not use it as an autonomous fact finder, generic image generator, HTML sanitizer, publishing bot, compliance certification system, or substitute for domain review.

## Install

Prerequisites:

- Codex or Claude Code;
- Git for clone-based installation;
- Python 3.10+ for initialization, validation, HTML inspection, tests, and packaging;
- a writable location for Loomfiles.

### Codex

Install the complete repository so `SKILL.md`, `knowledge/`, `assets/`, `schemas/`, `scripts/`, and `fallbacks/` stay together.

```powershell
$target = Join-Path $env:USERPROFILE '.codex\skills\signal-loom'
git clone https://github.com/Stunspot/signal-loom.git $target
python (Join-Path $target 'scripts\self_check.py')
```

Or in a Bash-compatible shell:

```bash
git clone https://github.com/Stunspot/signal-loom.git ~/.codex/skills/signal-loom
python ~/.codex/skills/signal-loom/scripts/self_check.py
```

Refresh the Codex skill inventory or start a new task. Confirm `signal-loom` is discoverable, then invoke `$signal-loom`.

### Claude Code

```powershell
$target = Join-Path $env:USERPROFILE '.claude\skills\signal-loom'
git clone https://github.com/Stunspot/signal-loom.git $target
python (Join-Path $target 'scripts\self_check.py')
```

Or:

```bash
git clone https://github.com/Stunspot/signal-loom.git ~/.claude/skills/signal-loom
python ~/.claude/skills/signal-loom/scripts/self_check.py
```

Claude Code's documented personal-skill location is `~/.claude/skills/<skill-name>/SKILL.md`. Use `/skills` to inspect discovery and `/signal-loom` to invoke it. If you created the top-level skills directory after Claude Code started, restart the host. See [Anthropic's skills documentation](https://code.claude.com/docs/en/slash-commands).

## Verify installation

Do not collapse these states:

| State | Evidence |
|---|---|
| Constructed | Source files exist in a development repository |
| Packaged | The installed directory contains the complete package and `self_check.py` passes |
| Installed | The package occupies the intended host path |
| Discoverable | The host reports `signal-loom` in its current inventory |
| Invoked | The host actually loads the skill for a request |
| Healthy | The skill creates coherent state and its applicable checks pass |

Run:

```bash
python scripts/self_check.py
python -m unittest discover -s tests -v
```

Then invoke the skill with one small, non-sensitive source and ask it to initialize a Loomfile, inventory the source, draft five beats, and stop before publication. Inspect the files and run:

```bash
python scripts/validate_loomfile.py PATH_TO_LOOMFILE
```

The validator's pass covers its implemented state contract only. It does not prove that the host followed the skill faithfully or that generated content is correct.

## Begin successfully

A good brief supplies:

- the actual source materials and their authority;
- the audience and intended change in understanding or action;
- the required outputs and named platforms;
- time, brand, format, privacy, and accessibility constraints;
- whether to create a Loomfile or resume one;
- whether current external research is separately authorized.

Example:

```text
Use $signal-loom with the supplied report and CSV. The audience is city budget staff; the intended change is understanding which maintenance delays create compounding cost. Build a semantic web infographic only. Treat the report as dated to 2026-06-30, do not fetch outside evidence, do not publish, and leave disputed claims visibly unresolved.
```

Signal Loom should return or create an inspectable project—not merely a polished image. Expected outputs include a source manifest, brief, claim ledger, story spine, visual plan, web artifact, diagnostic record, and explicit unproved layers.

## Representative workflows

### Report to semantic infographic

1. Inventory the report and record a hash.
2. Extract source-linked claims and classify currentness.
3. Shape a five-to-nine-beat narrative.
4. Assign prose, diagram, chart, interaction, or omission.
5. Build `output/web/index.html` with essential meaning available without JavaScript.
6. Run the static inspector and record its exact limit.
7. Conduct rendered, keyboard, zoom/reflow, contrast, and screen-reader reviews separately.

### Existing infographic diagnostic

Supply the artifact source or an authorized image description. Signal Loom determines which evidence layer is present, identifies purpose and audience, and returns three highest-leverage corrections plus secondary findings. Source-only inspection must not be described as rendered visual review.

### Web story to carousel

Distribution runs only when requested. The carousel is reconstructed as a six-to-fourteen-panel reveal sequence with per-panel copy, visual direction, claim ids, source note, alt text, and transition purpose. It is not a crop stack of the webpage. The claim set, uncertainty, and causal order must remain consistent.

### Resume reviewed work

Open the existing Loomfile. Before changing consequential reviewed state, create a snapshot under `checkpoints/snapshots/` or a versioned copy. Record decisions and authority changes; re-run every review invalidated by the change.

## Configuration and state

`project.yaml` is JSON-compatible data despite its filename. Its key state fields are:

- `loomfile_version`: currently `0.1.0`;
- `stage`: `intake`, `spined`, `planned`, `built`, `reviewed`, or `approved_for_export`;
- `authority_status`: `draft`, `reviewed`, or `approved`;
- `publication_status`: always `manual_only` in this product;
- `requested_outputs`: one or more of `web`, `carousel`, or `platform`.

These are independent. `approved_for_export` requires human `approved` authority. Neither means published.

Claim records in `state/claims.jsonl` use:

- status: `sourced`, `inferred`, `illustrative`, `missing`, `stale`, or `disputed`;
- currentness: `timeless`, `dated`, or `current-sensitive`;
- a valid source id and locator for sourced claims;
- an `as_of` value for current-sensitive sourced claims.

At `approved_for_export`, unresolved `missing`, `stale`, or `disputed` claims block validation. Schema files document intended structure; the current validator implements a focused subset rather than full JSON Schema evaluation.

## Deterministic tools

### Initialize

```bash
python scripts/init_loomfile.py DESTINATION --title "Title"
```

The destination must be missing or an empty, non-symlink directory. The initializer never merges into an existing project.

### Validate

```bash
python scripts/validate_loomfile.py LOOMFILE
```

Checks required paths, state enums, publication boundary, source containment and hashes, claim statuses and linkage, and stage-dependent artifacts. `--skip-hashes` intentionally weakens the check and should be recorded when used.

### Inspect HTML

```bash
python scripts/inspect_infographic_html.py LOOMFILE/output/web/index.html
```

Checks a bounded set of static HTML properties: semantic regions, language, title, viewport, one `h1`, heading order, alt presence, several dangerous element/attribute patterns, social metadata warnings, and reduced-motion treatment. It does not render or sanitize the document.

### Package

```bash
python scripts/package_loomfile.py LOOMFILE OUTPUT.zip
```

The output must resolve outside the Loomfile. The packager validates the source state, refuses symbolic links and several secret-like names, preserves required empty directories, and builds a one-root archive at a temporary path. It hashes the exact bytes written to each file entry and places the generated release manifest inside the ZIP; it does not alter the Loomfile's existing `review/release-manifest.json`. It then extracts and validates the archived Loomfile, so a registered source changed after pre-validation is rejected rather than exposed. Only a revalidated ZIP is linked at the requested path. Invalid archived state or write failure removes the unique temporary artifact and preserves the project. A final-link interruption is commit-ambiguous: the packager never deletes the destination automatically, because another process may own or replace that path. Inspect any surviving ZIP; if its embedded manifest validates, keep it. Otherwise choose a new path, or delete the exact invalid output only after confirming custody. An existing or concurrently created output is never overwritten. Its denylist is not a content scanner.

## Troubleshooting and recovery

### The host cannot find the skill

Confirm the exact path ends in `signal-loom/SKILL.md`, not `signal-loom/signal-loom/SKILL.md`. Confirm supporting directories sit beside `SKILL.md`. Refresh or restart the host and inspect its inventory. File presence proves installation, not discovery.

### Invocation loads but produces generic copy

Invoke the skill explicitly. Include actual sources, audience, intended change, and requested output. Ask for a Loomfile and claim ledger. If the host cannot read supporting resources, the package may be incomplete or outside its allowed file scope.

### Python is unavailable

Use `fallbacks/universal-copy-paste-workflow.md`. Create copy-ready state and HTML, label initialization, hashing, parsing, tests, packaging, rendering, and archive inspection `unexecuted`, and preserve an exact later command list.

### A tool fails

Record the failed command and error, what remains trustworthy, evidence not produced, smallest safe retry, and exact re-entry condition. After an unchanged repeated failure, change route or stop. `fallbacks/degraded-capability.md` is the governing recovery reference.

### Source hash mismatch

Treat it as a content change, not a validator nuisance. Establish whether the new bytes are authoritative, update the source entry deliberately, revisit dependent claims and representations, and invalidate downstream reviews that relied on the old hash.

### HTML inspector reports a problem

Fix source HTML, re-run the inspector, then still perform rendered and accessibility reviews. Never suppress or relabel a failure to obtain a green transcript.

### Packaging refuses content

Remove credentials and secret-like artifacts from the Loomfile. Inspect the complete archive candidate; the filename denylist is deliberately conservative and incomplete. Choose a new ZIP path outside the Loomfile if the requested archive already exists or resolves inside the project.

### Packaging was interrupted during the final link

Do not rerun against or delete the same output path automatically. If the path is absent, retry normally. If it exists, its ownership is unknown: another process may have replaced it. Inspect without modifying it:

```bash
python -m zipfile -l OUTPUT.zip
python -m zipfile -e OUTPUT.zip EMPTY_DIRECTORY
python scripts/validate_loomfile.py EMPTY_DIRECTORY/LOOMFILE_NAME
```

Compare the extracted project name, source manifest, source hashes, and embedded `review/release-manifest.json` with the intended Loomfile. If the archive is valid and expected, keep it. If it is different or uncertain, leave it untouched and package to a new filename. Delete only after confirming custody. A failed retry against the existing path is expected overwrite protection, not proof that the surviving archive is yours.

## Privacy, storage, and network behavior

Signal Loom creates no service account and contains no telemetry. The included Python scripts have no network code and operate on explicit local paths. The Loomfile holds whatever sources, claims, outputs, and review records you place inside it.

The AI host is a separate boundary and may send prompts or files to its configured provider. Apply the host's data controls and your organization's policy. Do not supply sensitive material merely because Signal Loom's helper scripts are local.

URLs are treated as supplied data unless a separate fetch or research action is authorized. Imported HTML is parsed without script execution by the included inspector. Do not open untrusted output in a privileged browser profile or host it publicly before security review.

## Security boundaries

Signal Loom does not claim to sanitize HTML, detect all secrets, verify dependencies, prove content safety, or establish professional fitness. Its default artifact pattern avoids required external runtimes. If a remote dependency is explicitly authorized, record the exact URL, version, purpose, license implications, integrity metadata where applicable, and failure behavior.

See [SECURITY.md](../SECURITY.md) for reporting and safe handling.

## Known limitations

- Quality depends on source quality, host capability, model behavior, and human review.
- Static validators cover named rules, not rendered behavior or truth.
- Schemas are shipped as reference contracts; `validate_loomfile.py` does not execute full JSON Schema validation.
- The initializer does not migrate or merge projects.
- The packager's secret-like filename denylist is incomplete and does not inspect file contents.
- Safe final-path creation requires the archive destination filesystem to support same-directory temporary files and hard links; choose another local destination if that operation is unavailable.
- No publication, hosting, social posting, media buying, or account login is performed.
- Current platform constraints and current-sensitive facts require fresh authorized evidence.
- Accessibility requires separate rendered, keyboard, zoom/reflow, contrast, and assistive-technology testing.
- Security-sensitive and regulated uses require appropriate specialist review.

## Update, remove, and clean up

For a Git clone, run `git pull --ff-only` inside the installed skill directory, then repeat package, discovery, invocation, and health checks. Inspect release notes and back up reviewed Loomfiles before adopting state-contract changes.

Remove only the resolved, exact install directory. On Windows, typical personal paths are `%USERPROFILE%\.codex\skills\signal-loom` and `%USERPROFILE%\.claude\skills\signal-loom`; on Unix-like systems they are `~/.codex/skills/signal-loom` and `~/.claude/skills/signal-loom`.

Removal does not delete projects created elsewhere. Inventory Loomfiles, output folders, archives, caches created by your host, synchronized copies, and backups separately. Ordinary deletion is not guaranteed secure erasure.

## Provenance, evidence, and terms

`SKILL.md` and `knowledge/operating-doctrine.md` govern product behavior. `knowledge/infographic-toolkit-v2-canonical.md` holds adapted faculty bearings. `manifest.json` identifies package version, declared hosts, runtime, publication mode, and license.

[VALIDATION.md](../VALIDATION.md) distinguishes performed checks from unproved layers. The [MIT license](../LICENSE.md) governs the software. You remain responsible for rights in inputs and outputs, confidentiality, platform rules, factual review, accessibility, and publication approval.

## Support and contribution

Report reproducible public defects through [GitHub Issues](https://github.com/Stunspot/signal-loom/issues). Follow [SUPPORT.md](../SUPPORT.md) and [CONTRIBUTING.md](../CONTRIBUTING.md). Never attach credentials, private sources, or proprietary Loomfiles to a public issue.
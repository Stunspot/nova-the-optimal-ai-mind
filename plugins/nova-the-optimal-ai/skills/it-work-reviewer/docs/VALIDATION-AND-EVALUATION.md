# Validate the package and interpret its evidence

This page is for release owners, installers, and reviewers who need to check case structure, package integrity, or the behavioral evaluation contract. Run commands from the release root unless a step says otherwise.

## Validate a case file

```text
python scripts/validate_case_file.py path/to/case.json
```

Expected result for a structurally valid case:

```text
PASS path/to/case.json
```

A failure names the missing key, invalid controlled state, incorrect array type, invalid disposition, or empty next action. The validator does not verify factual truth, authorization, execution, or repair success.

## Validate release integrity

```text
python scripts/validate_release.py .
```

Expected result:

```text
PASS <release-path> (<count> manifested files)
```

The release validator checks required files, skill frontmatter, package-relative runtime paths, text decoding, JSON-compatible data files, and SHA-256 inventory agreement with `release-manifest.json`.

If it reports that the manifest does not match, first determine whether files were intentionally changed. Do not regenerate the manifest merely to hide an unexplained addition, deletion, or modification.

Release maintainers may regenerate the inventory after an authorized, reviewed change:

```text
python scripts/validate_release.py --write-manifest .
```

Run validation again without `--write-manifest` afterward.

## Understand the behavioral suite

`evals/` uses the canonical `cd-augment-eval/v1` contract. Ten isolated cases examine:

- safety, data, privacy, and authority boundaries;
- causal discrimination under sparse or changing evidence;
- rollback and source applicability;
- managed-device security custody;
- resumable state;
- degraded operation without tools;
- useful handoff;
- completion based on the original failure envelope.

The suite must run through a compatible evaluation harness with a recorded subject adapter, judge adapter, host, model, context, package fingerprint, and trial count. The package does not include a standalone behavioral runner.

## Interpret results conservatively

A structural pass proves selected package properties. It does not prove that a model will follow every instruction, that a host installed the skill, or that a physical repair works.

A behavioral result is evidence only for its exact package fingerprint and runtime. Preserve invalid runs as invalid, partial criteria as partial, reviewer disagreements as disagreements, and environment failures as environment failures. Do not average a safety blocker into a high overall score.

## What was and was not verified

The current v0.1.3 package passes its one-root skill manifests, Codex-to-Claude byte parity, portable family verifier, safe archive topology, documentation link check, and fresh extraction rerun. Those are static package results; no new live-host or behavioral run was claimed for the presentation repair.

The following behavioral statements apply to the original v0.1.0 build and its exact recorded fingerprint:

- the working package, customer copy, and fresh ZIP extraction passed release and shared package validation;
- three valid example cases passed the case validator, and a malformed fixture failed as required;
- the canonical ten-case evaluation contract validated;
- multiple one-trial local context runs were retained;
- an exact-fingerprint release run completed, was independently reviewed, and its evidence seal verified;
- customer and ZIP-extracted files matched byte-for-byte at release time.

The local behavioral evidence showed both demonstrated cases and safe but incomplete responses across stochastic samples. One completion-case judge result conflicted with the evidence it cited by penalizing a text-only Agent for not physically performing a future verification test. The raw result was preserved, and the reviewer disposition was `REVIEW_PASS_WITH_CONDITIONS`.

Not tested during the build:

- target-host installation and fresh-task discovery;
- physical repair or device commands;
- credentials or remote-management access;
- current vendor-portal procedures;
- production or organizational environments;
- broad cross-model reliability;
- representative-user or assistive-technology use of the documentation.

## Release decision vocabulary

- `READY`: evidence supports the bounded claim with no unresolved release condition.
- `READY_WITH_RESIDUAL_RISK`: artifact release is supportable with named residual risk.
- `INSUFFICIENT_EVIDENCE`: the requested broader claim outruns available evidence.
- `NOT_READY`: a material product or verification defect blocks the claim.
- `BLOCKED_BY_ENVIRONMENT`: a required check could not run because of the environment.

The build-side verification decision for universal behavioral reliability remained `INSUFFICIENT_EVIDENCE`. That does not erase the validated customer artifact; it limits what may be claimed about behavior across hosts and models.

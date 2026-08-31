---
name: nova-operations
description: "💠 Nova setup, continuity, status, update, and recovery."
---

# Keep Nova operational without making the user become IT

Use this skill when the user asks to set up Nova's data estate, inspect persistence or product status, upgrade an earlier estate, diagnose a Nova-specific failure, run one of Nova's durable services, use Worldline, update Nova Free, roll back, remove it, or understand where Nova stores data. Do not intercept ordinary work or require onboarding before first value.

## Inspect before changing

Run the read-only status path first:

```text
python -B -X utf8 scripts/nova_estate.py status
```

Status reports Cognitive Continuity read support and mutation support separately, then reports canonical Commonplace verification independently from derived Concordance freshness or availability. Use `doctor` when a symptom suggests broken selectors, an unavailable Continuity workspace, a missing service directory, or package damage. Preserve the exact symptom and distinguish package presence, host discovery, estate configuration, service support, and model behavior. Never reset the harness, delete unrelated plugins, or erase state as a diagnostic shortcut.

## Set up the optional Nova estate

Persistent Nova-owned state is optional for ordinary work and required before Nova writes durable continuity, project, people, reminder, or deliberate general-note and capture records. Run `plan` with the intended absolute root and show its proposed root, selectors, directories, and existing-state result. Default to the operating system's per-user application-data location outside `.codex`; accept another customer-controlled absolute path.

Obtain explicit confirmation immediately before `init`. Initialization is transactional: it publishes the estate only after Cognitive Continuity, an empty generation-zero Commonplace, a bound empty Concordance, and every registry artifact are complete, and it removes staging residue if any service initialization fails. It never overwrites an existing root, selector registry, or Continuity workspace.

One exception repairs the known Nova Free v1.0.0 macOS failure footprint automatically. If the root contains only the exact empty Corkboard, Dunbar, and Project Management directories left before Continuity rejected initialization—and no registry, manifest, Continuity manifest, or unknown file—status reports legacy_1_0_0_partial and a retry replaces that revalidated empty residue with the completed estate. Any unknown content stops repair and remains untouched.

```text
python -B -X utf8 scripts/nova_estate.py plan --root "<absolute root>"
python -B -X utf8 scripts/nova_estate.py init --root "<absolute root>" --user "<opaque local user id>"
```

A nondefault root also receives one small platform-configuration pointer so a later GUI-launched agent can discover the current estate without a shell profile. The pointer contains no user records and has no selector authority; the estate registry must corroborate it. The platform-default root needs no duplicate pointer.

On Windows only, the user may separately request the optional convenience flag `--apply-user-environment`. It copies the registry selectors into the current user's environment and requires a fresh desktop-app process before those ambient values appear. Never pass that Windows-only flag on macOS or Linux. Nova's own launcher does not require global environment variables or a restart.

## Run stateful Nova services

The registry at `estate/path-selectors.json` is the correctness path. Use the single launcher below for Cognitive Continuity, Dunbar, Corkboard, Project Management, and Commonplace. It removes inherited Nova selectors, injects one exact registry snapshot, and invokes the bundled script directly without a shell.

```text
python -B -X utf8 scripts/nova_estate.py run continuity -- <continuity arguments>
python -B -X utf8 scripts/nova_estate.py run dunbar -- <dunbar arguments>
python -B -X utf8 scripts/nova_estate.py run corkboard -- <corkboard arguments>
python -B -X utf8 scripts/nova_estate.py run project-management -- <project arguments>
python -B -X utf8 scripts/nova_estate.py run commonplace -- <commonplace arguments>
```

Add `--root "<absolute root>"` before the service name only when deliberately addressing an explicit estate rather than the current discovered estate. Do not invoke the bundled service scripts directly for Nova-owned state: doing so would make inherited process environment part of correctness again.

Commonplace 0.2.0 exposes 25 commands. Estate initialization and ordinary `rebuild` remain lexical and require no model. Semantic or hybrid retrieval is an explicit post-initialization choice using the customer's loopback Ollama embedding service; no model is bundled or activated automatically. `federated-search` has fixed read-only adapters for Dunbar, Corkboard, Dennis, and Continuity. `history` and `as-of` read authenticated retained state. Promotion commands create and export non-executable proposals only; they never write a target owner. Installation, estate setup, and retrieval grant none of these commands mutation authority.

Before persistence setup, confirm that Python 3.10 or newer is already available to the harness. Do not silently install or replace Python. If a suitable runtime is unavailable, ordinary Nova work remains available. State that deterministic diagnostics and persistent Worldline, Project Management, Dunbar, Corkboard, Commonplace, and Concordance operations are unavailable; do not counterfeit a save or project record.

## Upgrade an existing estate

A status of `upgrade_required` means the registry lacks a required selector. Run `plan` against the same root, show the proposed change, obtain explicit confirmation, then run:

```text
python -B -X utf8 scripts/nova_estate.py upgrade --root "<existing absolute root>"
```

For the known additive 1.0.3 to 1.0.4 migration, the state-sensitive plan names only the selectors and empty service roots that are actually missing. Upgrade stages and verifies an empty canonical Commonplace and its rebuildable Concordance, updates the environment helper and product-owned service metadata, then publishes the registry as its commit point. A historical `nova-data-estate/v1` manifest remains byte-for-byte untouched; Nova Operations writes the additive `estate/nova-emergent-services.json` sidecar instead. Existing non-null `MIND_CORE_DATABASE` and `MIND_HOOK_RECEIPT_DIRECTORY` values remain unchanged in legacy registry and helper metadata but are never forwarded by the Nova service launcher. New estates keep both values null. Upgrade establishes the nondefault-root locator only when absent; a valid preexisting locator is corroborated and preserved byte-for-byte. It optionally applies Windows user-environment convenience only when that flag was explicitly requested. It does not move, merge, initialize over, or delete existing service data. A conflicting selector, pre-existing unregistered Commonplace or Concordance target, invalid core selector, malformed product-service sidecar, or current-estate locator stops before mutation and remains unchanged.

## Serve Worldline

Resolve one project key under the Cognitive Continuity contract before invocation. Preserve the winning source tier in visible work. The compatibility command remains:

```text
python -B -X utf8 scripts/nova_estate.py worldline --mode <resume|status|checkpoint|inspect> --project "<project key>" --task "<live task>" --user "<user id>"
```

It uses the same registry-backed launcher. Worldline never writes; a checkpoint remains ephemeral. Project purpose and delivery governance remain owned by `dennis-stratton-project-management`.

## Update, roll back, or remove

Use the package's `SUPPORT.md`, `START-HERE.md`, and `CHANGELOG.md`. Record the active product version, marketplace source, plugin state, and Nova data root before changing them. Preserve user data and other capabilities by default. Replacing plugin bytes, changing the current-estate pointer, applying Windows environment convenience, upgrading stores, deleting stores, and removing external exports are separate actions requiring separate authority.

Finish with the product result, observed evidence boundary, and smallest next move. Keep internal diagnostics backstage unless they help the user recover.
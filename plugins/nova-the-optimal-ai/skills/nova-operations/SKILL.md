---
name: nova-operations
description: "💠 Nova setup, continuity, status, update, and recovery."
---

# Keep Nova operational without making the user become IT

Use this skill when the user asks to set up Nova-owned persistent data, inspect persistence or product status, diagnose a Nova-specific failure, run a bundled durable service, use Worldline, update the Free edition, roll back, remove it, or understand where Nova stores data. Do not intercept ordinary work or require onboarding before first value.

## Inspect before changing

Run the read-only status path first:

    python -B -X utf8 scripts/nova_estate.py status

Use doctor when a symptom suggests broken selectors, an unavailable Continuity workspace, a missing service entrypoint, or package damage. Preserve the exact symptom. Keep package presence, host discovery, estate configuration, service support, and model behavior separate.

## Configure the optional Nova estate

Ordinary Nova work requires no estate. Persistent Continuity, Dunbar, and Corkboard writes require one customer-controlled root outside .codex.

First plan the exact root:

    python -B -X utf8 scripts/nova_estate.py plan --root "<absolute root>"

Show the proposed root, selectors, directories, and existing-state result. Obtain explicit confirmation immediately before init:

    python -B -X utf8 scripts/nova_estate.py init --root "<absolute root>" --user "<opaque local user id>"

Initialization is transactional. It publishes only after Cognitive Continuity and the registry artifacts are complete. It does not overwrite an existing root, registry, or Continuity workspace. A nondefault root receives a small platform configuration pointer; that pointer contains no user records and has no selector authority.

The optional --apply-user-environment flag is Windows-only convenience and requires explicit request. The registry-backed launcher does not require global environment variables or a restart.

## Run stateful services through the registry

The registry at estate/path-selectors.json is the correctness path. Use the launcher so inherited process variables cannot silently redirect Nova-owned state:

    python -B -X utf8 scripts/nova_estate.py run continuity -- <continuity arguments>
    python -B -X utf8 scripts/nova_estate.py run dunbar -- <dunbar arguments>
    python -B -X utf8 scripts/nova_estate.py run corkboard -- <corkboard arguments>

Use --root before the service name only when deliberately addressing an explicit estate.

Worldline remains read-only:

    python -B -X utf8 scripts/nova_estate.py worldline --mode <resume|status|checkpoint|inspect> --project "<project>" --task "<task>"

A Worldline checkpoint is a view, not a save receipt.

Before persistent setup, confirm Python 3.10 or newer is already available. Do not silently install or replace Python. If it is unavailable, ordinary Nova work remains available and persistent service operations are unavailable; never counterfeit a save.

## Upgrade and recovery

Upgrade preserves existing records and extra selectors while refreshing the Free edition binding:

    python -B -X utf8 scripts/nova_estate.py upgrade --root "<existing absolute root>"

Plan, show the proposed change, and obtain explicit confirmation before mutation. An estate created by a larger Nova edition may contain extra selectors such as DENNIS_PROJECT_HOME. Free Nova accepts and preserves them but does not inject, create, or claim their service.

Read references/estate-contract.md before initialization, upgrade, recovery, export, rollback, or removal. Never delete user data merely because a plugin is removed. Backups and exports must go to a user-chosen destination outside the active Nova selector boundary.

Finish with the useful result, the observed state, and one exact re-entry condition if a guarantee remains unavailable.

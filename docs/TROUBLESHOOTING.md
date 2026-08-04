# Troubleshooting

Keep the full error before changing anything. Establish what happened before deciding what to reinstall.

## The harness could not install the attached ZIP

Confirm that the complete Nova + MIND release ZIP was attached and accessible to the task. Ask the harness to explain the exact installation boundary it reached.

If the host cannot install a package from an attachment, extract the ZIP and use [Manual Codex installation](INSTALL-CODEX.md).

## The installer finds an older Nova, MIND, or database

It stopped to avoid replacing something you may care about. Identify the exact older Nova or MIND plugin and follow [Upgrade](UPGRADE.md). Remove only the installation you have deliberately chosen to replace. Do not reset Codex or remove unrelated plugins.

## Python is missing or too old

The manual installer and local MIND reminder runtime require Python 3.11 or newer. Confirm the Python version in the same environment performing the installation, then rerun the installer.

## The plugins installed but Nova or a skill is missing

Confirm that both **Nova the Optimal AI** and **MIND by Collaborative Dynamics** are enabled, then start a new task. Codex discovers installed skills at that boundary.

Ask the harness to report which plugin and skill handles it discovered. If Nova remains absent, preserve that report and the host version. A package folder on disk does not prove host discovery.

## The hook or reminder field is unavailable

Open `/hooks` and confirm the MIND prompt-submit hook is present and trusted. Then confirm Python and the configured MIND database are available.

If you see `MIND · ARM'S REACH UNAVAILABLE`, preserve the failure code and receipt. Nova can still use capabilities that Codex exposes; the missing piece is the local semantic reminder field.

## A reminder seems too broad or misses something

Record the task context, nearby handles returned, active snapshot, and whether the result came from a relation or semantic match. The included profile is structurally checked but still undergoing broader behavioral qualification.

## A portable Claude ZIP will not upload

Confirm the archive has one matching top-level folder and a direct `SKILL.md`. A ZIP can be structurally sound while a host still rejects it because of policy or version.

## Ask for help with useful evidence

Include the package version, exact host and operating system, complete error, discovered plugin state, what changed immediately before the failure, and the smallest safe reproduction. Redact private prompts, credentials, and sensitive paths.

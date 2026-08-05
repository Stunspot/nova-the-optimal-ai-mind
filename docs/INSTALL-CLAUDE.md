# Use Nova skills in a Claude-compatible harness

Nova + MIND Free is integrated and verified primarily as a Codex package. The release also contains one portable ZIP for each included skill under `claude/zips/`.

## Install a portable skill

Give the skill ZIP to the harness and ask it to install and enable the skill. If the host has a dedicated skill-management interface, uploading the ZIP there is equivalent. Start a new conversation after installation so the host can discover it.

Each ZIP has one matching top-level folder with its `SKILL.md` and required local resources.

## Recreating more of Nova

You may install Nova, the MIND integrator, its sixteen Faculties, Capability Promotion, both TestForge skills, Promptcraft, and whichever specialists you want. The individual packages preserve their own contents, but this release does not claim that a Claude-compatible host reproduces Codex's shared MIND database, prompt hook, automatic capability reminders, or fully integrated Nova-with-MIND behavior.

In other words: the skills are portable; the complete cognitive runtime remains Codex-first until an equivalent host integration is exercised.

## If a ZIP is rejected

Preserve the host's error. Confirm that the archive contains one matching top-level folder and a direct `SKILL.md`. A structurally correct skill ZIP can still be declined by a host policy or version; those are different failures.

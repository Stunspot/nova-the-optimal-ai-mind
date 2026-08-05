# Use Nova skills in a Claude-compatible harness

Nova + MIND Free is integrated and verified primarily as a Codex package. The current repository ZIP contains each included skill as a self-contained source folder under `plugins/*/skills/`.

## Install a portable skill

Select the skill folder you need and package that folder as a ZIP whose single top-level directory has the same name and contains a direct `SKILL.md`. Give that ZIP to the harness and ask it to install and enable the skill. If the host accepts folders directly, the source folder is equivalent.

Maintainers can run `python -X utf8 tools/build_release.py` to produce prebuilt per-skill archives under `dist/claude/zips/`.

## Recreating more of Nova

You may install Nova, the MIND integrator, its sixteen Faculties, Capability Promotion, both TestForge skills, Promptcraft, and whichever specialists you want. The individual packages preserve their own contents, but this source revision does not claim that a Claude-compatible host reproduces Codex's shared MIND database, prompt hook, automatic capability reminders, or fully integrated Nova-with-MIND behavior.

In other words: the skills are portable; the complete cognitive runtime remains Codex-first until an equivalent host integration is exercised.

## If a ZIP is rejected

Preserve the host's error. Confirm that the archive contains one matching top-level folder and a direct `SKILL.md`. A structurally correct skill ZIP can still be declined by a host policy or version; those are different failures.

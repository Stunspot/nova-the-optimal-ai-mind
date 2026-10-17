# Use a bounded tool only when it advances the question

Discover a selected workbench with `python scripts/osint_bridge.py --workbench HOME discover`. Explicit selection does not fall back to another home when missing. The bridge can otherwise use `NOVA_OSINT_HOME`, `NOVA_DATA_ROOT/integrations/osint`, the maintained Windows estate location, or the default user data home. Discovery of a directory is not proof that every tool or provider works.

Maigret reports candidate handles, not people. Recursion is off unless explicitly requested; a shared username is not an identity match. theHarvester's named P0 profile queries providers rather than actively scanning the target. Shodan reads existing indexed records, requires its process API key and may consume entitled credits. SpiderFoot loads a narrow reviewed module profile with selected HTTPS providers and request/time budgets. These limits describe the bundled adapter, not all behaviors or accuracy of upstream projects.

Before a live command, confirm the authorized target, purpose, boundary and any cost. Dry-run the command when its scope is not obvious. Do not execute live investigations against people or infer permission from a public data label. Stop provider/tool failures at a useful boundary and continue ordinary source work.

For supported command names use `python scripts/osint_bridge.py run --help` and the workbench's `help TOOL` or `list`. A missing executable produces an unavailable/failed native result. Retain native stdout/stderr/report files and receipt; success only means the selected command returned its declared status. Secrets belong in process environment/configuration, not case prose.

Attach an existing run with `attach-run --case CASE --run RUN --output NEW-CASE`. All final case/report paths are preflighted. No entity, claim or relation is resolved by attachment. Review the original record index and report source; a truncated observation summary does not replace the native report. New receipts bind top-level report bytes; legacy receipts are visibly unverified snapshots. Partial runs remain partial, and report subdirectories are explicitly outside the attachment.

[Setup](osint-setup.md) is optional. Blackbird remains excluded; this update does not activate it or revive unrelated source-only tools.

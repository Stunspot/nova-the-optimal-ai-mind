# Project Bridge

Read [the current workspace guide](../workspace/WORKSPACE-GUIDE.md) for the local read-only reader. Browse project posture, purpose, next move, the active route and linked evidence; use Refresh project after native state changes. The bridge keeps viewing preferences and comparison snapshots separately from canonical project records. Carry authorized project edits through the project-control workflow and validate the saved record before treating the changed view as current. Structural validity is not delivery or owner acceptance.

In a Nova edition, open it from the sibling Nova Operations skill with `python -B -X utf8 scripts/nova_estate.py run project-bridge -- <arguments>`. This selects the same registry-backed estate as `run project-management`. For standalone Dennis, launch `scripts/project_bridge.py --store <resolved-estate>` with Python 3.10+; `--no-browser` prints the local URL. The own-location wrappers preserve that standalone launch path.

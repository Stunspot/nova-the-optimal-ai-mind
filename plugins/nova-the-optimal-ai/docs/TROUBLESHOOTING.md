# Troubleshooting

Preserve the exact symptom before changing anything: product version, package hash, host and operating system, installation route, command or request, complete sanitized error, and whether the failure concerns package presence, discovery, enabled state, restart state, invocation, optional estate configuration, tool availability, or behavior.

## Plugin not found

Confirm the local marketplace path points to the extracted codex directory. Inspect codex plugin marketplace list and codex plugin list as JSON. Do not delete other marketplaces as a shortcut. Open a new task after catalog changes.

## Nova responds but a specialist is absent

Inspect the installed plugin's skills directory and compare it with LOADOUT-MANIFEST.json. A named skill is not proof that the host discovered or invoked it. Preserve the missing handle and one minimal activation request.

## Persistent services unavailable

Ordinary Nova work should continue. For stateful services, confirm Python 3.10 or newer is already available, then invoke:

    $nova-operations Show status for my existing Free Nova estate. Read only; do not initialize, repair, or move anything.

Do not silently install Python, initialize a new estate, or move a selector to make a read request pass.

A missing estate is not corruption. To create one, name an absolute customer-controlled root and invoke:

    $nova-operations Plan Free Nova estate initialization at <absolute path>. Show every proposed selector and write. Do not execute until I approve.

A registry error, unsupported mutation filesystem, and missing service entrypoint are different failures. Preserve the exact status or doctor output before requesting repair.

## Upgrade collision

If another Nova or MIND is installed, stop before replacement. Record its selector, version, and any data locations. Follow the [upgrade guide](UPGRADE.md). Never infer that uninstalling a plugin deletes its database, hook configuration, model, or user records.

## Verification mismatch

If you have the source repository, rebuild and rerun `tools/verify_package.py` against the extracted package directory. The extracted customer package is not a buildable source checkout; without the repository, compare the supplied archive digest and `SHA256SUMS.txt`, preserve the failing artifact, and report the mismatch. A static PASS does not settle fresh-host behavior. Preserve the failing artifact and digest instead of editing a built ZIP in place.

## Scope or root conflict

Keep the exact diagnostic. User and agent scope selectors are exact: `Nova` and `nova` can name different scopes. A `scope_denied` result does not establish an empty or lost store. Use the identity recorded by the owner.

For `nova_root_mismatch`, inspect the estate locator, registry and caller launch context read-only. Use the registry-backed Nova Operations route; a direct caller must be launched with the selected registry's values. Correct only the authorized caller context, without globally changing environment settings or initializing another estate. A timeline occurrence and represented project state are different: a project-resumption view may accurately report `project_scope_unrepresented` while returning retained events. Do not turn an event into a completion or project-state claim.

## An app opens empty or cannot save

Check the app title and displayed work folder. An empty view can mean a different location was selected. Use its **Work folder** chooser when supplied, or the documented `--data-home` launch option. Keep the original folder intact. Confirm the selected folder is writable before relying on a save, then reload and check that the work returns.

If another window changed the saved state, preserve your working copy with backup/export before reloading and reconciling. If a document has no extractable text, keep its original and add a reading note or use an appropriate OCR tool; a scan is not an empty source. Ordinary file support differs by task. The [workspace guide](VISUAL-WORKSPACES.md) links each app's supported flow.

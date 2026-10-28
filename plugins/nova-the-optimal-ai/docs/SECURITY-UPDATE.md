# Update Nova Free 4.3.1

The 27 October 2026 maintenance repair keeps version 4.3.1 and uses build `nova-free-4.3.1-boundary-repair-20261027-r1`. Reinstall the complete current package to receive the repaired files. It fixes PDF dependency gaps, enforces TLS verification and receipt-time response limits across Maigret transports, and restores ordinary combined note search without optional semantic setup. Existing saved work and the skill roster stay intact.

## Repair an existing Observatory environment

Updating Nova does not update a separately installed Python environment. If you already use Observatory's optional OSINT workbench, run this from the updated Observatory skill folder before the next Maigret query:

```text
python scripts/upgrade_osint_security.py --home "PATH_TO_EXISTING_OSINT_HOME"
```

Use the existing workbench home. This requires uv, package-index access and its existing isolated Maigret environment. It backs up recognized previous entrypoints and adapters under `security-backups`, preserves configuration, credentials and reports, and makes no provider query. Success reports `upgraded: true`, `tls_verification: true`, `body_limit_bytes: 16777216`, and both native-decoding fields as false. If it reports an unrecognized modified adapter, preserve that file and have Nova inspect the difference; do not delete the check or reset the workbench.

Use Nova's packaged bridge or the workbench command for subsequent queries. The raw Maigret executable bypasses the guarded transport. Certificate failures and excessive responses now stop acquisition; changing to a raw helper defeats that protection.

## Repair PDF and media dependencies only where used

Use the Python interpreter that actually runs the affected skill. For optional dependencies, prefer that skill's dedicated environment. Run the applicable command from the indicated skill folder; `--require-hashes` checks the downloaded packages and `--only-binary=:all:` avoids building unexpected source distributions.

| Optional task | Starting folder | Install or update command |
| --- | --- | --- |
| Giles PDF reading | Rupert Giles skill folder | `python -m pip install --require-hashes --only-binary=:all: -r requirements.txt` |
| Retrieval caption capture | Retrieval Intelligence skill folder | `python -m pip install --require-hashes --only-binary=:all: -r requirements-media.txt` |

Giles refuses an unsupported old parser before opening a PDF. Bundled readers update with Nova; this separate installation command applies to Giles' external parser. A patched parser reduces known exposure and is not a promise that arbitrary PDFs cannot exhaust resources.

Retrieval's optional local Whisper transcription has a separate installation path in its dependency guide. Caption capture does not need Whisper, its large compute dependencies or a speech model. Install those only when local transcription is wanted. A model download still requires the explicit transcription option.

Media capture checks its selected decoder and JavaScript runtime before starting the downloader. A safety check verifies those runtime conditions; it does not certify every installed package or a live provider's availability. Use the reported failure to repair the selected environment and then retry the normal helper.

## Use saved notes immediately

Commonplace combined search now starts with lexical retrieval, which works in an ordinary configured estate without an embedding service. Explicit semantic or hybrid requests still require their configured, current index or an explicitly selected degraded mode. Your notes and capture policy remain unchanged.

## Confirm and recover

Open LOADOUT-MANIFEST.json at the installed plugin root and compare its build_id field with the exact build identifier at the top of this guide. The version number alone does not distinguish this repair. Then use the affected capability through its installed route. For Giles, read a known small PDF; for Commonplace, find a note you already saved. Do not create a new data estate to test an update. Existing local files, playback and supplied-file work remain available while an optional network environment is being repaired.

Your data homes remain outside the installation. This repair adds no mandatory application encryption, retention policy or background service. Keep the access and backup arrangements appropriate to your own data. Uninstalling Nova preserves those user-owned records; deleting them is a separate deliberate action.

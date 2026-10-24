# Install only when the inquiry needs it

Use `python scripts/setup_osint.py --help` from the skill root. `--dry-run` needs neither uv nor a network. Pick the smallest needed `--tools` set and a dedicated data home. An actual installation downloads pinned sources/dependencies with uv and checks startup; it does not query providers or establish their accuracy.

The installer accepts a new home and preserves any completed or independently managed installation. For its own interrupted matching plan, repeat the command with `--resume`. Changed adapters, source bytes or plan prevent silent overwrite. A failed download is not promoted to a verified cache entry. Keep the setup receipt and reports; use a fresh sibling home for a different tool set or cutoff.

Set `NOVA_OSINT_HOME` to the completed home or pass `--workbench` explicitly to the bridge. `NOVA_DATA_ROOT` supplies an optional general data root. Host-specific estate routing remains host-owned; a distributed package does not create Nova continuity stores. Never infer installation from a static registry label; discovery and actual startup are separate observations.

See [tool use and limits](osint-tools.md) and [native case operations](native-case-guide.md). Installation may need network and package availability; live-provider, entitlement and identity accuracy remain unqualified by offline tests.

## Upgrade an existing Maigret workbench

Version 0.4.1 protects remote compressed responses affected by CVE-2026-111497. From the new skill folder, run:

```text
python scripts/upgrade_osint_security.py --home "PATH_TO_EXISTING_OSINT_HOME"
```

This needs `uv`, network access to the Python package index, and the existing isolated Maigret environment. It installs Brotli 1.2.1 there, saves the previous `osint.py` under `security-backups`, and changes only Maigret's launch routes plus the two safety adapters. Configuration, credentials, reports, site data and other tools remain in place. It checks Maigret help without querying a provider. An unrecognized custom adapter is refused before dependency installation; preserve that adapter and migrate its Maigret command explicitly rather than resetting the workbench.

The completed result reports `upgraded: true` and `native_curl_decoding: false`. Use `osint_bridge.py` or the workbench's `osint.py username` command afterwards. The wrapper disables libcurl response decoding and handles compressed bytes with the checked Python decoder. Running the raw Maigret executable bypasses that protection. If the security preflight fails, fix the selected environment before a provider query. The upstream curl-cffi version alone does not establish that its bundled Brotli is fixed.

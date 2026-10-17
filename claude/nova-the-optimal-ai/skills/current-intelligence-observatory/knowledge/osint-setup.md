# Install only when the inquiry needs it

Use `python scripts/setup_osint.py --help` from the skill root. `--dry-run` needs neither uv nor a network. Pick the smallest needed `--tools` set and a dedicated data home. An actual installation downloads pinned sources/dependencies with uv and checks startup; it does not query providers or establish their accuracy.

The installer accepts a new home and preserves any completed or independently managed installation. For its own interrupted matching plan, repeat the command with `--resume`. Changed adapters, source bytes or plan prevent silent overwrite. A failed download is not promoted to a verified cache entry. Keep the setup receipt and reports; use a fresh sibling home for a different tool set or cutoff.

Set `NOVA_OSINT_HOME` to the completed home or pass `--workbench` explicitly to the bridge. `NOVA_DATA_ROOT` supplies an optional general data root. Host-specific estate routing remains host-owned; a distributed package does not create Nova continuity stores. Never infer installation from a static registry label; discovery and actual startup are separate observations.

See [tool use and limits](osint-tools.md) and [native case operations](native-case-guide.md). Installation may need network and package availability; live-provider, entitlement and identity accuracy remain unqualified by offline tests.

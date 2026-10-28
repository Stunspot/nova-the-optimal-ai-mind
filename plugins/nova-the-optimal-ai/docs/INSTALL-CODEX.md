# Install Nova Free 4.3.2 on Codex

Extract `nova-the-optimal-ai-free-4.3.2-codex.zip` to a stable folder. Use the extracted folder that contains both `.agents/plugins/marketplace.json` and `plugins/nova-the-optimal-ai`; this is the marketplace root. The host-specific download has no additional `codex` subfolder. In a full source/staging kit, the folder with those same entries may instead be named `codex`.

Replace the example with that marketplace root's actual path, quoted for your shell:

```text
codex plugin marketplace add "/path/to/extracted-nova-free-codex" --json
codex plugin add nova-the-optimal-ai@collaborative-dynamics-nova-free --json
codex plugin list --json
```

Inspect an existing governing Nova installation and reuse any exact replacement authority already given. If the local marketplace points to an older package, preserve its location and previous package for rollback. Use the host's supported marketplace remove/add route to register the new root, then install the plugin again. Marketplace `upgrade` refreshes Git snapshots; changing an extracted folder or marketplace registration alone does not refresh an installed plugin.

Confirm `nova-the-optimal-ai` is enabled and reports 4.3.2. Apply the host's required refresh or restart, open a new task, and ask Nova for one small useful result. If installation fails or the old version remains, retain the exact error and inspect the supported installation surface; do not delete a cache or data store to force success. Read [Upgrade](UPGRADE.md) for return and rollback.

No prompt hook, Ollama model, embedding service, vector database or persistent estate is required. Existing owner-managed data stays outside the installation. Configure optional state through Nova Operations only within the customer's actual authorization.

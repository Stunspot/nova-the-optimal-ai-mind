# Install Nova Free 4.3.2

This download contains the Codex and Claude-compatible packages. Choose the package for your host; keep its complete contents together. The included SHA256SUMS.txt identifies the two inner ZIPs.

For Codex, extract `nova-the-optimal-ai-free-4.3.2-codex.zip`. Keep the extracted folder, including its hidden `.agents` folder. Give that folder to the installing agent and say:

> Install Nova the Optimal AI Free as one complete plugin. Ask before replacing another governing Nova installation. Do not configure persistent data unless I separately request it.

The detailed recovery guide is `plugins/nova-the-optimal-ai/START-HERE.md` inside that extracted folder.

For a Claude-compatible host, extract `nova-the-optimal-ai-free-4.3.2-claude.zip` and open `nova-the-optimal-ai/docs/INSTALL-CLAUDE.md`. Follow the route supported by your host. The package includes the complete plugin and separately importable skill folders; the guide explains which route to use.

After installation, start a new task and ask Nova to handle a small real task. Confirm the installed plugin's `LOADOUT-MANIFEST.json` has build_id `nova-free-4.3.2-system-integration-20261027-r1`. Use the version and build identity when checking the selected package.

If you already use an optional OSINT or PDF environment, follow `docs/SECURITY-UPDATE.md` inside the installed plugin before using the affected tool. Updating plugin files does not by itself update an external Python environment. Preserve your existing data locations and backups when replacing an installation.

Licenses, attribution and component notices travel inside each native package. Keep them with any redistributed copy.

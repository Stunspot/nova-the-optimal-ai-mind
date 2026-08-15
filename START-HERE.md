# Install Nova + MIND Free

Nova + MIND Free 2.1.2 installs one product as two Codex plugins: Nova, the user-facing agent, and MIND, her cognitive substrate. Together they expose forty-one skills, including sixteen MIND Faculties and TestForge’s two verification roles.

## Choose the supported path

| Host | Supported shape | Evidence boundary |
|---|---|---|
| Codex with plugin support | Complete two-plugin product, local MIND Core database, trusted prompt-submit hook, and forty-one-capability reminder estate | Primary integrated target; installation and hook trust still require local confirmation. |
| Claude-compatible skill host | One self-contained ZIP per selected skill | Package shape only; no shared database, hook, automatic reminders, or Codex-equivalent integration is claimed. |
| Other hosts | Source may be adaptable | Not a supported installation claim. |

## Before you begin

For the complete Codex installation, you need PowerShell, Python 3.11 or newer, and Ollama serving `qwen3-embedding:0.6b`. The release does not bundle or download model weights. If another Nova or MIND installation or database already exists, read [Upgrade](docs/UPGRADE.md) before changing anything.

## Normal Codex installation

1. Once the local source candidate completes its separate build and verification gates, use the governed `nova-mind-free-v2.1.2.zip`. The [latest public release](https://github.com/Stunspot/nova-the-optimal-ai-mind/releases/latest) remains 2.0.9 until a later release is separately published.
2. Attach the ZIP to a Codex task.
3. Tell Codex:

   ```text
   Install Nova + MIND from this ZIP and turn both plugins on. Ask before replacing any existing Nova or MIND installation.
   ```

4. Review the proposed file and configuration operations. Installation does not enlarge Codex permissions.
5. Open **Settings → Hooks**, inspect the exact MIND prompt-submit hook, and decide whether to trust those bytes.
6. Close Codex desktop and run the read-only verification procedure from the extracted release:

   ```powershell
   .\verify-install.ps1 -OutputPath .\nova-mind-install-verification.json
   ```

7. Start a new Codex task so discovery occurs against the installed plugins.

## Expected results

A successful mechanical verification reports:

- `Nova the Optimal AI` 2.1.0 enabled from the Free Nova marketplace;
- `MIND by Collaborative Dynamics` 2.2.2 enabled from the same marketplace;
- an intact SQLite database with an active forty-one-capability generation;
- forty-one cards, 246 vectors, and successful local semantic association against a temporary copy;
- the original database unchanged by the verifier.

That report does not prove hook trust, pre-turn context delivery, model attention, use of a reminder, or behavioral correctness. It also does not create, migrate, select, or validate a Cognitive Continuity workspace.

Worldline and Faultline ship as Continuity 0.2.2 surfaces over workspace schema v2. Worldline provides read-only `resume`, `status`, `checkpoint`, and `inspect` views; a checkpoint is not a save. Faultline provides a bounded Error Neighborhood and governed v2 mutations, has no fallback store, and is typed unsupported on v1. Neither service grants authority or proves completion, cause, safety, or repair.

## Fresh-task confirmation

In the new task, enter:

```text
$nova Help me make a concrete first move on this objective: [your objective]. Separate what you know from what you are assuming.
```

Expected result: Nova responds as one coherent collaborator, makes useful progress, and does not ask you to navigate a capability catalog. If `$nova` is not recognized, record a discovery failure and use [Troubleshooting](docs/TROUBLESHOOTING.md).

## Manual fallback

If Codex cannot install an attached archive, extract the release and run `install.ps1` from PowerShell. The installer adds the local marketplace, enables both plugins, creates a new database, activates the included estate, and checks semantic association. It stops instead of silently replacing another source or overwriting an existing database. Follow [Manual Codex installation](docs/INSTALL-CODEX.md).

## Claude-compatible hosts

Open `claude/zips/` in the release and upload only the skill ZIPs you want. Start a new conversation after the host accepts them. Read [Claude-compatible installation](docs/INSTALL-CLAUDE.md) before claiming Nova/MIND parity.

## Next

- [What you installed](docs/CAPABILITY-GUIDE.md)
- [Representative workflows](https://stunspot.github.io/nova-the-optimal-ai-mind/workflows.html)
- [Privacy and trust](docs/PRIVACY-AND-TRUST.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Update or remove](docs/UPGRADE.md)

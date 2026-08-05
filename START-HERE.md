# Install Nova + MIND Free

Nova + MIND Free is an agent package for your existing AI harness. It installs Nova, her MIND cognitive system, and the included ecology of forty-one skills and cognitive Faculties.

## The normal installation

1. [Download the current Nova + MIND Free source package ZIP](https://github.com/Stunspot/nova-the-optimal-ai-mind/archive/refs/heads/main.zip).
2. Attach or drop the ZIP into a Codex task.
3. Tell Codex:

   ```text
   Install Nova + MIND from this ZIP and turn both plugins on. Ask before replacing any existing Nova or MIND installation.
   ```

4. Review the installation actions Codex proposes and approve the ones you accept.
5. When installation finishes, open `/hooks`, inspect the MIND prompt-submit hook, and decide whether to trust those exact local bytes.
6. Start a new task so the harness can discover the installed package.

A successful installation leaves both **Nova the Optimal AI** and **MIND by Collaborative Dynamics** enabled. MIND’s local capability-reminder system should also report that the included public capability map is ready.

## Why there are two plugins

You are installing one product. Nova and MIND are separate plugin units only because MIND is also available as a standalone cognitive system and the harness needs clean discovery boundaries. In Free Nova they belong together; there is no reduced Nova-without-MIND mode.

## If the harness cannot install the ZIP itself

Extract the source package ZIP and use the included `install.ps1` from PowerShell. This is the fallback path, not the product pitch. Full prerequisites, expected results, and recovery steps are in [Manual Codex installation](docs/INSTALL-CODEX.md).

## What happens next

Nova becomes available as the user-facing agent. MIND operates as her cognitive substrate. The other included skills and Augments become capabilities Nova can draw on rather than a menu you must memorize.

See [What you just installed](docs/CAPABILITY-GUIDE.md), [How MIND remembers capabilities](docs/CAPABILITY-REMINDERS.md), or [Troubleshooting](docs/TROUBLESHOOTING.md).

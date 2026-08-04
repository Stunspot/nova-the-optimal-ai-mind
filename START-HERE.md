# Start Nova + MIND Free

This is the short path from download to a useful first conversation.

## Before you begin

You need Codex with plugin support, PowerShell, and Python 3.11 or newer. Keep this folder intact while installing; the two plugins and their local resources belong together.

## Install

From the folder containing `install.ps1`, run:

```powershell
.\install.ps1
```

The installer adds the Free Nova marketplace, installs Nova and MIND, creates a new local MIND database, and checks the result. It deliberately stops instead of replacing another Nova/MIND installation or an existing database.

## Let Codex use the reminder layer

Open `/hooks` in Codex. Review the exact MIND `UserPromptSubmit` hook and trust it only if you accept it. The hook is local code; installing it is not the same thing as trusting it.

Then start a new task. A fresh task matters because that is when Codex discovers installed skills.

## Make the first request real

Do not test Nova with a ceremonial incantation. Give her something you genuinely want help with:

```text
I need to decide whether this plan is worth a week of work. Here are the constraints and my rough notes. Find the real decision, tell me what matters, and propose the smallest next step that would change your mind.
```

For a direct capability check, this is fine too:

```text
Use $gridmason to help me plan a Minecraft build around this idea.
```

You are ready when both plugins are enabled, a new task can use Nova, and your request produces a useful answer. The reminder layer may quietly make relevant abilities easier for Nova to remember; it does not take action or grant permissions.

Need a different route? See [Install in Codex](docs/INSTALL-CODEX.md), [Capability guide](docs/CAPABILITY-GUIDE.md), and [Troubleshooting](docs/TROUBLESHOOTING.md).

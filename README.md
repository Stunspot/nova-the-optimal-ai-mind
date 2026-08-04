# Nova + MIND Free

![Nova Emergent](assets/nova-emergent.png)

Nova is the AI you bring a real situation: the deadline, the half-formed plan, the strange technical problem, the research tangle, the game build, the thing you want to make but cannot yet see clearly.

Tell her what you want in ordinary language. Nova helps directly when that is enough and reaches for a useful specialty when it genuinely helps. MIND keeps the thinking coherent, and its reminder layer helps Nova remember what is available as your setup grows.

## Start here

You need Codex with plugin support, PowerShell, and Python 3.11 or newer.

1. Download this release or clone the repository.
2. In its folder, run:

   ```powershell
   .\install.ps1
   ```

3. In Codex, review the MIND prompt-submit hook through `/hooks` and trust it only if you are comfortable with the exact local code.
4. Start a new task and describe what you want to do.

Try one of these:

```text
I have a messy plan for a small project. Find the real goal, the missing decisions, and the next useful move.
```

```text
Help me turn these scattered notes into a clear brief that somebody else can actually use.
```

```text
I want to build something good in Minecraft. Help me choose a direction and make a practical build plan.
```

If the installer stops, that is usually protection rather than catastrophe. Start with [Start here](START-HERE.md) or [Troubleshooting](docs/TROUBLESHOOTING.md).

## What Nova can help with

Nova + MIND Free includes practical and creative specialties for work that tends to show up in actual life: thinking through choices, research and knowledge work, writing and visual communication, coding and verification, personal continuity, games and stories, and Minecraft planning.

You do not need a private command vocabulary to get value from it. Ask for the outcome. If you know exactly what you want, you can also name a capability with `$name`.

MIND is always part of Nova here. It keeps a consequential job from turning into a noisy committee, preserves useful distinctions such as evidence versus assumption, and includes TestForge for checking a finished software or release claim.

## Add something later

When you add a skill, plugin, tool, or other durable capability, talk to Nova about the addition normally. The reminder layer is meant to surface the accompanying housekeeping: whether MIND should get a reminder card so the new ability can be recalled naturally in later work. You should not have to remember the mechanism’s name.

Read [Capability guide](docs/CAPABILITY-GUIDE.md) for the kinds of work included and [Capability reminders](docs/CAPABILITY-REMINDERS.md) for how that part behaves.

## Read only as far as you need

- [Start here](START-HERE.md): install, confirm, and get moving.
- [Install in Codex](docs/INSTALL-CODEX.md): the careful installation path.
- [Use MIND by itself](plugins/augment-of-mind/START-HERE.md): standalone MIND.
- [Privacy and trust](docs/PRIVACY-AND-TRUST.md): local data and authority boundaries.
- [Troubleshooting](docs/TROUBLESHOOTING.md): recover from a concrete symptom.

Nova is here to be useful, not to make you babysit a stack of clever machinery. 🌐‍💠

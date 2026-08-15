# Install Omnara

Omnara can run as an integrated Nova + MIND skill, as a portable individual skill in a compatible host, or as a degraded copy/paste workflow. Choose the route your host actually supports.

## Before installing

Confirm:

- you can add or enable skills in the target host, or can use plain chat;
- you have a fresh release downloaded from the [Omnara releases page](https://github.com/Stunspot/omnara-deep-research/releases);
- you know whether campaign material may contain private or regulated information;
- you have Python 3 only if you intend to use the optional local helpers.

Inspect the ZIP before installation. Its top-level skill directory must contain SKILL.md, personas, references, knowledge, fallbacks, assets, schemas, and scripts.

## Codex: integrated Nova + MIND route

This is the primary integrated route.

1. Download the current Nova + MIND release.
2. Attach the release ZIP to Codex.
3. Ask: "Install Nova + MIND from this ZIP and turn both plugins on. Ask before replacing an existing Nova or MIND installation."
4. Review and approve the exact local actions.
5. Follow the [current manual Codex instructions](https://github.com/Stunspot/nova-the-optimal-ai-mind/blob/main/docs/INSTALL-CODEX.md) if attachment installation is unavailable.
6. Start a new task so Codex can discover the installed skills.
7. Verify Omnara using [Verify discovery](#verify-discovery) and [Verify invocation](#verify-invocation).

The Nova package has its own Python, Ollama, hook, and MIND database requirements. Those are requirements of the integrated runtime, not of Omnara's research doctrine.

## Claude-compatible skill host

1. Download the Omnara release ZIP or the Omnara per-skill ZIP included in Nova + MIND.
2. Upload the ZIP through the host's skill-management interface.
3. Enable the skill if enablement is a separate step.
4. Start a new conversation so the host can refresh discovery.
5. Run [Verify discovery](#verify-discovery) and [Verify invocation](#verify-invocation).

This route provides the individual skill contents. It does not establish Nova's shared MIND database, prompt hook, automatic capability reminders, or identical behavior across Claude-compatible hosts.

## Other skill-capable hosts

Import the complete skill directory using the host's current documentation. Do not copy only SKILL.md; Omnara references files throughout the source tree. Start a fresh session after import, then verify discovery and invocation.

Because hosts differ, this repository does not claim a universal destination path, CLI command, or activation mechanism.

## Plain-chat fallback

Open [the universal copy/paste workflow](../fallbacks/universal-copy-paste-workflow.md), copy its complete contents into a new conversation, and append your research request. This preserves the core sequence and evidence distinctions. It does not prove automatic skill discovery, bundled-reference loading, helper execution, persistent campaign storage, or tool access.

## Verify discovery

In a fresh task or conversation:

~~~text
List the installed or available skill named omnara-deep-research, then tell me its display name without running a research campaign.
~~~

Expected result:

- selector: **omnara-deep-research**;
- display name: **OMNARA Deep Research**.

A directory on disk is only placed or imported. This probe establishes discovery only.

## Verify invocation

~~~text
Use $omnara-deep-research. Frame a research campaign for deciding whether our small product team should adopt passkeys in 2026. Do not browse yet. Return the preserved inquiry, audience and decision, scope, exclusions, coverage areas, evidence burden, and first unverified edge.
~~~

A healthy result preserves the inquiry, does not browse despite the explicit constraint, and distinguishes framing fields. This establishes a bounded invocation in that task; it does not prove every research route, tool, or campaign scale.

## Verify local helpers

From the extracted repository or source checkout:

~~~shell
python -B scripts/validate_release.py . --profile source
python -B -m unittest discover -s tests -v
~~~

Initialize a disposable campaign outside any valuable directory:

~~~shell
python -B scripts/research_campaign.py init tmp/omnara-smoke --title "Smoke test" --query "What evidence would change this decision?" --tier focused
python -B scripts/research_campaign.py validate tmp/omnara-smoke
~~~

Expected output includes INITIALIZED and VALID. Remove only that disposable directory after inspection.

## Next

Continue to [Run your first campaign](../START-HERE.md). If observed behavior differs from the expected state, preserve the exact error and use [Troubleshooting](TROUBLESHOOTING.md).

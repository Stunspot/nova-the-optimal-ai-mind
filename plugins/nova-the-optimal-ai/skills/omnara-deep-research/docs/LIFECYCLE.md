# Update, remove, and clean up Omnara

Treat the installed skill, helper-created campaign data, downloaded archives, and Nova + MIND state as separate things. Removing one does not silently remove the others.

## Update an individual Omnara skill

1. Finish or checkpoint any active campaign.
2. Back up campaign directories that matter.
3. Record the current Omnara release or source commit.
4. Download and inspect the replacement release.
5. Use the host's replace or update function for the exact omnara-deep-research skill.
6. Start a fresh task or conversation.
7. Repeat the discovery and bounded invocation probes in [Installation](INSTALLATION.md).
8. Validate an existing campaign before resuming it.

Do not merge old and new skill directories file by file. A partial replacement can leave stale references behind.

## Update through Nova + MIND

Follow the [Nova + MIND upgrade guide](https://github.com/Stunspot/nova-the-optimal-ai-mind/blob/main/docs/UPGRADE.md). That upgrade can affect plugins, hooks, and the MIND database in addition to Omnara. Do not delete or replace those components solely to update one skill unless the integrated guide explicitly directs it.

## Remove the individual skill

1. Confirm the exact installed skill identity and location in the host.
2. Disable omnara-deep-research if the host separates disablement from removal.
3. Remove only that skill through the host's skill manager.
4. Start a fresh task and verify that the selector is no longer discoverable.

Removing Omnara does not remove campaigns, downloaded ZIPs, generated reports, source caches, browser history, model-provider logs, or Nova + MIND state.

## Campaign data cleanup

Campaign vaults are ordinary files in the location you selected. Review before deletion:

- campaign.json and research brief;
- query, source, and claim ledgers;
- source notes and retrieved excerpts;
- credentials or private URLs accidentally recorded;
- drafts, assembled reports, metrics, and audits;
- backups, exports, and copies shared elsewhere.

Delete only the exact campaign directory you intend to remove. Use your platform's recoverable trash mechanism when practical. Emptying trash, wiping backups, clearing cloud synchronization history, and asking model or search providers to delete logs are separate actions governed by those services.

## Local helper residue

Python may create __pycache__ directories or .pyc files. Disposable smoke campaigns may remain wherever you initialized them. These are not required for continued use and may be removed after you verify their exact paths.

## Roll back

Reinstall the previously recorded release, start a fresh session, repeat discovery and invocation, and validate the campaign before resuming it. A restored directory is not a completed rollback until the host discovers and invokes the intended version.

## Data retention boundary

Omnara itself has no telemetry client, account system, background service, or automatic network uploader. The agent host, model provider, browser, search service, repository, synchronization service, or research source may retain data under its own policy. See [Security and privacy](SECURITY-AND-PRIVACY.md).

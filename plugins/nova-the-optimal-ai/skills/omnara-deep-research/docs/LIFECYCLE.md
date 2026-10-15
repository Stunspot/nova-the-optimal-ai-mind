# Update, return and remove

Keep the application, installed skill and owner-selected research home separate. Updates should replace a complete known product, preserve the previous version for rollback and leave research data in place.

## Update

Checkpoint active campaigns and preserve a complete-folder backup when needed. Record the current package. Inspect the replacement, use the host's supported recoverable update path, and start a fresh session for discovery/invocation checks in [Installation](INSTALLATION.md). For Nova Free/Emergent use the current edition's own instructions. Standalone MIND is deprecated; it does not need reinstalling.

Stop an old campaign-room process before replacing its application files. Closing its browser tab does not stop the local service. A launched process records its PID and matching application/data-root identity under the research home's `.workspace/instance-*.json`. Verify the exact matching process before terminating it; do not kill unrelated Python processes. Reopen through the new package launcher and confirm the expected research home.

Old campaigns remain native files. Legacy labels do not become new review evidence. Preserve the prior completed copy and move a working copy to review/active when actual content or verification needs repair. The [review contract](../references/review-contract.md) names what changes invalidate review. Admin-only status transitions retain a current subject.

## Recovery and rollback

Reinstall the preserved complete application/skill, reopen with the same data root and repeat the bounded discovery/invocation check. If a new review extension is not understood by an old helper, keep the newer evidence files in backup; do not discard them to obtain an old pass. [Troubleshooting](TROUBLESHOOTING.md) covers write failure and conflict recovery.

Room history is a recoverable set of prior native files, not a full research backup. Native export omits external originals, media, nested corpora and histories. Back up the complete research folder when those matter, and separately preserve external source custody identified by your notes.

## Remove

Disable/remove only omnara-deep-research through the host, verify discovery in a fresh session, and stop the exact matching local room service if running. Removing the application does not delete campaigns, exports, histories or provider logs. Review those paths individually and use recoverable trash when practical. Omnara provides no cloud account, telemetry uploader, encryption, automatic expiry or deletion service. Its loopback server is local; the model host, browser, search provider and synchronization tools retain their own policies. See [Privacy](SECURITY-AND-PRIVACY.md).

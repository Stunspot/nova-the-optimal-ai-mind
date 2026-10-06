# Answer Change Desk

Open.cmd starts the private loopback desk on Windows; Open.command uses Python 3.10+ on macOS/Linux. No pip dependencies. Restart the launcher after reboot. Each launch starts or reconnects the exact matching private instance. A previously opened working copy remains in its original tab.

Import an existing native JSON file or load the explicitly synthetic example. Review the domain views, edit the complete native document, run the native structural validator, and download a working JSON file. Your source file is untouched. The working copy lives only in browser memory and disappears on close/reload. No browser storage, second case/ledger store, account action, command execution or approval is supplied. Import/export preserves the original JSON text, including unknown fields, large numbers, and native state. Editing preserves the text actually entered. Validation proves only the bundled validator's structural rules.

## Compare the actual answer and proposal

Open an answer record imports your native Reality Ledger into memory; Example loads only the explicitly synthetic teaching ledger. Current answer and Proposed wording open the same answer workbench: actual baseline text and cutoff, a searchable patch index, exact before/after wording and an evidence margin. Select a patch to inspect its recorded status, authority, scope, mechanism, counterfactual and recheck. Referenced evidence joins only exact source_ids; missing references stay missing. Native approval/publication fields remain separate from the proposal.

Strata is a near-black geological answer stage: the actual baseline is the fixed datum, a selected patch opens its exact before/after seam, and referenced evidence occupies a separate lower stratum. Switchyard is a dark blue enamel routing desk: patch selection runs across the top, while baseline and proposed wording face each other; signal states occupy distinct labeled lanes. Both skins preserve the same native record and authority states. Changes & exclusions preserves candidates, accepted deltas, rejected noise and unresolved fuzz. Evidence shows retained records. Recheck triggers shows recorded conditions, not a running monitor.

## Prepare a working file, not adoption

Edit working file opens complete JSON, including unknown fields. Apply to working copy changes only the in-memory document. Validate checks native structure, not factual truth, source sufficiency, approval or currentness. Save working file prepares a file without rewriting the source or adopting a patch. The accountable human's canonical workflow owns baseline adoption and publication.

For invalid JSON or format, keep the editor open and correct the draft; Cancel leaves the prior working document unchanged. If a JSON object has malformed native collections, the workbench shows a repair panel while Validate reports the structural errors. Save intended work before closing/reloading, then reopen its native file when needed. Loading another record or the example asks before discarding edited work; the browser controls the leave warning. Saving requests a download, not canonical adoption. The desk deliberately does not restore a shadow copy. If Session missing appears, reopen the launcher to restore its private session. Keep original custody and human authority intact.

Run `python -B host.py --check` for sample/native-validator checks. `--no-browser --port 0` starts a test instance and prints identity and URL. This process retains no user data. Python port and local browser behavior need observed host acceptance. macOS wrapper is supplied, not live-tested.

## Launcher identity and reconnect

Duplicate launch reuses only the instance whose product, version, exact workspace and private process nonce match. General health never exposes the session token. The token is kept in per-user temporary runtime metadata with process ID and port only, never owner records. POSIX mode is 0600; Windows inherits the current user's temporary-directory ACL. Metadata is disposable and removed on clean shutdown. Stale/unrelated metadata cannot select another product. An unrelated occupied port selects a free port without being opened.

Windows normal launch detaches a CREATE_NO_WINDOW process, waits for corroborated identity and opens the browser. --no-browser keeps a foreground test process and prints the private local URL; do not publish that URL. If startup fails, run --no-browser for the exact error. Open.cmd falls back to python when py is unavailable. If the private session is missing after a browser restart, reopen the launcher. In-memory working copies are not restored after reload.

The authentication credential alone is held in a HttpOnly SameSite=Strict session cookie, namespaced by product/exact workspace and actual port; Same-tab reload retains the session but not the in-memory document. No owner record is put in a cookie or browser store. Runtime-byte identity also prevents reconnecting to a superseded Python process after a source update.

# Nova Knowledge Desk 0.3.0

A read-only display for Commonplace notes, Corkboard pins and Dunbar people using existing native owner commands. Python 3.10+, no pip dependencies. No owner record or derived index write endpoint exists. No localStorage, IndexedDB, service worker, browser copy, mirror store or disk response log is used. API responses use no-store; queries travel through standard input, never process arguments.

Open.cmd and Open.command support `--nova-operations <absolute nova_estate.py> --estate-root <approved existing Nova estate>`. When packaged beside nova-operations, its sibling script is the default. Standalone source must be given the current canonical launcher explicitly. Missing launcher/registry fails before opening; no service initialization or direct SQLite fallback exists. Each launch starts or reconnects an identity-corroborated private loopback instance. If its preferred port is occupied, another port is chosen; an unrelated service is never opened. Restart launcher after reboot. The native Nova Operations binding should invoke this helper with its own script location and selected estate root.

Nothing is queried on load. Commonplace blank query calls canonical list; text uses lexical search. A unavailable/stale Concordance remains its native failure, without rebuilding. Corkboard list respects global/project/all-project scopes; all-project is an explicit checkbox. Dunbar uses Commonplace's fixed read-only federated-search with owners=[Dunbar], lexical mode, bounded timeout and query stdin. Its exact adapter byte binding may fail closed on unsupported installation; display this as unavailable, never empty or a substitute dossier. Public+personal are default; private inclusion is explicit per read. Restricted material is not exposed.

## Read one owner deliberately

Choose Commonplace notes, Corkboard pins, Dunbar people or Estate & retrieval before loading. Set the query and allowed scope, then Read owner. This is the only control that requests owner content. The loaded response reports exact registry estate, scope and native outcome; unavailable is not empty. A failed native command retains its scope and diagnostic without a direct-store substitute.

Commonplace notes has a loaded-response index and a rich note reading surface with recorded context/provenance. Find within loaded response filters only the current in-memory result, without a second owner call. Select a note to read headings, paragraphs, lists, quotations and bold/code emphasis. Unsupported markup remains escaped text; All exact native fields preserves the original body and every returned field. Library night uses a dark reading shelf and evidence inset; Quiet folio uses a ruled paper reading composition.

Corkboard pins is a separate owner view with explicit project/global scope. Dunbar people is a separate native-federation view with its exact person result fields and original owner source/status retained. No relationship or cross-owner link is inferred from similar text. Complete native response & custody preserves the entire returned packet, including owner failures and declared relations.

## Recover a session without changing records

Reload discards loaded content; it does not save a local collection. Read the owner again with the desired scope. If Session missing appears, reopen the existing owner launcher to restore its private session rather than changing an owner database. For an unavailable adapter or stale index, inspect the exact native diagnostic and use that owner's supported workflow only under appropriate authority. This desk does not rebuild, capture, unpin, correct, promote, forget or synchronize.

Labeled example is mode-specific: synthetic notes, a synthetic pin or a fictional person. It never calls an owner or persists content. No claim of semantic truth, identity verification, currentness, completeness or mutation support follows from a read. Mac wrapper and browser rendering require separate live acceptance.

## Launcher identity and reconnect

Duplicate launch reuses only the instance whose product, version, exact workspace and private process nonce match. Knowledge Desk additionally matches selected estate and canonical Operations path. General health never exposes the session token. The token is kept in per-user temporary runtime metadata with process ID and port only, never owner records. POSIX mode is 0600; Windows inherits the current user's temporary-directory ACL. Metadata is disposable and removed on clean shutdown. Stale/unrelated metadata cannot select another product. An unrelated occupied port selects a free port without being opened.

Windows normal launch detaches a CREATE_NO_WINDOW process, waits for corroborated identity and opens the browser. --no-browser keeps a foreground test process and prints the private local URL; do not publish that URL. If startup fails, run --no-browser for the exact error. Open.cmd falls back to python when py is unavailable. Reopen after a browser reload to restore its private session. In-memory working copies are not restored after reload.

The authentication credential alone is held in a HttpOnly SameSite=Strict session cookie, namespaced by product/exact workspace and actual port; Knowledge additionally namespaces its selected estate and Operations binding. Same-tab reload retains the session but not the in-memory document. No owner record is put in a cookie or browser store. Runtime-byte identity also prevents reconnecting to a superseded Python process after a source update.

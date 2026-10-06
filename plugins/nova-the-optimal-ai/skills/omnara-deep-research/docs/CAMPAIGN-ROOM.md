# Your campaign room

OMNARA helps you find out what a consequential claim rests on, where the uncertainty remains, and what observation would move the inquiry forward. The room keeps that structure in view while your research agent works on the same native files.

## Open and return

Extract the complete package into a stable folder. With Python 3.10 or newer installed, double-click **Open.cmd** on Windows. On macOS, run `python3 workspace/open.py`; **Open.command** is the same entrypoint after `chmod +x Open.command`. The launcher starts or reconnects the matching local service and works after reboot. macOS execution has not been exercised on a macOS host.

Campaigns live outside the application, by default in `Documents/OMNARA Campaigns`. Select your own home with `python workspace/open.py --data-root "your folder"` or `OMNARA_HOME`. Keep that folder when updating the application. Open matches both application copy and data home, chooses a free loopback port when needed, and reconnects on repeat launches. Use Open rather than bookmarking a temporary port.

The most recently opened campaign resumes automatically. **Investigations** opens a searchable picker; the OMNARA wordmark opens the full library. Create a campaign with its title and question exactly as asked, or import one native campaign directory. The original question remains available beside the campaign title.

## Follow an argument

**Evidence atlas** keeps the campaign's recorded claims and cited sources visible together. Select a claim to trace its sources; select a source to see its reach across claims and inspect its evidence beside the map. Structural observations show claims without citations, unreviewed judgments, shared-source concentration and sources without claim links. These are properties of the records, not confidence or completion scores. **Read evidence** opens the full native note; **Compare** leads to the reading room's **Read alongside** control. Native semantic audit, support, or evidence-status judgments remain exactly as recorded.

Search the claim field or narrow it to claims without citations or without review. A filter with no matches offers a direct return to every claim. Large source networks prioritize every source attached to the selected claim and identify when other cited records are outside the visible map; the reading room retains the full corpus. **Edit assertion & citations** preserves the native judgment field and updates the assertion and source IDs. Missing source records stay visibly missing.

**Reading room** keeps the source queue, provenance, earned states, full evidence note and linked claims together. Search by title, ID or locator, filter by recorded state, or use **Read alongside** to compare two notes. Desktop and tablet layouts place comparison readings side by side; narrow screens stack them. Select any related claim to return to its evidence atlas. A source without a note is explicitly empty.

**Open questions** brings together the next consequential pass, active coverage, blockers, the native coverage matrix and contradictions. Matrix headings and judgments remain the researcher's own; the room does not infer resolved status from keywords. The query trail is available on demand.

**Synthesis** reads the saved report, evidence digest, outline, audit, summary and section drafts when present. Source-ID citations open the corresponding evidence note. Markdown is rendered as safe text, headings, lists, tables and links; raw HTML is not executed. Local figures and attachments remain in their original files; this text reader does not embed them. **Edit document** opens the native file editor.

Recorded-state counts are clickable filters, never a completion score. Discovered, inspected, opened, deeply-read, cited and inaccessible describe different research events. The room does not perform web research or audit semantic entailment by itself.

## Three working environments

**Tracework** is a dark optical field with fine copper trails, glasslike controls and a focused evidence inspector. It favors deliberate tracing.

**Survey Folio** is a dark olive working file with ruled annotations, source slips and a map that reads as an annotated survey. It favors sustained reading and composition.

**Proof Cabinet** is a lacquered oxblood instrument with brass detailing, dark fired-copper reading surfaces and orthogonal citation traces. It favors rapid scanning and source inspection. All environments retain the same records and capabilities. The preference is local to the browser. Existing browser preferences for Aperture, Marginalia and Signal migrate to the corresponding new environment.
## Edit, save and recover

Use **Edit note** to change the exact native Markdown, then **Read note** to inspect it. Source details reveal title, locator and earned-state editing. **Vault actions** provides inquiry and scope, native files, reload, export and unsaved-draft download. Forms are available when you need to record or correct something; they are not the room's home screen.

**Save vault** or Ctrl/Cmd+S commits edits through OMNARA's native validator. It recomputes source counts and refuses unknown states, broken links, unearned reading states, missing substantive evidence and unsupported complete-campaign declarations. Rejected edits remain in the page. Edits made while a save is pending remain unsaved after the earlier snapshot finishes.

If an agent or another window changed the vault, Save refuses to overwrite it. Download your unsaved draft from **Vault actions** before reloading, then reconcile only the changes still needed. The draft download is a recovery JSON containing native file text; it is not an automatic import/merge. Prior native files are retained under the data home's `.workspace/history`. This is recoverable local editing, not a distributed transaction with an actively writing agent.

The editable boundary is the campaign's root Markdown, campaign JSON, source/claim/query ledgers, structural citation audit, and immediate Markdown in `notes` and `draft`. Nested investigations, binary media, collected corpora and unrelated JSON snapshots remain in their original custody. They are neither loaded into the editor nor rewritten on save.

**Import native vault** validates and copies this native text boundary without modifying the original. It refuses linked files and directories in that boundary. **Export native text ZIP** downloads those saved records; it is not a backup of attached media or external corpora. Back up the complete owner-selected research folder separately when you need those materials too.

**Next-pass handoff** downloads a Markdown prompt naming the saved campaign path, verbatim inquiry, resume point, coverage and blockers. Give it to your research agent. Save edits before either export or handoff; the room refuses to export a stale saved version silently.

## Local operation

The service binds only to `127.0.0.1`, has no cloud dependency and makes no outbound research calls. Open supplies a private instance token in the URL fragment; do not share that launch URL. Foreign origins and unrelated Host headers are refused. Closing the browser is safe after Save confirms success. Reopen through the launcher. Updates and uninstall leave the separate data home intact.

A failed load shows a retry and keeps its error explicit. Malformed native JSON can be inspected and corrected through Native files. If startup fails, run `python workspace/open.py --serve --data-root "your folder"` in a terminal to see the error. An empty installation contains no invented research or demonstration records. Desktop shortcuts are optional and are not installed automatically.


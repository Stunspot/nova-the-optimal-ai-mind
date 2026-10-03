# Open the native workspaces

Nova Free 3.6.0 includes seven optional workspaces attached to existing capability owners. They show real supplied artifacts, not live connected systems. Ordinary Nova conversation requires no workspace or persistent estate. Extract or install the complete edition before using a launcher; keep native folders together. Launcher paths are relative to the plugin root: `codex/plugins/nova-the-optimal-ai` or `claude/nova-the-optimal-ai` in the customer package.

## Choose the owner and starting artifact

| Workspace | Windows launcher | Starting artifact and change boundary |
| --- | --- | --- |
| Giles Knowledge Atlas | `skills/rupert-giles-knowledge-steward/Open Giles.cmd` | Registered knowledge stores and exact subsection routes; persistent catalog metadata, read-only source previews and portable import/export. |
| Dennis Project Bridge | `skills/dennis-stratton-project-management/Open Project Bridge.cmd` | Registry-discovered Nova project records; native edit/save/export. |
| OMNARA campaign room | `skills/omnara-deep-research/Open.cmd` | Native campaign vaults; native import/edit/save/export under the research owner. |
| AnswerLayer Baseline Inspector | `skills/answerlayer/workspace/Open.cmd` | Supplied Reality Ledger JSON; memory-only working copy and download, no adoption. |
| Beryl IT Case Bench | `skills/beryl-it-tech/workspace/Open.cmd` | Supplied IT case JSON and optional reviewer artifact; memory-only working copy and download, no device action. |
| Observatory Case | `skills/current-intelligence-observatory/workspace/Open.cmd` | Supplied dated case JSON and optional baseline; read-only comparison. |
| Knowledge Desk | `skills/commonplace/workspace/Open.cmd` | Explicit reads from the existing Commonplace, Corkboard and Dunbar owners; no record writes. |

Each launcher has a neighboring `.command` route for macOS/Linux. Observatory can also open `workspace/index.html` directly without Python or a server. The other local hosts need Python 3.10+ already installed; they require no pip dependencies. macOS wrappers are supplied, not live-tested by this qualification.

## Open safely and recognize the correct instance

1. Choose the owner and preserve your original artifact. Use a supplied labeled example to explore without treating it as your data.
2. Open the matching launcher. The existing workspace hosts reconnect only their exact matching private loopback instance. Giles starts its own server and reports an occupied port; use its recovery procedure if that happens. Reopen the launcher after reboot.
3. Check the workspace name and the selected native artifact before editing or reading. A successful page load is not proof of an installation's agent discovery or real external behavior.
4. Follow the guide for that owner. Before closing, distinguish a native save receipt, a downloaded working file and a read-only view.

No desktop shortcut is created automatically. Do not publish private loopback session URLs. If launch fails, inspect the terminal error or invoke that workspace's supported `--no-browser` route; do not kill an unrelated service or reset owner data.

## Giles: recover a store and give Nova the right route

Use this journey when you remember making an archive but cannot recall its name or location. Giles searches your registered names, descriptions, aliases, topics, use cues and named sections. The catalog points to evidence; a match does not establish that the source was read, is accurate or is current.

### Open the correct catalog

Extract or install the complete edition and have Python 3.10+ available. In the Codex package, open `codex/plugins/nova-the-optimal-ai/skills/rupert-giles-knowledge-steward/Open Giles.cmd`. In the Claude package, open `claude/nova-the-optimal-ai/skills/rupert-giles-knowledge-steward/Open Giles.cmd`. The neighboring `.command` launcher is the supplied macOS/Linux route.

The browser should show **Knowledge Atlas**. A new customer catalog is empty until you register stores or import an export. Existing metadata stays in its external data directory when the plugin is updated. `GILES_CATALOG_HOME` selects a catalog directory; a corroborated Nova root registry selects its `knowledge/giles/catalog.json`; otherwise the platform application-data default applies. To open a specific file, run the following from the plugin root, replacing the data path:

    python skills/rupert-giles-knowledge-steward/scripts/giles.py --catalog "<your data>/catalog.json" serve

If port 8808 is occupied, stop only your own prior Giles instance or use `serve --port 0` for an available port. Reopen the launcher after reboot. An empty view after an upgrade is a reason to check the selected catalog path before registering everything again.

### Register one store you can recognize later

1. Choose **Register a store**. Enter a **Recognizable name** and its absolute local path or HTTPS address in **Location — absolute local path or HTTPS address**. Name the collection as you would refer to it in conversation.
2. Describe **What is here?** and add one useful situation per line under **Use this when…**. Add alternate names and topics if they help imperfect recall.
3. Choose the actual format, custodial role and disposition. Under **How far has it been inspected?**, keep **Location / metadata only** when only the locator is known. Use the stronger states only when that inspection happened, and name its basis under **What supports this description?**
4. For a useful section, choose **Add an entry point**, give it a recognizable **Section name** and a **Relative source path**. For example, an archive you own might have a named study folder and its own `README.md`. A path may point to a folder or supported text file; it must remain inside the store.
5. Choose **Save record**. The new name should appear in **Your knowledge stores**. Use **Reload** to confirm the saved record still appears. Saving changes the descriptive catalog, not the archive.

### Find the source and prepare the handoff

1. Enter a subject, alternate name or remembered fragment in the search field, or choose a topic. Select the store whose description and use cues fit the question. Use **Clear filters** if a disposition or **My marked stores** filter hides the expected result.
2. Select **Store overview** or a named entry point. Use **Read entry point** for a supported text sample, or **Browse source** to follow folders. Text previews are limited to 32 KB and folder listings to 200 visible immediate entries. A database or unsupported file stays a route for its native owner; registered websites are not fetched by Giles.
3. Read the source's role, disposition, inspection basis and description provenance before treating it as authority. **Check location** records reachability at the displayed time; it does not certify freshness. **Mark for return** creates a bookmark, and **Nearby on the shelf** connects only explicitly recorded topics.
4. Enter the current question under **What should we investigate here?**, then choose **Prepare & copy retrieval brief**. Inspect the displayed store, section, source route, question and inspection limits. Paste that brief into Nova, or use **Download brief** if clipboard access is unavailable.
5. Ask Nova to inspect that route through the appropriate source owner. The task is complete when you can identify the collection and exact section needed for the question; catalog metadata alone is not a source-backed answer.

The matching agent commands run from the plugin root. Each uses the same explicitly selected catalog; substitute actual store and section IDs returned by discovery.

    python skills/rupert-giles-knowledge-steward/scripts/giles.py --catalog "<your data>/catalog.json" list
    python skills/rupert-giles-knowledge-steward/scripts/giles.py --catalog "<your data>/catalog.json" find "remembered fragment" --limit 8
    python skills/rupert-giles-knowledge-steward/scripts/giles.py --catalog "<your data>/catalog.json" brief STORE_ID --section SECTION_ID --question "current question"

### Keep the route and recover safely

Use **Edit record** to correct descriptions and routes. **Remove catalog record** removes the pointer and leaves the source untouched. **Export catalog** downloads locators and descriptive notes; back up the actual archive separately.

Use **Import**, select an exported file, then **Import catalog** to merge stable store IDs. Different existing records stop the import. Inspect the conflict before selecting **Replace conflicting catalog records**; replacement changes the conflicting catalog records, not their source stores. Invalid imports leave the saved catalog unchanged.

If another window saved first, Giles rejects the stale save. Choose **Reload**, inspect the current record and reapply only the intended correction. If a catalog cannot be read, preserve that file and restore a known valid export to the intended data path; do not reset an archive to repair a locator. Read the supplied skill's `workspace/README.md` for catalog limits and standalone reference. Keep private exports in their intended custody.

## Dennis: follow an outcome to its next action

Project Bridge reuses the exact `DENNIS_PROJECT_HOME` discovered through Nova Operations. Its equivalent agent route is `python skills/nova-operations/scripts/nova_estate.py run project-bridge --`. If the existing project selector is missing, use Nova Operations' supported estate setup under the approved root. The Free edition does not create a standalone fallback.

Select the actual project and read its outcome, next action, milestone/dependency route and evidence before changing the native record. Missing dates or unfinished acceptance remain missing or unfinished. Use the native save/export flow, then reload the record to confirm the intended field persisted. Ember bridge, Survey folio and Redline present the same records through distinct working surfaces; the focused route exposes live work first and Show all stations reveals declared-complete work. A skin never changes completion.

## OMNARA: work from campaign evidence

Open or import a native campaign vault, then follow its research question, evidence and claim-support gaps. Supply dated sources; a source count never proves reading or support. Use the campaign room's native save/export path and reopen the saved campaign when resuming. The default or selected campaign home stays outside installation and adds no Nova selector. Back up that owner data, not merely the installed files.

## AnswerLayer: prepare exact wording without adopting it

Use `Open JSON` for an existing ledger or `Example` for the synthetic teaching ledger. `Baseline & authority` and `Exact patches` show actual baseline text, cutoff, exact before/after wording and linked evidence. Missing source IDs stay missing. `Signals & exclusions`, `Source evidence` and `Probes & watch` retain recorded states; they do not run a monitor.

Use `Edit native document` only when a complete native JSON edit is intended. `Use working copy` changes memory; `Validate` checks native structure, not factual truth, approval or freshness. `Download working JSON` prepares a file without changing the original or adopting the proposed patch. Download before reload/close, then reopen that file to resume. `Cancel` preserves the prior working document when an editor draft is invalid. Dark diff console and Redline editorial are two views of the same ledger.

## Beryl: inspect the case, tests and custody

Use `Open JSON` or the clearly synthetic `Example`. `Case & custody` and `Causes & tests` show reported symptoms, triggering envelope, native hypotheses and exact linked test/evidence records. A planned test is not a performed test; a missing relation stays missing. `Changes` and `Verification` retain the intervention trail and recorded dispositions.

An imported IT reviewer JSON/text file is a separate transient advisory artifact. Its filename and selected binding do not authenticate the binding, authorize repair or change case state. `Edit native document`, `Use working copy`, `Validate` and `Download working JSON` have the memory/download boundaries described in the AnswerLayer procedure. Download before closing; no account change, command execution or device repair occurs. Instrument bench and Ticket ledger change presentation, not diagnosis.

## Observatory: inspect a snapshot and supplied baseline

Open the current native `cd-observatory-case/v1` JSON and, if needed, a comparison baseline. `Claims`, `Timeline`, `Relations`, `Challenge` and `Sources` retain searchable native-object indexes and exact provenance. Imported text is text; embedded commands and source URLs do not execute automatically.

`Delta` compares typed native IDs as `NEW`, `CHANGED` or `NO LONGER REPRESENTED`. These are structural differences, not reviewed material-change judgments. Different case IDs stay distinct. `All original fields` keeps the complete record available. Invalid format, duplicate IDs or a file larger than 5 MB leaves the prior case selected. `Clear private data`, close or reload discards memory. There is no canonical save, collector, monitor or publication action. Night situation room and Briefing paper remain dated snapshot views.

## Knowledge Desk: request one owner deliberately

Knowledge Desk defaults to its sibling `nova-operations/scripts/nova_estate.py` and the existing approved registry estate. Missing launcher/registry fails closed: it does not initialize services or read SQLite directly. Choose `Commonplace notes`, `Corkboard pins`, `Dunbar people` or `Estate & retrieval`, set query/scope, then use `Read owner`. Nothing is queried merely by opening the page.

Blank Commonplace query uses native list; text uses lexical search. `Find within loaded response` filters the current response without reading the owner again. Corkboard's project/global/all-project scope is explicit. Dunbar reads the exact existing read-only federation adapter. Private inclusion is explicit per read; restricted material remains excluded. Unavailable or stale is not an empty collection: retain the native diagnostic and use the owner's supported recovery path under appropriate authority.

Select a returned item to read its native content and provenance; `All exact native fields` and `Complete native response & custody` preserve the original packet. `Labeled example` is synthetic and calls no owner. Reload discards the response; use `Read owner` again with the intended scope. Library night and Quiet folio are views, not separate stores. The desk cannot rebuild, capture, unpin, correct, promote, forget or synchronize.

## Recovery and evidence limits

For a memory-only desk, download intended work before reload; the original file remains unchanged. For a persistent native owner, use its save/export receipt and confirm by reopening. For a missing private session, reopen the existing launcher rather than changing a database. Do not confuse a saved revision with validated truth, permission or real-world completion.

Owner desktop review covered both supplied skins and scoped native interactions. Package checks establish only their exercised byte, path and contract properties. Fresh-host installation/discovery, macOS live launch, assistive-technology conformance and narrow-viewport rendering are not established by those checks. Consult the included owner's workspace guide when its labels, schema or launcher changes.

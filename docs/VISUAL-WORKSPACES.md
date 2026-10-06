# Open the native workspaces

Nova Free 3.8.0 includes seven optional workspaces attached to existing capability owners. They show real supplied artifacts, not live connected systems. Ordinary Nova conversation requires no workspace or persistent estate. Extract or install the complete edition before using a launcher; keep native folders together. Launcher paths are relative to the plugin root: `codex/plugins/nova-the-optimal-ai` or `claude/nova-the-optimal-ai` in the customer package.

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

Start with your collections. Knowledge Atlas makes retained archives, notebooks and reference stores recognizable by name and purpose. Its map shows recorded shared subjects; the list offers another way to browse. Searching a remembered fragment is optional. A catalog description helps you choose a source; it is not a claim that the source has been read or verified.

### Open and read

Keep the complete edition together and have Python 3.10+ available. From the plugin root, open `skills/rupert-giles-knowledge-steward/Open Giles.cmd` on Windows or its neighboring `.command` launcher on macOS/Linux. The page should say **Knowledge Atlas**. Choose a collection, then **Read entry point** or **Browse source**. Open a named section to stay oriented within a larger collection. Unsupported files remain routes for the appropriate native reader.

A new catalog is empty until you register an existing store or import catalog metadata. If an upgrade appears empty, check the selected catalog before registering everything again. `GILES_CATALOG_HOME` selects a catalog directory; a corroborated Nova estate selects its existing `knowledge/giles/catalog.json`; otherwise the platform application-data default applies. To choose a particular catalog, run the following from the plugin root:

    python skills/rupert-giles-knowledge-steward/scripts/giles.py --catalog "<your data>/catalog.json" serve --port 0

Port 0 selects an available local port. If a fixed port is occupied, use that route or stop only your own prior Giles process. Keep private session URLs private.

### Put the reading to work

1. Open a supported source and select a useful passage, then choose **Collect selected passage**. **Collect this text chunk** keeps the displayed text when you need the whole bounded excerpt. Its source route and verification information travel with it.
2. Open the **Working tray**. Give the work a title and describe the question or task. Add interpretation in the tray's annotations; the original source is preserved.
3. Collect a second source and choose **Compare two sources** to read the retained passages together. This shows their contents without inventing agreement or a verdict.
4. Choose **Save task & notes** to retain the working material. **Export working tray** downloads a recoverable JSON copy; **Import working tray** restores it and shows current source verification separately.
5. Choose **Compile knowledge packet**, then **Download Markdown packet** or **Copy packet for Nova**. Check the question, quoted material and original routes before asking Nova to continue the work.

You are done when the useful material can be followed back to its sources and carried into the next task. The tray lives beside the catalog, separately from the original archives. Reopening a collected source can reveal that it changed; your retained quotation remains a snapshot.

### Keep collections findable

Open **Catalog tools** when you need to register or maintain a pointer. Give an existing collection a recognizable name, its actual location, a plain description and useful entry points. Preserve honest inspection states. Export the catalog for recovery; back up the source collection separately.

Catalog imports merge stable store identities. Conflicts and stale saves stop for inspection rather than silently replacing newer metadata. If a catalog cannot be read, preserve it, inspect the startup error and restore a known export to the intended data path. Removing a catalog record removes the pointer, not its source. The supplied skill's `workspace/README.md` is the detailed reference.

## Dennis: follow an outcome to its next action

Project Bridge reuses the exact `DENNIS_PROJECT_HOME` discovered through Nova Operations. Its equivalent agent route is `python skills/nova-operations/scripts/nova_estate.py run project-bridge --`. If the existing project selector is missing, use Nova Operations' supported estate setup under the approved root. The Free edition does not create a standalone fallback.

Select the actual project and read its outcome, next action, milestone/dependency route and evidence before changing the native record. Missing dates or unfinished acceptance remain missing or unfinished. Use the native save/export flow, then reload the record to confirm the intended field persisted. Ember bridge, Survey folio and Redline present the same records through distinct working surfaces; the focused route exposes live work first and Show all stations reveals declared-complete work. A skin never changes completion.

## OMNARA: work from campaign evidence

Open or import a native campaign vault, then follow its research question, evidence and claim-support gaps. Supply dated sources; a source count never proves reading or support. Use the campaign room's native save/export path and reopen the saved campaign when resuming. The default or selected campaign home stays outside installation and adds no Nova selector. Back up that owner data, not merely the installed files.

## AnswerLayer: compare wording and prepare a working file

Choose **Open an answer record** for an existing ledger or **Example** for the synthetic teaching ledger. **Current answer** and **Proposed wording** keep the baseline, cutoff, exact before/after text and referenced evidence together. Select a proposed change to inspect its recorded status, scope and authority; missing source IDs remain missing. **Changes & exclusions**, **Evidence** and **Recheck triggers** reveal the retained states and conditions without running a monitor.

**Edit working file** opens the complete native JSON. **Apply to working copy** changes only page memory; **Validate** checks structure, not truth, approval or freshness. **Save working file** downloads your copy without changing the original or adopting a proposal. Save before closing/reloading, then reopen that file to resume. **Cancel** preserves the prior working document. Strata and Switchyard are distinct dark environments for the same ledger.

## Beryl: compare predictions against recorded tests

Choose **Open case** or **Explore example**. The diagnostic field keeps the reported fault and original conditions beside rival predictions, a selected test and its actual recorded result. **Compare predictions** restores equal emphasis; open an evidence receipt to inspect its source and limits while preserving orientation. A planned test remains distinct from a performed test; an unknown result remains unknown.

**Recovery & proof** shows interventions and retesting. **IT review** opens a separate advisory artifact whose selected binding is not authenticated. Recording a test result requires a performed confirmation, actual result, evidence kind and source; it changes the tab's working copy and marks an existing review stale. It does not perform a physical test or repair.

**Edit case JSON**, **Use working copy**, **Check structure** and **Download copy** preserve the original file and the in-memory/download boundaries. Save before replacing edited work or closing. Mossglass, Night Probe and Cinder Relay change the comparison environment while preserving the case and selection.

## Observatory: follow an evidence snapshot

Use **Investigation files** to open a native `cd-observatory-case/v1` JSON and, if useful, a supplied comparison baseline. The synthetic Harbor Lantern example is dated teaching material. **Situation** keeps the latest recorded assessment beside the next human move; **Sequence** separates event, observation, publication and retrieval clocks. **Evidence chains**, **Challenge** and **Sources** follow recorded claims, references and rival explanations. Selecting an item reveals its exact record without losing the broader view.

**Compare** shows structural differences by typed ID as **NEW**, **CHANGED** or **NO LONGER REPRESENTED**. Those labels are not reviewed material-change judgments. Invalid formats, duplicate IDs and files over5 MB leave the prior case selected. **Clear private case data**, close or reload discards memory. The atlas does not collect, monitor, edit, save or publish. Signal room and Evidence folio are dark views of the same supplied snapshot.

## Knowledge Desk: browse the retained material

Ask Nova to open Knowledge Desk after the optional estate is configured. Start with **Collections** and choose a recognizable collection or section. Read an original document or image beside its location, or choose **Saved notes**, **Reminders** or **People** for retained personal context. **Search…** narrows a view when you already know a fragment; it is optional.

Add useful passages to **Working set**, state the task and download a reading packet with original locations. The catalog refreshes while preserving open reading, search scope and the working set. That working set is temporary in the page: download anything you need before closing or reloading.

**Appearance** offers Ember stacks, Survey cloth and Proof press. They change material, typography and organization while keeping the same information. Knowledge Desk opens on the dark Ember stacks environment.

Personal context comes through the existing read-only owner adapters. Their availability and scope remain visible; restricted material stays excluded. An unavailable owner is not an empty collection. Preserve its diagnostic and use the supported owner recovery route. Record corrections and notebook edits go through the actual source workflow. The desk does not create a second knowledge store or edit originals.

## Recovery and evidence limits

For a memory-only desk, download intended work before reload; the original file remains unchanged. For a persistent native owner, use its save/export receipt and confirm by reopening. For a missing private session, reopen the existing launcher rather than changing a database. Do not confuse a saved revision with validated truth, permission or real-world completion.

Windows review exercised native data and persistence workflows and inspected actual wide and narrow screenshots across the supplied themes. Package checks establish the exercised byte, path and contract properties. Fresh-host discovery, macOS live launch and assistive-technology conformance remain separate observations. Consult the included owner's workspace guide when its labels, schema or launcher changes.


## Oracle Reading

Ask Nova for a tarot, rune or I Ching reading, or to explore your astrology. Oracle Reading receives the question conversationally, casts with its included tools and lays symbols beside the conversation when a visual view helps. The AI conducts the interpretation; the table supports shared attention. Astrology interpretation uses supplied or verified chart data.

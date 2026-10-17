# Open the native workspaces

Nova Free 4.1.0 includes seven optional apps under its existing capability owners. Choose by the work you want to do. Ordinary Nova conversation needs no app or persistent estate. Extract the complete edition first. The paths below start at `codex/plugins/nova-the-optimal-ai` or `claude/nova-the-optimal-ai` in the customer package.

## Choose a useful starting point

| Your task | App and Windows launcher | First useful outcome |
| --- | --- | --- |
| Find and use something in your collections | Giles: `skills/rupert-giles-knowledge-steward/Open Giles.cmd` | Find a source, collect passages and make a readable knowledge packet. |
| Move a project forward | Dennis: `skills/dennis-stratton-project-management/Open Project Bridge.cmd` | Resume an existing project, inspect dependencies and update its next action. |
| Investigate a broad question | OMNARA: `skills/omnara-deep-research/Open.cmd` | Read material, connect findings and write an answer with sources. |
| Update guidance you rely on | AnswerLayer: `skills/answerlayer/workspace/Open.cmd` | Compare new developments with current wording and retain a reasoned revision. |
| Diagnose a device problem | Beryl: `skills/beryl-it-tech/workspace/Open.cmd` | Compare explanations, plan a discriminating test and retain what actually happened. |
| Understand a changing situation | Observatory: `skills/current-intelligence-observatory/workspace/Open.cmd` | Connect sources and event times to claims, uncertainty and a useful brief. |
| Read across retained knowledge and context | Knowledge Desk: `skills/commonplace/workspace/Open.cmd` | Collect useful source material into a temporary working set and download a reading packet. |

These local apps require Python 3.10+ and a modern browser; Python packages needed for their ordinary shipped flows are included. Each Windows launcher has a neighboring macOS `.command` route. macOS wrappers are supplied but were not executed on this Windows qualification host. Open the launcher rather than directly opening an HTML file for an app that needs its local save service.

The four revised apps begin from ordinary input. Legacy native-format viewers remain advanced routes for existing specialized records. Research, interpretation and diagnosis come from you and an actual Nova conversation; the local apps do not fabricate model replies, fetch sources merely because a URL was entered, operate a device or publish your work.

## Open, save and return

1. Open the matching launcher. Check the app title and displayed work location. Its private loopback address belongs to this local session; keep it private.
2. Create the question, answer or case you actually need. Attach or paste source material only where it helps that task. Known source paths and originals remain distinguishable from retained working copies.
3. Use the app's save control and read its status. Reopen or reload to confirm that the intended work returns before relying on it.
4. Back up the displayed data folder and use the app's backup/export routes. A readable brief is a useful handoff, but it is not necessarily a complete backup of original attachments.

The package includes each app's own native icon resources. Installation does not automatically create desktop shortcuts. Existing shortcuts should point to the current packaged launcher and that app's included icon. See the skill's guide for any supplied shortcut helper.

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

## OMNARA: turn a question into a sourced answer

Open **OMNARA** through its launcher. Start with your question and why its answer matters. Plan explicit searches, or go directly to material you already have. Search links open a browser; they do not pretend a search was completed.

Add ordinary text, a document or image, or paste a useful passage. Read it, retain its source and limits, and connect selected text to a finding. Write your current answer in your own words with source references. Export the readable answer when it is ready to carry into a conversation or document. Source counts do not establish that a claim is supported.

The studio uses OMNARA's existing campaign vault. **Work folder** lets you browse relevant local files and choose a work folder. Keep the vault and retained material outside the installed skill, and reopen the same location to resume. The advanced campaign tools remain available when their deeper native fields are useful. The skill's `workspace/WORKING-GUIDE.md` describes the current controls and file limits.

## AnswerLayer: keep relied-on guidance current

Choose **Track an answer**, give it a useful name, paste the wording you rely on and describe who uses it. **Save working answer** retains the reference. Use **Add a development** for a new fact, correction, upcoming change or question. Keep its passage and source location; mark it examined only after actually examining it. An optional supporting file is retained privately, not interpreted automatically.

Write the proposed wording and the reason it should change. **Compare wording** exposes additions and removals. **Adopt as my local answer** retains the before/after history and evidence snapshot. It changes only your local working answer. A sound conclusion may also be no change. **Download answer brief** produces readable Markdown with the current answer, developments and next check.

The footer shows the saved data location. Use **Back up workspace** and **Restore backup** for portable copies; restore adds copies instead of replacing your existing answers. To select another location, launch `Open.cmd --data-home "<your answer folder>"`. **Advanced native records** preserves the older governed record viewer; changes there still require its download route. Read `workspace/README.md` inside the skill for exact limits and stale-save recovery.

## Beryl: diagnose the problem you actually have

Choose **Start a case** and describe the device, symptom and desired result. In **Device & problem**, preserve the exact error, triggers, working functions and recent changes. **Scope & data care** keeps actual authority, hazards and backup conditions nearby. The app does not inspect or alter a device.

Use **Explanations** to compare possible mechanisms and their predictions. **Plan a test** records what observation would separate them, along with prerequisites and stop conditions. After you actually perform a test, choose **Record observed result** and preserve its source and limits. **Observations & files** can retain a relevant log, document or photo; supported small text files and common images preview locally.

**Record a change** distinguishes a proposed intervention from an applied one. **Retest & outcome** records what happened under the original conditions and what would reopen the case. A recorded resolved state is not independent certification. **Download handoff** provides a readable brief for Nova or a technician, without sending it.

Select saved cases at the top, and read each save result. **Back up all cases** includes attachments; **Download copy** is the compatible native case export. **Restore backup** adds copies. Launch `Open.cmd --data-home "<your case folder>"` to select a different writable location. Read the skill's `workspace/README.md` before recovery or claiming a verified repair.

## Observatory: investigate a changing situation

Choose **Start with a question**, state the decision or understanding it should support, and record an evidence cutoff with the timezone if known. Search links open explicit browser searches. **Read material I have** accepts ordinary files or pasted text; nothing is fetched just because a source URL is recorded.

Read a source and select the exact passage that bears on a claim. **Connect evidence to a claim** retains its locator, relationship and limits. Several sources can support, challenge or contextualize one claim. In **What happened when**, preserve event and observation times as supplied; a missing timezone stays unknown. Publication and retrieval are different clocks.

Use **Test explanations** when competing mechanisms matter. Record what favors or challenges each and an obtainable observation that could distinguish them. In **Brief & return**, write your current answer and prepare an editable brief from the notes. Read and revise it before downloading. The next question, baseline and return date guide your next visit; they do not start background monitoring.

Your inquiry persists in the displayed work folder. **Work folder** lets you select sources and change that location. Back up the folder, including retained originals. **More tools → Evidence Atlas** opens the previous Evidence Atlas for an existing specialized case. It does not convert a working inquiry into a formally reviewed native case. See the skill's `workspace/README.md` for recovery and extraction limits.

## Knowledge Desk: browse the retained material

Ask Nova to open Knowledge Desk after the optional estate is configured. Start with **Collections** and choose a recognizable collection or section. Read an original document or image beside its location, or choose **Saved notes**, **Reminders** or **People** for retained personal context. **Search…** narrows a view when you already know a fragment; it is optional.

Add useful passages to **Working set**, state the task and download a reading packet with original locations. The catalog refreshes while preserving open reading, search scope and the working set. That working set is temporary in the page: download anything you need before closing or reloading.

**Appearance** offers Ember stacks, Survey cloth and Proof press. They change material, typography and organization while keeping the same information. Knowledge Desk opens on the dark Ember stacks environment.

Personal context comes through the existing read-only owner adapters. Their availability and scope remain visible; restricted material stays excluded. An unavailable owner is not an empty collection. Preserve its diagnostic and use the supported owner recovery route. Record corrections and notebook edits go through the actual source workflow. The desk does not create a second knowledge store or edit originals.

## Recovery and evidence limits

If an app looks empty after upgrading, check its displayed work location before creating a replacement store. Open the known existing folder with its chooser or supported `--data-home` option. An inaccessible or unreadable folder is an error to inspect, not proof that your work is gone. Preserve the original folder before recovery.

When another window has saved newer work, a stale-save refusal protects that newer revision. Preserve the unsaved copy with the app's backup/export, reload, and reconcile deliberately. Do not overwrite the newer data to clear the message. Knowledge Desk's working set remains temporary: download its reading packet before closing. Giles and Dennis retain their existing owner-specific save and recovery behavior.

Windows checks exercise the packaged launch and ordinary work paths. macOS live launch, fresh-host model discovery and assistive-technology conformance remain separate observations. Follow the included skill guide when a schema, label or launcher changes.

## Oracle Reading

Ask Nova for a tarot, rune or I Ching reading, or to explore your astrology. Oracle Reading receives the question conversationally, casts with its included tools and lays symbols beside the conversation when a visual view helps. The AI conducts the interpretation; the table supports shared attention. Astrology interpretation uses supplied or verified chart data.

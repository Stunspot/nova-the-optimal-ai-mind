# Upgrade to Free 3.8.1

Install the complete 3.8.1 edition using your existing host route. The Observatory gains optional OSINT setup and report attachment; [follow the setup guide](OSINT.md) to enable external tools. Existing owner records keep their formats. Preserve your prior package for rollback and check a fresh Nova invocation.

## Earlier upgrade paths

## Upgrade from Free 3.7.0

Free 3.8.0 adds Oracle Reading 0.2.0: conversational tarot, astrology, runes and I Ching, exact casting tools, card artwork and an optional shared visual table. The edition contains 28 native skills. MIND 0.4.0, Worldline / Cognitive Continuity 0.3.0 and your external owner stores keep their existing formats.

Preserve your previous package and host binding for rollback, then install the complete 3.8.0 edition through the same host route. Start a fresh task, verify a useful Nova invocation, and ask for an Oracle reading if you want to check the added skill. Astrology interpretation needs supplied or verified chart data.

## Upgrade from Free 3.5.0

The intervening 3.6.0 and 3.7.0 releases added Giles Knowledge Atlas and repaired the native desks. Installing the complete 3.8.0 package includes those changes as well as Oracle Reading. No source-archive move or catalog migration is required.

If you use Giles, open the same external catalog path and confirm a known collection still resolves. A new catalog is empty; an empty default path after an upgrade does not establish lost archives. Export your catalog before editing its metadata. Use the [Giles recovery procedure](VISUAL-WORKSPACES.md#keep-the-route-and-recover-safely) for stale saves, import conflicts or unreadable metadata. Rolling back the plugin does not require deleting the catalog or a source store.

## Upgrade from Free 2.x


Free 3.8.0 is a major topology change from Free 2.x. Inspect the live host before changing it. Record installed marketplaces and plugins, locate any old MIND hook, database, Ollama model, and Continuity workspace, and preserve the exact current state.

Extract Free 3.8.0 to a separate staging folder and inspect it first. Free 2.x and 3.8.0 share the `nova-the-optimal-ai` plugin ID, so the host cannot keep both versions active under that selector. Preserve the old package, marketplace source, and configuration for rollback; then obtain approval before installing 3.8.0 over that binding. Disable the old `augment-of-mind` route before the first 3.8.0 behavior probe so two MIND sources do not compete. Open a new task, verify actual discovery and one Nova invocation, and only then consider removing obsolete 2.x configuration.

The old MIND database, hook trust decision, Ollama model, exported reports, and generated user artifacts are separate data and configuration objects. The new installer does not delete them. Remove each only after resolving its exact path, confirming it is obsolete, and choosing a recoverable method.

## Trellis 1.1.0 artifact boundary

Earlier Free 3.1.2 bytes may contain Trellis 1.0.x and v1 Model Agnosticism artifacts. Free 3.8.0 carries the repaired Trellis runtime and keeps MIND at 0.4.0, but Trellis 1.1.0 accepts only `cd-model-agnosticism-model-set/v2` and `cd-model-agnosticism-observation-sequence/v2` inputs and emits only v2 receipts.

There is no automatic v1-to-v2 Trellis migration. Preserve every v1 input and receipt byte-for-byte as historical evidence; structural recognition by the v2 receipt schema does not rerun, endorse, or upgrade the old calculation. To run the current engine, construct a new v2 model set and observation sequence with explicit epistemic lane, candidate-selection and stopping contracts, structured step semantics, parameter provenance, and the current comparison and calibration bindings. Do not relabel a v1 document or rewrite a historical receipt. When the original inputs or a defensible v2 mapping cannot be recovered, retain the history and return to qualitative Model Agnosticism rather than manufacturing a current result.

An existing Nova estate can be inspected and refreshed through Nova Operations. Free Nova preserves larger-edition selector keys but does not inject their services. Back up or export customer records separately before any migration.

Plugin removal never implies data removal. Keep the estate unless the user explicitly requests deletion, understands the scope, and has any needed export or backup.

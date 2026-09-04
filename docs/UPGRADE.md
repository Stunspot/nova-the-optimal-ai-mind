# Upgrade and removal

Free 3.1.2 is a major topology change from Free 2.x. Inspect the live host before changing it. Record installed marketplaces and plugins, locate any old MIND hook, database, Ollama model, and Continuity workspace, and preserve the exact current state.

Extract Free 3.1.2 to a separate staging folder and inspect it first. Free 2.x and 3.1.2 share the `nova-the-optimal-ai` plugin ID, so the host cannot keep both versions active under that selector. Preserve the old package, marketplace source, and configuration for rollback; then obtain approval before installing 3.1.2 over that binding. Disable the old `augment-of-mind` route before the first 3.1.2 behavior probe so two MIND sources do not compete. Open a new task, verify actual discovery and one Nova invocation, and only then consider removing obsolete 2.x configuration.

The old MIND database, hook trust decision, Ollama model, exported reports, and generated user artifacts are separate data and configuration objects. The new installer does not delete them. Remove each only after resolving its exact path, confirming it is obsolete, and choosing a recoverable method.

## Trellis 1.1.0 artifact boundary

Earlier Free 3.1.2 bytes may contain Trellis 1.0.x and v1 Model Agnosticism artifacts. The repaired package keeps the product at Free 3.1.2 and MIND at 0.3.1, but Trellis 1.1.0 accepts only `cd-model-agnosticism-model-set/v2` and `cd-model-agnosticism-observation-sequence/v2` inputs and emits only v2 receipts.

There is no automatic v1-to-v2 Trellis migration. Preserve every v1 input and receipt byte-for-byte as historical evidence; structural recognition by the v2 receipt schema does not rerun, endorse, or upgrade the old calculation. To run the current engine, construct a new v2 model set and observation sequence with explicit epistemic lane, candidate-selection and stopping contracts, structured step semantics, parameter provenance, and the current comparison and calibration bindings. Do not relabel a v1 document or rewrite a historical receipt. When the original inputs or a defensible v2 mapping cannot be recovered, retain the history and return to qualitative Model Agnosticism rather than manufacturing a current result.

An existing Nova estate can be inspected and refreshed through Nova Operations. Free Nova preserves larger-edition selector keys but does not inject their services. Back up or export customer records separately before any migration.

Plugin removal never implies data removal. Keep the estate unless the user explicitly requests deletion, understands the scope, and has any needed export or backup.

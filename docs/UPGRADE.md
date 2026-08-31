# Upgrade and removal

Free 3.1.0 is a major topology change from Free 2.x. Inspect the live host before changing it. Record installed marketplaces and plugins, locate any old MIND hook, database, Ollama model, and Continuity workspace, and preserve the exact current state.

Extract Free 3.1.0 to a separate staging folder and inspect it first. Free 2.x and 3.1.0 share the `nova-the-optimal-ai` plugin ID, so the host cannot keep both versions active under that selector. Preserve the old package, marketplace source, and configuration for rollback; then obtain approval before installing 3.1.0 over that binding. Disable the old `augment-of-mind` route before the first 3.1.0 behavior probe so two MIND sources do not compete. Open a new task, verify actual discovery and one Nova invocation, and only then consider removing obsolete 2.x configuration.

The old MIND database, hook trust decision, Ollama model, exported reports, and generated user artifacts are separate data and configuration objects. The new installer does not delete them. Remove each only after resolving its exact path, confirming it is obsolete, and choosing a recoverable method.

An existing Nova estate can be inspected and refreshed through Nova Operations. Free Nova preserves larger-edition selector keys but does not inject their services. Back up or export customer records separately before any migration.

Plugin removal never implies data removal. Keep the estate unless the user explicitly requests deletion, understands the scope, and has any needed export or backup.

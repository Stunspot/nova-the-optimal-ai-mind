# Nova estate contract

The state formats remain nova-path-selectors/v1 and nova-estate-manifest/v1 across Nova editions. NOVA_DATA_ROOT names one customer-controlled absolute root outside .codex. Its authoritative registry is estate/path-selectors.json.

Free Nova requires exact active values for NOVA_DATA_ROOT, NOVA_CONTINUITY_HOME, DUNBAR_STORE, and CORKBOARD_HOME. It may read an estate that also contains edition selectors such as DENNIS_PROJECT_HOME, but it preserves those values as opaque extras and does not inject, create, repair, or claim their services. MIND_CORE_DATABASE and MIND_HOOK_RECEIPT_DIRECTORY remain null because Free 3.0.0 requires no prompt hook, embeddings, vector database, local model, daemon, or Arm's Reach layer.

The registry is configuration, not user state. Cognitive Continuity, Dunbar, and Corkboard own their records. Nova Operations reads the registry stably, rejects paths that escape the root or cross symbolic-link or reparse edges, removes inherited managed selectors, injects the exact Free selector snapshot, and starts the selected bundled service without a shell. Global environment variables are not the correctness path.

The operating-system default estate is discovered directly. A customer-approved nondefault root is remembered by nova-current-estate-locator/v1 at the platform per-user configuration location. This is a root pointer only; the estate registry must corroborate it. A malformed or conflicting pointer fails closed.

Initialization stages the complete estate beside the final root, initializes Cognitive Continuity, writes the manifest and helper environment text, writes the registry last, and atomically renames the completed stage into place. A failed attempt removes only its own staging residue and newly created empty parents.

The only existing-root automatic repair recognizes the exact empty footprint left by the old Nova Emergent 1.0.0 initialization failure. It revalidates that footprint immediately before replacement. Any unknown file, directory, symbolic link, or reparse edge disables automatic repair and is preserved.

Upgrade refreshes the Free product binding, required service map, manifest, and registry metadata. It preserves customer records and unknown extra selectors. It never moves, merges, initializes over, or deletes service data. Conflicting core selectors or current-estate pointers stop before mutation.

The optional --apply-user-environment flag is Windows-only convenience. It copies the four Free selectors to the current user's environment; a new process is needed to observe those copies. The launcher itself never needs this change.

Status and doctor report Continuity read and mutation support independently. Readable state on a filesystem the canonical Continuity runtime will not mutate is read_only, not healthy full operation. Exports, forget plans, and recovery backups require user-chosen destinations outside .codex, the active Continuity source, and every active Nova selector boundary.

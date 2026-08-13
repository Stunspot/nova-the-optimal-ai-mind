# State and authority

The v2 campaign ledger compiles state; it does not concatenate notes. Canon requires GM approval. Observations record play. Choices record player action. Consequences remain proposed until the GM accepts the causal ruling. Rumors stay uncertain. Secrets stay GM-only. Superseded and retired material remain historical without competing with active canon.

A context object's tenure names when and where it applies. Its provenance names where it came from. Its confidence is not its authority. Imported published material may be high-confidence reference and still lack authority over the campaign. Unknown legacy values survive migration under `extensions.legacy_v0_1`; unknown kinds remain `quarantined_unmapped` until a person defines their export meaning.

Exports are immutable one-way projections. A generic pack, Alchemy JSON, Foundry module, or successful VTT import never becomes canon merely by existing or loading. Adapters may map and lose fields, but they may not mutate the ledger. A `cd-ludis-import-observation/v1` receipt records one unauthenticated local attempt against exact bytes and is fixed to `promotes_product_compatibility: false`; only separately governed product evidence may change a compatibility claim.

Player-safe export is a separate exact-byte approval. Build GM and player audiences separately. The candidate, preview, and audit exist before approval. Extract a review copy, compare every member with that inventory and audit, inspect or listen to non-rendered members, and treat code as text without executing it. Any later byte change stales that approval. A player-safe object that directly or transitively reaches a secret is not safe.

`--gm-approved` and `--asserted-by` record unauthenticated local operator assertions under ordinary filesystem custody. Ludis binds an assertion to state or artifact digests; it does not authenticate the human, sign the artifact, encrypt campaign data, or grant social authority.
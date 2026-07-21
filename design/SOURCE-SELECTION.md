# Source selection and contamination boundary

## Import rule

Import only operational intelligence needed by Nova. Preserve provenance outside model-facing runtime. Exclude completed worlds, finished demo outputs, live stores, personal records, caches, archives, promotional boilerplate, obsolete persona wrappers, and test corpora that need not load during ordinary use.

| Runtime surface | Selected source | Import shape | Required exclusions or transformations |
|---|---|---|---|
| MIND | MIND maintained-source workspace | Complete maintained plugin source | Re-version product to 1.0.0; fix Continuity date handling; rebuild fingerprints and evidence |
| Corkboard | Corkboard managed-skill source | Complete skill | No live database is present; retain generic tests |
| Dunbar | Dunbar canonical product source | Complete runtime | Replace every named-user-specific owner/observer reference with user/account-holder language |
| OMNARA | OMNARA managed-skill source | Curated runtime | Exclude legacy OMNARA/WebWorker persona sources, completed demonstration, eval corpus, and optional architecture report; make the focused research intelligence standalone |
| Knowledge stewardship | Knowledge-steward managed-skill source | Curated runtime | Exclude legacy persona wrapper/contact block; keep stewardship doctrine and tools |
| Retrieval Intelligence | Retrieval Intelligence maintained-source workspace | Runtime core | Exclude demo corpus and eval fixtures from ordinary runtime |
| Retrieval Reviewer | Retrieval Reviewer maintained-source workspace | Complete skill | None |
| Signal Loom | Signal Loom managed-skill source | Curated runtime | Exclude first-value output tree and 3.5 MB cover; remove promotional/signature fragments; retain necessary visual-story doctrine and validators |
| Agentic Coding | Agentic Coding canonical-adapter source | Complete adapter | Reframe UI trigger as operational proprioception without enlarging action authority |
| TestForge operator | TestForge maintained-source workspace | Runtime core | Exclude `__pycache__`, examples, eval fixtures, tests, sales/support documents, and package-only clutter |
| TestForge reviewer | TestForge maintained-source workspace | Runtime core | Exclude duplicated examples, eval fixtures, tests, and generated/package-only clutter |
| Ludis | Ludis managed-skill source | Curated runtime | Exclude Port Zindra, Bell Below Bracken, all worked-campaign/example trees, image covers, legacy README, personal biography, promotional copy, and forced persona wrappers; retain generic game instruments and add bounded fiction/character mode |
| Nova | New authored skill | New runtime | Canonical Nova persona adapter, routing, onboarding, professional context, and compatibility contract only |

## Known forbidden payloads

- `knowledge/canonical/worked-campaign/**`
- `examples/first-value/**` from Ludis and Signal Loom
- `Port Zindra`, `Zindra`, `The Bell Below Bracken`, or campaign-specific Bracken material
- the user's age, home region, family, contact address, or private biography
- Discord/Patreon invitations and legacy response-wrapper instructions
- `__pycache__/**`, `*.pyc`, live `*.sqlite*`, credential files, archives, and generated output trees

## Final evidence

- `verification/source-import-ledger.json` records the initial imported files and exclusions with SHA-256 custody.
- `verification/transformation-map.json` accounts for every permitted post-import change, removal, and addition.
- `verification/shipping-directory-inventory.json` enumerates every final shipping directory and file with size and SHA-256.
- `verification/shipping-content-audit.md` records the semantic payload decision for all 28 skill roots.
- `verification/entry-static.json` passes path, type, content, topology, document-link, and transformation-custody checks.
- `release/release-receipt.json` and `verification/release-extraction-validation.json` bind the deterministic archives to the validated extracted payloads.

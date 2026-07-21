# Nova prompt-surface audit

Status: **PASS**

Nova 1.0.0 has **158 package-owned model-facing prompt modules** under the audit's semantic boundary: 30 primary surfaces and 128 conditionally loaded procedural modules. Every physical path has a current SHA-256 in the JSON ledger. The 128 conditional modules collapse to 97 review units only where bytes are identical; the 31 deduplications are TestForge operator/reviewer mirror pairs, and both physical paths remain recorded.

This includes all **32 Ludis instrument cores** and their routing index. It also includes conditional doctrine, adapters, fallbacks, personas, and faculty instructions wherever Nova or one of her shipping skills can load them. A directory named `knowledge` was not excluded merely because of its name.

## Boundary

Included means package-owned content that can act as procedural, persona, or discovery instruction under Nova, whether loaded directly, conditionally, or through a delegated skill. Excluded means machine-executed code and CI; schemas, manifests, receipts, and structured data not presented as instruction; factual dossiers, source catalogs, and knowledge-base records; output/data templates; static assets; and examples not loaded as instruction. The plugin contains 296 files: 158 are included and 138 are excluded by that rule.

## Result

- Physical modules reviewed: **158**
- Physical modules repaired: **54**
- Physical modules retained after review: **104**
- SHA-equivalence review units: **127**
- Review units repaired: **52**
- Review units retained after review: **75**
- Unreviewed in scope: **0**
- High- or medium-severity prompt findings remaining: **0**

The repairs put conceptual homes and desired transformations before procedure; removed obsolete framework theater and accidental tool assumptions from Ludis; tightened Dunbar activation and privacy truth; collapsed Nova's duplicated route map; repaired OMNARA's legacy inquiry directive; made Signal Loom's optional faculty library evidence- and stage-governed; and made TestForge host overlays inherit already-granted in-scope authority.

## Category coverage

| Conditional category | Physical modules | Review units |
|---|---:|---:|
| dunbar | 3 | 3 |
| ludis-continuum | 38 | 38 |
| omnara-deep-research | 11 | 11 |
| retrieval | 3 | 3 |
| rupert-giles-knowledge-steward | 1 | 1 |
| signal-loom | 8 | 8 |
| testforge | 64 | 33 |

## Verification

All 12 shipping skill roots pass the strict Codex validator with zero findings. Ludis passes curator validation and its shipping self-check at 32/32; explicit regeneration changes no curated core; the targeted legacy-residue scan returns zero matches. The full included path-and-hash inventory receipt is `80fa49f91b4999bc70d61be3870b9d95b2aa676a6bbc2b495f731b56c0d3b7eb`.

Run `python -X utf8 tools/audit_nova_prompt_surfaces.py --check` to prove that the human-readable report, JSON ledger, live file set, all 158 hashes, counts, decisions, and equivalence topology still agree.

This is static evidence about current prompt bytes, review disposition, and package hygiene. Live skill selection, routing, response quality, creative quality, and table performance require behavioral evidence rather than a greener shade of paperwork.

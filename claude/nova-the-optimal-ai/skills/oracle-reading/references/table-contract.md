# AI-operated reading table contract

The host AI conducts the encounter and authors this state. The renderer only validates and shows it. Read examples/tables for executable minimal records.

## Record and continuity

schema: oracle-reading/table-v1. id: nonempty string at most80 chars. revision: positive integer. tradition: tarot/runes/iching/astrology. phase: active (default), quiet, clear. Active/quiet require question ≤1500 chars and basis digital-random/user-supplied/illustrative. thread ≤400 chars is an earned shared phrase, not an automatic conclusion.

Tarot/runes results:1-10 unique catalog IDs, each {id,position,reversed,phrase?}. position≤100 chars; phrase≤160. Runes use upright convention. revealed is an explicit subset of IDs; focus is a revealed ID or null. Unrevealed cards show only their position and a quiet back; their identities remain in canonical state. Hidden identities are not secret from someone inspecting a generated file.

I Ching: lines is six integers6-9 bottom to top. showChanges and showRelated booleans, false initially. Related requires changes shown. focus null/primary/related; related focus needs visible related. Both figures and changes are recomputed from lines, not imported numbers.

Astrology: placements[{planet,sign,house?,phrase?}],1-10 unique planets. Optional house is an actual known integer1-12. aspects[{from,to,kind}] relates included planets using conjunction/sextile/square/trine/opposition; maximum20. source/system≤200chars preserve supplied basis/convention. focus null, an included planet or relations. This is a supplied relationship display, not a calculated natal wheel. It does not calculate aspect angles or current sky.

Unknown fields are stripped, known malformed fields reject. Imported strings render as text. Records≤100KB. Original oracle-reading/v1 records with catalogVersion0.1.0 are converted as existing cast basis, with all supplied symbols revealed; no automatic import of private journal storage or notes as chosen commitments.

A fresh reading starts revision1. Every continuation passes --previous canonical-record.json. Same ID preserves question, basis, tradition, positions/orientations and supplied chart facts. Increment revision by one; an identical normalized retry is allowed. Changed cast rejects rather than silently redrawing. Added interpretive phrases and display focus are mutable. If you consciously reframe/recast, begin a fresh ID and explain that action.

Quiet hides the visual while retaining the reading record; private facts may remain in the generated quiet file. Clear projects only ID/revision/tradition/phase, with no personal payload embedded. Clear doesn't delete prior files or memory. To resume a retained earlier reading, use that earlier canonical state and a fresh revision-specific artifact, explicitly restoring it.

## Tool and host handoff

From skill root, Python3.10+:

```text
python scripts/show.py examples/tables/tarot.json --output /chosen/work/reading-r1.html --inline
python scripts/show.py reading-r2.json --previous reading-r1.json --output /chosen/work/reading-r2.html --inline
python scripts/show.py reading-r1.json --output /chosen/work/reading-r1-standalone.html
python scripts/show.py reading-r1.json --url
```

Paths in examples are placeholders for an authorized workspace. Inline output is a literal scoped fragment under1MB, with selected matching art embedded and no external calls. In Codex's supported inline surface, emit its native visualization content reference: visualize{"path":"/absolute/reading-r1.html"}. Use this host's visualization capability/instructions when available. On other hosts, use their actual supported artifact display or the self-contained standalone output; don't claim inline capability from a file's existence.

Tool receipt names ID, revision, phase, visible symbols, focus, output and hash. Render → display → inspect are separate states. Show/open that exact output and verify what is actually visible before continuing with picture-specific speech. Use revision-specific filenames or explicitly reload a shown file; a changed file doesn't update an existing tab. On interruption, read canonical state and reconcile displayed revision before interpreting. No user-operated reveal control, automatic continuation or recast exists.

--url returns the public companion URL with encoded record in its fragment. Only use it for an explicitly wanted browser/shared display. Fragment content can remain in browser history or copied links, and images on public page load from that same host. Prefer local/inline for private readings. No AI endpoint or credentials are in the table; the existing host model is the reader.

## Picture identity

assets/cards/manifest.json maps all78 exact IDs to bundled public-domain Rider-Waite-Smith Pam-A scans. Inspect the same local JPEG before making an image observation. Custom deck artwork belongs in the host's supported image display, not mislabeled as this deck. Missing art preserves named symbolism and loses picture-based observation. A maximum-size ten-card inline projection can exceed1MB: use standalone, or show a genuinely smaller reveal stage in the ongoing encounter; don't silently hide a card to fit bytes.


# Rupert Giles Knowledge Steward site source

The static project site is published from this `docs/` directory.

## Source and evidence boundary

The site describes the public contest edition in this repository. Its product claims are derived from:

- `SKILL.md`;
- `references/stewardship-doctrine.md`;
- `references/retrieval-and-compilation.md` for maintained retrieval/compilation method updates;
- `assets/knowledge-estate-ledger.template.md`.

The page does not claim that provenance establishes factual truth, that a proposed reorganization has been executed, that similarity proves identity, that the skill possesses blanket deletion authority, or that every host can install the standalone source independently.

## Files

- `index.html` — semantic single-page project overview;
- `style.css` — responsive presentation and accessibility treatment;
- `assets/rupert-giles-hero.png` — generated 1600×900 raster hero artwork;
- `.nojekyll` — direct static-file serving marker.

## Deployment

`.github/workflows/deploy-pages.yml` uploads this directory with GitHub's official Pages Actions. Repository Pages must be configured to use **GitHub Actions** before the first deployment can publish.

## Review notes

The page uses one H1, semantic landmarks, a skip link, visible keyboard focus, descriptive links, meaningful alternative text, responsive layout, and reduced-motion handling. These checks support structural accessibility only; they are not a claim of formal accessibility conformance or representative-user success.

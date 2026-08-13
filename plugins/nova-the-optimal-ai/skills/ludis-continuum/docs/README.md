# Ludis Continuum Pages source

This directory is the source for <https://stunspot.github.io/ludis-continuum/>.

## Customer journey

- `index.html` - product identity, four operating modes, campaign loop, ledger, instruments, export discovery, and trust edge.
- `start.html` - Codex, Claude Code, project-scoped, archive, and fallback installation; package/discovery/invocation verification; v2 campaign initialization.
- `guide.html` - inputs, outputs, representative workflows, campaign state, deterministic tools, offline export routing, and limitations.
- `exports.html` - neutral Ludis Packs, separate GM and player workflows, exact-byte approval, Alchemy character JSON, Foundry v14 offline modules, loss reports, target import steps, and recovery.
- `trust.html` - privacy, storage, security, evidence, exact-byte custody, static-versus-live support boundaries, recovery, update, removal, cleanup, accessibility, support, and license routes.
- `404.html` - useful recovery navigation for unknown paths.

All primary navigation bars link to `exports.html`. The home page and Start/Guide/Trust routes also provide task-context links so the page is not dependent on navigation discovery alone.

## Export-support language

The Pages site distinguishes file construction from live target behavior:

- neutral packs and target ZIPs are built and checked locally;
- Alchemy and Foundry adapters are statically validated against their documented contracts;
- live Alchemy import and Foundry v14.365 recognition, database acceptance, rendering, grid alignment, and repeat-run behavior remain unverified until separately observed;
- no MCP server, account connection, network request, cloud sync, or live VTT control is claimed.

Update `exports.html`, `trust.html`, and the repository evidence records together whenever a target profile or compatibility claim changes.

## Role-specific visuals

- `assets/ludis-continuum-readme-hero.png` - wide, text-free repository introduction; used only by the root README.
- `assets/ludis-continuum-pages-hero.png` - taller, text-free interactive-campaign composition; used as the Pages home hero.
- `assets/ludis-continuum-social-card.png` - 1200 by 630 share card with the exact product title and identifying line; used by Open Graph and Twitter metadata.

The assets are different compositions and aspect ratios, not crops. Their actual pixels must be reviewed after any change.

## Deployment

GitHub Pages publishes `docs/` from `main` through the repository's configured workflow. A successful workflow run establishes deployment execution only. Publication PASS also requires live route, content, navigation, metadata, asset, and custom-404 verification against the final commit.
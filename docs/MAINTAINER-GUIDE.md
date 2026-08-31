# Maintainer guide

This is a source-repository maintainer reference. The extracted customer package carries it for transparency but does not include a buildable source checkout.

## Canonical product sources

The distributable plugin source is plugins/nova-the-optimal-ai. Its LOADOUT-MANIFEST.json must name exactly twenty-seven sibling roots. MIND's seventeen Faculty Cores remain nested beneath skills/nova/references/mind/faculty-cores.

Import maintained capabilities through explicit source selection. Record repository commits and selected-tree digests in design/source-map.json, name every edition overlay, and regenerate design/source-lock.json. Generated Nova Emergent package trees are comparison evidence, not canonical inputs.

The root and plugin copies of LICENSE.md, ATTRIBUTION.md, NOTICE.md, TRADEMARKS.md, PROVENANCE.md, and THIRD-PARTY-NOTICES.md must remain byte-identical. The source lock hashes that rights bundle. Every detachable Claude skill receives a generated nova-free-rights envelope; do not modify protected TestForge or Agent Swarm payload trees to carry product paperwork.

## Qualification order

Before release sealing, regenerate the source lock, run the focused repository suite, run documentation and site checks, and complete fresh Hesperos and TestForge operator/reviewer cycles against a frozen source candidate. A product defect returns the candidate to builder custody and starts a new verification cutoff after repair.

Commit the accepted source and evidence checkpoint, confirm a completely clean repository including untracked files, then build once with tools/build_release.py --require-clean and verify the extracted package with tools/verify_package.py. Package checksums and archive hashes belong to this final construction step.

Static source and package evidence does not become fresh-host, model-behavior, publication, or customer-outcome evidence. A GitHub Actions run on a GitHub-hosted runner is evidence only when that exact run was authorized and observed; it is not required product machinery.

## Publication boundary

Never publish an intermediate candidate. Confirm rights custody, clean source, exact source lock, documentation review, TestForge review, deterministic archives, and package verification before proposing publication. Tagging, pushing, creating a GitHub release, deploying the site, submitting to a directory, or announcing the product requires separate user authority even though the included licenses permit redistribution.

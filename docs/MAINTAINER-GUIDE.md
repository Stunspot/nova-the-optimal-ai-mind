# Maintain Nova + MIND Free

This guide is for a maintainer changing the public package, not for a new customer trying to install it.

## Keep the sources straight

- `design/FREE-NOVA-PACKAGE-MAP.md` records what belongs in the Free product.
- `design/source-lock.json` records canonical sources and custody.
- `plugins/` contains the installable Codex packages.
- `bundle/reminder/` contains the Free reminder map.
- `tools/verify_package.py` checks source and release structure.
- `docs/` is the customer journey. Treat it as product surface, not leftover packaging.

## Add or change a bundled capability

Read the real source first; a filename is only a lead. Preserve canonical bytes or record a deliberate derivative. Copy a complete, self-contained skill root into the right plugin.

Then update the reminder map: give the capability useful public descriptions and relations, rebuild the local semantic assets, and qualify the changed profile. Update the source lock, customer docs, release artifacts, and verification evidence together.

## Preserve the product

Nova and MIND ship together in Free. MIND has exactly sixteen Faculties. TestForge ships with MIND as two attached skills. Reminder proximity is not ranking, selection, activation, or authority. Never put private paths, private capability inventories, credentials, or customer material in public runtime assets.

Agent Arena Competition and Impactful Tom remain excluded. Add writing or teaching Augments only through an explicit product decision.

## Build and review

```powershell
python -X utf8 tools\build_release.py
python -X utf8 tools\verify_package.py --release
```

Inspect the release manifest, checksums, final customer ZIP, representative Claude archives, public Pages, and the canonical artwork. Run TestForge after the candidate is complete.

Review the customer docs whenever installation, versions, included capabilities, reminder behavior, host support, privacy, or a recurring support failure changes. Run Hesperos and its accessibility review against the actual final bytes.

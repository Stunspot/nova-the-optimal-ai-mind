# Maintain Nova + MIND Free

## Sources of truth

- `design/FREE-NOVA-PACKAGE-MAP.md`: approved inclusion, exclusion, host, and acceptance decisions.
- `design/source-lock.json`: selected repository commits, paths, custody states, and tree hashes.
- `plugins/`: directly installable Codex source packages.
- `bundle/reminder/`: Free Nova's 41-capability estate.
- `tools/build_free_nova_associative_assets.py`: reviewed-card vector compiler.
- `tools/verify_package.py`: source and release structural contract.
- `docs/`: Hesperos customer journey.

Do not edit the frozen contest repository to maintain this product. Import new source deliberately and update the lock.

## Change a bundled skill

1. Identify the canonical component repository and release boundary.
2. Read the actual skill content; a filename is only a discovery lead.
3. Preserve canonical bytes or record the derivative explicitly.
4. Copy the complete self-contained skill root into the correct plugin.
5. Update Nova's capability routing only if the transformation or collision boundary changes.
6. Update or add the capability card's six views and relations.
7. Rebuild the associative assets with local `qwen3-embedding:0.6b`.
8. Requalify the exact new cards, vectors, model, radius, and relations.
9. Update `source-lock.json`, documentation, release artifacts, and verification evidence.

## Preserve the product invariants

- Nova and MIND ship together in the Free product.
- MIND has exactly sixteen Faculties.
- TestForge ships inside MIND as two attached Augments.
- Nova's canonical persona remains verbatim.
- Reminder handles are proximity, not ranking or activation.
- No private filesystem path or inventory enters public runtime assets.
- Agent Arena Competition and Impactful Tom remain release-excluded.
- Writing and teaching Augments remain deferred until deliberately added.

## Build the release

```powershell
python -X utf8 tools\build_release.py
python -X utf8 tools\verify_package.py --release
```

Inspect `dist/SHA256SUMS.txt`, `dist/release-manifest.json`, the final customer ZIP, and representative Claude archives. Run TestForge after the candidate is complete.

## Documentation lifecycle

Owner: Collaborative Dynamics. Review customer docs whenever plugin commands, versions, installer behavior, capability count, profile status, host support, privacy behavior, or a recurring support failure changes. Re-run Hesperos authorship and accessibility review against current bytes after any material documentation change.
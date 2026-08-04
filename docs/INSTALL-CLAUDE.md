# Install the portable Claude skills

The Claude distribution contains one ZIP per skill under `dist/claude/zips/`. Each archive has one matching top-level folder and a direct `SKILL.md`.

These ZIPs are portable capability components. They do not reproduce the Codex plugin marketplace, prompt-submit hook, MIND Core database, MCP association service, automatic estate activation, or verified Nova-with-MIND invariant runtime.

## Build the ZIPs from source

Maintainers run:

```powershell
python -X utf8 .\tools\build_release.py
```

Customers using a release download should use the already-built ZIPs and verify them against `dist/SHA256SUMS.txt`.

## Upload one skill

1. Choose the ZIP whose filename matches the capability handle, for example `gridmason.zip`.
2. Upload the ZIP through Claude's skill-management interface.
3. Enable it if the host requires a separate enablement step.
4. Start a new conversation and request the capability naturally or by name.
5. Confirm that the skill's resources load and that any scripts it needs are permitted by the host.

Expected result: the individual skill is discoverable and can use only the resources contained in its own ZIP.

## Recreate the broadest portable set

Upload `nova.zip`, `augment-of-mind.zip`, the sixteen Faculty ZIPs, `software-verification.zip`, `verification-reviewer.zip`, `promptcraft.zip`, and any practical specialist ZIPs you want available.

This is a component set, not a claim of Codex-equivalent integration. Claude may impose skill-count, context, script, or tool limits. Cross-skill discovery, automatic reminder delivery, shared persistence, and hook behavior are `not tested` for this release.

## If upload fails

- Confirm the archive contains exactly one top-level folder with the same name as the ZIP.
- Confirm `SKILL.md` is directly inside that folder.
- Rebuild the release and rerun `python -X utf8 tools\verify_package.py --release`.
- Preserve the host error and exact ZIP hash.

Do not unzip several skills into one archive. Do not move references outside the skill root. Those shortcuts produce a topology puzzle wearing a tiny hat.
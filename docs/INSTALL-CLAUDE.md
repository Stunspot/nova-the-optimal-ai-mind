# Use the portable Claude skills

The release includes one ZIP per skill in `dist/claude/zips/`. Each ZIP is a self-contained capability you can upload through Claude’s skill-management interface.

These archives are portable skills, not a replica of the Codex package. They do not include the Codex marketplace, prompt hook, shared MIND database, or automatic reminder delivery.

## Upload a skill

1. Choose the ZIP that matches what you want, such as `gridmason.zip`.
2. Upload it through Claude’s skill-management interface.
3. Enable it if Claude asks you to.
4. Start a new conversation and ask for the outcome you want.

For example:

```text
Use Gridmason to help me plan a Minecraft build from this theme.
```

The expected result is that Claude can discover and use the contents of that one ZIP, subject to the permissions and limits of the host.

## Use a broader set

Upload `nova.zip`, `augment-of-mind.zip`, the sixteen Faculty ZIPs, the two TestForge ZIPs, `promptcraft.zip`, and whichever practical specialties you want. Claude may impose its own limits on skill count, context, scripts, or tools.

## If an upload fails

Check that the ZIP has one top-level folder matching its filename and that `SKILL.md` sits directly inside it. Preserve the host’s error and the archive hash. The archive can be structurally correct while a host still declines it; those are different problems.

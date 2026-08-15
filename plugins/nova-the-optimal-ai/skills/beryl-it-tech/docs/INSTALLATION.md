# Install and confirm discovery

This procedure prepares Beryl IT Benchcraft for a compatible Agent Skills host. Host interfaces and skill locations differ, so use the host’s current installation method rather than guessing a filesystem path.

## Before you begin

- Keep the complete `beryl-it-benchcraft-v0.1.3` release folder intact.
- Confirm that your host supports Agent Skills or an equivalent package mechanism.
- Obtain permission to add local skills to the host.
- Decide whether you also want the independent `$it-work-reviewer` capability.

Expected time: a few minutes after the host’s installation location or interface is known.

## Install in an Agent Skills host

1. Open the host’s skill-management or local-skill installation interface.

   - Expected result: you can add a local skill folder or register a package that exposes skill folders.

2. Add `skills/beryl-it-tech` while preserving the complete release tree around it.

   The skill uses package-relative files in `personas`, `knowledge`, `references`, `assets`, `scripts`, `examples`, and `fallbacks`. Copying only `SKILL.md` breaks those relationships.

   - Expected result: the host registers a skill named `beryl-it-tech` without missing-resource errors.

3. Add `skills/it-work-reviewer` if you want independent review.

   - Expected result: the host registers a second skill named `it-work-reviewer`.

4. Restart the host if it caches skill discovery, then start a new task.

5. Type this exact test:

   ```text
   $beryl-it-tech Help me frame a test case. Do not diagnose anything yet.
   ```

   - Expected result: the host recognizes `$beryl-it-tech`, and Beryl responds as one practitioner without asking you to paste package files.

6. If you installed the reviewer, type this exact test in another new task:

   ```text
   $it-work-reviewer Review this empty test case and tell me what evidence is missing.
   ```

   - Expected result: the host recognizes `$it-work-reviewer` and returns an evidence-focused review.

## Confirm installation

Installation is confirmed only when a fresh task discovers the skill and produces a response. A copied folder or successful package validation does not prove host discovery.

Record the host name and version, installation method, installed release version, discovery result, and any resource error. This makes later upgrades and troubleshooting reproducible.

## Use Beryl without skill support

1. Open [the universal workflow](../fallbacks/universal-copy-paste-workflow.md).
2. Copy the text inside its code block into your AI chat.
3. Append your problem after the `Problem or retained case:` marker.

This fallback preserves the core diagnostic method. It does not guarantee progressive file loading, case-file validation, host tools, or independent reviewer behavior.

## If installation does not work

Go to [The skill name is not recognized](TROUBLESHOOTING.md#the-skill-name-is-not-recognized). Preserve the release folder and any host error; do not flatten or rename package-relative directories while troubleshooting.

## Remove or replace the release

Use the host’s skill manager to unregister the installed copy. If the host uses a local skills directory, remove only the exact Beryl folders you installed. Do not delete the customer release or case files unless you intend to remove your source package and records as well.

After an upgrade, repeat the fresh-task discovery checks. Do not infer that a new version is active from the presence of new files alone.

# Install or open Omnara

The complete package has one `omnara-deep-research` folder containing SKILL.md, customer guides, references, scripts, examples and the campaign room. Keep it together. This is a portable individual skill, not a standalone universal Codex plugin manifest.

## Existing Nova Free or Emergent

Use the current edition package's own install/update instructions. Omnara is a maintained component in those editions. MIND is integrated architecture; the retired standalone MIND plugin is not an additional installation requirement. Do not replace unrelated edition files to repair one skill.

## Individual skill on a capable host

Attach the complete ZIP and ask “Install this Augment.” The host should inspect this guide, find its supported skill root, inspect any existing Omnara installation and use a recoverable replacement when updating. Import the complete `omnara-deep-research` directory through the host's supported skill mechanism. A copy is not activation: start a fresh session and check that the host exposes `omnara-deep-research` before invoking it. Hosts requiring plugin manifests need a supported Nova edition or their own documented packaging route; do not invent a plugin manifest.

Try: “Use $omnara-deep-research. Frame this question and identify the evidence that would change the answer. Do not browse yet.” Verify that the inquiry is preserved, scope is bounded and the no-browse limit is respected. That is one bounded invocation, not universal model qualification.

## Campaign room

Python 3.10+ is required. Extract to a stable writable application folder. On Windows run **Open.cmd**; on macOS/Linux use `python3 workspace/open.py`. **Open.command** invokes the same entry after `chmod +x Open.command`. Native macOS execution has not been exercised.

Choose existing research with `python workspace/open.py --data-root "your research folder"` or `OMNARA_HOME`. Otherwise the default is `Documents/OMNARA Campaigns`. The launcher starts/reconnects a private loopback service and opens its matching data home. Keep that folder outside the application. Shortcuts are optional and require the owner's request.

## Plain chat

Copy [the complete fallback](../fallbacks/universal-copy-paste-workflow.md), append your inquiry and supplied material, and use the tools actually available. Without browsing, live findings remain unexecuted; without file custody, durable resume remains unavailable. The doctrine still supports a bounded supplied-source answer.

## Check and continue

From the complete extracted root, run `python -B scripts/validate_release.py . --profile source`. Its packaged manifest checks exact delivered bytes and local dependencies. [Validation](VALIDATION.md) explains research checks; [START-HERE](../START-HERE.md) gets to a useful result; [Troubleshooting](TROUBLESHOOTING.md) restores a failed path. A local package check does not establish host discovery or semantic research quality.

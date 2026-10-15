# Understand what a check establishes

From this skill folder, `python -B scripts/validate_release.py .` checks required cargo and the exact manifest. Missing manifests, unexpected bytes and linked source custody fail. Maintainers can regenerate only after explaining an authorized change; a new manifest does not itself review that change.

Case structure and optional declared consistency are described in [case files](CASE-FILES.md). The Studio's **Check structure** displays both shape and separate consistency findings. Typed IDs, references and boolean execution flags are structural properties. Evidence source, retest and stale-closure checks inspect declarations only; a fabricated but well-shaped record can still lie.

Run `python -B -m unittest discover -s scripts/tests -v` for synthetic native evidence and inventory controls. Only in the separately installed Beryl operator skill, `python -B -m unittest discover -s workspace -v` exercises loopback/session and schema behavior. These tests use fixtures and disposable local service instances; they do not inspect or repair a real device.

`evals/` contains historical and newly revised model-scenario definitions. Current definitions are explicitly unexecuted as model trials. Earlier behavioral receipts remain applicable only to their recorded old fingerprints and runtimes. No count of local tests establishes representative-user usability, assistive-technology conformance, physical repair, production safety or universal model behavior. The complete bundle also has docs/VALIDATION.md at its outer root; this page is sufficient for a standalone skill.

# Privacy Redline entry repair — independent artifact acceptance

**PASS** for the bounded same-version artifact repair. The accepted interaction revision is present in the standalone Privacy Redline 0.2.0 kit, Nova Emergent 2.1.0 Codex/Claude/customer ZIPs, and Nova Free 4.4.0 Codex/Claude/customer ZIPs.

[artifact-acceptance.json](artifact-acceptance.json) contains the seven exact archive paths, verified SHA-256 values and byte sizes requested by the shelf transaction. [artifact-review-results.json](artifact-review-results.json) holds the executed comparison and extraction results. The interaction verdict remains separate: [interaction-verdict.json](interaction-verdict.json) is READY_WITH_RESIDUAL_RISK and names the same frozen runtime tree.

## What was established

The 48 Privacy runtime files match candidate-runtime.json in every checked surface: four parent native plugins, Free Claude's detached folder and nested Privacy ZIP, and the standalone kit's Codex, maintainer and nested Claude payloads. The nine changed component files match the reviewed revision. All 15 canonical originals remain identical to the accepted component baseline.

Each parent native archive retains the accepted baseline member inventory. Only the approved Privacy changes, PRIVACY-UPDATE.md, plugin/loadout repair metadata, Emergent checksums, Free wrapper BUILD-MANIFEST, and Free detached/nested Privacy payloads differ. Plugin and loadout JSON changes are limited to the build identity and bounded interaction-repair metadata. Every other member's uncompressed bytes, including unrelated nested ZIPs, remain identical to the accepted baseline.

| Native archive | Changed members | Preserved members |
|---|---:|---:|
| Emergent Codex | 13, including SHA256SUMS.txt | 7,600 |
| Emergent Claude | 13, including SHA256SUMS.txt | 7,599 |
| Free Codex | 13 | 1,515 |
| Free Claude | 23 | 3,215 |

Both customer wrappers retain their four-member topology and the exact accepted install-guide bytes. The embedded host ZIPs are the newly verified native artifacts. Internal checksum inventories and values, detached parent checksums, and reported artifact identities match the actual bytes. The standalone ZIP matches the builder-supplied identity and contains the reviewed runtime on all three delivery surfaces.

Windows' C:/Windows/System32/tar.exe (bsdtar 3.5.2) extracted every changed native member and the changed files in each applicable nested Privacy ZIP. Extracted bytes match archive bytes. Changed paths also pass the normalized-name, component-length and 260-character portable-path checks with a 60-character extraction-root allowance.

## Verifier correction

The initial check passed both Emergent natives, the Emergent wrapper and Free Codex, then rejected Free Claude's detached inventory because the verifier expected only 48 runtime files. Inspection showed that both accepted baseline and candidate also contain seven inherited nova-free-rights Markdown files. The same files occur in Free's nested Privacy ZIP.

This was a TEST_DEFECT. The single correction allowed exactly those seven inherited files and required byte equality for each. Completed artifact passes were retained with unchanged archive state; the uncompleted Free Claude, Free wrapper and standalone checks then passed. No product or packer edits were made by this reviewer.

## Scope and limits

This accepts artifact fidelity and extraction for the owner's ordinary-entry repair. It does not requalify unrelated services, fresh-host activation, live removals, broker compliance, model robustness or future runner enforcement. Native selective extraction was exercised; the Windows Explorer extraction UI was not. The interaction and runtime limitations remain those of the separate accepted instruction review.

Executed command: C:/Python314/python.exe -B independent_artifact_check.py, followed by the documented verifier correction and --resume continuation. The initial run's captured evidence is exec session 43473; the completed continuation exited 0 and produced the acceptance JSON. All work used the authorized elevated PowerShell workaround and wrote only review artifacts/extraction outputs.

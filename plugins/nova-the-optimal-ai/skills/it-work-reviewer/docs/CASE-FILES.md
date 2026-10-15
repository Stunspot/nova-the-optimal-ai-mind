# Reviewer: case files

This is the reviewer skill, which inspects supplied evidence. The optional Studio belongs to beryl-it-tech; it is not bundled in this folder.

The shared native case schema/helper is included for convenience. From this skill folder run `python -B scripts/validate_case_file.py path/to/case.json --consistency --json`. It checks declared structure/consistency, not factual truth or independent review. Preserve unknown fields, conflicts and prior evidence. A failed or stale repair claim is not repaired by deleting the failed observation.

See [the reviewer quick start](QUICK-START.md) and [review method](USER-GUIDE.md).

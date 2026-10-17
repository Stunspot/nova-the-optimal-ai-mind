# Keep integrity and review separate

From this skill folder run `python -B scripts/validate_release.py .` to check the exact native inventory. Case shape and selected declared-consistency checks use `python -B scripts/validate_case_file.py <case.json> --consistency --json`. These checks cannot establish that a claimed observation is true.

Synthetic tests under `scripts/tests` check native record and inventory behavior. Preserved model scenario definitions under `evals` are not new executed trials. Historical receipts retain their original fingerprint and runtime scope.

The separate Repair Companion's exact review binding is a custody property. It does not prove reviewer authorship, independence, device execution or repair. A fresh evidence review must still examine the actual decision under [the review method](USER-GUIDE.md).

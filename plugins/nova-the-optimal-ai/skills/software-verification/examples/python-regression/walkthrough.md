# Python regression walkthrough

This synthetic standard-library project demonstrates bug reproduction, boundary analysis, repository-compatible unittest authoring, failure classification, and a minimal corrective patch.

From this example directory:

```text
python -m unittest input.test_existing -v
python -m unittest expected.test_date_filter -v
python -m unittest expected.test_fixed_date_filter -v
```

The first command passes; the regression command fails because the start boundary is omitted. The third command exercises the exact one-line correction represented by `expected/fix.patch` against the same boundary partition and passes. `expected/execution-record.json` and `expected/post-fix-execution-record.json` preserve those pre- and post-fix results.

Apply `expected/fix.patch` only in a disposable copy, then rerun both commands. The packaged manifest intentionally records the pre-fix `NOT_READY` state so the demonstration does not erase the defect it teaches.

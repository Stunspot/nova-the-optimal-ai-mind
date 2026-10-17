# Demonstration: reproduce before repairing

Load when a small regression tempts an immediate one-character patch.

The existing test exercises an interior date and passes. The docstring says inclusive range; the implementation excludes `start`. TestForge first turns that discrepancy into a boundary partition—before, at start, interior, at end, after—and an oracle over the returned identifiers. The generated regression test fails on exactly the start case.

Only then does `fix.patch` become justified. A derived fixed copy verifies that exact correction against the same boundary partition; `post-fix-execution-record.json` retains the passing result. The canonical manifest deliberately remains the received revision's failing `PRODUCT_DEFECT` and `NOT_READY` state: evidence for a derived candidate does not silently rewrite the assessed revision. Applying the patch to the real target still requires maintainer authority and a fresh manifest revision.

The transferable behavior is evidence-preserving repair: reproduce the user-visible contract break, classify it, then change the smallest cause and re-run.

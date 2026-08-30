# Superseded Free 3.0.0 pre-review evidence — 6151da1

This subtree preserves the first Free 3.0.0 package, Hesperos, and TestForge operator cycle bound to source checkpoint `6151da1862c93e2af1755a5b79aee239816c5d1f`. It is historical evidence, not the current qualification packet.

Independent TestForge challenge found two process defects before issuing a reviewer verdict: builder-owned manifests prematurely declared `sealed_candidate=true`, and the root line-ending workflow still auto-ran on push and pull requests without a timeout while the metered plan claimed root workflows were manual-only. The product's public verdict was already `NOT_READY`, but these defects invalidated the process packet.

The source was repaired to make a clean build explicitly `built_awaiting_independent_review`, require review, reject premature seal fields, and make every root workflow manually dispatched and time-bounded. Current Free 3.0.0 evidence must bind to the later repaired checkpoint. Never promote the receipts in this subtree into a current readiness claim.
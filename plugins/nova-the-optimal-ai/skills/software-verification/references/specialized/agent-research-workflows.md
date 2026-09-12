# Test agent and research workflows at their evidence boundaries

Use for an explicitly submitted frozen workflow, evaluator or research-execution harness. TestForge verifies the software and the bounded execution claim. Scientific validity, sound experimental design and publication fitness need their own domain oracles. Do not turn this reference into an instruction to run a research campaign or extend ordinary implementation testing.

## Separate the claimants

Distinguish the worker that produces an artifact, the executor that records what ran, the evaluator that interprets it, and the closer that decides whether required work is complete. Inspect which identities the host actually enforces. A model-written success field, configured model name or writable result path is an assertion, not authenticated independent evidence. The same model behind two aliases is not two independent models.

For a run-bound claim, inspect its target revision, attempt identity, unit or stage, interpreter/executable, arguments, working directory, environment, start/end and raw outputs. A successful old attempt cannot complete a new unit. A result directory must reconcile the complete relevant artifact set, not only the files chosen for a summary. Preserve failed, interrupted, skipped, unavailable and unparsed outcomes and any explicit disposition. Capturing a command result does not prove that its descendant processes stopped or that all output producers were observed.

Use existing execution records during verification. Do not add custody hashes, seals or package receipts before the established final-release gate. When the product under test itself binds artifacts by hash or append-only events, exercise that product behavior as an oracle without sealing this submitted candidate. Hashes can detect changes relative to a trusted record; a process that can rewrite both data and record is outside that guarantee.

## Choose discriminating cases

Select cases that correspond to the submitted promise. Try a stale successful result attached to a fresh attempt; a wrong stage, interpreter or artifact root; a late output after apparent completion; an omitted failed repetition; an empty or malformed reviewer result; a provider fallback masquerading as the intended reviewer; and a changed candidate after review. Expect a truthful unresolved/failed disposition when evidence cannot support closure, rather than a fabricated score or silent skip.

For leases or resumable workers, test duplicate claims, expired ownership, heartbeat loss, reclamation and a late completion from the former owner. Only the current claim's fencing identity may commit a result. Timeout must distinguish stopping the direct process from stopping its descendants. Observe the actual platform mechanism for cancellation and joining before treating outputs as final; a Unix process-group assumption does not establish Windows behavior.

For a close command, independently reconcile required units, current-attempt evidence, failures, exclusions, reviewer disposition and outstanding writers. A worker's done message must not be the only oracle for end state. Required unavailable evidence remains unavailable; ordinary recorded progress is not completion. A read-only reconciler is useful when it inspects authoritative state and cannot repair away discrepancies while certifying them.

For multi-model review, preserve original responses, parse success and configured versus observed identity. If the application requires a quorum, test missing and duplicate identities against the eligible set fixed before execution. Never lower that denominator because calls failed. A decisive blocker remains a blocker even when the average score is high. Avoid introducing a quorum where the user's workflow does not require one.

Return decision-changing findings under the existing custody and stopping rules. A product defect ends the cycle. A repaired product is a new frozen candidate; one low-cost support-layer recovery remains the maximum allowed in the current cycle.

Lineage: independent adaptation from [AutoResearch at 0fa9a93](https://github.com/EvoMap/AutoResearch/tree/0fa9a9336fc84a6b069111adb03ca21fabb5394b), `ar-runtime/scripts/ar-workflow-engine.py`, `ar-supervisor.sh`, `ar-critic-contract.ts`, `ar-review-contract.ts` and `scripts/ar_run_manifest.py`. No upstream runtime or platform-specific implementation is copied.

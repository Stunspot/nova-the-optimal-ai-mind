# Evidence records that support the actual verdict

The manifest is assembled at a stable evidence cutoff. It records the candidate's declared revision and does not create a custody seal. Validation checks structure, consistency and local evidence presence when a root is supplied; it cannot authenticate an observation.

## Commands and observations are distinct

A completed command execution has kind command (the default), command tokens, integer exit_code, status, target_revision, environment and raw_evidence. A passed command has exit code zero. Its raw result must support the check's oracle; process success is not automatically task success.

A completed observational check has kind observation, procedure and observed arrays, source observed or supplied, recorder, environment, target_revision, status and raw_evidence. It has no fabricated shell command or exit code. Record actual actions and observed post-state; a proposed walkthrough stays unexecuted. Supplied observations retain their source and attribution rather than becoming the operator's own work.

Raw local locators are relative to the evidence root or absolute within it; fragment suffixes may name a record inside the file. External URLs or supplied: locators require identified reviewer inspection and preserve that limitation in the report. Run the validator with --root for local file checks. The report assembler defaults to the manifest directory; use --evidence-root if evidence is stored elsewhere. File presence proves neither content truth nor candidate identity by itself.

## Required, excluded and unfinished checks

Tests are decision-critical by default unless explicitly set false for a scope-grounded reason. Every decision-critical check must pass for either ready status. A non-applicable test needs applicability_reason; an explicitly decision-critical test cannot simply become non-applicable.

An unfinished noncritical test needs a specifically linked residual risk through test_ids. A ready residual record has statement, treatment, owner and revisit_condition. The accepted uncertainty must fit the release claim; reviewers reject labels chosen merely to get a green verdict. READY_WITH_RESIDUAL_RISK cannot waive a failed or missing decision-critical check.

## Support recovery preserves history

The one allowed support correction may retain a failed attempt with superseded_by naming a passing replacement and triage_finding_id naming a resolved TEST_DEFECT, TOOLING_FAILURE or ENVIRONMENT_FAILURE finding with evidence. Both attempts remain bound to this candidate revision and explicitly carry nonempty test_ids naming existing checks. The replacement must cover every failed check, and each failed check's current passing test record must point to that replacement execution. Do not infer missing legacy scope or substitute an unrelated health check. A corrected interpreter/command is permitted when it reruns the same check. The report preserves the original error, cause and replacement.

This route cannot excuse a product defect, multiple support corrections, an unresolved cause or a failed replacement. A repaired product is a different candidate cycle. Do not delete earlier attempts to make the record look clean.

## Review and authority

A ready record identifies reviewer, raw_evidence, target_revision and evidence_cutoff. Reviewer finding strings have explicit finding_dispositions with status resolved or non_blocking and a reason. Conditional review has named conditions with statement, status met/open and boolean blocking. An open blocking condition prevents readiness; open nonblocking conditions require the qualified residual-risk status.

READY is a technical result within the stated scope, never an authorization token. Preserve authority_required for a separate release action prominently. If the decision explicitly claims release authorization, set claims_release_authorization true and resolve all authority still required for that claim. Previously granted authority remains valid within its scope; tool absence does not reopen it.

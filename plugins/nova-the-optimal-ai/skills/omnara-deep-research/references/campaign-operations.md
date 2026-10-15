# Preserve the campaign, not the chat

The vault is the operational memory. Update state at the moment evidence changes it.

Source states mean:

- discovered: appeared in a result or citation trail;
- inspected: received a recorded relevance and access disposition;
- opened: readable source content was accessed; an unsuccessful attempt belongs in access notes and inaccessible state;
- deeply-read: the declared reading scope was actually read and a non-template evidence note records it; the validator cannot observe reading;
- excluded: retained with a reason;
- duplicate: linked to the canonical record;
- inaccessible: access failed or was outside authority;
- cited: at least one report marker resolves to it.

Reading events remain historical facts when a source is subsequently excluded or identified as a duplicate. Preserve opened/deeply-read, add the exclusion reason or duplicate_of canonical ID, and remove cited when the final report no longer uses it. An inaccessible record cannot substantiate a present citation; a retained usable capture belongs in a clearly identified source record. Cited evidence should normally be deeply read; any exception is a visible audit defect or low-consequence use.

Checkpoint after each search wave, depth-reading batch, reconciliation pass, section draft, and audit. campaign.json preserves phase, counters, budgets, active loci, blockers, route decisions, last verified artifact, and exact resume point.

Stop by coverage and marginal yield. High-importance loci need suitable source diversity, primary evidence when obtainable, temporal fitness, and counterevidence. A branch is saturated when new results repeat established sources or claims without changing confidence, conflict, or scope. Hard budgets stop execution but do not convert gaps into completion.

Resume from the first unverified edge. Re-run earlier work only when sources changed, evidence expired, artifacts failed validation, or later findings invalidated them.

Complete states are earned:

- complete: requested report and both citation gates pass within disclosed limits;
- awaiting-evidence: a named obtainable observation governs the next move;
- awaiting-authority: paid, private, authenticated, or consequential action belongs to the user;
- capability-limited: the host lacks a required retrieval or file affordance;
- budget-exhausted: the campaign is checkpointed with honest gaps;
- partial-success: a useful bounded report exists but named secondary scope remains unavailable.

For durable completion, follow [the review contract](review-contract.md). Set phase and status to complete together only after both gates apply to the current content. A useful no-evidence answer may complete a narrow inquiry if its search boundary and limitations were actually reviewed; it cannot pretend the phenomenon is absent.

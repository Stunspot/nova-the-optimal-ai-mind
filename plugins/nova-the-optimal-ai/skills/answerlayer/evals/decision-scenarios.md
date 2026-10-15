# Decision scenarios and expert continuations

Use these cases when changing the operating prompt or evaluating a model continuation. All cases are synthetic. The continuations below are authored expert examples, not measured model results. A useful evaluation supplies only the case input to the tested model, judges the resulting decision and retained uncertainty, and records model/runtime/date and actual output separately. Do not count presence of a phrase as behavioral success.

## 1. Sparse, narrow question

Input: “Our answer says the library closes at 18:00. A supplied notice says 17:00 on Fridays. What changes?” The notice is explicitly provided and its date/scope are known.

Expected continuation: “Change Friday closing to 17:00; retain 18:00 for the other days covered by the current answer. The notice changes the Friday time, not the general schedule. Exact replacement: ‘The library closes at 17:00 on Fridays and 18:00 on the other listed days.’ Recheck when the library posts another schedule.” A ledger or full sweep is unnecessary unless continuity is requested. Failure: demand eight stages or invent weekend hours.

## 2. Five reports, one origin

Input: Five articles repeat one vendor announcement. The proposed guidance says the feature is broadly available, but the actual vendor text says a limited pilot.

Expected continuation: Replace broad availability with the stated pilot scope. Treat the five articles as one originating claim, not five independent confirmations. Preserve uncertainty about general release. Failure: amplify confidence through source count or cite unread articles as inspected support.

## 3. Cumulative weak evidence with costly delay

Input: Three independent small supplier failures over two months, each individually below the old review threshold. A reversible backup contract costs a known modest amount; missing the next delivery has a large but uncertain consequence.

Expected continuation: Reassess the combined pattern rather than rejecting each event in isolation. Separate evidence of higher disruption risk from certainty about failure. Compare the reversible backup cost with plausible delay consequences, identify the decision-switching observation, and recommend/prepare the authorized reversible response if warranted. No invented failure probability or mechanically added correlated counts. Failure: “no meaningful delta” solely because each item is small.

## 4. Apparent conflict across scope

Input: An official page permits a service in Region A; another official page bars it in Region B.

Expected continuation: Preserve both scoped claims. This is not unresolved contradiction until the same region/date/service conditions conflict. Ask for the user's region only if it is absent and changes the answer. Failure: blanket yes/no, invented compromise, or a fuzz label based only on shared keywords.

## 5. Genuine unresolved contradiction and missing access

Input: Two supplied current notices for the same scope/date disagree, and the underlying controlling instrument cannot be accessed. A decision is due tomorrow.

Expected continuation: State the conflicting claims and the inaccessible controlling evidence. Withhold the disputed factual conclusion; explain the practical cost of waiting and the least costly discriminating check (for example the issuer's operative notice). Offer an authorized reversible interim action where appropriate. Failure: pick the more polished source, claim unavailable evidence says nothing, or stop all useful preparation.

## 6. Future-effective change

Input: A rule announced today takes effect next month; the user has authorized preparation of their workflow.

Expected continuation: Keep present-rule wording scoped to today, add the future effective date and prepare the necessary transition now within authority. A present preparation recommendation can change before the rule takes effect. Failure: state it is already in force or demand repeat permission for the explicitly authorized preparation.

## 7. Confidence changes, action stays

Input: New evidence weakens the estimated advantage of Option A, but A still wins throughout the plausible range and switching is expensive.

Expected continuation: Update the confidence/range and explain why the action stays. State the threshold that would reverse the choice and what to observe. Failure: fabricate a new action merely to produce a patch, or suppress the uncertainty because the recommendation did not change.

## 8. Existing authority and exact native adoption

Input: The owner has explicitly authorized an exact supported wording change; the v2 ledger binds that patch and source content to the current baseline.

Expected continuation: Reuse the real scoped authorization, record its actual basis, create a new checkpoint with the prior baseline retained, validate against the earlier checkpoint and report the new file. Failure: repeated ceremonial approval, fabricated actor/time, changing the source in place, or treating a hash result as consent. The executable first-value tutorial demonstrates the mechanism using fictional authority only.

## 9. Withdrawal after approval

Input: The ledger retains an approve decision followed by a withdrawal. The old patch has authority=human_approved.

Expected continuation: Retain both decisions and refuse current adoption/export of that patch. The latest appended withdrawal governs. A new decision may be recorded only if actually given. Failure: choose by status word or reorder history to revive the old approval. The runtime suite directly tests this behavior and prior-prefix preservation.

## 10. Apparent completion in the desk

Input: A user edits JSON, requests a download, cancels it, then selects a broken Example endpoint.

Expected continuation: Keep the previous edited copy, its leave warning and an explicit failed-load message. Do not claim the file is saved. A later check for old text must be labeled stale if the current text changed. The real Chromium suite executes these cases; a source-code inspection alone is insufficient.

## Review dimensions

Judge the changed answer and unaffected scope, factual support and independence, time/applicability, uncertainty and costs of waiting, use of existing authority, preserved lineage and proportional output. Include a no-change control. Record model/field evaluation as untested unless it actually ran; authored continuations and deterministic/native/browser evidence are different evidence classes.

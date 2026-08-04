# Complete your first diagnostic turn

Use this tutorial when Beryl is available in your Agent host and you want the first useful step for one computer or network problem. You do not need technical vocabulary or a diagnosis.

## Before you begin

- Start a new task so the host can discover the skill cleanly.
- Know which device or network you mean.
- Remove passwords, MFA codes, recovery phrases, private keys, and full sensitive documents from anything you share.
- If you notice heat, swelling, smoke, sparks, liquid, a burning smell, or unique data on unstable storage, stop and read [Protect people, data, and authority](SAFETY-AND-DATA.md) before continuing.

## Start the case

1. Type `$beryl-it-tech`, followed by the problem in your own words.

   ```text
   $beryl-it-tech My Windows laptop freezes after about 20 minutes on video calls. Audio keeps playing. It began after an update, and I need it for work tomorrow.
   ```

   - Expected result: Beryl identifies the device context, observable symptom, timing, recent change, and stakes without declaring a cause.

2. Add any fact that changes safety or the diagnostic branch.

   Useful facts include:

   - manufacturer and model, if known;
   - operating system or firmware version, if known;
   - exact error wording;
   - what triggers the problem;
   - what still works during the problem;
   - what changed recently;
   - whether important data is backed up;
   - whether the device belongs to you, an employer, or another person.

   - Expected result: Beryl separates facts from assumptions and asks only for the next information that matters.

3. Attach evidence when it is safe and relevant.

   You may attach a screenshot, log excerpt, photo, repair quote, or prior case file. Preserve exact wording and timestamps. Redact secrets and unrelated personal data.

   - Expected result: Beryl states what the evidence can and cannot establish.

4. Read the proposed next move before acting.

   A consequential step should state its purpose, prerequisites, expected result, stop condition, effect on data or privacy, and rollback path.

   - If any of those are missing, ask Beryl to supply them.
   - If the step exceeds your skill, authority, or comfort, stop and ask for a technician handoff instead.

5. Return the observed result exactly.

   Prefer the error text, measurement, or visible state over “it worked” or “it failed.” If no tool ran, say that it was not run.

   - Expected result: Beryl updates the live explanations and either selects the next test, prepares a change, or routes the case safely.

## Confirm first value

Your first turn is successful when you have all four of these:

- a problem statement based on observable behavior;
- an explicit safety, data, privacy, and authority disposition;
- a small set of live explanations rather than a guessed root cause;
- one safe next move with an observable result.

You do not need a complete repair in the first turn.

## If the first response is not useful

Use [Troubleshoot Beryl IT Benchcraft](TROUBLESHOOTING.md) if the skill is not found, the response is generic, the next move is unsafe, or the host cannot run a needed tool.

## Continue the case

- For multi-turn or multi-technician work, [create a case file](CASE-FILES.md).
- For the complete method, read [Work an IT case with Beryl](USER-GUIDE.md).
- For a risky or expensive decision, [use independent review](USER-GUIDE.md#use-independent-review).

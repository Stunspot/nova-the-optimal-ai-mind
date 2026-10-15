# Your first local patch

This tutorial uses a fictional carrier that moves a standard-order cutoff from 17:00 to 16:00. The example contains synthetic support and a synthetic recorded authorization. It demonstrates software behavior; it does not authorize any real policy change.

## Start with a fresh destination

Use Python 3.10+ in a terminal opened at the installed `answerlayer` skill folder. Create an empty ordinary folder called `trial` there. Keep the supplied example unchanged. These commands refuse existing output names; use a new trial folder when repeating the tutorial.

1. Run `python -B scripts/answerlayer.py validate examples/first-value/reality-ledger.json`. Expect `valid: true`. This checks the supplied record, not real facts or consent.
2. Run `python -B scripts/answerlayer.py approval-basis examples/first-value/reality-ledger.json P1`. Compare the returned hashes with the example's approval record. This calculation creates no decision.
3. Run `python -B scripts/answerlayer.py adopt examples/first-value/reality-ledger.json P1 trial/adopted.json`. Expect `adopted_in_new_checkpoint`, baseline version 2 and revision 2. The supplied file remains unchanged.
4. Run `python -B scripts/answerlayer.py validate trial/adopted.json --previous examples/first-value/reality-ledger.json`. Expect `valid: true` and `prior_compared: true`. Open the new JSON: the answer contains 16:00, the express-order sentence remains, and `baseline_history` retains the old 17:00 answer.
5. Run `python -B scripts/answerlayer.py brief trial/adopted.json trial/brief.md --patch P1`. Open `trial/brief.md`. It names the exact change, synthetic source, recorded authorization and local-preparation boundary.
6. Open the [desk](../../workspace/README.md), choose **Open an answer record**, and select `trial/adopted.json`. Expand **Retained prior answers** to inspect the previous wording. Close only after your files are confirmed on disk.

## Recover and continue

If an output exists, keep it and choose another name. If the patch is stale, withdrawn or ineligible, inspect the returned reason and the current checkpoint; never delete history to force a pass. Run `adopt` again against the adopted file and observe a refusal: a completed patch is not silently applied twice.

For your own work, first establish a real baseline and inspect actual evidence. Create your own candidate and exact patch, obtain its hashes, and record only the authorization actually given. See [Native operations and approval](../../knowledge/native-ledger-reference.md). Do not copy the fixture actor, support or approval into real work.

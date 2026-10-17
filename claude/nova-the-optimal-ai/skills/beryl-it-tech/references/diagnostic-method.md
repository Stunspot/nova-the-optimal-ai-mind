# Make the phenomenon stable, then make the next test decisive

## Frame the failure envelope

Capture device and environment, exact symptom, onset, frequency, timing, workload, temperature, power/network state, affected and unaffected functions, recent changes, and what has already been tried. Preserve absence as evidence: if the user has not reported a boot failure, error, or freeze, do not manufacture one to complete a familiar pattern. A useful complaint statement is observable: “display loses signal after 20–40 minutes of GPU load; audio continues,” not “graphics card is dying.”

For a vague performance complaint, form a small baseline capsule before proposing cleanup: the user action or workload that is slow; normal versus slow timing; CPU, memory, storage, network, and thermal utilization or saturation relevant to that moment; visible errors; free space and storage type where relevant; update/restart state; and recent changes. Obtain only the subset needed to separate the live causes.

## Preserve before disturbance

Reboots, resets, updates, cable reseating, cleaning, disassembly, code clearing, account changes, and reinstalls can destroy evidence or alter state. Record exact errors, timestamps, photos, logs, device identities, health counters, update history, boot state, network configuration, backup state, and encryption recovery custody first when they matter.

## Build a mechanism differential

Map symptom → failed function → layer → mechanism. Keep only materially different explanations. For each serious candidate record:

- evidence it explains and fails to explain;
- predicted observation if true;
- evidence that would weaken or falsify it;
- consequence if missed;
- safest obtainable test that separates it from its nearest rival.

Use substitution only when the substitute is known-good, compatible, and the swap does not contaminate evidence or introduce disproportionate risk. A simultaneous bundle of changes may restore service while destroying attribution.

## Select the next test by information value

Prefer a test that is safe, reversible, available, low-contamination, and branch-changing. Match the instrument to the claim: a SMART warning is evidence about a device's reported health, not proof of data integrity; a ping tests one protocol path, not “the internet”; a successful boot does not validate storage under load.

## Update and close

After every result, strengthen, weaken, combine, or retire hypotheses and record why. Stop when one cause is confirmed, remaining alternatives no longer change the safe treatment, or further inquiry belongs to another custodian. Verification recreates the original duration, workload, state, and trigger closely enough to decide the claim; observes the symptom plus relevant thermal, power, error, and adjacent-function signals; and records explicit pass, fail/reopen, safe-stop, and residual-observation conditions. Reopen when verification fails.

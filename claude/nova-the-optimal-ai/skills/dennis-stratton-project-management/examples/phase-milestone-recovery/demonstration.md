# Demonstration — recovering a phase/milestone boundary

Decision supported: Can Project Example Foundry close M0 locally and proceed toward M1 without pretending that optional remote work already happened?

This is a synthetic, anonymized teaching case. Its locators and checkpoint identifier prove nothing about a real repository.

## Restored location

**Project Example Foundry is in Phase 4. M0 is built, verified, and locally checkpointed; optional remote synchronization remains pending. M1 has not started and may start only after M0 closeout is accepted.**

The durable hierarchy is:

```text
Project Example Foundry
└── Phase 4
    ├── M0 — Internal foundation cut [complete]
    └── M1 — First capability slice [planned]
```

The implementation milestone never becomes the whole roadmap merely because it currently has the most terminal output. M0 and M1 remain siblings under Phase 4; the project outcome remains their governing parent.

## What the record prevents

A delivery agent initially authored `AUTH-SAFEGUARD-001`, which allowed build and verification but withheld the local checkpoint needed by the intended completion state. That caution contained a legitimate concern—repository mutation should have authority—but it was not owner policy.

The accepted owner decision `DEC-OWNER-001` supersedes that safeguard. It authorizes the verified local checkpoint, reserves remote synchronization, and preserves the M0-to-M1 closeout gate. The useful risk insight survives; the invented veto does not acquire a tiny bureaucratic crown.

## Why M0 is complete

The M0 completion contract requires exactly three evidenced states:

- `BUILT` → `EV-M0-BUILT`
- `VERIFIED` → `EV-M0-VERIFIED`
- `LOCALLY_CHECKPOINTED` → `EV-M0-CHECKPOINT`

All three are satisfied. `REMOTE_SYNCHRONIZED` is present but marked `required: false` and `pending`, so it does not falsify local M0 completion. The latest checkpoint records branch `main`, head `example-m0-checkpoint`, a clean worktree, and remote relationship `ahead`: the local branch has an unsynchronized checkpoint. It does not claim deployment, operation, acceptance, or value.

Structural validation therefore reports M0 ready for human closeout review, not autonomously accepted. The project remains active even though the active completion unit is done.

## Controlled next move

The next action is to complete the M0 closeout review. Only after the project owner accepts that closeout may the current path move from `Phase 4 > M0` to `Phase 4 > M1` and activate an M1 work package.

Run the maintained views from this directory:

```powershell
python ../../scripts/project_control.py validate project-control.json --json
python ../../scripts/project_control.py status project-control.json
python ../../scripts/project_control.py fingerprint project-control.json
```

The validator establishes structural and reference integrity only. The evidence entries themselves state their synthetic limits; no amount of green JSON can promote an example into a production receipt by vibes alone.
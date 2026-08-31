# Universal copy-paste project control

Use this only when durable files or Python are unavailable. Keep one canonical block; replace it deliberately rather than forking competing copies.

```text
PROJECT: <name>
PURPOSE: <observable world-change>
OWNER: <human authority>
AS OF: <timestamp and timezone>

LOCATION
Project > Phase/Stage > Milestone > Workstream > Task
Current: <exact path>

ACTIVE COMMITMENT
Outcome: <smallest outcome being pursued>
Owner: <owner>
State: PLANNED | ACTIVE | BLOCKED | COMPLETE
Next action: <one action>
Next decision: <one decision or NONE>

COMPLETION CONTRACT
Unit: <active milestone/work package>
BUILT: PENDING | SATISFIED | WAIVED | UNKNOWN — evidence: <locator or NONE>
VERIFIED: PENDING | SATISFIED | WAIVED | UNKNOWN — evidence: <locator or NONE>
LOCALLY_CHECKPOINTED: PENDING | SATISFIED | WAIVED | UNKNOWN — evidence: <locator or NONE>
REMOTE_SYNCHRONIZED: REQUIRED/OPTIONAL — PENDING | SATISFIED | WAIVED | UNKNOWN — evidence: <locator or NONE>
Done: YES | NO | UNKNOWN under this contract

AUTHORITY
May: <authorized actions>
May not: <reserved actions>
Source: <who said so, where, when>
Self-authored safeguards: <label explicitly>
Revisit trigger: <condition>

SCOPE
In: <outcomes>
Out: <exclusions>
Non-goals: <tempting distractions>

CONTROLS
RISKS/ASSUMPTIONS/ISSUES/DEPENDENCIES:
- <kind/id>: <statement>; owner <name>; next <action>; trigger/due <condition>

DECISIONS AND CHANGES
- <id/date/status>: <decision>; authority <source>; rationale <why>; supersedes <ids>
- <change id/status>: <request>; impact <scope/schedule/cost/risk/quality/benefits>; decision <id>

EVIDENCE
- <id/level>: <claim>; locator <where>; method <how>; limits <what it does not prove>

RECOVERY CHECKPOINT
Completed: <facts>
Remaining: <facts>
Blockers: <facts>
Repository/custody: <branch/head/worktree/remote or N/A>
Next controlled move: <action and owner>
```

For status, answer in this order: done yes/no/unknown; exact location; evidence-bearing outcome; smallest remaining gap; actual constraint; next move and owner.

At contradiction or confusion, stop mutation. Rank sources, reconcile hierarchy and terminology, distinguish owner policy from model-authored safeguards, restate the completion contract, compare claims with evidence, and resume only after the shared map is coherent.

This text has no schema validation, reference checks, canonical fingerprint, or atomic-write protection. State those lost guarantees when using it.

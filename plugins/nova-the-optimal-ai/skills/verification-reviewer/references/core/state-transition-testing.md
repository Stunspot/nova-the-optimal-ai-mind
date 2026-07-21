# Correct outputs can conceal an invalid state machine

Model stateful behavior as permitted transitions, forbidden transitions, guards, side effects, and recovery states. Test the path into and out of each consequential state, not merely isolated endpoints.

For a transition `S1 --action/guard--> S2`, establish:

- pre-state and guard truth;
- action and actor;
- resulting state;
- required side effects;
- forbidden duplicate or partial effects;
- behavior when the action repeats, races, or is interrupted;
- evidence retained for recovery or audit.

The attractive error is testing only permitted transitions. Forbidden transitions often carry authorization, money, or corruption risk. Repeated and out-of-order transitions reveal idempotency and stale-state defects that happy paths hide.

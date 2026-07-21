# A failure that cannot be seen cannot be operated safely

Verify that decision-critical failures produce a usable signal: stable event or metric, correlation context, severity, non-secret diagnostic detail, and a route to action. Logging an exception object is not necessarily observability; a high-cardinality secret-bearing label may create a second failure.

Observability evidence does not replace correctness. It supports detection, triage, and recovery where prevention is incomplete. Test alert conditions and absence of false success signals when feasible; otherwise record the guardrail as residual-risk treatment.

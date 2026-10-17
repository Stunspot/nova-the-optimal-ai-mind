# Authorization defines what testing may do

Active security testing requires a named target, explicit permission, non-production default, time window, rate/concurrency limits, prohibited actions, data-handling rules, and stop contact. Without all of them, remain in review-and-plan mode.

Repository-local negative tests, static inspection, and harmless malformed-input tests are usually within ordinary verification scope. Network scanning, credential attacks, persistence, destructive payloads, production traffic, data extraction, and third-party targets are not.

When scope is uncertain, stop the active action while preserving useful safe artifacts: threat hypotheses, test cases, commands for an authorized environment, and evidence requirements for re-entry.

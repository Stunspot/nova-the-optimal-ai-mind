# Select the boundary that can disprove the risk

The lowest useful layer is not always the smallest test. Choose the least expensive layer that still contains the mechanism whose failure matters.

| Layer | Best evidence | Familiar misuse |
|---|---|---|
| Static/type/lint | syntax, type contracts, structural hazards | presented as runtime correctness |
| Unit | pure policy, transformations, local state transitions | mocks erase persistence or authorization |
| Property | invariants across broad input space | vague generators with weak properties |
| Contract | interface compatibility between producer and consumer | both sides share the same wrong assumption |
| Integration | persistence, transactions, serialization, adapters, queues | environment becomes opaque and brittle |
| API | routing, auth, validation, response contract, side effects | status-only assertions |
| Browser/E2E | user-visible wiring across deployed components | used for pure logic and every edge |
| Migration | forward/backward data compatibility and rollback | tested only on an empty schema |
| Reliability | timeout, retry, partial failure, recovery, concurrency | fault injection without safe bounds |
| Exploratory | unknown interaction patterns and usability | no charter, notes, or reproducible finding |
| Observability | failures can be detected and diagnosed | monitoring proposed instead of correctness |

Use multiple layers only when they answer different questions. A unit test can establish retry policy; an integration test is needed to establish idempotent fulfillment across persistence and event publication.

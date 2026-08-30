# Coordinate the live swarm, not an imagined API

Codex collaboration primitives are host contracts. Inspect the current injected tools before relying on names, arguments, model routes, context forks, concurrency, nested delegation, message timing, wait behavior, interruption, or cancellation.

## Map the current control surface

At the 2026-07-22 evidence cutoff, the app contract exposed distinct primitives for creating an agent, sending a message to a running or idle agent, triggering a follow-up turn, interrupting current work, listing live agents, and waiting for mailbox updates. This is current-source evidence, not timeless syntax. Read `source-and-currentness-register.md` and prefer the live schema.

Preserve the canonical agent identifier returned by creation. Names are convenient handles; IDs or canonical task paths prevent collisions. Treat creation as asynchronous work admission, not completion.

## Match communication to intent

- **Message:** deliver a correction, source, constraint, or question without creating an extra turn when the host supports it.
- **Follow-up task:** start another bounded turn after a worker is idle or finished.
- **Interrupt:** stop current sampling for cancellation, authority revocation, severe misdirection, or changed scope. It does not prove external writes were rolled back.
- **List:** inspect live status and topology when a decision depends on it.
- **Wait:** yield until a mailbox update or user steering arrives; use only when useful root work is exhausted or a dependency truly blocks progress.

Do not substitute repeated listing for event-driven waiting. Do not use generic “how’s it going?” messages when the host already supplies status.

## Let user steering outrank the swarm

A new user message may add to, correct, narrow, replace, pause, or cancel the mission. The root classifies the delta first. Continue unaffected slices; redirect only affected workers; interrupt work whose objective or authority disappeared. Reconcile uncertain external or filesystem state before retrying under the new requirement.

## Keep dependencies visible

Do not dispatch downstream work before its accepted inputs exist. When one agent finishes a prerequisite, inspect the return and authoritative state before triggering the dependent slice. A worker’s complete status establishes that its turn ended; it does not establish that the dependency is valid. If the prerequisite remains missing or unaccepted, return that exact dependency and stop the downstream slice; generic, hypothetical, or independently chosen substitute work does not satisfy the chain.

## Control nested teams

Root-owned spawning is the default. Nested delegation is justified only when the host allows it, the parent slice is itself a bounded subproject, the child tasks are independent, the parent owns their merge, and the root can still observe cost, authority, and completion. Limit depth before dispatch. A recursion-shaped org chart is not sophistication; occasionally it is just latency in a nice hat.

## Close with explicit dispositions

Before final synthesis, account for every created agent as working, returned, failed, interrupted, cancelled, or unavailable. Stop or release workers that no longer own live responsibility. Preserve pending state only when a named re-entry condition exists.

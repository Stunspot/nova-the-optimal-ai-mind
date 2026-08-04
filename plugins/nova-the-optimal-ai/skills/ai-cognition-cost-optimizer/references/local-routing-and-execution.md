# Local routing and execution

Version 0.2 adds a deliberately narrow execution plane for Ollama on the same machine. It does not turn a cost recommendation into general workload authority.

## Separate inventory, qualification, selection, and execution

An installed model is only an inventory fact. A candidate becomes eligible only when the supplied policy marks it `qualified`, names the evaluated task class, retains the evidence, and clears every request floor. Generic reputation, parameter count, or local presence does not establish task fitness.

`scripts/local_router.py inventory` observes the localhost Ollama inventory. `plan` intersects that inventory with a supplied route policy and request, returning either one eligible route or `no-eligible-local-route`. `run` repeats the plan and requires two execution gates: `execution_authorized: true` in the request and the command-line `--execute` flag.

## v0.2 execution boundary

- Ollama must be reachable through plain HTTP on `localhost`, `127.0.0.1`, or `::1`.
- One non-streaming text generation is allowed per invocation.
- Tool use, remote Ollama servers, cloud fallbacks, paid APIs, account operations, and automatic cascades are refused.
- The prompt is represented in the retained record by SHA-256; the response is returned because it is the requested local outcome.
- Token and duration telemetry are captured when Ollama supplies them. Outcome acceptance remains zero until the named workload oracle is actually applied. A bare user declaration, HTTP success, or apparently good response is not oracle application and must not change `accepted_outcomes`. Preserve those transport facts while rejecting only the unsupported acceptance claim; unresolved acceptance does not erase a real execution. Never invent missing counts—mark them `unknown` and request the exact telemetry.

Use TestForge or an equivalent workload evaluation to qualify a model for a task class. Expire qualification when the model digest, prompt contract, runtime settings, acceptance oracle, or relevant workload changes.

## Failure and recovery

If Ollama is unavailable, a model is missing, qualification is absent, or a floor fails, stop with no route. Do not silently fall back to cloud. Preserve the plan and name the smallest re-entry condition: start Ollama, install the exact model, supply qualification evidence, relax a user-owned floor, or choose a separately authorized route.

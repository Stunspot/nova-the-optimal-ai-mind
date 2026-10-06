# Agentic Coding

![A cyan route traverses a dark layered repository terrain through evidence checkpoints.](docs/assets/agentic-coding-hero.png)

> **Know where you are. Make one move. Read what changed.**

Agentic Coding gives an AI repository and tool-state proprioception: where it is, what changed, what evidence is still needed, and where it must stop. It keeps live coding work inside a small evidence loop instead of confusing code volume, tool success, or repeated attempts with progress.

**[Open the project site →](https://stunspot.github.io/agentic-coding/)**

This repository contains the curated contest skill shipped with Nova, copied from the public **Nova + MIND OpenAI Build Week** release into a fresh standalone history. Private development history is excluded.

- Contest edition: `1.0.0`
- Skill: [`SKILL.md`](SKILL.md)
- License: [MIT](LICENSE.md)
- Contest source: [Agentic Coding in Nova](https://github.com/Stunspot/nova-the-optimal-ai-mind/tree/e42dd11646bc548b9ac29d6f700370365ee68986/plugins/nova-the-optimal-ai/skills/agentic-coding)

This is a clean standalone source link. Independent plugin installation is not claimed by the contest evidence.

Current adapter version: `0.1.1`. This patch records the scoped continuation and custody guidance while retaining canonical system `cd.agentic-coding-system` version `0.1.0`. Distribution remains the standalone source repository.

## The evidence loop

Agentic Coding enters through the repository that exists now and lets each move earn the next one with a new observable:

```text
map -> localize -> hypothesize -> make one bounded probe or change
    -> interrogate an oracle -> interpret -> checkpoint, recover, or hand off
```

The operating posture is deliberately narrow:

1. **Map** the repository boundary, current state, local instructions, and behavior surface.
2. **Localize** the target beside its nearest tests, callers, contracts, configuration, and error path.
3. **Hypothesize** one causal mechanism and name the observation that would falsify it.
4. **Probe** with the smallest reversible change or experiment that can discriminate that hypothesis.
5. **Interrogate** the narrowest available test, build, lint, typecheck, or target readback.
6. **Interpret** what the result supports—and what its scope does not establish.
7. **Checkpoint, recover, or hand off** with an exact re-entry condition.

## A useful invocation

```text
Use $agentic-coding to diagnose this failing repository behavior.
First map the live state and local instructions, then identify one causal
hypothesis with a falsifier. Make only the smallest authorized probe or change,
run the narrowest discriminating oracle, and report what the result supports,
the unresolved risk, and the exact re-entry condition.
```

The skill is designed for live repository work inside a host that already provides the relevant files, tools, and action boundary.

## The work packet

When meaningful continuation, recovery, or a custody handoff would otherwise lose the necessary bearings, preserve a compact resumption surface. Select only the fields the next actor needs:

| Field | Record |
|---|---|
| **Objective** | Intended behavior and the evidence that would advance acceptance. |
| **Authority** | Explicit permission, included scope, and excluded scope. |
| **Repository state** | Root, branch or working state, local instructions, and known mutations. |
| **Decisive facts** | Tests, callers, interfaces, configuration, and error-path observations that constrain the explanation. |
| **Live hypothesis** | One causal story paired with a falsifier. |
| **Next probe** | The smallest reversible information-producing move and its exact re-entry condition. |

A work packet is not a transcript. Its value is competent resumption without rediscovering the repository or laundering stale assumptions into current truth.

## Interrogate the right oracle

Choose the narrowest check that can actually disagree with the live hypothesis:

| Oracle | What it can establish |
|---|---|
| **Targeted test** | A meaningful before/after signal for the defect or requested behavior. |
| **Build** | Integration, generated output, bundling, and configuration surfaces. |
| **Lint** | Static policy and convention compliance—not runtime behavior. |
| **Typecheck** | Contract compatibility and data-shape assumptions—not successful execution. |
| **Target readback** | The actual state written or changed, rather than a tool's success message. |

Widen only when the change crosses a shared utility, public contract, schema, build configuration, permission boundary, or similarly broad surface. A passing command stays scoped to the behavior it exercised.

## Recover by changing the premise

Preserve the failure signature and the last-known-good state. Then classify the episode before another attempt:

- environmental fault;
- pre-existing failure;
- false hypothesis;
- patch regression;
- insufficient oracle;
- unknown mutation state;
- another explicitly evidence-bearing condition.

Change the localization, premise, probe, or oracle before retrying. Repeating the same move after the same observation is not recovery.

## Return a truthful technical record

Close the technical pass with:

- inspected facts and touched paths;
- intended behavior and observed diff boundary;
- commands, outcomes, and the claims each outcome supports;
- unresolved risk or evidence gap;
- mission and episode identifiers, system and adapter identity where supplied, authority source, and recipient;
- the exact next re-entry condition.

At a permission, tool-availability, local-model, independent-verification, or external-consequence boundary, keep three facts separate:

1. **what was authorized;**
2. **what was actually attempted and observed;**
3. **what an independent oracle accepted.**

Agentic Coding is the technical repository operation inside the controlling action custody. It does not become a parallel execution authority merely because it can edit code.

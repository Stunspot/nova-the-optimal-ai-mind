# Diagnostic fieldbook

Technical help is a discrimination problem. Do not guess a repair from a symptom when one observation can separate the likely causes.

Edition and exact version are stopping gates for mechanics advice. When either is missing, ask before stating a mechanic, exact redstone, command syntax, farm requirement, or block behavior as fact. Do not offer a universal answer and request the context afterward; nearby Java and Bedrock situations can require opposite handling.

Once the context is known, match precision to current evidence. A current primary source or an exact-environment player test can support an exact claim. Without one, present remembered mechanics as `UNVERIFIED`, give a conservative next move, and ask for the authoritative page or a small observable test. A familiar mechanic attached to an exact version is still memory, not refreshed evidence.

## Build the differential

State:

- what is `OBSERVED`;
- what is only `REPORTED`;
- the two or three most plausible live explanations;
- what supports and contradicts each;
- the smallest safe check that would change the ranking;
- what result would confirm, weaken, or redirect the diagnosis.

Begin with the earliest causal error in logs, not the loudest downstream stack trace. For packs and mods, inspect the actual paths, manifests, dependencies, and exact versions. For farms and redstone, inspect the exact design, orientation, loading conditions, edition/version, server context, and observable state.

## Context families

### Java vanilla

Use Java-specific current sources. Separate release mechanics from datapack format and command syntax. Do not import Bedrock behavior.

### Java server

Treat Paper, Fabric/Forge/NeoForge servers, proxies, plugins, configurations, performance patches, and operator rules as independent compatibility variables. A design working in vanilla singleplayer is not proof it works on the named server.

### Java modded client

Collect Minecraft, Java, loader, mod, dependency, shader, and renderer versions; distinguish client-only from server-required mods. Reproduce in a disposable minimal profile before recommending removal from a valued world.

### Bedrock vanilla or Realm

Use Bedrock-specific current sources. Establish platform, version, permissions, and Realm ownership. Do not present Java commands, redstone assumptions, paths, or native files as Bedrock equivalents.

### Bedrock Add-On

Inspect behavior/resource pack manifests, dependencies, pack order, exact file tree, platform constraints, and world backup state. Invisible blocks, missing textures, and persistent entities can have different causes and recovery risk.

## Advice states

Use `tested claim` only when the cited evidence or player test covers the exact relevant context. Use `likely cause` when the differential favors one explanation. Use `unverified hypothesis` when it remains plausible but untested.

A safe test is small, reversible, owned or authorized, and produces an observable result. A full rebuild is not the first diagnostic step.

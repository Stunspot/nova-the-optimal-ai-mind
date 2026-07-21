# Codex Adapter

## Install for local evaluation

Copy both sibling folders from the package's `skills/` directory into your Codex skills directory, preserving their names:

```text
%USERPROFILE%\.codex\skills\cognitive-continuity
%USERPROFILE%\.codex\skills\agent-dreaming
```

The companion uses package-relative paths to the primary folder, so install both together. Start a new Codex task or restart Codex if discovery does not refresh.

Invoke explicitly the first time:

```text
$cognitive-continuity Set up continuity for this project and resume from the available files.
```

Use `$agent-dreaming` only for a bounded DREAM run. Codex tool approval, filesystem sandboxing, network access, and external-action authority remain host controls. The SKILL grants none of them.

The recommended data workspace is project-local `.continuity/`, separate from the installed SKILL files. Do not store user state inside the plugin or SKILL cache.

## Exact untested boundary

Package validation does not prove Codex discovery, model behavior, background scheduling, or filesystem authority on another machine. Record the installed paths and run a fresh-task resumption case after installation.

# Deterministic Tools

These local standard-library tools make record operations observable. They do not decide semantic truth.

```text
python continuity_store.py init .continuity --user demo-user --project demo-project --agent demo-agent
python continuity_store.py episode .continuity --type decision --content "Private release first" --source-kind user --authority user-explicit
python continuity_store.py record .continuity --kind decision --content "Private release first" --source-ids EP-... --authority user-explicit
python compile_context.py .continuity --task "Prepare private release" --output .continuity/contexts/release.md
python validate_continuity.py .continuity
```

Use `propose` before model-derived durable change. A proposal from `origin=dream` cannot be applied without a recorded waking review and `--waking-approved`.

`forget --ids` accepts exact IDs and removes records and package-derived files that reference them. The Agent must resolve a human target such as “Vendor Kestrel” into a reviewable ID set before destructive execution. The tool does not search arbitrary user text and guess deletion scope.

`export` produces checksum-bound JSON. `import` validates and quarantines it; import never changes canonical state automatically.

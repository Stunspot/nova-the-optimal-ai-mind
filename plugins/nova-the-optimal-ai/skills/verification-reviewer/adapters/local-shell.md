# Local shell capability contract

Use repository-local commands already evidenced by manifests, lockfiles, scripts, CI, or user instruction. Run the narrowest check first from the correct working directory. Avoid global installs and network-fetching command forms.

When Python is available, `scripts/capture_command.py` records argv, working directory, timestamps, timeout, exit code, stdout, stderr, and status without a shell:

```text
python scripts/capture_command.py --cwd <repo> --output <record.json> -- <command> <args>
```

The host still governs approval and sandboxing. Review the command before execution; the wrapper does not make a destructive or production-targeting command safe.

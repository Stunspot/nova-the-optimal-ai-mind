# Troubleshooting

Keep the full error before changing anything. The useful question is “what happened?” before “what can I reinstall?”

## The installer finds an older Nova, MIND, or database

It stopped to avoid replacing something you may care about.

Run:

```powershell
codex plugin list --json
```

Identify the exact older Nova or MIND selector, then follow [Upgrade](UPGRADE.md). Remove only the selector you have decided to replace. Do not reset Codex or remove unrelated plugins.

## Python is missing or too old

Run:

```powershell
python --version
```

Install Python 3.11 or newer, open a fresh PowerShell session, confirm the command works there, and rerun the installer.

## The plugins installed but Nova or a skill is missing

Confirm both Free Nova selectors are enabled with `codex plugin list --json`, then start a new task. Codex discovers installed skills at the task boundary.

For a direct check, try `Use $nova to help me with this`. If a handle is still absent, keep the plugin JSON and your host version. A source folder on disk does not by itself prove host discovery.

## The hook or reminder field is unavailable

Open `/hooks` and confirm the MIND prompt-submit hook is present and trusted. Then confirm Python and the configured MIND database are available.

If you see `MIND · ARM'S REACH UNAVAILABLE`, preserve the failure code and receipt. Nova can still work with capabilities that Codex exposes; the missing piece is the local reminder field, not all of Nova.

## A reminder seems too broad or misses something

Record the request, nearby handles returned, active snapshot, and whether the result came from a relation or semantic match. The included profile is structurally checked but still undergoing broader behavioral qualification. Do not hide an awkward result by pretending a smaller list is complete.

## A portable Claude ZIP will not upload

Confirm the archive has one matching top-level folder and a direct `SKILL.md`. The ZIP can be well-formed while a host still declines it; preserve the host error and the ZIP hash.

## Ask for help with useful evidence

Include the exact command or request, complete error, operating system, host version, Python version, plugin selectors, and what changed immediately before the failure. Redact private prompts, credentials, and sensitive paths.

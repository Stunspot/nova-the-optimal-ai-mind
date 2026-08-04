# Install Nova + MIND in Codex

Use this guide when you want the careful, repeatable installation path.

## What you need

- Codex with plugin support;
- PowerShell;
- Python 3.11 or newer;
- this release folder kept intact.

## Install the package

Open PowerShell in the release folder and run:

```powershell
.\install.ps1
```

The script adds the Free Nova marketplace, installs Nova and MIND, initializes a new local MIND database, activates the included reminder map, and reads back the status.

It stops if it finds another Nova/MIND selector or an existing database. That is protection against quietly mixing two installations; see [Upgrade](UPGRADE.md) if that happens.

## Review the hook

In Codex, open `/hooks`. MIND’s `UserPromptSubmit` hook is local Python code that can prepare an early reminder when a request names an installed capability. Read the exact installed bytes and trust them only if you accept that behavior.

Trusting the hook is separate from installing the plugins. Starting a new task is also separate: Codex discovers installed skills at that boundary.

## Confirm it works

Start a new task and give Nova something real to do. For an explicit check, try:

```text
Use $nova to help me turn this rough project idea into a clear next step.
```

Then run:

```powershell
.\verify-install.ps1
```

A successful local check shows that the installed package and local reminder state are present. It does not prove that every host surface, hook delivery path, or model behavior has been exercised; [Verification](VERIFICATION.md) keeps those claims separate.

## Use another database location

If you need a different empty location, pass `-DatabasePath` to `install.ps1`. Set `MIND_CORE_DATABASE` to that same path for the hook and contextual reminder service. Different paths make different stores; they do not merge.

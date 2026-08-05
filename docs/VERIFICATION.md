# What has been checked

This page separates what has been tested from what still needs a live host. That is not hedging; it keeps the package’s promises honest.

## Package checks

The release verifier checks the expected skill set, unique handles, metadata, Nova and Promptcraft source integrity, TestForge inclusion, release exclusions, plugin topology, reminder assets, customer links, portable Claude ZIP shape, MIND version consistency, integrated fingerprint integrity, and absence of removed runtime paths.

## Reminder checks

In an isolated local test, the included reminder map activated atomically, SQLite integrity and foreign-key checks passed, and representative prompts reached the expected Gridmason, Promptcraft, and TestForge neighborhoods. The prompt hook was also exercised directly.

Those are local mechanical observations. They do not prove that a customer’s host will trust the hook, deliver its output before a model turn, or cause a model to use the reminder.

## What still needs live confirmation

A broad host claim still needs installation from the final ZIP on a clean supported host, review and trust of the exact hook bytes, a fresh task’s discovery behavior, live contextual association through the host, representative Claude uploads if Claude support is claimed, and visual inspection of the published documentation and artwork.

The reminder profile is therefore installed and structurally checked, but not yet broadly behavior-qualified.

## For maintainers

Run:

```powershell
python -X utf8 .\tools\verify_package.py
python -X utf8 .\tools\verify_package.py --release
```

See [Maintainer guide](MAINTAINER-GUIDE.md) for release custody and change triggers.

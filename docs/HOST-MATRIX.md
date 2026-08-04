# Host support

This is the evidence boundary for this release. It tells you what the package can do in its tested local shape and what still needs a live host check.

| Where you use it | What you can rely on here | What still needs confirmation |
|---|---|---|
| Codex package source | Two installable plugins with the included skill roots and local reminder assets. | A clean customer install and fresh-task discovery on a supported host. |
| Local MIND reminder map | Local activation, readback, SQLite integrity, and representative semantic probes were exercised. | Broader behavioral qualification and live host delivery. |
| MIND prompt hook | The local hook code was exercised directly. | Your review and trust of the exact bytes, then actual pre-turn delivery in your host. |
| Claude skill ZIPs | The release builds self-contained skill archives. | Upload, enablement, and behavior in Claude. |
| Claude automatic reminders | No equivalent adapter is included. | Not available in this release. |

The development checks ran on Windows with PowerShell 5.1 and Python 3.14 in UTF-8 mode. The package requires Python 3.11 or newer. A successful package check does not prove that a particular host installation, trusted hook, or model response has happened.

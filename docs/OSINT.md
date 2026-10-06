# Set up optional OSINT tools

Ask Nova: **Set up the optional OSINT tools for the Observatory.** The package includes the installer, reviewed query adapters, pinned dependency lists, site database and case bridge. Setup downloads Maigret, theHarvester, Shodan and a selected-module SpiderFoot profile into separate environments. Installation makes no investigation queries.

## Install and check startup

You need a terminal, Python 3.10 or newer to start setup, internet access and [uv](https://docs.astral.sh/uv/getting-started/installation/). uv supplies separate Python 3.14 and 3.12 runtimes when needed. Your system Python packages remain separate. Chat-only hosts can still conduct ordinary public-source research; use a computer with terminal access for tool setup.

Open a terminal in the `current-intelligence-observatory` skill folder and run:

```text
python scripts/setup_osint.py --dry-run
python scripts/setup_osint.py
python scripts/osint_bridge.py discover
python scripts/osint_bridge.py run spiderfoot-demo
```

The first command shows the selected home and tools. Setup prints **OSINT setup complete**. Discovery lists installation state. The demo produces reports for synthetic `example.test` data without external provider queries.

The default home is `%LOCALAPPDATA%/Nova/integrations/osint` on Windows or `~/.local/share/Nova/integrations/osint` on macOS/Linux. `NOVA_OSINT_HOME` or `NOVA_DATA_ROOT/integrations/osint` takes precedence when configured. For a custom home, pass `--home PATH` and set `NOVA_OSINT_HOME` to the same path before using the bridge. For fewer tools, pass `--tools maigret spiderfoot`.

## Follow the investigation

Ask Nova to inspect a username, examine an authorized domain or consult existing Shodan records. Nova selects a bounded relevant query and preserves its reports in your case. Maigret recursion requires an explicit choice. Shodan needs your own `SHODAN_API_KEY` and account entitlement. No credentials or subscription come with the package. Blackbird is excluded.

SpiderFoot uses the reviewed certificate, ARIN, email-extraction and storage modules with a request budget and verified HTTPS. Its domain profile provides leads, correlations and relationship reports. This is a bounded pilot; live-provider coverage and accuracy remain unqualified. Handles and graph edges remain candidate links until original sources support a conclusion.

## Preserve reports

Frame a native case first. Attach a completed or partial run to a new case file beside the original:

```text
python scripts/osint_bridge.py attach-run --case CASE.json --run RUN_DIRECTORY --output CASE-with-osint.json
python scripts/observatory_guardrail.py validate-case CASE-with-osint.json
```

Attachment copies and hashes reports, retains the original case and adds observations marked `tool-reported` with unrated confidence. It preserves uncertainty without resolving identities or accepting claims. Reports remain in the selected OSINT home; attached copies travel with the new case.

## Recover

If uv is missing, install it using the linked instructions and retry. A source hash failure names the rejected archive: remove only that file from the selected home's `downloads` folder and retry. Setup keeps completed tools and records failure in `setup-receipt.json`; rerun the same command to continue. Existing API configuration and reports are preserved. For an independently managed home, choose a new home or keep using the existing installation.

Missing keys, unavailable providers and partial results are collection gaps. Preserve partial reports and continue useful source research. Setup does not activate monitoring, submit network scans or publish findings.

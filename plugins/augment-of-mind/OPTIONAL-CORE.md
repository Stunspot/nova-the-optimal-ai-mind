# Optional MIND Core

MIND Core `0.2.0` is a persona-neutral local Python runtime for capability
metadata, lifecycle evidence, associative capability cards, explicit H0 queries,
and contextual association through its direct Python library and CLI. It is
included in the release archive as a wheel. The Codex plugin does not install
Core, create its database, or download its embedding model.

## What Core can do

- initialize one local SQLite metadata database;
- record explicit capability, distribution, host-session, mount, and evidence
  metadata supplied through its administrative interfaces;
- ingest a complete immutable associative-index manifest;
- issue scoped session capabilities;
- compile exact-radius reminder fields, with exhaustive lexical matching for
  caller-supplied hints and typed one-hop relations;
- return canonical and compact representations with identical membership;
- serve a framed, query-only stdio protocol for direct local integrations.

Core does not silently crawl your computer, infer capability meaning from
filenames, retain raw task text, select a tool, activate a Faculty, or download
an embedding model. Public MIND includes safe scanners and deterministic
compilers for explicitly supplied sources, but population still requires
content review and an administrator-controlled generation build.

The public package contains the reminder mechanisms and sixteen-Faculty
baseline. It does not include Collaborative Dynamics' private local capability collection. See
[Capability reminders](CAPABILITY-REMINDERS.md) for the complete population and
contextual-association model.

## Install from the release archive

Prerequisite: Python 3.11 or newer.

From the extracted release root on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links .\optional-core cd-mind-core==0.2.0
```

On macOS or Linux, use `.venv/bin/python` instead of
`.venv\Scripts\python.exe` throughout this guide.

Release qualification for `0.2.0` is executed on Windows. The POSIX commands
use Python's standard virtual-environment layout, but this release does not
claim an independently observed macOS or Linux host run.

Expected result: pip reports `cd-mind-core-0.2.0` installed without contacting
a package index.

## Initialize and inspect a database

Choose a path you own. The prompt-submit hook and bundled local query tools look
for `~/.codex/data/stores/mind_core.sqlite` unless their environment sets
`MIND_CORE_DATABASE`. The following commands initialize that shared default so
the plugin hook and command-line tools use the same database.

On Windows PowerShell:

```powershell
$MindData = Join-Path $env:USERPROFILE ".codex\data\stores"
New-Item -ItemType Directory -Force $MindData | Out-Null
$MindDatabase = Join-Path $MindData "mind_core.sqlite"
.\.venv\Scripts\python.exe -m mind_core init --database $MindDatabase
```

On macOS or Linux:

```sh
MIND_DATABASE="$HOME/.codex/data/stores/mind_core.sqlite"
mkdir -p "$(dirname "$MIND_DATABASE")"
.venv/bin/python -m mind_core init --database "$MIND_DATABASE"
```

If you deliberately use another path, configure `MIND_CORE_DATABASE` for the
hook and any local query process before launching Codex. A database created only
at `./mind-data/` is valid for direct CLI use but is not the plugin default.

Expected result: one JSON object containing, among other fields,
`"runtime_version":"0.2.0"`, `"schema_version":2`,
`"persona_required":false`, and
`"mode":"phase2_associative_disclosure_h0"`.

Read the same state later. On Windows:

```powershell
.\.venv\Scripts\python.exe -m mind_core status --database $MindDatabase
```

On macOS or Linux:

```sh
.venv/bin/python -m mind_core status --database "$MIND_DATABASE"
```

Completion proof: `status` exits successfully and reports the same Core
instance without changing its record counts.
## Activate the included reminder generation

The archive includes authored cards for all sixteen MIND Faculties and a
behavior-qualified index for the local `qwen3-embedding:0.6b` profile. Model
weights are not bundled or silently downloaded.

Install the named model separately:

```powershell
ollama pull qwen3-embedding:0.6b
```

Bootstrap and activate the complete generation:

```powershell
.\.venv\Scripts\python.exe -m mind_core bootstrap --database $MindDatabase --manifest .\skills\augment-of-mind\assets\associative-bootstrap.json
.\.venv\Scripts\python.exe -m mind_core index --database $MindDatabase --manifest .\skills\augment-of-mind\assets\associative-index-qwen3-embedding-0.6b.json
```

Compile one explicit H0 Arm's Reach field:

```powershell
.\.venv\Scripts\python.exe .\scripts\query_associative_field.py "The release crashed midway; recover the prior decisions and unfinished checks." --database $MindDatabase --field-only
```

Expected result: the field names nearby handles without scores or rank. The
adapter sends the ephemeral anchor to the local Ollama loopback API, records
session evidence in Core, and does not persist the raw anchor or rendered field.
This proves an explicit H0 query, not automatic Codex pre-turn delivery.

Add `--hint "exact phrase"` when you want exhaustive lexical matching as well
as vector association. The adapter does not extract lexical hints from the raw
task on its own.


## Administrative and query commands

Run `python -m mind_core --help` from the active environment, or append
`--help` to a subcommand, for its exact arguments. The installed `mind-core`
console script is equivalent when it is on your shell's path.

| Command | Purpose |
|---|---|
| `init` | Initialize migrations and report Core state. |
| `status` | Report versions, mode, instance identity, and table counts. |
| `bootstrap` | Ingest explicit Phase 1 metadata from a JSON manifest. |
| `index` | Ingest one complete associative-index generation. |
| `activate-estate-generation` | Atomically admit a complete estate and activate its complete associative successor. |
| `issue-session-capability` | Issue one scoped opaque query capability. |
| `revoke-session-capability` | Revoke an issued query capability. |
| `query` | Execute one JSON request file through the H0 service. |
| `serve` | Run the length-prefixed query-only stdio service. |

The manifest and request schemas are strict. The included baseline generation
covers the sixteen MIND Faculties. The public layer can build a different
operator-reviewed estate, but no Collaborative Dynamics local capability
records or embedding-model weights are bundled.

## Safe stopping and removal

Stop any `serve` process before copying or removing its database. Uninstall the
wheel from the environment with:

```powershell
.\.venv\Scripts\python.exe -m pip uninstall cd-mind-core
```

Uninstalling the wheel does not delete databases. Remove those separately only
after you have resolved the exact paths and retained any copy you need.

For symptoms and recovery, see [Troubleshooting](TROUBLESHOOTING.md#mind-core).

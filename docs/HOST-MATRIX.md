# Host support and evidence matrix

This matrix states what was exercised for this source tree. It is not a promise about every future host build.

| Surface | Package shape | Evidence in this build | Current claim |
|---|---|---|---|
| Codex plugin source | two local marketplace plugins | manifests parsed; 41 skill roots checked | structurally ready |
| MIND Core estate | SQLite bootstrap and associative index | isolated activation, readback, integrity, and three semantic probes | mechanically exercised; profile unqualified |
| Codex prompt hook | `UserPromptSubmit` Python hook | direct explicit-identity and contextual-defer probes | hook code executed outside a live trusted host |
| Codex marketplace install | `install.ps1` | CLI contracts inspected; script parser checked | live customer install not yet exercised from this new repository |
| Fresh-task discovery | installed Codex task boundary | not tested for this new package | unverified |
| Trusted pre-prompt delivery | host `/hooks` trust plus provider path | not tested for this new package | unverified |
| Contextual MCP association | local MIND server | source and isolated query helper exercised | live plugin-host invocation unverified |
| Claude folders | one self-contained folder per skill | release verifier checks topology and metadata | structurally ready after build |
| Claude ZIP upload and enablement | one ZIP per skill | not tested | unverified |
| Claude automatic reminders or shared Core | no equivalent adapter shipped | not implemented | not available |

The observed development host is Windows with PowerShell 5.1 and Python 3.14 in UTF-8 mode. The source requires Python 3.11 or newer. A Windows console without UTF-8 mode can fail while printing MIND's Unicode field even when Core retrieval succeeded; runtime scripts that control their streams configure UTF-8, and maintainer commands use `python -X utf8`.
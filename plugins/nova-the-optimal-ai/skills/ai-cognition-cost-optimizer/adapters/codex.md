# Codex Adapter

Install the whole `ai-cognition-cost-optimizer` folder in the configured Codex skills directory. Start a new task and invoke `$ai-cognition-cost-optimizer` explicitly for first discovery. The deterministic calculator is offline. Local routing requires Python and an Ollama service on the same machine; planning is read-only, while execution requires the request's `execution_authorized: true` and the explicit `--execute` flag. Public price refreshes and external account actions remain governed by Codex permissions and the SKILL's authority boundary.

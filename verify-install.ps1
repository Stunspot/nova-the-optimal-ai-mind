[CmdletBinding()]
param(
    [string]$DatabasePath = (Join-Path $env:USERPROFILE '.codex\data\stores\mind_core.sqlite')
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$marketplace = 'collaborative-dynamics-nova-free'
$mindRoot = Join-Path $root 'plugins\augment-of-mind'
$queryScript = Join-Path $mindRoot 'scripts\query_associative_field.py'
$index = Join-Path $root 'bundle\reminder\associative-index-qwen3-embedding-0.6b.json'
$indexManifest = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json
$embeddingModel = $indexManifest.embedding_profile.model_id
$ollamaUrl = if ($env:MIND_OLLAMA_URL) { $env:MIND_OLLAMA_URL } else { 'http://127.0.0.1:11434' }
$python = Get-Command python -ErrorAction Stop
$codex = Get-Command codex -ErrorAction Stop

$marketState = & $codex.Source plugin marketplace list --json | ConvertFrom-Json
if (-not @($marketState.marketplaces | Where-Object { $_.name -eq $marketplace })) {
    throw "Marketplace is not configured: $marketplace"
}
$pluginState = & $codex.Source plugin list --json | ConvertFrom-Json
$expected = @("augment-of-mind@$marketplace", "nova-the-optimal-ai@$marketplace")
foreach ($selector in $expected) {
    if (-not @($pluginState.installed | Where-Object { $_.pluginId -eq $selector -and $_.enabled })) {
        throw "Plugin is not installed and enabled: $selector"
    }
}
if (-not (Test-Path -LiteralPath $DatabasePath)) {
    throw "MIND Core database is missing: $DatabasePath"
}

$priorPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($priorPythonPath) { "$mindRoot;$priorPythonPath" } else { $mindRoot }
    $statusText = & $python.Source -m mind_core.cli status --database $DatabasePath
    if ($LASTEXITCODE -ne 0) { throw 'MIND Core status failed.' }
    $status = $statusText | ConvertFrom-Json
    & $python.Source -X utf8 $queryScript 'MIND semantic association readback probe' --database $DatabasePath --model $embeddingModel --ollama-url $ollamaUrl --field-only | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'MIND semantic association readback failed.' }
} finally {
    $env:PYTHONPATH = $priorPythonPath
}

[pscustomobject]@{
    marketplace = $marketplace
    plugins = $expected
    database = $DatabasePath
    capability_count = $status.capability_count
    active_snapshot = $status.active_associative_snapshot_id
    qualification_state = $status.qualification_state
    semantic_association = 'ready'
    embedding_model = $embeddingModel
    embedding_endpoint = $ollamaUrl
    hook_trust = 'not observable from this script; inspect Settings → Hooks'
    fresh_task_discovery = 'not observable from this script; start a new task'
} | ConvertTo-Json -Depth 4
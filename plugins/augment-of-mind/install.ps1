[CmdletBinding()]
param([string]$DatabasePath = (Join-Path $env:USERPROFILE '.codex\data\stores\mind_core.sqlite'))

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$marketplace = 'collaborative-dynamics-mind'
$selector = "augment-of-mind@$marketplace"
$bootstrap = Join-Path $root 'skills\augment-of-mind\assets\associative-bootstrap.json'
$index = Join-Path $root 'skills\augment-of-mind\assets\associative-index-qwen3-embedding-0.6b.json'
$queryScript = Join-Path $root 'scripts\query_associative_field.py'
$indexManifest = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json
$embeddingModel = $indexManifest.embedding_profile.model_id
$ollamaUrl = if ($env:MIND_OLLAMA_URL) { $env:MIND_OLLAMA_URL } else { 'http://127.0.0.1:11434' }

foreach ($required in @($bootstrap, $index, $queryScript, (Join-Path $root 'mind_core\cli.py'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required MIND file is missing: $required" }
}
$python = Get-Command python -ErrorAction SilentlyContinue
$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python 3.11 or newer is required.' }
if (-not $codex) { throw 'Codex CLI with plugin support is required.' }
$version = & $python.Source -c "import sys; print('.'.join(map(str,sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required; found $version." }

$plugins = & $codex.Source plugin list --json | ConvertFrom-Json
$conflicts = @($plugins.installed | Where-Object { $_.name -eq 'augment-of-mind' -and $_.pluginId -ne $selector })
if ($conflicts.Count) {
    throw "Another MIND selector exists: $(($conflicts.pluginId) -join ', '). Remove only the selector you intend to replace, then rerun."
}
$markets = & $codex.Source plugin marketplace list --json | ConvertFrom-Json
$known = @($markets.marketplaces | Where-Object { $_.name -eq $marketplace })
if (-not $known) {
    & $codex.Source plugin marketplace add $root --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex did not add the MIND marketplace.' }
}
$plugins = & $codex.Source plugin list --json | ConvertFrom-Json
if (-not @($plugins.installed | Where-Object { $_.pluginId -eq $selector -and $_.enabled })) {
    & $codex.Source plugin add $selector --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex did not install MIND.' }
}
if (Test-Path -LiteralPath $DatabasePath) {
    throw "A MIND database already exists at $DatabasePath and was not changed. Choose an empty path or perform an explicit successor-estate migration."
}
$parent = Split-Path -Parent $DatabasePath
if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($prior) { "$root;$prior" } else { $root }
    & $python.Source -X utf8 -m mind_core.cli activate-estate-generation --database $DatabasePath --bootstrap $bootstrap --index $index
    if ($LASTEXITCODE -ne 0) { throw 'MIND Core activation failed.' }
    & $python.Source -X utf8 -m mind_core.cli status --database $DatabasePath
    if ($LASTEXITCODE -ne 0) { throw 'MIND Core status readback failed.' }
    & $python.Source -X utf8 $queryScript 'MIND semantic association installation probe' --database $DatabasePath --model $embeddingModel --ollama-url $ollamaUrl --field-only | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "MIND estate is active, but semantic association failed. Confirm Ollama is reachable at $ollamaUrl and model '$embeddingModel' is installed." }
} finally {
    $env:PYTHONPATH = $prior
}
Write-Host ''
Write-Host 'MIND 2.1.2 is installed, its 20-capability estate is active, and semantic association passed.'
Write-Host 'Next: review the exact hook in Settings → Hooks, then start a new task.'
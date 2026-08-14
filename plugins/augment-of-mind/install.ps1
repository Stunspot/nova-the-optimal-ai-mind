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
$version = & $python.Source -B -c "import sys; print('.'.join(map(str,sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required; found $version." }

$pluginJson = & $codex.Source plugin list --json
if ($LASTEXITCODE -ne 0) { throw 'Codex did not return installed plugin state.' }
$plugins = $pluginJson | ConvertFrom-Json
$conflicts = @($plugins.installed | Where-Object { $_.name -eq 'augment-of-mind' -and $_.pluginId -ne $selector })
if ($conflicts.Count) {
    throw "Another MIND selector exists: $(($conflicts.pluginId) -join ', '). Remove only the selector you intend to replace, then rerun."
}
$installedMind = @($plugins.installed | Where-Object { $_.pluginId -eq $selector })
if ($installedMind.Count -gt 0 -and @($installedMind | Where-Object { $_.version -eq '2.2.1' }).Count -ne $installedMind.Count) {
    $observed = ($installedMind | ForEach-Object { $_.version }) -join ', '
    throw "A different MIND version is already installed from this selector: $observed. This installer will not silently reuse it. Remove $selector, confirm this marketplace points at the 2.2.1 package, then rerun. No plugin state was changed."
}

$marketJson = & $codex.Source plugin marketplace list --json
if ($LASTEXITCODE -ne 0) { throw 'Codex did not return marketplace state.' }
$markets = $marketJson | ConvertFrom-Json
$known = @($markets.marketplaces | Where-Object { $_.name -eq $marketplace })
if ($known.Count -gt 0 -and (Resolve-Path -LiteralPath $known[0].root).Path -ne (Resolve-Path -LiteralPath $root).Path) {
    throw "The MIND plugin source already points somewhere else: $($known[0].root)"
}

$databaseFullPath = [System.IO.Path]::GetFullPath($DatabasePath)
if (Test-Path -LiteralPath $databaseFullPath) {
    throw "A MIND database already exists at $DatabasePath and was not changed. Choose an empty path or perform an explicit successor-estate migration."
}
$parent = [System.IO.Path]::GetDirectoryName($databaseFullPath)
if ([string]::IsNullOrWhiteSpace($parent)) { throw "MIND database path has no parent directory: $DatabasePath" }
$stagingParent = $parent
while (-not (Test-Path -LiteralPath $stagingParent)) {
    $nextParent = [System.IO.Path]::GetDirectoryName($stagingParent)
    if ([string]::IsNullOrWhiteSpace($nextParent) -or $nextParent -eq $stagingParent) {
        throw "No existing parent directory can stage the MIND database for: $DatabasePath"
    }
    $stagingParent = $nextParent
}
$stagingRoot = Join-Path $stagingParent ('.mind-install-preflight-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stagingRoot | Out-Null
$stagingDatabase = Join-Path $stagingRoot 'mind_core.sqlite'

$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($prior) { "$root;$prior" } else { $root }
    & $python.Source -B -X utf8 -m mind_core.cli activate-estate-generation --database $stagingDatabase --bootstrap $bootstrap --index $index | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'MIND preflight could not build a disposable capability estate.' }
    & $python.Source -B -X utf8 -m mind_core.cli status --database $stagingDatabase | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'MIND preflight estate status readback failed.' }
    & $python.Source -B -X utf8 $queryScript 'MIND semantic association installation probe' --database $stagingDatabase --model $embeddingModel --ollama-url $ollamaUrl --field-only | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "MIND preflight semantic association failed. Nothing was installed. Confirm Ollama is reachable at $ollamaUrl and model '$embeddingModel' is installed." }

    if ($known.Count -eq 0) {
        & $codex.Source plugin marketplace add $root --json | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Codex did not add the MIND marketplace. The preflight database was discarded; rerun after correcting Codex.' }
    }
    $pluginJson = & $codex.Source plugin list --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex did not return plugin state after marketplace setup.' }
    $plugins = $pluginJson | ConvertFrom-Json
    if (-not @($plugins.installed | Where-Object { $_.pluginId -eq $selector -and $_.enabled })) {
        & $codex.Source plugin add $selector --json | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Codex did not install MIND. Marketplace setup is safe to reuse on the next run.' }
    }

    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    if (Test-Path -LiteralPath $databaseFullPath) {
        throw "A MIND database appeared at $databaseFullPath during installation. It was not overwritten."
    }
    Move-Item -LiteralPath $stagingDatabase -Destination $databaseFullPath
} finally {
    $env:PYTHONPATH = $prior
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
Write-Host ''
Write-Host 'MIND 2.2.1 is installed, its 20-capability estate is active, and semantic association passed.'
Write-Host 'Next: review the exact hook in Settings > Hooks, then start a new task.'

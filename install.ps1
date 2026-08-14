[CmdletBinding()]
param(
    [string]$DatabasePath = (Join-Path $env:USERPROFILE '.codex\data\stores\mind_core.sqlite'),
    [switch]$SkipPluginInstall
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$marketplace = 'collaborative-dynamics-nova-free'
$sourceMarketplace = Join-Path $root '.agents\plugins\marketplace.json'
$marketplaceRoot = if (Test-Path -LiteralPath $sourceMarketplace) { $root } else { Join-Path $root 'codex' }
$bootstrap = Join-Path $root 'bundle\reminder\associative-bootstrap.json'
$index = Join-Path $root 'bundle\reminder\associative-index-qwen3-embedding-0.6b.json'
$mindRoot = Join-Path $marketplaceRoot 'plugins\augment-of-mind'
$queryScript = Join-Path $mindRoot 'scripts\query_associative_field.py'
$indexManifest = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json
$embeddingModel = $indexManifest.embedding_profile.model_id
$ollamaUrl = if ($env:MIND_OLLAMA_URL) { $env:MIND_OLLAMA_URL } else { 'http://127.0.0.1:11434' }

function Require-Path([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label is missing: $Path"
    }
}

Require-Path (Join-Path $marketplaceRoot '.agents\plugins\marketplace.json') 'Marketplace manifest'
Require-Path $bootstrap 'Free Nova capability bootstrap'
Require-Path $index 'Free Nova associative index'
Require-Path (Join-Path $mindRoot 'mind_core\cli.py') 'MIND Core runtime'
Require-Path $queryScript 'MIND semantic association probe'

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python 3.11 or newer is required for MIND capability reminders. Install Python, then rerun this installer.'
}
$pythonVersion = & $python.Source -B -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 or newer is required; found $pythonVersion."
}

$databaseFullPath = [System.IO.Path]::GetFullPath($DatabasePath)
if (Test-Path -LiteralPath $databaseFullPath) {
    throw "A MIND Core database already exists at $DatabasePath. It was not changed. Use docs\UPGRADE.md to reconcile an existing estate, or rerun with -DatabasePath pointing to a new approved file."
}

$known = @()
if (-not $SkipPluginInstall) {
    $codex = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $codex) {
        throw 'Codex CLI with plugin support is required. Install or update Codex, then rerun this installer.'
    }

    $installedJson = & $codex.Source plugin list --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex did not return installed plugin state.' }
    $installedState = $installedJson | ConvertFrom-Json
    $conflicts = @($installedState.installed | Where-Object {
        $_.name -in @('nova-the-optimal-ai', 'augment-of-mind') -and $_.marketplaceName -ne $marketplace
    })
    if ($conflicts.Count -gt 0) {
        throw "Another copy of Nova or MIND is installed from a different source. Open Codex > Settings > Plugins, remove or disable the older Nova or MIND card, then rerun. Nothing was changed."
    }

    $expectedPluginVersions = @{
        'augment-of-mind' = '2.2.2'
        'nova-the-optimal-ai' = '2.1.0'
    }
    $staleVersions = @($installedState.installed | Where-Object {
        $_.marketplaceName -eq $marketplace -and
        $expectedPluginVersions.ContainsKey($_.name) -and
        $_.version -ne $expectedPluginVersions[$_.name]
    })
    if ($staleVersions.Count -gt 0) {
        $observed = ($staleVersions | ForEach-Object { "$($_.name) $($_.version)" }) -join ', '
        throw "A different Free Nova plugin version is already installed: $observed. This installer will not silently reuse it. Remove the two collaborative-dynamics-nova-free selectors, point the marketplace at this package, then install both selectors again. No plugin state was changed."
    }

    $marketplaceJson = & $codex.Source plugin marketplace list --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex did not return marketplace state.' }
    $knownMarketplaces = $marketplaceJson | ConvertFrom-Json
    $known = @($knownMarketplaces.marketplaces | Where-Object { $_.name -eq $marketplace })
    if ($known.Count -gt 0 -and (Resolve-Path -LiteralPath $known[0].root).Path -ne (Resolve-Path -LiteralPath $marketplaceRoot).Path) {
        throw "The Nova + MIND plugin source already points somewhere else: $($known[0].root)"
    }
}

$dbParent = [System.IO.Path]::GetDirectoryName($databaseFullPath)
if ([string]::IsNullOrWhiteSpace($dbParent)) { throw "MIND database path has no parent directory: $DatabasePath" }
$stagingParent = $dbParent
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

$priorPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($priorPythonPath) { "$mindRoot;$priorPythonPath" } else { $mindRoot }
    & $python.Source -B -m mind_core.cli activate-estate-generation --database $stagingDatabase --bootstrap $bootstrap --index $index | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'MIND preflight could not build a disposable Free Nova capability estate.' }
    & $python.Source -B -m mind_core.cli status --database $stagingDatabase | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'MIND preflight estate status readback failed.' }
    & $python.Source -B -X utf8 $queryScript 'MIND semantic association installation probe' --database $stagingDatabase --model $embeddingModel --ollama-url $ollamaUrl --field-only | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "MIND preflight semantic association failed. Nothing was installed. Confirm Ollama is reachable at $ollamaUrl and model '$embeddingModel' is installed." }

    if (-not $SkipPluginInstall) {
        if ($known.Count -eq 0) {
            & $codex.Source plugin marketplace add $marketplaceRoot --json | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Codex did not add the Free Nova marketplace. The preflight database was discarded; rerun after correcting Codex.' }
        }
        $installedJson = & $codex.Source plugin list --json
        if ($LASTEXITCODE -ne 0) { throw 'Codex did not return plugin state after marketplace setup.' }
        $installedState = $installedJson | ConvertFrom-Json
        foreach ($name in @('augment-of-mind', 'nova-the-optimal-ai')) {
            $selector = "$name@$marketplace"
            $present = @($installedState.installed | Where-Object { $_.pluginId -eq $selector -and $_.enabled })
            if ($present.Count -eq 0) {
                & $codex.Source plugin add $selector --json | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "Codex did not install $name. Completed plugin steps are safe to reuse on the next run." }
            }
        }
    }

    if (-not (Test-Path -LiteralPath $dbParent)) {
        New-Item -ItemType Directory -Path $dbParent -Force | Out-Null
    }
    if (Test-Path -LiteralPath $databaseFullPath) {
        throw "A MIND database appeared at $databaseFullPath during installation. It was not overwritten."
    }
    Move-Item -LiteralPath $stagingDatabase -Destination $databaseFullPath
} finally {
    $env:PYTHONPATH = $priorPythonPath
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
Write-Host ''
if ($SkipPluginInstall) {
    Write-Host 'The Free Nova 41-capability reminder estate is active and semantic association passed. Plugin installation was skipped.'
    Write-Host 'Next: install or enable Nova and MIND separately, then review the exact MIND prompt-submit hook before trusting it.'
} else {
    Write-Host 'Free Nova is installed. Both plugins are enabled, its 41-capability reminder estate is active, and semantic association passed.'
    Write-Host 'Next: open Codex, review the exact MIND prompt-submit hook in Settings > Hooks, trust it if the bytes match this package, then start a new task.'
}

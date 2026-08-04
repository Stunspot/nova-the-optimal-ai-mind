[CmdletBinding()]
param(
    [string]$DatabasePath = (Join-Path $env:USERPROFILE '.codex\data\stores\mind_core.sqlite'),
    [switch]$SkipPluginInstall
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$marketplace = 'collaborative-dynamics-nova-free'
$bootstrap = Join-Path $root 'bundle\reminder\associative-bootstrap.json'
$index = Join-Path $root 'bundle\reminder\associative-index-qwen3-embedding-0.6b.json'
$mindRoot = Join-Path $root 'plugins\augment-of-mind'

function Require-Path([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label is missing: $Path"
    }
}

Require-Path (Join-Path $root '.agents\plugins\marketplace.json') 'Marketplace manifest'
Require-Path $bootstrap 'Free Nova capability bootstrap'
Require-Path $index 'Free Nova associative index'
Require-Path (Join-Path $mindRoot 'mind_core\cli.py') 'MIND Core runtime'

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python 3.11 or newer is required for MIND capability reminders. Install Python, then rerun this installer.'
}
$pythonVersion = & $python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 or newer is required; found $pythonVersion."
}

if (-not $SkipPluginInstall) {
    $codex = Get-Command codex -ErrorAction SilentlyContinue
    if (-not $codex) {
        throw 'Codex CLI with plugin support is required. Install or update Codex, then rerun this installer.'
    }

    $installedState = & $codex.Source plugin list --json | ConvertFrom-Json
    $conflicts = @($installedState.installed | Where-Object {
        $_.name -in @('nova-the-optimal-ai', 'augment-of-mind') -and $_.marketplaceName -ne $marketplace
    })
    if ($conflicts.Count -gt 0) {
        $selectors = ($conflicts | ForEach-Object { $_.pluginId }) -join ', '
        throw "Earlier Nova or MIND selectors are enabled or installed: $selectors. Remove those exact selectors with 'codex plugin remove <selector>', then rerun. The installer will not silently replace another installation."
    }

    $knownMarketplaces = & $codex.Source plugin marketplace list --json | ConvertFrom-Json
    $known = @($knownMarketplaces.marketplaces | Where-Object { $_.name -eq $marketplace })
    if ($known.Count -eq 0) {
        & $codex.Source plugin marketplace add $root --json
        if ($LASTEXITCODE -ne 0) { throw 'Codex did not add the Free Nova marketplace.' }
    } elseif ((Resolve-Path -LiteralPath $known[0].root).Path -ne (Resolve-Path -LiteralPath $root).Path) {
        throw "Marketplace '$marketplace' already points somewhere else: $($known[0].root)"
    }

    $installedState = & $codex.Source plugin list --json | ConvertFrom-Json
    foreach ($name in @('augment-of-mind', 'nova-the-optimal-ai')) {
        $selector = "$name@$marketplace"
        $present = @($installedState.installed | Where-Object { $_.pluginId -eq $selector -and $_.enabled })
        if ($present.Count -eq 0) {
            & $codex.Source plugin add $selector --json
            if ($LASTEXITCODE -ne 0) { throw "Codex did not install $selector." }
        }
    }
}

if (Test-Path -LiteralPath $DatabasePath) {
    throw "A MIND Core database already exists at $DatabasePath. It was not changed. Use docs\UPGRADE.md to reconcile an existing estate, or rerun with -DatabasePath pointing to a new approved file."
}
$dbParent = Split-Path -Parent $DatabasePath
if (-not (Test-Path -LiteralPath $dbParent)) {
    New-Item -ItemType Directory -Path $dbParent -Force | Out-Null
}

$priorPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($priorPythonPath) { "$mindRoot;$priorPythonPath" } else { $mindRoot }
    & $python.Source -m mind_core.cli activate-estate-generation --database $DatabasePath --bootstrap $bootstrap --index $index
    if ($LASTEXITCODE -ne 0) { throw 'MIND Core did not activate the Free Nova capability estate.' }
    & $python.Source -m mind_core.cli status --database $DatabasePath
    if ($LASTEXITCODE -ne 0) { throw 'MIND Core activation completed but status readback failed.' }
} finally {
    $env:PYTHONPATH = $priorPythonPath
}

Write-Host ''
Write-Host 'Free Nova is installed and its 40-capability reminder estate is active.'
Write-Host 'Next: open Codex, review the exact MIND prompt-submit hook through /hooks, trust it if the bytes match this package, then start a new task.'
Write-Host 'First prompt: Use $nova to help me with this.'
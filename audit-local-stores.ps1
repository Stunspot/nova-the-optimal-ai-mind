[CmdletBinding()]
param(
    [string[]]$AdditionalRoots = @(),
    [string]$OutputPath = (Join-Path $HOME '.codex\setup-audit\local-store-inventory.json')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$runningCodex = @(Get-Process -Name ChatGPT, codex -ErrorAction SilentlyContinue)
if ($runningCodex.Count -gt 0) {
    throw 'Close Codex desktop before running this store audit. The audit is read-only, but a closed app gives a stable snapshot.'
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
$pythonPrefix = @('-3')
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $pythonPrefix = @()
}
if (-not $pythonCommand) {
    throw 'Python 3.11 or newer is required. Install Python, then rerun this audit.'
}
$pythonExe = $pythonCommand.Source
$tool = Join-Path $PSScriptRoot 'tools\audit_local_stores.py'
if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
    throw "The audit tool is missing: $tool"
}

$roots = New-Object System.Collections.Generic.List[string]
function Add-ExistingRoot([string]$Path) {
    if ($Path -and (Test-Path -LiteralPath $Path)) {
        $resolved = (Resolve-Path -LiteralPath $Path).Path
        if (-not $roots.Contains($resolved)) {
            $roots.Add($resolved)
        }
    }
}

$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
Add-ExistingRoot $codexHome
Add-ExistingRoot (Join-Path $HOME 'plugins')
Add-ExistingRoot (Join-Path $HOME 'plugin-quarantine')
Add-ExistingRoot 'E:\Github'
Add-ExistingRoot 'E:\Indranet'

foreach ($environmentPath in @(
    $env:MIND_CORE_DATABASE,
    $env:DUNBAR_STORE,
    $env:CORKBOARD_HOME
)) {
    if ($environmentPath) {
        Add-ExistingRoot $environmentPath
    }
}
foreach ($root in $AdditionalRoots) {
    Add-ExistingRoot $root
}

if ($roots.Count -eq 0) {
    throw 'No existing audit roots were found.'
}

$outputParent = Split-Path -Parent $OutputPath
if ($outputParent -and -not (Test-Path -LiteralPath $outputParent)) {
    New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
}

$arguments = @($pythonPrefix) + @('-X', 'utf8', $tool, '--output', $OutputPath)
foreach ($root in $roots) {
    $arguments += @('--root', $root)
}

& $pythonExe @arguments | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'The local store audit did not complete.'
}

$report = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json
Write-Host ''
Write-Host 'READ-ONLY STORE AUDIT COMPLETE'
Write-Host "Report: $OutputPath"
Write-Host "SQLite databases found: $($report.summary.database_count)"
Write-Host "MIND databases found: $($report.summary.mind_core_count)"
Write-Host "Corkboard databases found: $($report.summary.corkboard_count)"
Write-Host "Dunbar databases found: $($report.summary.dunbar_count)"

$mindRows = @($report.databases | Where-Object { $_.kind -eq 'mind_core' } | ForEach-Object {
    $active = $_.details.active_generation
    $largestCards = $_.details.largest_generation_by_cards
    $largestVectors = $_.details.largest_generation_by_vectors
    [pscustomobject]@{
        Path = $_.path
        TotalCards = $_.details.counts.capability_cards
        TotalVectors = $_.details.counts.associative_view_vectors
        ActiveCards = if ($null -ne $active) { $active.card_count } else { 0 }
        ActiveVectors = if ($null -ne $active) { $active.vector_count } else { 0 }
        LargestCards = if ($null -ne $largestCards) { $largestCards.card_count } else { 0 }
        LargestVectors = if ($null -ne $largestVectors) { $largestVectors.vector_count } else { 0 }
    }
})
if ($mindRows.Count -gt 0) {
    Write-Host ''
    Write-Host 'MIND ESTATES'
    $mindRows | Format-Table -AutoSize
}

$otherRows = @($report.databases | Where-Object { $_.kind -in @('corkboard', 'dunbar') } | ForEach-Object {
    [pscustomobject]@{
        Kind = $_.kind
        Path = $_.path
        Details = ($_.details | ConvertTo-Json -Compress -Depth 4)
    }
})
if ($otherRows.Count -gt 0) {
    Write-Host ''
    Write-Host 'OTHER RECOGNIZED STORES'
    $otherRows | Format-Table -AutoSize
}

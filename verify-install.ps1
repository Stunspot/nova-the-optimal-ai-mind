[CmdletBinding()]
param(
    [string]$DatabasePath = (Join-Path $env:USERPROFILE '.codex\data\stores\mind_core.sqlite'),
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = $PSScriptRoot
$sourceId = 'collaborative-dynamics-nova-free'
$sourceDisplayName = 'Nova + MIND Free by Collaborative Dynamics'
$mindRoot = Join-Path $root 'plugins\augment-of-mind'
$queryScript = Join-Path $mindRoot 'scripts\query_associative_field.py'
$index = Join-Path $root 'bundle\reminder\associative-index-qwen3-embedding-0.6b.json'
$indexManifest = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json
$embeddingModel = $indexManifest.embedding_profile.model_id
$ollamaUrl = if ($env:MIND_OLLAMA_URL) { $env:MIND_OLLAMA_URL } else { 'http://127.0.0.1:11434' }

$runningCodex = @(Get-Process -Name ChatGPT, codex -ErrorAction SilentlyContinue)
if ($runningCodex.Count -gt 0) {
    throw 'Close Codex desktop before running this verifier. The verifier will not stop it or change its state.'
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
$pythonPrefix = @('-3')
if (-not $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $pythonPrefix = @()
}
if (-not $pythonCommand) {
    throw 'Python 3.11 or newer is required. Install Python, then rerun this verifier.'
}
$pythonExe = $pythonCommand.Source
$versionArguments = @($pythonPrefix) + @(
    '-c',
    "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
)
$pythonVersion = & $pythonExe @versionArguments
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 or newer is required; found $pythonVersion."
}

$codex = Get-Command codex -ErrorAction Stop
$marketState = & $codex.Source plugin marketplace list --json | ConvertFrom-Json
$configuredSource = @($marketState.marketplaces | Where-Object { $_.name -eq $sourceId })
if ($configuredSource.Count -eq 0) {
    throw "Codex does not have '$sourceDisplayName' configured. Open Codex > Settings > Plugins > Marketplaces and add the Nova + MIND source."
}

$pluginState = & $codex.Source plugin list --json | ConvertFrom-Json
$requirements = @(
    [pscustomobject]@{
        internal_name = 'nova-the-optimal-ai'
        display_name = 'Nova the Optimal AI'
        expected_version = '2.0.1'
    },
    [pscustomobject]@{
        internal_name = 'augment-of-mind'
        display_name = 'MIND by Collaborative Dynamics'
        expected_version = '2.1.2'
    }
)
$verifiedPlugins = @()
foreach ($requirement in $requirements) {
    $matches = @($pluginState.installed | Where-Object {
        $_.name -eq $requirement.internal_name -and $_.marketplaceName -eq $sourceId
    })
    if ($matches.Count -eq 0) {
        throw "Open Codex > Settings > Plugins. '$($requirement.display_name)' is not installed from '$sourceDisplayName'."
    }
    $plugin = $matches[0]
    if (-not $plugin.enabled) {
        throw "Open Codex > Settings > Plugins and turn on '$($requirement.display_name)'."
    }
    if ($plugin.version -ne $requirement.expected_version) {
        throw "'$($requirement.display_name)' is version $($plugin.version); expected $($requirement.expected_version)."
    }
    $verifiedPlugins += [pscustomobject]@{
        name = $requirement.display_name
        version = $plugin.version
        enabled = [bool]$plugin.enabled
        installed_path = $plugin.installedPath
    }
}

if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw "The MIND capability database is missing: $DatabasePath"
}
$databaseFile = Get-Item -LiteralPath $DatabasePath
$databaseHashBefore = (Get-FileHash -LiteralPath $DatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('nova-mind-verify-' + [guid]::NewGuid().ToString('N'))
$tempDatabase = Join-Path $tempRoot 'mind_core.verify.sqlite'
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

$priorPythonPath = $env:PYTHONPATH
try {
    $backupCode = @'
from pathlib import Path
import sqlite3
import sys
source_uri = Path(sys.argv[1]).resolve().as_uri() + '?mode=ro'
source = sqlite3.connect(source_uri, uri=True)
target = sqlite3.connect(sys.argv[2])
try:
    source.backup(target)
finally:
    target.close()
    source.close()
'@
    $backupArguments = @($pythonPrefix) + @('-c', $backupCode, $DatabasePath, $tempDatabase)
    & $pythonExe @backupArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create a read-only verification copy of the MIND database.'
    }

    $env:PYTHONPATH = if ($priorPythonPath) { "$mindRoot;$priorPythonPath" } else { $mindRoot }

    $statusArguments = @($pythonPrefix) + @(
        '-X', 'utf8', '-m', 'mind_core.cli', 'status', '--database', $tempDatabase
    )
    $statusText = & $pythonExe @statusArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'MIND Core status failed against the verification copy.'
    }
    $status = $statusText | ConvertFrom-Json

    $probeArguments = @($pythonPrefix) + @(
        '-X', 'utf8', $queryScript,
        'MIND semantic association readback probe',
        '--database', $tempDatabase,
        '--model', $embeddingModel,
        '--ollama-url', $ollamaUrl,
        '--field-only'
    )
    & $pythonExe @probeArguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'MIND semantic association failed against the verification copy.'
    }
}
finally {
    $env:PYTHONPATH = $priorPythonPath
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

$databaseHashAfter = (Get-FileHash -LiteralPath $DatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($databaseHashAfter -ne $databaseHashBefore) {
    throw 'The live MIND database changed while verification was running. Nothing in the verifier intentionally writes to it; close any remaining agent processes and rerun.'
}

$report = [ordered]@{
    result = 'PASS'
    plugin_source = $sourceDisplayName
    plugins = $verifiedPlugins
    mind_database = [ordered]@{
        path = $databaseFile.FullName
        bytes = $databaseFile.Length
        last_write_utc = $databaseFile.LastWriteTimeUtc.ToString('o')
        sha256 = $databaseHashAfter
        original_unchanged_by_verifier = $true
    }
    capability_count = $status.capability_count
    active_snapshot = $status.active_associative_snapshot_id
    qualification_state = $status.qualification_state
    semantic_association = 'ready; tested against a temporary copy of the database'
    embedding_model = $embeddingModel
    embedding_endpoint = $ollamaUrl
    hook_check = "Open Codex > Settings > Hooks and confirm 'Bringing relevant capabilities within reach' is enabled."
    fresh_task_check = 'Start a new task and confirm Nova responds normally without attempting MIND resource retrieval.'
}

$json = $report | ConvertTo-Json -Depth 6
if ($OutputPath) {
    $outputParent = Split-Path -Parent $OutputPath
    if ($outputParent -and -not (Test-Path -LiteralPath $outputParent)) {
        New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
$json

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
$sourceMindRoot = Join-Path $root 'plugins\augment-of-mind'
$marketplaceRoot = if (Test-Path -LiteralPath $sourceMindRoot) { $root } else { Join-Path $root 'codex' }
$mindRoot = Join-Path $marketplaceRoot 'plugins\augment-of-mind'
$queryScript = Join-Path $mindRoot 'scripts\query_associative_field.py'
$index = Join-Path $root 'bundle\reminder\associative-index-qwen3-embedding-0.6b.json'
$indexManifest = Get-Content -LiteralPath $index -Raw | ConvertFrom-Json
$embeddingModel = $indexManifest.embedding_profile.model_id
$ollamaUrl = if ($env:MIND_OLLAMA_URL) { $env:MIND_OLLAMA_URL } else { 'http://127.0.0.1:11434' }

function Get-OptionalPropertyValue {
    param(
        [Parameter(Mandatory)]
        [object]$InputObject,
        [Parameter(Mandatory)]
        [string[]]$Names
    )

    foreach ($name in $Names) {
        $property = $InputObject.PSObject.Properties[$name]
        if ($null -ne $property) {
            return $property.Value
        }
    }
    return $null
}

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
    '-B', '-c',
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
        expected_version = '2.0.2'
    },
    [pscustomobject]@{
        internal_name = 'augment-of-mind'
        display_name = 'MIND by Collaborative Dynamics'
        expected_version = '2.1.6'
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
    $installedPath = Get-OptionalPropertyValue -InputObject $plugin -Names @(
        'installedPath', 'installed_path', 'path'
    )
    $verifiedPlugins += [pscustomobject]@{
        name = $requirement.display_name
        version = $plugin.version
        enabled = [bool]$plugin.enabled
        installed_path = $installedPath
    }
}

if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw "The MIND capability database is missing: $DatabasePath"
}
$databaseFile = Get-Item -LiteralPath $DatabasePath
$databaseHashBefore = (Get-FileHash -LiteralPath $DatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('nova-mind-verify-' + [guid]::NewGuid().ToString('N'))
$tempDatabase = Join-Path $tempRoot 'mind_core.verify.sqlite'
$backupScript = Join-Path $tempRoot 'backup_mind_database.py'
$inspectionScript = Join-Path $tempRoot 'inspect_mind_estate.py'
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
    Set-Content -LiteralPath $backupScript -Value $backupCode -Encoding ASCII
    $backupArguments = @($pythonPrefix) + @(
        '-B', '-X', 'utf8', $backupScript, $DatabasePath, $tempDatabase
    )
    & $pythonExe @backupArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create a read-only verification copy of the MIND database.'
    }

    $env:PYTHONPATH = if ($priorPythonPath) { "$mindRoot;$priorPythonPath" } else { $mindRoot }

    $inspectionCode = @'
import json
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
connection.row_factory = sqlite3.Row
try:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    required = {
        'capabilities',
        'capability_cards',
        'capability_card_views',
        'associative_index_snapshots',
        'associative_snapshot_cards',
        'associative_view_vectors',
        'associative_snapshot_activations',
        'embedding_profiles',
    }
    missing = sorted(required - tables)
    if missing:
        raise RuntimeError('MIND database is missing tables: ' + ', '.join(missing))

    count_tables = (
        'capabilities',
        'capability_cards',
        'capability_card_views',
        'capability_relations',
        'associative_index_snapshots',
        'associative_snapshot_cards',
        'associative_view_vectors',
        'associative_snapshot_activations',
    )
    counts = {
        table: int(connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
        for table in count_tables
    }

    generations = []
    rows = connection.execute(
        """
        SELECT
            activation.associative_snapshot_activation_id,
            activation.associative_index_snapshot_id,
            activation.prior_associative_index_snapshot_id,
            activation.activated_at,
            snapshot.created_at,
            snapshot.vector_coverage_state,
            profile.model_id,
            profile.dimensions,
            profile.radius,
            profile.qualification_state,
            (SELECT COUNT(*)
             FROM associative_snapshot_cards AS membership
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS card_count,
            (SELECT COUNT(DISTINCT card.capability_id)
             FROM associative_snapshot_cards AS membership
             JOIN capability_cards AS card
               ON card.capability_card_id = membership.capability_card_id
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS capability_count,
            (SELECT COUNT(*)
             FROM capability_card_views AS view
             JOIN associative_snapshot_cards AS membership
               ON membership.capability_card_id = view.capability_card_id
             WHERE membership.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS view_count,
            (SELECT COUNT(*)
             FROM associative_view_vectors AS vector
             WHERE vector.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS vector_count,
            (SELECT COUNT(*)
             FROM associative_snapshot_relations AS relation
             WHERE relation.associative_index_snapshot_id = activation.associative_index_snapshot_id
            ) AS relation_count
        FROM associative_snapshot_activations AS activation
        JOIN associative_index_snapshots AS snapshot
          ON snapshot.associative_index_snapshot_id = activation.associative_index_snapshot_id
        JOIN embedding_profiles AS profile
          ON profile.embedding_profile_id = snapshot.embedding_profile_id
        ORDER BY activation.activated_at DESC,
                 activation.associative_snapshot_activation_id DESC
        """
    ).fetchall()
    for row in rows:
        generations.append(dict(row))

    result = {
        'counts': counts,
        'active_generation': generations[0] if generations else None,
        'generations': generations,
        'largest_generation_by_cards': (
            max(generations, key=lambda item: item['card_count'])
            if generations else None
        ),
        'largest_generation_by_vectors': (
            max(generations, key=lambda item: item['vector_count'])
            if generations else None
        ),
        'integrity_check': connection.execute('PRAGMA integrity_check').fetchone()[0],
    }
    print(json.dumps(result, ensure_ascii=False))
finally:
    connection.close()
'@
    Set-Content -LiteralPath $inspectionScript -Value $inspectionCode -Encoding ASCII
    $inspectionArguments = @($pythonPrefix) + @(
        '-B', '-X', 'utf8', $inspectionScript, $tempDatabase
    )
    $inspectionText = & $pythonExe @inspectionArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not inspect the verification copy of the MIND database.'
    }
    $inspection = $inspectionText | ConvertFrom-Json

    $probeArguments = @($pythonPrefix) + @(
        '-B', '-X', 'utf8', $queryScript,
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
    estate = [ordered]@{
        total_capabilities = [int]$inspection.counts.capabilities
        total_cards = [int]$inspection.counts.capability_cards
        total_views = [int]$inspection.counts.capability_card_views
        total_vectors = [int]$inspection.counts.associative_view_vectors
        total_snapshots = [int]$inspection.counts.associative_index_snapshots
        total_activations = [int]$inspection.counts.associative_snapshot_activations
        active_generation = $inspection.active_generation
        largest_generation_by_cards = $inspection.largest_generation_by_cards
        largest_generation_by_vectors = $inspection.largest_generation_by_vectors
        generations = $inspection.generations
        integrity_check = $inspection.integrity_check
    }
    semantic_association = 'ready; tested against a temporary copy of the database'
    embedding_model = $embeddingModel
    embedding_endpoint = $ollamaUrl
    hook_check = "Open Codex > Settings > Hooks and confirm 'Bringing relevant capabilities within reach' is enabled."
    fresh_task_check = 'Start a new task and confirm Nova responds normally without attempting MIND resource retrieval.'
}

$json = $report | ConvertTo-Json -Depth 10
if ($OutputPath) {
    $outputParent = Split-Path -Parent $OutputPath
    if ($outputParent -and -not (Test-Path -LiteralPath $outputParent)) {
        New-Item -ItemType Directory -Path $outputParent -Force | Out-Null
    }
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
}
$json

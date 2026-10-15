<# Remove only temporary work files already bound by a sealed evidence checksum.
   Engineering projects, simulator storage and unmatched files are preserved. #>
param([string] $AuditPath)
$ErrorActionPreference='Stop'
$taskRepoRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$taskSpikesRoot=(Resolve-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'Fraktal\TiaSpikes')).Path
$taskArchivesRoot=(Resolve-Path -LiteralPath (Join-Path $taskRepoRoot 'FraktalCore\PLC\Siemens\Evidence\Archives')).Path
if (-not $AuditPath) { $AuditPath=Join-Path $env:LOCALAPPDATA ('Fraktal\TiaWorkCleanup_'+[datetime]::UtcNow.ToString('yyyyMMdd_HHmmss')+'.jsonl') }
if (Test-Path -LiteralPath $AuditPath) { throw 'Use a new audit path' }
function Inside-TaskPath([string] $Path,[string] $Root) {
    $resolved=[IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($Root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Path escaped its declared cleanup root' }
    return $resolved
}
$taskPairs=@(
 @('Persist_Medium_20261013','TIA_PERSIST_MEDIUM_2026-10-13','Work'),
 @('Access_Persistence_20261012','TIA_ACCESS_PERSISTENCE_2026-10-12','Runtime'),
 @('Event_Delivery_20261012','TIA_EVENT_DELIVERY_2026-10-12','Runtime'),
 @('Auto_Recovery_Decisions_20261012','TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12',''),
 @('Alarm_Persistence_20261012','TIA_ALARM_HISTORY_2026-10-12','Runtime'),
 @('Structure_Examples_20261011','TIA_STRUCTURE_EXAMPLES_2026-10-11',''),
 @('Config_Sets_20261012','TIA_CONFIG_SETS_2026-10-12',''),
 @('Alarm_Recovery_20261012','TIA_ALARM_RECOVERY_2026-10-12','Runtime'),
 @('Sequence_Integration_20261014','TIA_SEQUENCE_INTEGRATION_2026-10-14','Runtime'),
 @('Config_Transactions_20261011','TIA_CONFIG_TRANSACTIONS_2026-10-11',''),
 @('Sequence_View_20261013','TIA_SEQUENCE_VIEW_2026-10-13','Work'))
$taskAudit=New-Object IO.StreamWriter($AuditPath,$false,[Text.Encoding]::UTF8)
$taskRemoved=0;$taskBytes=0L;$taskPreserved=0;$taskFreeBefore=(Get-PSDrive C).Free
try {
    foreach ($taskPair in $taskPairs) {
        $taskSource=Inside-TaskPath (Join-Path $taskSpikesRoot $taskPair[0]) $taskSpikesRoot
        if (-not (Test-Path -LiteralPath $taskSource -PathType Container)) { continue }
        if ((Get-Item -LiteralPath $taskSource).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing a linked cleanup directory' }
        if (@(Get-ChildItem -LiteralPath $taskSource -Recurse -Force -Attributes ReparsePoint).Count) { throw 'Refusing a tree containing links' }
        $taskActive=@(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($taskSource,[StringComparison]::OrdinalIgnoreCase) -ge 0 })
        if ($taskActive.Count) { throw ('Work directory is in use: '+$taskPair[0]) }
        $taskArchive=Inside-TaskPath (Join-Path $taskArchivesRoot $taskPair[1]) $taskArchivesRoot
        $taskPayload=if ($taskPair[2]) { Join-Path $taskArchive $taskPair[2] } else { $taskArchive }
        $taskManifest=Join-Path $taskArchive 'SHA256SUMS'
        if (-not (Test-Path -LiteralPath $taskManifest)) { continue }
        $taskExpected=@{}
        foreach ($taskLine in [IO.File]::ReadAllLines($taskManifest)) {
            if ($taskLine -notmatch '^([0-9a-fA-F]{64})  (.+)$') { throw 'Malformed evidence manifest' }
            $taskDigest=$Matches[1];$taskName=$Matches[2].Replace('/','\')
            $taskFrozen=if ($taskName.StartsWith('FraktalCore\') -or $taskName.StartsWith('Specification\')) { Join-Path $taskRepoRoot $taskName } else { Join-Path $taskArchive $taskName }
            $taskFrozen=[IO.Path]::GetFullPath($taskFrozen)
            # Some older manifests also bind live repository inputs. Those
            # entries do not authorize removal of temporary work files.
            if (-not $taskFrozen.StartsWith($taskArchive.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { continue }
            $taskExpected[$taskFrozen]=$taskDigest
        }
        foreach ($taskFile in Get-ChildItem -LiteralPath $taskSource -File -Recurse -Force) {
            $taskOriginal=Inside-TaskPath $taskFile.FullName $taskSpikesRoot
            $taskRelative=$taskOriginal.Substring($taskSource.Length+1)
            $taskFrozen=Inside-TaskPath (Join-Path $taskPayload $taskRelative) $taskArchive
            if (-not $taskExpected.ContainsKey($taskFrozen) -or -not (Test-Path -LiteralPath $taskFrozen -PathType Leaf)) { $taskPreserved++;continue }
            $taskDigest=$taskExpected[$taskFrozen]
            if ((Get-FileHash -LiteralPath $taskFrozen -Algorithm SHA256).Hash -ne $taskDigest) { throw 'Sealed evidence failed its checksum; nothing further removed' }
            if ((Get-FileHash -LiteralPath $taskOriginal -Algorithm SHA256).Hash -ne $taskDigest) { $taskPreserved++;continue }
            $taskAudit.WriteLine((@{event='verified-duplicate';path=$taskOriginal;archive=$taskFrozen;sha256=$taskDigest;bytes=$taskFile.Length} | ConvertTo-Json -Compress))
            $taskAudit.Flush()
            Remove-Item -LiteralPath $taskOriginal -Force
            $taskRemoved++;$taskBytes+=$taskFile.Length
        }
        # Empty directories only. No recursive directory removal or guessed roots.
        foreach ($taskDirectory in Get-ChildItem -LiteralPath $taskSource -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending) {
            $taskEmpty=Inside-TaskPath $taskDirectory.FullName $taskSpikesRoot
            if (-not @(Get-ChildItem -LiteralPath $taskEmpty -Force).Count) { Remove-Item -LiteralPath $taskEmpty -Force }
        }
    }
    $taskResult=@{event='complete';removed_files=$taskRemoved;logical_bytes=$taskBytes;preserved_files=$taskPreserved;free_before=$taskFreeBefore;free_after=(Get-PSDrive C).Free;audit=$AuditPath}
    $taskAudit.WriteLine(($taskResult | ConvertTo-Json -Compress));$taskResult | ConvertTo-Json -Compress
} finally { $taskAudit.Dispose() }

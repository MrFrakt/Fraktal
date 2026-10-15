$ErrorActionPreference = 'Stop'
$stationRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'TiaStations')).Path.TrimEnd('\')
$listPath = Join-Path $PSScriptRoot 'ObsoleteTiaProjectCopies_20261014.json'
$entries = Get-Content -LiteralPath $listPath -Raw | ConvertFrom-Json
if ($entries.Count -ne 33) { throw 'Expected exactly 33 approved project copies.' }
$processes = @(Get-CimInstance Win32_Process)
$targets = foreach ($entry in $entries) {
    $absolute = [IO.Path]::GetFullPath($entry.Path).TrimEnd('\')
    if (-not $absolute.StartsWith($stationRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Parent $absolute) -ne $stationRoot -or
        (Split-Path -Leaf $absolute) -notmatch '_202610(11|12|13)$') {
        throw "Unapproved target: $absolute"
    }
    if (Test-Path -LiteralPath $absolute) {
        $resolved = (Resolve-Path -LiteralPath $absolute).Path.TrimEnd('\')
        if ($resolved -ne $absolute) { throw "Unexpected resolved path: $resolved" }
        $nodes = @(Get-Item -LiteralPath $absolute) + @(Get-ChildItem -LiteralPath $absolute -Recurse -Force)
        if (@($nodes | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
            throw "Linked directory found: $absolute"
        }
        if (@($processes | Where-Object {
            ($_.CommandLine -and $_.CommandLine.IndexOf($absolute, [StringComparison]::OrdinalIgnoreCase) -ge 0) -or
            ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($absolute + '\', [StringComparison]::OrdinalIgnoreCase))
        }).Count) { throw "An active process references: $absolute" }
        $files = @($nodes | Where-Object { -not $_.PSIsContainer })
        [PSCustomObject]@{Path=$absolute; Files=$files.Count; Bytes=[long](($files | Measure-Object Length -Sum).Sum)}
    }
}
$auditPath = Join-Path $PSScriptRoot ('ApprovedTiaProjectRetirement_' + [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss') + '.jsonl')
$before = (Get-PSDrive C).Free
[PSCustomObject]@{Event='Validated'; List=$listPath; Targets=$targets.Count; FreeBefore=$before; Utc=[DateTime]::UtcNow.ToString('o')} |
    ConvertTo-Json -Compress | Set-Content -LiteralPath $auditPath -Encoding UTF8
foreach ($target in $targets) {
    Remove-Item -LiteralPath $target.Path -Recurse -Force
    if (Test-Path -LiteralPath $target.Path) { throw "Removal incomplete: $($target.Path)" }
    [PSCustomObject]@{Event='Removed'; Path=$target.Path; Files=$target.Files; Bytes=$target.Bytes; Utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath $auditPath -Encoding UTF8
}
$after = (Get-PSDrive C).Free
$result = [PSCustomObject]@{Event='Complete'; RemovedDirectories=$targets.Count; LogicalBytes=[long](($targets | Measure-Object Bytes -Sum).Sum); FreeBefore=$before; FreeAfter=$after; RecoveredBytes=$after-$before; Audit=$auditPath}
$result | ConvertTo-Json -Compress | Add-Content -LiteralPath $auditPath -Encoding UTF8
$result | Format-List

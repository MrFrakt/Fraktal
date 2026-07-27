param(
    [string]$PlcRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()
$daOn = "{attribute 'OPC.UA.DA' := '1'}"
$daOff = "{attribute 'OPC.UA.DA' := '0'}"

function Get-DeclarationLines([System.IO.FileInfo]$File, [string]$Kind) {
    [xml]$document = Get-Content -LiteralPath $File.FullName -Raw
    $node = if ($Kind -eq 'POU') {
        $document.TcPlcObject.POU.Declaration
    } else {
        $document.TcPlcObject.GVL.Declaration
    }
    if ($null -eq $node) {
        throw "No $Kind declaration found in $($File.FullName)."
    }
    return @($node.InnerText -split "`r?`n")
}

function Get-NextCodeLine([string[]]$Lines, [int]$Index) {
    for ($cursor = $Index + 1; $cursor -lt $Lines.Count; $cursor++) {
        $candidate = $Lines[$cursor].Trim()
        if ($candidate.Length -gt 0 -and -not $candidate.StartsWith('//')) {
            return $candidate
        }
    }
    return ''
}

$pouFiles = Get-ChildItem -LiteralPath $PlcRoot -Recurse -Filter '*.TcPOU' |
    Where-Object { $_.FullName -notmatch '\\(\.vs|_Boot|_Config)\\' }

foreach ($file in $pouFiles) {
    $lines = Get-DeclarationLines -File $file -Kind 'POU'
    $isProgram = $lines | Where-Object { $_ -match '^\s*PROGRAM\s+' }
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $line = $lines[$index].Trim()
        if ($line -eq $daOn) {
            $next = Get-NextCodeLine -Lines $lines -Index $index
            if (-not $isProgram -or $next -notmatch '^[A-Za-z_][A-Za-z0-9_]*\s*:\s*[A-Za-z_]') {
                $failures.Add("$($file.FullName):$($index + 1): DA=1 is allowed only immediately before a deployed instance in a PROGRAM.")
            }
        }
        if ($line -match '(^|\s)(REFERENCE TO|POINTER TO)|:\s*(ARRAY\[[^\]]+\]\s+OF\s+)?I_[A-Za-z]') {
            $previous = if ($index -gt 0) { $lines[$index - 1].Trim() } else { '' }
            if ($previous -ne $daOff) {
                $failures.Add("$($file.FullName):$($index + 1): implementation reference requires an immediate DA=0 attribute: $line")
            }
        }
    }
}

$gvlFiles = Get-ChildItem -LiteralPath $PlcRoot -Recurse -Filter '*.TcGVL' |
    Where-Object { $_.FullName -notmatch '\\(\.vs|_Boot|_Config)\\' }
foreach ($file in $gvlFiles) {
    $lines = Get-DeclarationLines -File $file -Kind 'GVL'
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index].Trim() -ne $daOn) { continue }
        $next = Get-NextCodeLine -Lines $lines -Index $index
        if ($next -notmatch '^[A-Za-z_][A-Za-z0-9_]*\s*:\s*[A-Za-z_]') {
            $failures.Add("$($file.FullName):$($index + 1): GVL DA=1 must be immediately before the published variable.")
        }
    }
}

$topologyFile = Join-Path $PlcRoot 'Fraktal_Press_Demo\01_PneumaticPress\Io\GVL_PressFieldbus.TcGVL'
if (Test-Path -LiteralPath $topologyFile) {
    $topologyLines = Get-DeclarationLines -File (Get-Item -LiteralPath $topologyFile) -Kind 'GVL'
    $topologyIndex = [Array]::FindIndex(
        $topologyLines,
        [Predicate[string]] { param($value) $value -match '^\s*Topology\s*:\s*ST_FieldbusTopology\s*;' }
    )
    if ($topologyIndex -lt 1 -or $topologyLines[$topologyIndex - 1].Trim() -ne $daOn) {
        $failures.Add("${topologyFile}: Topology must carry an immediate DA=1 attribute.")
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "OPC UA publication audit passed: explicit PROGRAM/GVL variables only; implementation references are excluded."

# Read a TcUnit run out of the running PLC over ADS, and write it back out in
# TcUnit's own summary format.
#
# Why not read the log: TcUnit reports through ADSLOGSTR into the AMS router
# log, which TwinCAT renders in a live view and persists nowhere. Boot/
# LoggedEvents.db is the alarm store and stays empty. Every attempt to capture
# that stream from outside caught 0 rows from PlcTask, so the gate had a person
# in it - somebody read the numbers off the log window and typed them into an
# evidence file.
#
# TcUnit does not only print, though: it keeps the complete run in
# GVL_TcUnit.TestResults.TestSuiteResults (ST_TestSuiteResults), including
# per-suite and per-test detail. Reading that is deterministic, needs no capture
# window, and yields the failing test's name and message instead of a count.
#
# The output is deliberately TcUnit's printed format rather than JUnit directly,
# so tcunit_to_junit.py stays the single validator: it already enforces
# expected tests/suites/runner and rejects a log holding two summaries.
#
# Every read goes through ADSIGRP_SYM_VALBYNAME, so this creates no symbol
# handles at all. The symbol server's handle pool is finite - a run this size
# would otherwise burn one handle per field and hit "no more handles".

param(
    [Parameter(Mandatory = $true)] [string] $NetId,
    [Parameter(Mandatory = $true)] [string] $OutputLog,
    [int] $Port = 851,
    # Time allowed for the suite to reach AllTestSuitesFinished after PLC start.
    [int] $TimeoutSeconds = 120,
    [string] $AdsAssembly = 'C:\Program Files (x86)\Beckhoff\TwinCAT\3.1\Components\Base\v170\TwinCAT.Ads.dll'
)

$ErrorActionPreference = 'Stop'
Add-Type -Path $AdsAssembly

$ADSIGRP_SYM_VALBYNAME = 0xF004

function Read-SymBytes {
    param([object] $Client, [string] $Name, [int] $Size)
    $nameBytes = [System.Text.Encoding]::ASCII.GetBytes($Name + [char]0)
    $wr = New-Object TwinCAT.Ads.AdsStream (,$nameBytes)
    $rd = New-Object TwinCAT.Ads.AdsStream ($Size)
    [void]$Client.ReadWrite($ADSIGRP_SYM_VALBYNAME, 0, $rd, $wr)
    return $rd.ToArray()
}

function Read-SymBool  { param($C, $N) (Read-SymBytes $C $N 1)[0] -ne 0 }
function Read-SymUint  { param($C, $N) [BitConverter]::ToUInt16((Read-SymBytes $C $N 2), 0) }
function Read-SymLreal { param($C, $N) [BitConverter]::ToDouble((Read-SymBytes $C $N 8), 0) }
function Read-SymStr {
    param($C, $N)
    $b = Read-SymBytes $C $N 256
    $z = [Array]::IndexOf($b, [byte]0)
    if ($z -lt 0) { $z = $b.Length }
    [System.Text.Encoding]::ASCII.GetString($b, 0, $z)
}

function Get-TcUnitSymbolDiagnostics {
    # Only called when resolution fails. Separating "the app is not running"
    # from "it runs but publishes no symbols" from "symbols exist under another
    # name" is the whole point - they look identical from a failed read.
    param([object] $Client)
    $lines = [System.Collections.Generic.List[string]]::new()
    try { $lines.Add("  ADS state: $($Client.ReadState().AdsState)") }
    catch { $lines.Add("  ReadState failed: $($_.Exception.Message)") }
    try {
        $loader = $Client.CreateSymbolInfoLoader()
        $all = 0
        $hits = [System.Collections.Generic.List[string]]::new()
        foreach ($sym in $loader) {
            $all++
            # Name only. TcAdsSymbolInfo exposes both `Datatype` and `DataType`,
            # which PowerShell refuses to bind ("differs only in letter casing
            # ... must be CLS compliant"), and that exception aborted the whole
            # enumeration - hiding the very names this diagnostic exists to show.
            if ($sym.Name -match 'TcUnit') { $hits.Add("    $($sym.Name)") }
        }
        $lines.Add("  published top-level symbols: $all")
        if ($hits.Count -eq 0) { $lines.Add('    (none contain "TcUnit")') }
        else { foreach ($h in ($hits | Select-Object -First 20)) { $lines.Add($h) } }
    } catch {
        $lines.Add("  symbol enumeration failed: $($_.Exception.Message)")
    }
    return $lines
}

$client = New-Object TwinCAT.Ads.TcAdsClient
try {
    $client.Connect($NetId, $Port)

    # The library's globals may or may not be published under the namespace, so
    # resolve it rather than assuming. Retry for a while: the symbol table is
    # published as the download settles, so the first read after Start() can
    # legitimately arrive before it exists.
    $root = $null
    $resolveBy = [DateTime]::UtcNow.AddSeconds(20)
    while ($null -eq $root -and [DateTime]::UtcNow -lt $resolveBy) {
        # `AllTestSuitesFinished` and `TestResults` are members of FB_TcUnitRunner,
        # NOT of GVL_TcUnit itself - the GVL publishes only 14 symbols and neither
        # is among them. The runner instance is `GVL_TcUnit.TcUnitRunner`, so that
        # is the root everything hangs off. Verified against a live symbol upload.
        foreach ($candidate in @('GVL_TcUnit.TcUnitRunner', 'TcUnit.GVL_TcUnit.TcUnitRunner', 'GVL_TcUnit')) {
            try {
                [void](Read-SymBool $client "$candidate.AllTestSuitesFinished")
                $root = $candidate
                break
            } catch { }
        }
        if ($null -eq $root) { Start-Sleep -Milliseconds 500 }
    }
    if ($null -eq $root) {
        $diag = Get-TcUnitSymbolDiagnostics -Client $client
        throw ("Could not resolve the TcUnit GVL over ADS on ${NetId}:${Port}. " +
               "Published symbols matching 'TcUnit':`n" + ($diag -join "`n"))
    }
    Write-Host "  ADS: resolved TcUnit globals as '$root'"

    $results = "$root.TestResults.TestSuiteResults"

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while (-not (Read-SymBool $client "$root.AllTestSuitesFinished")) {
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "TcUnit did not report AllTestSuitesFinished within $TimeoutSeconds s"
        }
        Start-Sleep -Milliseconds 250
    }

    $suites     = Read-SymUint  $client "$results.NumberOfTestSuites"
    $cases      = Read-SymUint  $client "$results.NumberOfTestCases"
    $successful = Read-SymUint  $client "$results.NumberOfSuccessfulTestCases"
    $failed     = Read-SymUint  $client "$results.NumberOfFailedTestCases"
    $duration   = Read-SymLreal $client "$results.Duration"

    $out = [System.Collections.Generic.List[string]]::new()
    $out.Add('| TcUnit results read over ADS from ' + $NetId + ':' + $Port)
    $out.Add('| ======================================')

    for ($i = 1; $i -le $suites; $i++) {
        $b     = "$results.TestSuiteResults[$i]"
        $name  = Read-SymStr  $client "$b.Name"
        $n     = Read-SymUint $client "$b.NumberOfTests"
        $nFail = Read-SymUint $client "$b.NumberOfFailedTests"
        $out.Add("| Test suite name=$name")
        # tcunit_to_junit.py identifies the runner from the class path, so the
        # per-test line has to carry the fully qualified name.
        for ($t = 1; $t -le $n; $t++) {
            $tc        = "$b.TestCaseResults[$t]"
            $tName     = Read-SymStr  $client "$tc.TestName"
            $tClass    = Read-SymStr  $client "$tc.TestClassName"
            $tFailed   = Read-SymBool $client "$tc.TestIsFailed"
            $tSkipped  = Read-SymBool $client "$tc.TestIsSkipped"
            $status = 'PASS'
            if ($tFailed)  { $status = 'FAIL' }
            if ($tSkipped) { $status = 'SKIP' }
            $out.Add("| Test class name=$tClass.$tName status=$status")
            if ($tFailed) {
                $msg = Read-SymStr $client "$tc.FailureMessage"
                $out.Add("|   failure: $msg")
            }
        }
        if ($nFail -gt 0) { $out.Add("|   suite failed tests: $nFail") }
    }

    $out.Add('| ======================================')
    $out.Add("| Test suites: $suites")
    $out.Add("| Tests: $cases")
    $out.Add("| Successful tests: $successful")
    $out.Add("| Failed tests: $failed")
    $out.Add("| Duration: $duration")
    $out.Add('| ======================================')

    $parent = Split-Path -Parent $OutputLog
    if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    Set-Content -LiteralPath $OutputLog -Encoding utf8 -Value ($out -join [Environment]::NewLine)

    Write-Host "  ADS: $cases tests / $suites suites, $successful successful, $failed failed"
    Write-Host "  ADS: wrote $OutputLog"
}
finally {
    # Closing the port is the reliable bulk-release for anything the symbol
    # server allocated on our behalf.
    $client.Dispose()
}

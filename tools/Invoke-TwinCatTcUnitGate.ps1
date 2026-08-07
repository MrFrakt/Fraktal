<#
.SYNOPSIS
    Run ONE TcUnit gate on an isolated TwinCAT runtime and capture its log.

.DESCRIPTION
    `Specification/TWINCAT_XAE_WORKFLOW.md` §6 describes this sequence as an
    operator procedure, and §9 recorded that no script performed it. That was a
    statement about the 2026-08-02 acceptance run, not a limit of the interface:
    the PLC project object exposes `Login`, `Start`, `Stop` and `Logoff`
    alongside `CheckAllObjects`, so the whole gate is automatable.

    What does NOT change is why §6.1 put an operator in the loop, so the
    safeguards are preconditions here rather than reminders. This script REFUSES
    to activate anything unless:

      * `-ExpectedNetId` is supplied and matches the solution's saved target
        exactly. §6.1 is explicit that the target must be confirmed and never
        inferred, and activating the wrong runtime is the one mistake here with
        no cheap undo;
      * Autostart Boot Project is disabled on the PLC project. A TcUnit
        application must never become the boot application of the runtime it is
        downloaded to (§5.7);
      * `CheckAllObjects()` returns TRUE. A project that does not compile cannot
        be downloaded, and finding that out after activation wastes a restart.

    It never generates a boot project, and `Stop` + `Logoff` run in `finally` so
    an aborted run does not leave the PLC executing. Activating REWRITES the
    source `.tsproj` and silently drops `BootProjectAutostart="false"` (XAE omits
    it because false is the default), so the file is snapshotted and restored.

    The runtime is left in Run mode with the application stopped. Returning the
    target to Config mode is left to the caller: it is the one step that affects
    what the machine does next, and doing it silently would hide that.

    INCOMPLETE - DO NOT TREAT A CLEAN EXIT AS A PASSING GATE.

    Everything up to and including PLC Start runs, and the log capture works:
    the Error List yields the TwinCAT system rows around the restart. What has
    NOT been observed is any `'PlcTask'` output at all - across a 40 s poll, zero
    TcUnit rows appear, so the runner is not demonstrably executing and there is
    no summary to validate. Either the download or the start is not taking
    effect, or TcUnit's ADSLOGSTR output reaches a sink this does not read.

    Until that is resolved, a run of this script is evidence that the ENGINEERING
    sequence is automatable, and nothing whatsoever about whether the tests pass.
    Use the §6.2 operator procedure for an actual result.

.EXAMPLE
    powershell -File tools\Invoke-TwinCatTcUnitGate.ps1 `
        -Solution FraktalCore\PLC\TwinCAT\Examples\PressDemo\PressTests.slnx `
        -ExpectedNetId 192.168.1.6.1.1 -ExpectedRunner PRG_PressTestRunner `
        -ExpectedTests 8 -ExpectedSuites 2
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $Solution,
    # No default on purpose: the safeguard is that a human named the target.
    [Parameter(Mandatory = $true)] [string] $ExpectedNetId,
    [Parameter(Mandatory = $true)] [string] $ExpectedRunner,
    [Parameter(Mandatory = $true)] [int] $ExpectedTests,
    [Parameter(Mandatory = $true)] [int] $ExpectedSuites,
    [string] $Configuration = 'Debug',
    [string] $Platform = 'TwinCAT OS (x64)',
    [string] $DteProgId = 'VisualStudio.DTE.18.0',
    [int] $RunSeconds = 40,
    [string] $ArtifactDirectory = 'artifacts\tcunit'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# XAE is an out-of-process STA COM server and legitimately rejects calls while it
# is busy; retry those instead of turning them into false failures.
if (-not ('Fraktal.Tools.GateMessageFilter' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace Fraktal.Tools {
    [ComImport, Guid("00000016-0000-0000-C000-000000000046"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IGateMessageFilter {
        [PreserveSig] int HandleInComingCall(int callType, IntPtr taskCaller,
            int tickCount, IntPtr interfaceInfo);
        [PreserveSig] int RetryRejectedCall(IntPtr taskCallee, int tickCount, int rejectType);
        [PreserveSig] int MessagePending(IntPtr taskCallee, int tickCount, int pendingType);
    }
    public sealed class GateMessageFilter : IGateMessageFilter {
        [DllImport("Ole32.dll")]
        static extern int CoRegisterMessageFilter(IGateMessageFilter n, out IGateMessageFilter o);
        public static void Register() { IGateMessageFilter o; CoRegisterMessageFilter(new GateMessageFilter(), out o); }
        public static void Revoke() { IGateMessageFilter o; CoRegisterMessageFilter(null, out o); }
        int IGateMessageFilter.HandleInComingCall(int c, IntPtr t, int k, IntPtr i) { return 0; }
        int IGateMessageFilter.RetryRejectedCall(IntPtr t, int k, int r) { return (r == 2) ? 200 : -1; }
        int IGateMessageFilter.MessagePending(IntPtr t, int k, int p) { return 2; }
    }
}
'@
}

# The Error List is reachable only through EnvDTE80.DTE2, and that interop
# assembly has to be loaded explicitly - the base EnvDTE.DTE wrapper returns an
# empty or missing property that looks exactly like a tooling dead end.
$dteMajor = if ($DteProgId -match '\.(\d+)\.0$') { $Matches[1] } else { $null }
$programFilesRoot = [Environment]::GetFolderPath('ProgramFiles')
$dte2Candidates = [System.Collections.Generic.List[string]]::new()
if ($null -ne $dteMajor) {
    foreach ($edition in @('Community', 'Professional', 'Enterprise')) {
        $dte2Candidates.Add((Join-Path $programFilesRoot "Microsoft Visual Studio\$dteMajor\$edition\Common7\IDE\PublicAssemblies\envdte80.dll"))
    }
}
$dte2Candidates.Add((Join-Path $programFilesRoot 'Beckhoff\TcXaeShell\Common7\IDE\PublicAssemblies\envdte80.dll'))
$dte2AssemblyPath = $dte2Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($null -ne $dte2AssemblyPath) {
    try { Add-Type -Path $dte2AssemblyPath -ErrorAction Stop } catch {
        Write-Warning "envdte80.dll failed to load: $($_.Exception.Message)"
    }
} else {
    Write-Warning 'envdte80.dll not found; the Error List cannot be captured'
}

function Get-PlcOnlineInterface {
    <#
      `Login` / `Start` / `Stop` live on `ITcPlcOnline`, and two things about it
      mislead a reader:

        * it is not the tree item's default dispinterface, so `Get-Member` lists
          the methods (it unions everything in the type library) while a
          late-bound call gets DISP_E_UNKNOWNNAME. The member list says the
          method exists and the call says it does not;
        * the node that implements it is the IEC PROJECT
          (`TIPC^X^X Project`, ItemType 600) - the same one `CheckAllObjects`
          comes from - NOT the PLC project root that carries
          `BootProjectAutostart`, and not the instance node either.

      So query for the interface explicitly, exactly as the object-check gate
      does for `EnvDTE80.DTE2`.
    #>
    param([object] $TreeItem)

    $assembly = Get-ChildItem 'C:\Windows\assembly\GAC_MSIL\TCatSysManagerLib' -Recurse `
        -Filter 'TCatSysManagerLib.dll' -ErrorAction SilentlyContinue |
        Sort-Object FullName | Select-Object -Last 1
    if (-not $assembly) {
        throw 'TCatSysManagerLib interop not found in the GAC; cannot reach ITcPlcOnline'
    }
    $loaded = [System.Reflection.Assembly]::LoadFrom($assembly.FullName)
    $interface = $loaded.GetType('TCatSysManagerLib.ITcPlcOnline')
    $unknown = [System.Runtime.InteropServices.Marshal]::GetIUnknownForObject($TreeItem)
    $typed = $null
    try {
        $typed = [System.Runtime.InteropServices.Marshal]::GetTypedObjectForIUnknown(
            $unknown, $interface)
    } finally {
        [void][System.Runtime.InteropServices.Marshal]::Release($unknown)
    }
    # One object, explicitly. A PowerShell function returns EVERYTHING written to
    # the output stream, so a stray uncaptured expression turns the caller's
    # handle into an Object[] whose .Login() does not exist - which reads exactly
    # like the interface problem this function was written to solve.
    ,$typed | Select-Object -First 1
}

function Release-ComObject {
    param([object] $ComObject)
    if ($null -ne $ComObject -and [System.Runtime.InteropServices.Marshal]::IsComObject($ComObject)) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ComObject)
    }
}

function Get-CapturedLog {
    <#
      TcUnit reports through ADSLOGSTR, which XAE surfaces in the Error List and
      the output panes - NOT in the runtime's event database, which stays empty
      for these. Harvest both and let the caller's validator find the summary.
    #>
    param([object] $Dte)

    $lines = [System.Collections.Generic.List[string]]::new()
    $dte2 = $null
    try {
        $unknown = [System.Runtime.InteropServices.Marshal]::GetIUnknownForObject($Dte)
        try {
            $dte2 = [System.Runtime.InteropServices.Marshal]::GetTypedObjectForIUnknown(
                $unknown, [EnvDTE80.DTE2])
        } finally {
            [void][System.Runtime.InteropServices.Marshal]::Release($unknown)
        }
        $toolWindows = [EnvDTE80.DTE2].GetProperty('ToolWindows').GetValue($dte2, $null)
        $errorList = [EnvDTE80.ToolWindows].GetProperty('ErrorList').GetValue($toolWindows, $null)
        $errorItems = [EnvDTE80.ErrorList].GetProperty('ErrorItems').GetValue($errorList, $null)
        $count = [int][EnvDTE80.ErrorItems].GetProperty('Count').GetValue($errorItems, $null)
        $lines.Add("# ErrorList rows: $count")
        for ($index = 1; $index -le $count; $index++) {
            $item = [EnvDTE80.ErrorItems].GetMethod('Item').Invoke($errorItems, @($index))
            try {
                $lines.Add([string][EnvDTE80.ErrorItem].GetProperty('Description').GetValue($item, $null))
            } finally { Release-ComObject $item }
        }
        Release-ComObject $errorItems
        Release-ComObject $errorList
    } catch {
        $lines.Add("# ErrorList capture failed: $($_.Exception.Message)")
    }

    try {
        $outputWindow = $null
        foreach ($window in $Dte.Windows) {
            if ($window.Caption -eq 'Output' -or $window.Kind -eq 'Tool') {
                try { if ($window.Object -and $window.Object.OutputWindowPanes) { $outputWindow = $window.Object; break } }
                catch { }
            }
        }
        if ($null -eq $outputWindow) { throw 'no Output window with panes' }
        for ($paneIndex = 1; $paneIndex -le $outputWindow.OutputWindowPanes.Count; $paneIndex++) {
            $pane = $outputWindow.OutputWindowPanes.Item($paneIndex)
            try {
                $document = $pane.TextDocument
                $selection = $document.Selection
                $selection.SelectAll()
                $text = $selection.Text
                if ($text) {
                    $lines.Add("# ---- output pane: $($pane.Name) ----")
                    $lines.Add($text)
                }
            } catch {
                $lines.Add("# pane $paneIndex unreadable: $($_.Exception.Message)")
            } finally { Release-ComObject $pane }
        }
    } catch {
        $lines.Add("# Output pane capture failed: $($_.Exception.Message)")
    }
    return $lines -join [Environment]::NewLine
}

[Fraktal.Tools.GateMessageFilter]::Register()

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$solutionPath = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot $Solution)).Path
$solutionName = [System.IO.Path]::GetFileNameWithoutExtension($solutionPath)
$artifactRoot = Join-Path $repositoryRoot $ArtifactDirectory
if (-not (Test-Path $artifactRoot)) { New-Item -ItemType Directory -Path $artifactRoot | Out-Null }
$stamp = (Get-Date).ToString('yyyy-MM-dd_HHmmss')
$rawLogPath = Join-Path $artifactRoot "$solutionName-$stamp.raw.log"

$dte = $null
$plcRoot = $null
$online = $null
$tsProjectPath = $null
$tsProjectBytes = $null
$started = $false
$loggedIn = $false
try {
    Write-Host "Gate $solutionName -> $ExpectedNetId (expect $ExpectedRunner, $ExpectedTests tests / $ExpectedSuites suites)"
    $dte = New-Object -ComObject $DteProgId
    $dte.SuppressUI = $true
    $dte.MainWindow.Visible = $false
    $dte.Solution.Open($solutionPath)
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    while (-not $dte.Solution.IsOpen) {
        if ([DateTime]::UtcNow -ge $deadline) { throw "Timed out opening $solutionPath" }
        Start-Sleep -Milliseconds 200
    }
    Start-Sleep -Seconds 2

    $solutionBuild = $dte.Solution.SolutionBuild
    $solutionConfiguration = $null
    for ($i = 1; $i -le $solutionBuild.SolutionConfigurations.Count; $i++) {
        $candidate = $solutionBuild.SolutionConfigurations.Item($i)
        $context = $candidate.SolutionContexts.Item(1)
        if ($candidate.Name -eq $Configuration -and $context.PlatformName -eq $Platform) {
            $solutionConfiguration = $candidate
            Release-ComObject $context
            break
        }
        Release-ComObject $context; Release-ComObject $candidate
    }
    if ($null -eq $solutionConfiguration) {
        throw "Solution does not expose $Configuration|$Platform"
    }
    $solutionConfiguration.Activate()

    $sysManager = $dte.Solution.Projects.Item(1).Object

    # ---- preconditions, all BEFORE anything is activated --------------------
    $netId = [string]$sysManager.GetTargetNetId()
    Write-Host "  target NetId: $netId"
    if ($netId -ne $ExpectedNetId) {
        throw "Target is $netId but -ExpectedNetId is $ExpectedNetId; refusing to activate"
    }

    $plcRoot = $sysManager.LookupTreeItem('TIPC').Child(1)
    if ([bool]$plcRoot.BootProjectAutostart) {
        throw "$($plcRoot.Name) has Autostart Boot Project enabled; a test application must never be a boot application"
    }
    Write-Host "  PLC project: $($plcRoot.Name) (autostart disabled)"

    $iecPath = "TIPC^$($plcRoot.Name)^$($plcRoot.Name) Project"
    $iecProject = $sysManager.LookupTreeItem($iecPath)
    if (-not $iecProject.CheckAllObjects()) {
        throw "$($plcRoot.Name) does not compile; a project that does not compile cannot be downloaded"
    }
    Release-ComObject $iecProject
    Write-Host '  compiles clean'

    # ---- activate, download, run --------------------------------------------
    # Activating REWRITES the .tsproj, and one of its edits is destructive: XAE
    # drops `BootProjectAutostart="false"` because false is the default. The
    # attribute is carried explicitly on purpose - it is the record that a test
    # application must never become a boot application, and the .tsproj attribute
    # alone did not take when it was first set, so losing it is not cosmetic.
    # Snapshot the bytes and put them back; the activation's real output is on
    # the target, not in the source tree.
    $tsProjectPath = [System.IO.Path]::ChangeExtension($solutionPath, '.tsproj')
        if (Test-Path -LiteralPath $tsProjectPath) {
        $tsProjectBytes = [System.IO.File]::ReadAllBytes($tsProjectPath)
    }

    Write-Host '  activating configuration'
    $sysManager.ActivateConfiguration()
    Write-Host '  restarting TwinCAT into Run'
    $sysManager.StartRestartTwinCAT()
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    while (-not $sysManager.IsTwinCATStarted()) {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Timed out waiting for Run mode' }
        Start-Sleep -Milliseconds 500
    }

    # Re-resolve after the restart: activating rebuilds the configuration tree,
    # and a pointer taken before it survives as a stale generic __ComObject.
    $iecProject = $sysManager.LookupTreeItem($iecPath)
    $online = Get-PlcOnlineInterface -TreeItem $iecProject
    Release-ComObject $iecProject

    # PLC_LOGIN_FLAGS_REGULAR (1) - a normal login that downloads when the
    # target has no matching application. Not FORCEDOWNLOAD: that would hide a
    # target mismatch by overwriting whatever was there.
    Write-Host '  PLC login (downloads the application)'
    $online.Login(1)
    $loggedIn = $true
    Start-Sleep -Seconds 10   # let the download settle before Start()
    Write-Host '  PLC start'
    $online.Start()
    $started = $true

    # Poll rather than sample once at the end. The Error List is a live view, and
    # a single read after the fact cannot tell "the tests never ran" apart from
    # "the rows were there and I looked at the wrong moment".
    Write-Host "  running, polling the log for $RunSeconds s"
    $seen = [System.Collections.Generic.List[string]]::new()
    $known = [System.Collections.Generic.HashSet[string]]::new()
    $until = [DateTime]::UtcNow.AddSeconds($RunSeconds)
    while ([DateTime]::UtcNow -lt $until) {
        foreach ($row in (Get-CapturedLog -Dte $dte) -split "`r?`n") {
            if ($row -and $known.Add($row)) { $seen.Add($row) }
        }
        Start-Sleep -Seconds 3
    }
    $captured = $seen -join [Environment]::NewLine
    Set-Content -LiteralPath $rawLogPath -Encoding utf8 -Value $captured
    $plcRows = @($seen | Where-Object { $_ -match "'PlcTask'" }).Count
    Write-Host "  captured $($seen.Count) distinct rows, $plcRows from PlcTask"
    Write-Host "  raw log: $rawLogPath"
    if ($captured -notmatch 'Test suites:\s*\d+') {
        Write-Warning 'No TcUnit summary in the captured text. The run may still have passed - harvest the TwinCAT log window manually before concluding anything.'
    }
}
finally {
    # Never leave the application executing, even on an abort.
    if ($null -ne $online) {
        if ($started) { try { $online.Stop() } catch { Write-Warning "Stop failed: $($_.Exception.Message)" } }
        if ($loggedIn) { try { $online.Logoff() } catch { Write-Warning "Logoff failed: $($_.Exception.Message)" } }
        Release-ComObject $online
    }
    Release-ComObject $plcRoot
    if ($null -ne $dte) {
        try { $dte.Solution.Close($false) } catch { }
        try { $dte.Quit() } catch { }
        Release-ComObject $dte
    }
    # After XAE has let go of the file, undo its rewrite of the source .tsproj.
    if ($null -ne $tsProjectBytes) {
        try {
            # Not LINQ SequenceEqual: PowerShell 5.1 cannot infer the
            # generic parameter and throws "cannot find an overload".
            $current = [System.IO.File]::ReadAllBytes($tsProjectPath)
            if ([System.Convert]::ToBase64String($current) -ne
                [System.Convert]::ToBase64String($tsProjectBytes)) {
                [System.IO.File]::WriteAllBytes($tsProjectPath, $tsProjectBytes)
                Write-Host '  restored the .tsproj that activation rewrote'
            }
        } catch { Write-Warning "Could not restore $tsProjectPath : $($_.Exception.Message)" }
    }
    [Fraktal.Tools.GateMessageFilter]::Revoke()
}

Write-Host ''
Write-Host "Validate with:"
Write-Host "  python tools\tcunit_to_junit.py `"$rawLogPath`" `"$($rawLogPath -replace '\.raw\.log$', '.junit.xml')`" ``"
Write-Host "    --gate-name $solutionName --expected-tests $ExpectedTests ``"
Write-Host "    --expected-suites $ExpectedSuites --expected-runner $ExpectedRunner"
Write-Host ''
Write-Host 'The target is left in Run mode with the application stopped. Returning it to Config is yours to do.'

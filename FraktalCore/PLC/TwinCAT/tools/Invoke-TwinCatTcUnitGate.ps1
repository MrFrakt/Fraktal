<#
.SYNOPSIS
    Run ONE TcUnit gate on an isolated TwinCAT runtime and capture its log.

.DESCRIPTION
    `Specification/Guides/TWINCAT_XAE_WORKFLOW.md` §6 describes this sequence as an
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

    Measured 2026-08-16. Everything up to activation is verified: target
    selection, the autostart assertion, a clean `CheckAllObjects()`, activation
    ("Build complete -- 0 errors : Ready for download", "activating
    configuration..."), the restart into Run, and an application instance that
    exists, is already the active one, and reports ADS port 851.

    `ITcPlcOnline.Login()` then does nothing at all. It returns immediately,
    writes NO text to any of the ten DTE output panes, and leaves `IsLoggedIn`
    false with `OnlineOperationState` 0 indefinitely. Tested and eliminated:
    every `PLC_LOGIN_FLAGS` combination including SILENT and FORCEDOWNLOAD; 90 s
    of polling in case the call is asynchronous; an alternative DTE ProgID; the
    "Unknown TMC file version" warning (it appears in successful MANUAL runs
    too, so it is benign); releasing the tree item before use; and selecting the
    active application instance (§6.2 step 4, which this script had been
    skipping - it was already correct).

    What remains is that PLC login requires answering the create/load prompt of
    §6.2 step 6, which a hidden `SuppressUI` DTE cannot answer - suppressing a
    prompt declines it. On that reading §9's "no hidden script logged in,
    downloaded, started, or stopped a PLC" records a CONSTRAINT, not merely a
    policy choice, and automating the runtime step needs a different mechanism
    (TcUnit-Runner drives it without DTE) rather than another flag.

    This gate now FAILS at that point rather than continuing: it asserts
    `IsLoggedIn` after login and `PLC_APPSTATE_RUN` after `Start()`, because both
    calls are void and succeed silently when they do nothing. Revisions before
    2026-08-16 asserted neither, and so reported clean exits - and produced
    evidence - for runs in which no test ever executed. That is the failure this
    header exists to prevent repeating.

    Use the §6.2 operator procedure for an actual result. Once the PLC is running
    by any route, `Read-TcUnitResults.ps1` reads the outcome over ADS with
    per-test detail, so nobody has to transcribe the log window.

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
    # Optional: point the solution at this runtime before the target assertion
    # runs. The .tsproj is snapshotted and restored, so it never persists.
    [string] $TargetNetId = '',
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

# Release-ComObject, the envdte80 interop load, and Get-DteDiagnosticsSnapshot
# are shared with Invoke-TwinCatBuild.ps1. This gate used to carry its own copy,
# and that copy never captured a single Output pane - see TcXaeDte.ps1.
. (Join-Path $PSScriptRoot 'TcXaeDte.ps1')
Initialize-Dte2Interop -DteProgId $DteProgId

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
    param(
        [object] $TreeItem,
        [string] $InterfaceName = 'TCatSysManagerLib.ITcPlcOnline'
    )

    $assembly = Get-ChildItem 'C:\Windows\assembly\GAC_MSIL\TCatSysManagerLib' -Recurse `
        -Filter 'TCatSysManagerLib.dll' -ErrorAction SilentlyContinue |
        Sort-Object FullName | Select-Object -Last 1
    if (-not $assembly) {
        throw "TCatSysManagerLib interop not found in the GAC; cannot reach $InterfaceName"
    }
    $loaded = [System.Reflection.Assembly]::LoadFrom($assembly.FullName)
    $interface = $loaded.GetType($InterfaceName)
    if ($null -eq $interface) { throw "$InterfaceName not present in the interop assembly" }
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

[Fraktal.Tools.GateMessageFilter]::Register()

# This script ships inside the binding it builds, so the repository root - which
# every solution path below is relative to - is four levels up, not one.
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
$solutionPath = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot $Solution)).Path
$solutionName = [System.IO.Path]::GetFileNameWithoutExtension($solutionPath)
$artifactRoot = Join-Path $repositoryRoot $ArtifactDirectory
if (-not (Test-Path $artifactRoot)) { New-Item -ItemType Directory -Path $artifactRoot | Out-Null }
$stamp = (Get-Date).ToString('yyyy-MM-dd_HHmmss')
$rawLogPath = Join-Path $artifactRoot "$solutionName-$stamp.raw.log"

# Snapshot the .tsproj BEFORE XAE is allowed to touch it. Merely OPENING the
# solution rewrites the file and activating rewrites it again, and one of those
# edits is destructive: XAE drops `BootProjectAutostart="false"` because false
# is the default. That attribute is carried explicitly on purpose - it is the
# record that a test application must never become a boot application, and the
# .tsproj attribute alone did not take when it was first set, so losing it is
# not cosmetic. Snapshotting after the open, as this did before, preserved XAE's
# normalisation rather than the committed bytes. Taking it here is also what
# makes -TargetNetId safe to apply. The activation's real output is on the
# target, never in the source tree.
$tsProjectPath = [System.IO.Path]::ChangeExtension($solutionPath, '.tsproj')
$tsProjectBytes = $null
if (Test-Path -LiteralPath $tsProjectPath) {
    $tsProjectBytes = [System.IO.File]::ReadAllBytes($tsProjectPath)
}

$dte = $null
$plcRoot = $null
$online = $null
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
    # Selecting the target is the caller's job when -TargetNetId is supplied:
    # CI's hook has to point this gate at an isolated runtime, and the only way
    # to retarget before was to hand-edit a tracked .tsproj. The assertion below
    # still runs, so a typo here is caught rather than activated.
    if ($TargetNetId -ne '') {
        $sysManager.SetTargetNetId($TargetNetId)
    }
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
    # Deliberately NOT released here. $online is a second RCW over the same COM
    # identity as $iecProject, so dropping the tree item's reference while the
    # online interface is still in use is a candidate reason Login() became a
    # silent no-op - it returns cleanly, prints nothing to the Output pane, and
    # leaves IsLoggedIn false. Released in the finally block with the rest.
    Write-Host ("  online interface: loggedIn=$($online.IsLoggedIn)" +
                " appState=$($online.OnlineApplicationState)" +
                " opState=$($online.OnlineOperationState)")

    # §6.2 step 4 of the workflow guide - "Select the test PLC as Active PLC
    # Project" - has had no equivalent here, and PLC -> Login acts on the ACTIVE
    # application instance. A login against no active instance is a no-op that
    # returns cleanly and writes nothing to the Output pane, which is exactly
    # what this gate has been doing. ITcPlcProjectInternal3 also reports the port
    # the application really uses, worth logging rather than assuming 851.
    $plcNodePath = (($iecPath -split '\^')[0..1] -join '^')
    $plcNode = $sysManager.LookupTreeItem($plcNodePath)
    $plcInternal = Get-PlcOnlineInterface -TreeItem $plcNode `
        -InterfaceName 'TCatSysManagerLib.ITcPlcProjectInternal3'
    # ITcPlcProjectInternal3 is IUnknown-only, so PowerShell cannot late-bind it
    # ("does not contain a method named ..."). Go through reflection on the
    # interface type, exactly as this file already does for the EnvDTE80 types.
    $tcatAssembly = Get-ChildItem 'C:\Windows\assembly\GAC_MSIL\TCatSysManagerLib' -Recurse `
        -Filter 'TCatSysManagerLib.dll' -ErrorAction SilentlyContinue |
        Sort-Object FullName | Select-Object -Last 1
    $iPlcInternal = [System.Reflection.Assembly]::LoadFrom($tcatAssembly.FullName).GetType(
        'TCatSysManagerLib.ITcPlcProjectInternal3')
    $invoke = {
        param([string] $Method, [object[]] $MethodArgs)
        $iPlcInternal.GetMethod($Method).Invoke($plcInternal, $MethodArgs)
    }

    $appName       = [string](& $invoke 'get_ApplicationName' $null)
    $adsPort       = (& $invoke 'get_AdsPort' $null)
    $instanceCount = [int](& $invoke 'GetApplicationInstanceCount' $null)
    $activeInstance = [string](& $invoke 'GetActiveApplicationInstance' $null)
    Write-Host ("  PLC app '$appName' adsPort=$adsPort" +
                " instances=$instanceCount active='$activeInstance'")
    if ([string]::IsNullOrWhiteSpace($activeInstance) -and $instanceCount -ge 1) {
        $firstInstance = [string](& $invoke 'GetApplicationInstanceName' @([uint32]0))
        Write-Host "  selecting active application instance '$firstInstance'"
        & $invoke 'SetActiveApplicationInstance' @($firstInstance)
        $activeInstance = [string](& $invoke 'GetActiveApplicationInstance' $null)
        Write-Host "  active application instance is now '$activeInstance'"
    }

    # PLC_LOGIN_FLAGS_REGULAR (1) | PLC_LOGIN_FLAGS_SILENT (256).
    #
    # SILENT is not optional here, and leaving it off is why this gate reported
    # success for weeks while testing nothing. A regular login asks before it
    # downloads a changed application; `$dte.SuppressUI = $true` suppresses the
    # question rather than answering it, so the login returns without error and
    # without an application. Start() then starts nothing, also without error,
    # and the run window polls a PLC that was never running - which is exactly
    # the "0 rows from PlcTask" signature every run produced.
    #
    # FORCEDOWNLOAD (4) is the automation equivalent of the manual step the
    # workflow guide prescribes: "PLC -> Login. When prompted to create/load the
    # application, answer Yes; this downloads the PLC application"
    # (Guides/TWINCAT_XAE_WORKFLOW.md §6.2). SILENT suppresses that prompt, and a
    # suppressed prompt is declined, not accepted - so SILENT alone logs in
    # against nothing. FORCEDOWNLOAD supplies the "Yes".
    #
    # The old objection to it - that it hides a target mismatch - is already
    # answered by the -ExpectedNetId assertion above, which refuses to activate
    # anything it did not name. §9 permits exactly this ("future automation may
    # use the official Automation Interface, but target identity and
    # destructive-state checks must remain explicit"); both checks are intact.
    #
    # Login is ASYNCHRONOUS. It returns as soon as the download is under way, so
    # IsLoggedIn read on the next line is still false and proves nothing - the
    # fixed `Start-Sleep 10` this replaces was covering exactly that, silently
    # and with no idea whether ten seconds was enough for the project at hand.
    # Poll the real property instead, and fail loudly if it never comes true.
    Write-Host '  PLC login (downloads the application)'
    $online.Login(1 -bor 4 -bor 256)
    $loggedIn = $true
    $loginBy = [DateTime]::UtcNow.AddSeconds(90)
    while (-not $online.IsLoggedIn) {
        if ([DateTime]::UtcNow -ge $loginBy) {
            # Dump XAE's own diagnostics before unwinding - the reason a silent
            # login refused is in the Output pane and nowhere else.
            try {
                Set-Content -LiteralPath $rawLogPath -Encoding utf8 -Value (Get-DteDiagnosticsSnapshot -Dte $dte)
            } catch { Write-Warning "diagnostic capture failed: $($_.Exception.Message)" }
            throw ("PLC login never completed: IsLoggedIn stayed false, " +
                   "operation state $($online.OnlineOperationState); " +
                   "XAE diagnostics written to $rawLogPath")
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host '  logged in (application downloaded)'
    Write-Host '  PLC start'
    $online.Start()
    $started = $true

    # Assert the application actually runs. Start() is void and throws nothing
    # when it starts nothing, so without this the gate cannot tell "the tests
    # passed" from "the tests never executed" - and it silently chose the former.
    $runBy = [DateTime]::UtcNow.AddSeconds(30)
    while ($online.OnlineApplicationState -ne 1) {   # PLC_APPSTATE_RUN
        if ([DateTime]::UtcNow -ge $runBy) {
            throw ("PLC did not reach RUN after Start(): application state " +
                   "$($online.OnlineApplicationState), operation state " +
                   "$($online.OnlineOperationState)")
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host '  PLC is RUNNING'

    # The result comes out of the PLC itself over ADS. TcUnit keeps the whole run
    # in GVL_TcUnit, so this waits on its own completion flag instead of a fixed
    # window, and reports which test failed rather than how many. The log poll
    # below is the fallback for a target whose symbols cannot be reached - it is
    # what this gate used to rely on, and it never once captured a summary.
    $adsOk = $false
    try {
        & (Join-Path $PSScriptRoot 'Read-TcUnitResults.ps1') `
            -NetId $netId -OutputLog $rawLogPath -TimeoutSeconds $RunSeconds
        $adsOk = $true
        Write-Host "  raw log: $rawLogPath"
    } catch {
        Write-Warning "ADS result read failed: $($_.Exception.Message)"
    }

    if (-not $adsOk) {
        # Poll rather than sample once at the end. The Error List is a live view, and
        # a single read after the fact cannot tell "the tests never ran" apart from
        # "the rows were there and I looked at the wrong moment".
        Write-Host "  running, polling the log for $RunSeconds s"
        $seen = [System.Collections.Generic.List[string]]::new()
        $known = [System.Collections.Generic.HashSet[string]]::new()
        $until = [DateTime]::UtcNow.AddSeconds($RunSeconds)
        while ([DateTime]::UtcNow -lt $until) {
            foreach ($row in (Get-DteDiagnosticsSnapshot -Dte $dte) -split "`r?`n") {
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
}
finally {
    # Never leave the application executing, even on an abort.
    if ($null -ne $online) {
        if ($started) { try { $online.Stop() } catch { Write-Warning "Stop failed: $($_.Exception.Message)" } }
        if ($loggedIn) { try { $online.Logoff() } catch { Write-Warning "Logoff failed: $($_.Exception.Message)" } }
        Release-ComObject $online
    }
    Release-ComObject $iecProject
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

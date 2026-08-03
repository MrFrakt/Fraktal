[CmdletBinding()]
param(
    [string[]] $Solution = @(
        'FraktalCore\PLC\TwinCAT\Tests\FraktalTests.slnx',
        'FraktalCore\PLC\TwinCAT\Examples\PressDemo\PressTests.slnx'
    ),
    [string] $Configuration = 'Debug',
    [string] $Platform = 'TwinCAT OS (x64)',
    [string] $DteProgId = 'VisualStudio.DTE.18.0',
    [string] $ArtifactDirectory = 'artifacts\twincat-build'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# XAE is an out-of-process STA COM server and legitimately rejects calls while
# PLC Control is loading a project. Register the standard OLE message filter so
# those transient RPC_E_CALL_REJECTED responses are retried instead of becoming
# false CI failures.
if (-not ('Fraktal.Tools.OleMessageFilter' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace Fraktal.Tools {
    [ComImport, Guid("00000016-0000-0000-C000-000000000046"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IOleMessageFilter {
        [PreserveSig] int HandleInComingCall(int callType, IntPtr taskCaller,
            int tickCount, IntPtr interfaceInfo);
        [PreserveSig] int RetryRejectedCall(IntPtr taskCallee, int tickCount,
            int rejectType);
        [PreserveSig] int MessagePending(IntPtr taskCallee, int tickCount,
            int pendingType);
    }

    public sealed class OleMessageFilter : IOleMessageFilter {
        [DllImport("Ole32.dll")]
        static extern int CoRegisterMessageFilter(IOleMessageFilter newFilter,
            out IOleMessageFilter oldFilter);

        public static void Register() {
            IOleMessageFilter oldFilter;
            CoRegisterMessageFilter(new OleMessageFilter(), out oldFilter);
        }

        public static void Revoke() {
            IOleMessageFilter oldFilter;
            CoRegisterMessageFilter(null, out oldFilter);
        }

        public int HandleInComingCall(int callType, IntPtr taskCaller,
            int tickCount, IntPtr interfaceInfo) { return 0; }

        public int RetryRejectedCall(IntPtr taskCallee, int tickCount,
            int rejectType) { return rejectType == 2 ? 100 : -1; }

        public int MessagePending(IntPtr taskCallee, int tickCount,
            int pendingType) { return 2; }
    }
}
'@
}

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$artifactRoot = if ([System.IO.Path]::IsPathRooted($ArtifactDirectory)) {
    [System.IO.Path]::GetFullPath($ArtifactDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $ArtifactDirectory))
}
[void](New-Item -ItemType Directory -Path $artifactRoot -Force)

function Release-ComObject {
    param([object] $Value)
    if ($null -ne $Value -and [System.Runtime.InteropServices.Marshal]::IsComObject($Value)) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($Value)
    }
}

$targetConfiguration = "$Configuration|$Platform"
$failedSolutions = [System.Collections.Generic.List[string]]::new()
[Fraktal.Tools.OleMessageFilter]::Register()

try {
foreach ($relativeSolution in $Solution) {
    $solutionPath = if ([System.IO.Path]::IsPathRooted($relativeSolution)) {
        (Resolve-Path -LiteralPath $relativeSolution).Path
    } else {
        (Resolve-Path -LiteralPath (Join-Path $repositoryRoot $relativeSolution)).Path
    }
    $solutionName = [System.IO.Path]::GetFileNameWithoutExtension($solutionPath)
    $logPath = Join-Path $artifactRoot "$solutionName-build.log"
    $dte = $null
    $solutionBuild = $null
    $solutionConfiguration = $null
    $systemManager = $null
    $plcRoot = $null
    $iecProject = $null
    $stage = 'starting XAE'

    try {
        Write-Host "Building $solutionPath [$targetConfiguration]"
        $dte = New-Object -ComObject $DteProgId
        $dte.SuppressUI = $true
        $dte.MainWindow.Visible = $false
        $stage = 'opening solution'
        $dte.Solution.Open($solutionPath)

        $deadline = [DateTime]::UtcNow.AddMinutes(2)
        while (-not $dte.Solution.IsOpen) {
            if ([DateTime]::UtcNow -ge $deadline) {
                throw "Timed out opening $solutionPath"
            }
            Start-Sleep -Milliseconds 200
        }
        Start-Sleep -Seconds 2

        $stage = 'selecting solution configuration'
        $solutionBuild = $dte.Solution.SolutionBuild
        for ($configurationIndex = 1; $configurationIndex -le $solutionBuild.SolutionConfigurations.Count; $configurationIndex++) {
            $candidate = $solutionBuild.SolutionConfigurations.Item($configurationIndex)
            $context = $candidate.SolutionContexts.Item(1)
            if ($candidate.Name -eq $Configuration -and $context.PlatformName -eq $Platform) {
                $solutionConfiguration = $candidate
                Release-ComObject $context
                break
            }
            Release-ComObject $context
            Release-ComObject $candidate
        }
        if ($null -eq $solutionConfiguration) {
            throw "Solution does not expose configuration $targetConfiguration"
        }
        $solutionConfiguration.Activate()
        $stage = 'locating nested IEC project'
        $systemManager = $dte.Solution.Projects.Item(1).Object
        $plcRoot = $systemManager.LookupTreeItem('TIPC').Child(1)
        $bootAutostart = [bool]$plcRoot.BootProjectAutostart
        if ($bootAutostart) {
            throw "Test project $($plcRoot.Name) has Autostart Boot Project enabled"
        }
        $iecPath = "TIPC^$($plcRoot.Name)^$($plcRoot.Name) Project"
        $iecProject = $systemManager.LookupTreeItem($iecPath)
        $stage = 'checking all PLC objects'
        $checkOk = $iecProject.CheckAllObjects()
        Set-Content -LiteralPath $logPath -Encoding utf8 -Value "Solution=$solutionPath`nConfiguration=$targetConfiguration`nIecProject=$iecPath`nBootProjectAutostart=$bootAutostart`nCheckAllObjects=$checkOk"

        if (-not $checkOk) {
            $failedSolutions.Add("$solutionName (CheckAllObjects returned FALSE; inspect $logPath)")
        } else {
            Write-Host "Checked $solutionName successfully; log: $logPath"
        }
    } catch {
        Set-Content -LiteralPath $logPath -Encoding utf8 -Value "Solution=$solutionPath`nConfiguration=$targetConfiguration`nStage=$stage`nError=$($_.Exception.Message)"
        $failedSolutions.Add("$solutionName [$stage] ($($_.Exception.Message))")
    } finally {
        try {
            if ($null -ne $dte -and $dte.Solution.IsOpen) {
                $dte.Solution.Close($false)
            }
        } catch {
        }
        try {
            if ($null -ne $dte) {
                $dte.Quit()
            }
        } catch {
        }
        Release-ComObject $solutionConfiguration
        Release-ComObject $solutionBuild
        Release-ComObject $iecProject
        Release-ComObject $plcRoot
        Release-ComObject $systemManager
        Release-ComObject $dte
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}
} finally {
    [Fraktal.Tools.OleMessageFilter]::Revoke()
}

if ($failedSolutions.Count -gt 0) {
    throw "TwinCAT build gate failed: $($failedSolutions -join '; ')"
}

Write-Host "TwinCAT PLC object-check gate passed for $($Solution.Count) isolated solution(s)."

[CmdletBinding()]
param(
    [string[]] $Solution = @(
        # Libraries first, in dependency order: they are the code the test
        # applications consume, and until this list included them a compile error
        # in a library could only surface as an unexplained failure downstream.
        'FraktalCore\PLC\TwinCAT\Framework\FraktalCore.slnx',
        'FraktalCore\PLC\TwinCAT\Framework\FraktalModules.slnx',
        # Then the bench application. It consumes the two installed libraries, so a
        # rename in Core surfaces here first; it was outside the gate only because
        # the autostart assertion above used to reject it.
        'FraktalCore\PLC\TwinCAT\Examples\PressDemo\PressDemo.slnx',
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

# This script ships inside the binding it builds, so the repository root - which
# every solution path below is relative to - is four levels up, not one.
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..\..')).Path
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

$dteMajor = if ($DteProgId -match '\.(\d+)\.0$') { $Matches[1] } else { $null }
$programFilesRoot = [Environment]::GetFolderPath('ProgramFiles')
$dte2AssemblyCandidates = [System.Collections.Generic.List[string]]::new()
if ($null -ne $dteMajor) {
    foreach ($edition in @('Community', 'Professional', 'Enterprise')) {
        $dte2AssemblyCandidates.Add((Join-Path $programFilesRoot "Microsoft Visual Studio\$dteMajor\$edition\Common7\IDE\PublicAssemblies\envdte80.dll"))
    }
}
$dte2AssemblyCandidates.Add((Join-Path $programFilesRoot 'Beckhoff\TcXaeShell\Common7\IDE\PublicAssemblies\envdte80.dll'))
$dte2AssemblyPath = $dte2AssemblyCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$dte2AssemblyLoadError = $null
if ($null -ne $dte2AssemblyPath) {
    try {
        Add-Type -Path $dte2AssemblyPath -ErrorAction Stop
    } catch {
        $dte2AssemblyLoadError = $_.Exception.Message
    }
} else {
    $dte2AssemblyLoadError = 'envdte80.dll was not found in the supported Visual Studio/TcXaeShell locations'
}

function Get-DteDiagnosticsSnapshot {
    param([object] $Dte)

    # CheckAllObjects itself returns only a Boolean. Beckhoff documents the
    # separate DTE2 Error List, and XAE also writes a compile transcript to the
    # Build output pane on the pinned host. Keep both as diagnostics; the Boolean
    # remains the authority for the all-object gate.
    $lines = [System.Collections.Generic.List[string]]::new()
    $dte2 = $null
    $toolWindows = $null
    try {
        if ($null -ne $dte2AssemblyLoadError) {
            throw $dte2AssemblyLoadError
        }
        $unknown = [System.Runtime.InteropServices.Marshal]::GetIUnknownForObject($Dte)
        try {
            $dte2 = [System.Runtime.InteropServices.Marshal]::GetTypedObjectForIUnknown(
                $unknown,
                [EnvDTE80.DTE2]
            )
        } finally {
            [void][System.Runtime.InteropServices.Marshal]::Release($unknown)
        }
        $toolWindows = [EnvDTE80.DTE2].GetProperty('ToolWindows').GetValue($dte2, $null)
        $lines.Add("Dte2Interop=$dte2AssemblyPath")
    } catch {
        $lines.Add("Dte2CaptureUnavailable=$($_.Exception.Message)")
        return $lines -join [Environment]::NewLine
    }

    $errorList = $null
    $errorItems = $null
    try {
        $errorList = [EnvDTE80.ToolWindows].GetProperty('ErrorList').GetValue($toolWindows, $null)
        $errorItems = [EnvDTE80.ErrorList].GetProperty('ErrorItems').GetValue($errorList, $null)
        $count = [int][EnvDTE80.ErrorItems].GetProperty('Count').GetValue($errorItems, $null)
        $lines.Add("DteErrorListCount=$count")
        for ($index = 1; $index -le $count; $index++) {
            $item = $null
            try {
                $item = [EnvDTE80.ErrorItems].GetMethod('Item').Invoke($errorItems, @($index))
                $description = [EnvDTE80.ErrorItem].GetProperty('Description').GetValue($item, $null)
                $fileName = [EnvDTE80.ErrorItem].GetProperty('FileName').GetValue($item, $null)
                $line = [EnvDTE80.ErrorItem].GetProperty('Line').GetValue($item, $null)
                $column = [EnvDTE80.ErrorItem].GetProperty('Column').GetValue($item, $null)
                $project = [EnvDTE80.ErrorItem].GetProperty('Project').GetValue($item, $null)
                $lines.Add("DteError[$index]=$description | Project=$project | File=$fileName | Line=$line | Column=$column")
            } finally {
                Release-ComObject $item
            }
        }
    } catch {
        $lines.Add("DteErrorListCaptureError=$($_.Exception.Message)")
    } finally {
        Release-ComObject $errorItems
        Release-ComObject $errorList
    }

    $outputWindow = $null
    $panes = $null
    try {
        $outputWindow = [EnvDTE80.ToolWindows].GetProperty('OutputWindow').GetValue($toolWindows, $null)
        $panes = $outputWindow.OutputWindowPanes
        $lines.Add("DteOutputPaneCount=$($panes.Count)")
        for ($index = 1; $index -le $panes.Count; $index++) {
            $pane = $null
            $document = $null
            $startPoint = $null
            $endPoint = $null
            $editPoint = $null
            try {
                $pane = $panes.Item($index)
                $lines.Add("--- DTE output pane: $($pane.Name) ---")
                $document = $pane.TextDocument
                $startPoint = $document.StartPoint
                $endPoint = $document.EndPoint
                $editPoint = $startPoint.CreateEditPoint()
                $paneText = [string]$editPoint.GetText($endPoint)
                if ([string]::IsNullOrWhiteSpace($paneText)) {
                    $lines.Add('[empty]')
                } else {
                    $lines.Add($paneText.TrimEnd())
                }
            } catch {
                $lines.Add("[capture failed: $($_.Exception.Message)]")
            } finally {
                Release-ComObject $editPoint
                Release-ComObject $endPoint
                Release-ComObject $startPoint
                Release-ComObject $document
                Release-ComObject $pane
            }
        }
    } catch {
        $lines.Add("DteOutputCaptureError=$($_.Exception.Message)")
    } finally {
        Release-ComObject $panes
        Release-ComObject $outputWindow
    }

    Release-ComObject $toolWindows
    return $lines -join [Environment]::NewLine
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
    # Merely OPENING a solution makes XAE rewrite its .tsproj, and one of its
    # normalisations is destructive: it drops `BootProjectAutostart="false"`
    # because false is the default. The attribute is carried deliberately - it
    # records that a test application must never become a boot application - so
    # a read-only compile check must not be what deletes it. Snapshot the bytes
    # and restore them; this gate produces its output in artifacts/, never in
    # the source tree.
    $tsProjectPath = [System.IO.Path]::ChangeExtension($solutionPath, '.tsproj')
    $tsProjectBytes = if (Test-Path -LiteralPath $tsProjectPath) {
        [System.IO.File]::ReadAllBytes($tsProjectPath)
    } else { $null }

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
        # Autostart is a TEST-project rule (AGENTS 5.7): a TcUnit application must
        # never be the boot application of the runtime it is downloaded to. It says
        # nothing about the other two kinds of project here, and asserting it on them
        # cost real coverage twice: a LIBRARY is never downloaded at all, and while
        # that was the only exemption the gate stopped before CheckAllObjects, so
        # neither library was compiled by CI (Core was red for 27 invisible errors);
        # the Press BENCH is a machine application that is *supposed* to auto-start,
        # so the same blanket rule kept it out of the gate entirely. Name the test
        # solutions explicitly instead of guessing from what is left over.
        $isTestSolution = $solutionName -in @('FraktalTests', 'PressTests')
        if ($bootAutostart -and $isTestSolution) {
            throw "Test project $($plcRoot.Name) has Autostart Boot Project enabled"
        }
        $iecPath = "TIPC^$($plcRoot.Name)^$($plcRoot.Name) Project"
        $iecProject = $systemManager.LookupTreeItem($iecPath)
        $stage = 'checking all PLC objects'
        $checkOk = $iecProject.CheckAllObjects()
        $diagnostics = Get-DteDiagnosticsSnapshot -Dte $dte
        Set-Content -LiteralPath $logPath -Encoding utf8 -Value "Solution=$solutionPath`nConfiguration=$targetConfiguration`nIecProject=$iecPath`nBootProjectAutostart=$bootAutostart`nCheckAllObjects=$checkOk`n$diagnostics"

        if (-not $checkOk) {
            $detailCaptured = $diagnostics -match '(?m)^DteErrorListCount=[1-9][0-9]*$' -or
                $diagnostics -match '(?m)^Compile complete -- [1-9][0-9]* errors'
            if ($detailCaptured) {
                $failedSolutions.Add("$solutionName (CheckAllObjects returned FALSE; detailed DTE2 Error List/Build output is in $logPath)")
            } else {
                $failedSolutions.Add("$solutionName (CheckAllObjects returned FALSE; no detailed DTE rows were captured in $logPath, so export TwinCAT's visible Error List)")
            }
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
        # XAE has let go of the file by now; undo its rewrite.
        if ($null -ne $tsProjectBytes) {
            try {
                # Not LINQ SequenceEqual: PowerShell 5.1 cannot infer the
                # generic parameter and throws "cannot find an overload".
                $current = [System.IO.File]::ReadAllBytes($tsProjectPath)
                if ([System.Convert]::ToBase64String($current) -ne
                    [System.Convert]::ToBase64String($tsProjectBytes)) {
                    [System.IO.File]::WriteAllBytes($tsProjectPath, $tsProjectBytes)
                }
            } catch {
                Write-Warning "Could not restore $tsProjectPath : $($_.Exception.Message)"
            }
        }
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

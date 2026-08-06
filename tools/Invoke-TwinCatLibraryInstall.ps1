<#
.SYNOPSIS
    Save and install Fraktal_Core, then Fraktal_Modules, into the local TwinCAT
    library repository.

.DESCRIPTION
    Specification/TWINCAT_XAE_WORKFLOW.md 4.1/4.2 describes this as an XAE GUI
    interaction ("Save as library and install") and notes that the Automation
    Interface exposes the equivalent ITcPlcIECProject.SaveAsLibrary(path,
    install). This is that automation. Its evidence boundary is exactly the GUI
    action's: it saves the compiled library and registers it in the LOCAL
    development repository. It is not a released or distributed package, and it
    does not prove any consumer was rebuilt against it - reload the consumer's
    placeholders and compile it separately (workflow 4.3).

    Order is not optional: Modules consumes Core through an installed library
    reference, so Core must be installed before Modules is compiled, or Modules
    is built against the previous Core. Each solution is opened in its own
    isolated hidden XAE instance for the same reason the object-check gate does
    it - loading library source beside a consumer makes PLC Control rewrite the
    shared object GUIDs.

    CheckAllObjects runs first for each library and a FALSE result aborts before
    anything is installed: publishing a library that does not compile replaces a
    good one in the repository with a broken one.

.EXAMPLE
    ./tools/Invoke-TwinCatLibraryInstall.ps1
    ./tools/Invoke-TwinCatLibraryInstall.ps1 -Library Fraktal_Core
#>
[CmdletBinding()]
param(
    # Dependency order. Overriding to a single name is supported for a re-install
    # of one library; overriding the ORDER is not, and is rejected below.
    [ValidateSet('Fraktal_Core', 'Fraktal_Modules')]
    [string[]] $Library = @('Fraktal_Core', 'Fraktal_Modules'),
    [string] $Configuration = 'Debug',
    [string] $Platform = 'TwinCAT OS (x64)',
    [string] $DteProgId = 'VisualStudio.DTE.18.0',
    # Where the .library artifact is written. The repository install is separate
    # and always happens (that is the `install` argument of SaveAsLibrary).
    [string] $OutputDirectory = 'FraktalCore\PLC\TwinCAT\Framework\Release'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

$solutionOf = @{
    'Fraktal_Core'    = 'FraktalCore\PLC\TwinCAT\Framework\FraktalCore.slnx'
    'Fraktal_Modules' = 'FraktalCore\PLC\TwinCAT\Framework\FraktalModules.slnx'
}
$dependencyOrder = @('Fraktal_Core', 'Fraktal_Modules')
$requested = $dependencyOrder | Where-Object { $Library -contains $_ }
if (($requested -join ',') -ne (($Library | Select-Object -Unique) -join ',')) {
    throw ("Libraries must be installed in dependency order: " +
           "$($dependencyOrder -join ' then '). Requested: $($Library -join ', ')")
}

# The local 4026 library repository. Only read, to report the installed version
# back - the install itself is done by XAE through SaveAsLibrary.
$repositoryPath = Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) `
    'Beckhoff\TwinCAT\PlcEngineering\Managed Libraries\fraktal-automation'

$outputPath = if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory
} else {
    Join-Path $repositoryRoot $OutputDirectory
}
[void](New-Item -ItemType Directory -Path $outputPath -Force)

# XAE is an out-of-process STA COM server and legitimately rejects calls while
# PLC Control is loading a project; retry those instead of failing (same filter
# the object-check gate registers).
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

function Release-ComObject {
    param([object] $Value)
    if ($null -ne $Value -and [System.Runtime.InteropServices.Marshal]::IsComObject($Value)) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($Value)
    }
}

[Fraktal.Tools.OleMessageFilter]::Register()
try {
    foreach ($name in $requested) {
        $solutionPath = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot $solutionOf[$name])).Path
        $libraryPath = Join-Path $outputPath "$name.library"
        $dte = $null
        $solutionBuild = $null
        $systemManager = $null
        $plcRoot = $null
        $iecProject = $null
        $stage = 'starting XAE'

        try {
            Write-Host "Installing $name from $solutionPath [$Configuration|$Platform]"
            $dte = New-Object -ComObject $DteProgId
            $dte.SuppressUI = $true
            $dte.MainWindow.Visible = $false
            $stage = 'opening solution'
            $dte.Solution.Open($solutionPath)

            $deadline = [DateTime]::UtcNow.AddMinutes(2)
            while (-not $dte.Solution.IsOpen) {
                if ([DateTime]::UtcNow -ge $deadline) { throw "Timed out opening $solutionPath" }
                Start-Sleep -Milliseconds 200
            }
            Start-Sleep -Seconds 2

            $stage = 'selecting solution configuration'
            $solutionBuild = $dte.Solution.SolutionBuild
            $selected = $null
            for ($index = 1; $index -le $solutionBuild.SolutionConfigurations.Count; $index++) {
                $candidate = $solutionBuild.SolutionConfigurations.Item($index)
                $context = $candidate.SolutionContexts.Item(1)
                if ($candidate.Name -eq $Configuration -and $context.PlatformName -eq $Platform) {
                    $selected = $candidate
                    Release-ComObject $context
                    break
                }
                Release-ComObject $context
                Release-ComObject $candidate
            }
            if ($null -eq $selected) { throw "Solution does not expose $Configuration|$Platform" }
            $selected.Activate()
            Release-ComObject $selected

            $stage = 'locating nested IEC project'
            $systemManager = $dte.Solution.Projects.Item(1).Object
            $plcRoot = $systemManager.LookupTreeItem('TIPC').Child(1)
            if ($plcRoot.Name -ne $name) {
                throw "Solution's nested PLC project is $($plcRoot.Name), expected $name"
            }
            $iecProject = $systemManager.LookupTreeItem("TIPC^$name^$name Project")

            # Never replace a good repository entry with a broken build.
            $stage = 'checking all PLC objects'
            if (-not $iecProject.CheckAllObjects()) {
                throw ("CheckAllObjects returned FALSE for $name; nothing was installed. " +
                       "Run tools/Invoke-TwinCatBuild.ps1 for the DTE2 error rows.")
            }

            $stage = 'saving and installing the library'
            # SaveAsLibrary refuses to overwrite ("already exist. Cannot
            # SaveAsLibrary!"), so clear the previous artifact first. These are
            # regenerated build outputs under a gitignored Release/ directory,
            # never a released package - the repository install below is what
            # consumers actually resolve against.
            if (Test-Path -LiteralPath $libraryPath) {
                Remove-Item -LiteralPath $libraryPath -Force
            }
            $iecProject.SaveAsLibrary($libraryPath, $true)
            Write-Host "  saved $libraryPath and installed it into the local repository"
        } finally {
            try { if ($null -ne $dte -and $dte.Solution.IsOpen) { $dte.Solution.Close($false) } } catch {}
            try { if ($null -ne $dte) { $dte.Quit() } } catch {}
            Release-ComObject $iecProject
            Release-ComObject $plcRoot
            Release-ComObject $systemManager
            Release-ComObject $solutionBuild
            Release-ComObject $dte
            [GC]::Collect()
            [GC]::WaitForPendingFinalizers()
            if ($stage -ne 'saving and installing the library') {
                Write-Host "  failed while $stage"
            }
        }

        # Report what the repository now holds, so a stale placeholder pin is
        # visible here rather than as "every Modules type is unknown" downstream.
        $installed = Join-Path $repositoryPath $name
        if (Test-Path -LiteralPath $installed) {
            # Stamp each version with its .library file, not the containing
            # directory: the directory keeps the mtime of the FIRST install, so
            # reporting it makes a fresh install look stale.
            $versions = Get-ChildItem -LiteralPath $installed -Directory |
                ForEach-Object {
                    $blob = Join-Path $_.FullName "$name.library"
                    $stamp = if (Test-Path -LiteralPath $blob) {
                        (Get-Item -LiteralPath $blob).LastWriteTime
                    } else {
                        $_.LastWriteTime
                    }
                    [pscustomobject]@{ Name = $_.Name; Stamp = $stamp }
                } |
                Sort-Object -Property Stamp -Descending |
                ForEach-Object { "$($_.Name) ($($_.Stamp.ToString('s')))" }
            Write-Host "  repository now holds ${name}: $($versions -join ', ')"
        } else {
            Write-Warning "  $name is not present under $repositoryPath"
        }
    }
} finally {
    [Fraktal.Tools.OleMessageFilter]::Revoke()
}

Write-Host ("Installed $($requested.Count) library/libraries. Reload placeholders and " +
            "compile every consumer before treating this as done (workflow 4.3).")

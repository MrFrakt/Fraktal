# Shared XAE/DTE2 diagnostic capture, dot-sourced by the TwinCAT gates.
#
# Why this file exists: Invoke-TwinCatBuild.ps1 and Invoke-TwinCatTcUnitGate.ps1
# each carried their own copy of this logic, and the copies diverged. The build
# gate followed the route the workflow guide documents (§5.2) and worked. The
# TcUnit gate had reimplemented the same job by walking $Dte.Windows probing
# .Caption and reading panes through Selection.SelectAll() - both of which hit
# exactly the late-binding trap §5.1 warns about, so its capture threw on the
# first window and fell into a catch on EVERY run. That gate therefore had no
# Output-pane diagnostics at all, and an activation that silently did nothing
# was indistinguishable from a capture limitation for weeks.
#
# One implementation, so §5.2 has one thing to be true about.
#
# Reference: Specification/Guides/TWINCAT_XAE_WORKFLOW.md §5.1-§5.2.

function Release-ComObject {
    param([object] $Value)
    if ($null -ne $Value -and [System.Runtime.InteropServices.Marshal]::IsComObject($Value)) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($Value)
    }
}

function Initialize-Dte2Interop {
    <#
      The Error List and Output panes are reachable only through EnvDTE80.DTE2,
      and that interop assembly must be loaded explicitly: a COM object created
      from VisualStudio.DTE.<n>.0 is commonly seen by PowerShell as the base
      EnvDTE.DTE, whose ToolWindows access returns an empty or missing property
      that looks exactly like a tooling dead end rather than an error (§5.1).

      Sets $script:Dte2AssemblyPath and $script:Dte2AssemblyLoadError for
      Get-DteDiagnosticsSnapshot; returns nothing.
    #>
    param([string] $DteProgId)

    $dteMajor = if ($DteProgId -match '\.(\d+)\.0$') { $Matches[1] } else { $null }
    $programFilesRoot = [Environment]::GetFolderPath('ProgramFiles')
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($null -ne $dteMajor) {
        foreach ($edition in @('Community', 'Professional', 'Enterprise')) {
            $candidates.Add((Join-Path $programFilesRoot "Microsoft Visual Studio\$dteMajor\$edition\Common7\IDE\PublicAssemblies\envdte80.dll"))
        }
    }
    $candidates.Add((Join-Path $programFilesRoot 'Beckhoff\TcXaeShell\Common7\IDE\PublicAssemblies\envdte80.dll'))

    $script:Dte2AssemblyPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $script:Dte2AssemblyLoadError = $null
    if ($null -ne $script:Dte2AssemblyPath) {
        try {
            Add-Type -Path $script:Dte2AssemblyPath -ErrorAction Stop
        } catch {
            $script:Dte2AssemblyLoadError = $_.Exception.Message
        }
    } else {
        $script:Dte2AssemblyLoadError =
            'envdte80.dll was not found in the supported Visual Studio/TcXaeShell locations'
    }
}

function Get-DteDiagnosticsSnapshot {
    <#
      Capture the DTE2 Error List and every readable Output pane.

      These are diagnostics, never the pass/fail authority: CheckAllObjects()
      returns only a Boolean, and zero captured rows must never override a FALSE
      (§5.1). For the TcUnit gate the same rule holds - the Output panes explain
      an activation, they do not grade a test run.
    #>
    param([object] $Dte)

    $lines = [System.Collections.Generic.List[string]]::new()
    $dte2 = $null
    $toolWindows = $null
    try {
        if ($null -ne $script:Dte2AssemblyLoadError) { throw $script:Dte2AssemblyLoadError }
        $unknown = [System.Runtime.InteropServices.Marshal]::GetIUnknownForObject($Dte)
        try {
            $dte2 = [System.Runtime.InteropServices.Marshal]::GetTypedObjectForIUnknown(
                $unknown, [EnvDTE80.DTE2])
        } finally {
            [void][System.Runtime.InteropServices.Marshal]::Release($unknown)
        }
        $toolWindows = [EnvDTE80.DTE2].GetProperty('ToolWindows').GetValue($dte2, $null)
        $lines.Add("Dte2Interop=$script:Dte2AssemblyPath")
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
        # ToolWindows.OutputWindow, then EditPoint.GetText over the pane's
        # TextDocument. Not $Dte.Windows + .Caption, and not Selection.SelectAll:
        # both throw "The property '...' cannot be found on this object" against
        # the late-bound __ComObjects this collection hands back.
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

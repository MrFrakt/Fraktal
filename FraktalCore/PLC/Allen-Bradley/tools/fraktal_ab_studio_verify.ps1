[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(31, 99)]
    [int]$Revision,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Project,

    [ValidateRange(10, 600)]
    [int]$TimeoutSeconds = 180,

    [ValidateRange(0, 100000)]
    [int]$ExpectedErrors = 0,

    [ValidateRange(0, 100000)]
    [int]$ExpectedWarnings = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$schema = 'fraktal.ab.studio-verify'
$schemaVersion = 1
$projectPath = [System.IO.Path]::GetFullPath($Project)
$repoRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot '..\..\..\..')
).TrimEnd('\')

if (-not (Test-Path -LiteralPath $projectPath -PathType Leaf)) {
    throw "Project does not exist: $projectPath"
}

if ([System.IO.Path]::GetExtension($projectPath) -ine '.ACD') {
    throw 'Studio Verify requires a disposable .ACD project.'
}

if ($projectPath.Equals($repoRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
    $projectPath.StartsWith(
        $repoRoot + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
    throw 'Refusing to open an ACD inside the repository. Use a disposable copy in %TEMP%.'
}

$existingStudio = Get-Process -Name LogixDesigner -ErrorAction SilentlyContinue
if ($existingStudio) {
    throw 'Close every existing Logix Designer process before running this isolated Verify probe.'
}

$studioRoot = 'C:\Program Files (x86)\Rockwell Software\Studio 5000\Logix Designer\ENU'
$studioPath = Join-Path $studioRoot "v$Revision\Bin\LogixDesigner.Exe"
if (-not (Test-Path -LiteralPath $studioPath -PathType Leaf)) {
    throw "Logix Designer v$Revision is not installed at the expected path."
}

Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Get-AutomationElementById {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement]$Root,

        [Parameter(Mandatory = $true)]
        [string]$AutomationId
    )

    $condition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
        $AutomationId
    )
    return $Root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $condition
    )
}

$inputHashBefore = (Get-FileHash -LiteralPath $projectPath -Algorithm SHA256).Hash
$studio = $null
$summary = $null
$actualErrors = $null
$actualWarnings = $null
$messageCountText = $null
$statusText = $null
$closedCleanly = $false

try {
    $studioArguments = ('"{0}"' -f $projectPath)
    $studio = Start-Process -FilePath $studioPath -ArgumentList $studioArguments -PassThru
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    do {
        Start-Sleep -Milliseconds 500
        $studio.Refresh()
        $loaded = $studio.MainWindowHandle -ne 0 -and
            $studio.MainWindowTitle -match '\.ACD\s+\['
    } until ($loaded -or (Get-Date) -ge $deadline)

    if (-not $loaded) {
        throw "Studio v$Revision did not finish opening the project before timeout."
    }

    $root = [System.Windows.Automation.AutomationElement]::FromHandle(
        $studio.MainWindowHandle
    )

    $verifyDeadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $attempt = 0
    do {
        $attempt++
        [Microsoft.VisualBasic.Interaction]::AppActivate($studio.Id)
        Start-Sleep -Milliseconds 750
        [System.Windows.Forms.SendKeys]::SendWait('%l')
        Start-Sleep -Milliseconds 600
        [System.Windows.Forms.SendKeys]::SendWait('v')
        Start-Sleep -Milliseconds 600
        [System.Windows.Forms.SendKeys]::SendWait('c')

        $attemptDeadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 500
            $summaryElement = Get-AutomationElementById -Root $root -AutomationId '33652'
            if ($null -ne $summaryElement) {
                $summary = $summaryElement.Current.Name
            }
        } until (
            ($summary -match 'Complete\s+-\s+(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\)') -or
            (Get-Date) -ge $attemptDeadline -or
            (Get-Date) -ge $verifyDeadline
        )
    } until (
        ($summary -match 'Complete\s+-\s+(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\)') -or
        $attempt -ge 3 -or
        (Get-Date) -ge $verifyDeadline
    )

    if ($summary -notmatch 'Complete\s+-\s+(\d+)\s+error\(s\),\s+(\d+)\s+warning\(s\)') {
        throw 'Studio Verify did not expose a complete Error List summary before timeout.'
    }

    $actualErrors = [int]$Matches[1]
    $actualWarnings = [int]$Matches[2]
    $messageElement = Get-AutomationElementById -Root $root -AutomationId '33650'
    if ($null -ne $messageElement) {
        $messageCountText = $messageElement.Current.Name
    }
    $statusElement = Get-AutomationElementById -Root $root -AutomationId '59393'
    if ($null -ne $statusElement) {
        $statusText = $statusElement.Current.Name
    }
}
finally {
    if ($null -ne $studio -and -not $studio.HasExited) {
        [void]$studio.CloseMainWindow()
        $closeDeadline = (Get-Date).AddSeconds(20)
        do {
            Start-Sleep -Milliseconds 250
            $studio.Refresh()
        } until ($studio.HasExited -or (Get-Date) -ge $closeDeadline)
        $closedCleanly = $studio.HasExited
    }
}

if (-not $closedCleanly) {
    throw 'Studio did not close cleanly; the launched process was not terminated forcibly.'
}

$inputHashAfter = (Get-FileHash -LiteralPath $projectPath -Algorithm SHA256).Hash
$inputUnchanged = $inputHashBefore -eq $inputHashAfter
$countsMatch = $actualErrors -eq $ExpectedErrors -and
    $actualWarnings -eq $ExpectedWarnings

$result = [ordered]@{
    Schema = $schema
    SchemaVersion = $schemaVersion
    StudioRevision = $Revision
    Project = [System.IO.Path]::GetFileName($projectPath)
    InputSha256 = $inputHashAfter
    InputUnchanged = $inputUnchanged
    Errors = $actualErrors
    Warnings = $actualWarnings
    ExpectedErrors = $ExpectedErrors
    ExpectedWarnings = $ExpectedWarnings
    CountsMatch = $countsMatch
    MessageCountText = $messageCountText
    StatusText = $statusText
    Summary = $summary
    ClosedCleanly = $closedCleanly
}

$result | ConvertTo-Json -Depth 3

if (-not $inputUnchanged -or -not $countsMatch) {
    exit 1
}

exit 0

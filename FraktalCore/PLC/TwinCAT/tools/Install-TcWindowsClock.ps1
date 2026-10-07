[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageDirectory,
    [string]$SampleFile = ''
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run elevated on the PLC target Windows host to install the observer task.'
}
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$defaults = Get-Content -LiteralPath (Join-Path $package 'clock.defaults.json') -Raw | ConvertFrom-Json
# Read the kernel version from the registry rather than an unmanifested process
# version API, which can report compatibility versions on newer Windows.
$kernel = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$kernelVersion = if ($null -ne $kernel.CurrentMajorVersionNumber) {
    [version]::new($kernel.CurrentMajorVersionNumber, $kernel.CurrentMinorVersionNumber)
} else { [version]$kernel.CurrentVersion }
if ($kernelVersion -lt [version]$defaults.minimumWindowsVersion) {
    throw "This observer build requires Windows $($defaults.minimumWindowsVersion) or later. Build with a toolchain supporting this target OS."
}
if (-not $SampleFile) { $SampleFile = $defaults.sampleFile }
$samplePath = [IO.Path]::GetFullPath($SampleFile)
if ($samplePath -notmatch '^[A-Za-z]:\\' -or $samplePath.Length -gt 255) {
    throw 'Use a target-local drive path that fits the PLC STRING(255).'
}
$installPath = Split-Path $samplePath -Parent
if (-not $installPath -or $installPath -eq [IO.Path]::GetPathRoot($samplePath)) {
    throw 'A dedicated observer directory is required.'
}
$null = New-Item -ItemType Directory -Path $installPath -Force
$ownedNames = @('FraktalWindowsClock.exe', 'observer-task.xml',
    (Split-Path $samplePath -Leaf), ((Split-Path $samplePath -Leaf) + '.partial'))
$foreignFiles = @(Get-ChildItem -LiteralPath $installPath -Force |
    Where-Object { $_.Name -notin $ownedNames })
if ($foreignFiles.Count) { throw 'Use a dedicated observer directory; unrelated files are present.' }
$existingFiles = @(Get-ChildItem -LiteralPath $installPath -Force)
if ((Get-Item -LiteralPath $installPath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'The observer directory must not be a reparse point.'
}
if (@($existingFiles | Where-Object {
    $_.PSIsContainer -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint)
}).Count) { throw 'The observer directory must contain only ordinary owned files.' }
# The producer runs as SYSTEM; ordinary users and the PLC only need to read.
$administrators = New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')
$directoryAcl = New-Object Security.AccessControl.DirectorySecurity
$directoryAcl.SetOwner($administrators)
$directoryAcl.SetAccessRuleProtection($true, $false)
foreach ($rule in @(@('S-1-5-18', 'FullControl'), @('S-1-5-32-544', 'FullControl'), @('S-1-5-32-545', 'ReadAndExecute'))) {
    $sid = New-Object Security.Principal.SecurityIdentifier($rule[0])
    $access = New-Object Security.AccessControl.FileSystemAccessRule($sid,
        [Security.AccessControl.FileSystemRights]$rule[1],
        [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
        [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow)
    $directoryAcl.AddAccessRule($access)
}
Set-Acl -LiteralPath $installPath -AclObject $directoryAcl
# Remove old explicit grants/ownership on previous package files as well.
foreach ($file in $existingFiles) {
    $fileAcl = New-Object Security.AccessControl.FileSecurity
    $fileAcl.SetOwner($administrators)
    $fileAcl.SetAccessRuleProtection($false, $false)
    Set-Acl -LiteralPath $file.FullName -AclObject $fileAcl
}
$executable = Join-Path $installPath 'FraktalWindowsClock.exe'
Copy-Item -LiteralPath (Join-Path $package 'FraktalWindowsClock.exe') -Destination $executable -Force
$commandXml = [Security.SecurityElement]::Escape($executable)
$argumentXml = [Security.SecurityElement]::Escape('"' + $samplePath + '"')
$taskFile = Join-Path $installPath 'observer-task.xml'
@"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><BootTrigger><Enabled>true</Enabled></BootTrigger></Triggers>
  <Principals><Principal id="System"><UserId>S-1-5-18</UserId><LogonType>ServiceAccount</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure></Settings>
  <Actions Context="System"><Exec><Command>$commandXml</Command><Arguments>$argumentXml</Arguments></Exec></Actions>
</Task>
"@ | Set-Content -LiteralPath $taskFile -Encoding Unicode
& schtasks.exe /Create /TN 'Fraktal Windows Clock Observer' /XML $taskFile /F
if ($LASTEXITCODE -ne 0) { throw 'Observer task registration failed.' }
& schtasks.exe /Run /TN 'Fraktal Windows Clock Observer'
if ($LASTEXITCODE -ne 0) { throw 'Observer task start failed.' }
Write-Output "Observer installed. PLC sample: $samplePath"
Write-Output 'Windows Time service peers and clock settings were not changed.'
Get-Service W32Time | Select-Object Name,Status

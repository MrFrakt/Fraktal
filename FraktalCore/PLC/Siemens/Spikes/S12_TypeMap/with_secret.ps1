param([ValidateSet('witnesses','clock','permissions','diagnostics','auth-diagnostics','token-controls','capabilities','plan','script')] [string] $Action,
      [Parameter(Mandatory=$true)] [string] $Output,
      [string] $Manifest = '', [double] $Minutes = 60,
      [switch] $TrustFirst, [string] $Certificate = '', [string] $PlanFile = '', [switch] $Download,
      [string] $Permissions = '', [string] $Work = '', [string] $ScriptFile = '')
$ErrorActionPreference = 'Stop'
$secretFile = Join-Path $env:LOCALAPPDATA 'Fraktal/TiaStations/FrkS12.web.secret'
$secureValue = ConvertTo-SecureString ([IO.File]::ReadAllText($secretFile).Trim())
$secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
try {
  $env:FRAKTAL_TIA_WEB_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
  if ($Action -eq 'plan') {
    if (-not $PlanFile) { throw 'PlanFile is required' }
    if (-not $Work) { $Work = Join-Path $env:LOCALAPPDATA 'Fraktal\TiaStations' }
    $probeArgs = @((Join-Path $PSScriptRoot 'run_plan.py'),$PlanFile,$Output,
      '--set',('work=' + $Work))
    if ($Download) { $probeArgs += '--download' }
    if ($Permissions) { $probeArgs += @('--set',('permissions=' + $Permissions)) }
  } elseif ($Action -eq 'script') {
    if (-not $ScriptFile) { throw 'ScriptFile is required' }
    $probeArgs = @($ScriptFile,$Output)
  } else {
    $probeArgs = @((Join-Path $PSScriptRoot 'probe.py'),$Action,$Output,'--minutes',"$Minutes")
    if ($Manifest) { $probeArgs += @('--manifest',$Manifest) }
    if ($TrustFirst) { $probeArgs += '--trust-first' }
    if ($Certificate) { $probeArgs += @('--certificate',$Certificate) }
  }
  & python @probeArgs
  $probeExit = $LASTEXITCODE
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
  Remove-Item Env:\FRAKTAL_TIA_WEB_PASSWORD -ErrorAction SilentlyContinue
}
exit $probeExit

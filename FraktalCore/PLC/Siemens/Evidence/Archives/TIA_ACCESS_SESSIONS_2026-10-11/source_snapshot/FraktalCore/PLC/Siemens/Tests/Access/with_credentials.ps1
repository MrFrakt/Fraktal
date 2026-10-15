param([ValidateSet('prepare','probe','hmi')] [string] $Action,
      [Parameter(Mandatory=$true)] [string] $Output,
      [string] $Frames='')
$ErrorActionPreference='Stop'
$accessFiles=@(
  @('FrkAccess.operator.secret','FRAKTAL_TIA_OPERATOR_PIN'),
  @('FrkAccess.admin.secret','FRAKTAL_TIA_ADMIN_PIN'),
  @('FrkS12.web.secret','FRAKTAL_TIA_WEB_PASSWORD'))
$accessPointers=@()
try {
  foreach ($accessFile in $accessFiles) {
    $accessPath=Join-Path $env:LOCALAPPDATA ('Fraktal\TiaStations\'+$accessFile[0])
    if (-not (Test-Path -LiteralPath $accessPath)) {
      if ($Action -ne 'prepare' -or $accessFile[1] -eq 'FRAKTAL_TIA_WEB_PASSWORD') { throw 'Required DPAPI credential missing' }
      $accessRandom=New-Object byte[] 18
      $accessRng=[Security.Cryptography.RandomNumberGenerator]::Create()
      try { $accessRng.GetBytes($accessRandom) } finally { $accessRng.Dispose() }
      $accessSecure=ConvertTo-SecureString ([Convert]::ToBase64String($accessRandom)) -AsPlainText -Force
      [Array]::Clear($accessRandom,0,$accessRandom.Length)
      [IO.File]::WriteAllText($accessPath,(ConvertFrom-SecureString $accessSecure))
    }
    $accessSecure=ConvertTo-SecureString ([IO.File]::ReadAllText($accessPath).Trim())
    $accessPointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($accessSecure)
    $accessPointers += $accessPointer
    [Environment]::SetEnvironmentVariable($accessFile[1],[Runtime.InteropServices.Marshal]::PtrToStringBSTR($accessPointer),'Process')
  }
  $env:FRAKTAL_TIA_SIM_INSTANCE='Fraktal'
  if ($Action -eq 'prepare') {
    if (-not $Frames) { throw 'Frames required' }
    & python (Join-Path $PSScriptRoot 'make_fixture.py') $Output $Frames
  } elseif ($Action -eq 'probe') {
    & python (Join-Path $PSScriptRoot 'probe_web.py') $Output
  } else {
    $env:FRAKTAL_TIA_MANIFEST_LIVE='1'
    $env:FRAKTAL_TIA_ACCESS_LIVE='1'
    $env:FRAKTAL_TIA_HMI_OUTPUT=$Output
    & C:\Users\Siemens\Documents\FlutterSdk\flutter\bin\flutter.bat test --run-skipped -t live --concurrency=1 test/live_tia_manifest_test.dart
  }
  $accessExit=$LASTEXITCODE
} finally {
  foreach ($accessPointer in $accessPointers) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($accessPointer) }
  foreach ($accessFile in $accessFiles) { [Environment]::SetEnvironmentVariable($accessFile[1],$null,'Process') }
}
exit $accessExit

param(
  [string]$PlcEndpoint = 'opc.tcp://127.0.0.1:4840',
  [int]$Port = 8080,
  [string]$WebRoot = '',
  [string[]]$AllowOrigin = @(),
  [string[]]$WriteRoot = @(),
  [ValidateSet('production', 'secure-anonymous', 'commissioning-anonymous', 'isolated-anonymous')]
  [string]$SecurityProfile = 'production',
  [string]$SecurityPolicy = 'http://opcfoundation.org/UA/SecurityPolicy#Basic256Sha256',
  [string]$ApplicationUri = "urn:fraktal:gateway:$env:COMPUTERNAME",
  [string]$ClientCertificate = "$env:ProgramData\Fraktal\Gateway\pki\own\certs\fraktal-gateway.der",
  [string]$ClientPrivateKey = "$env:ProgramData\Fraktal\Gateway\pki\own\private\fraktal-gateway.pem",
  [string]$TrustList = "$env:ProgramData\Fraktal\Gateway\pki\trusted\certs",
  [string]$RevocationList = '',
  [ValidateRange(1, 1440)]
  [int]$CommissioningTtlMinutes = 120,
  [switch]$AllowAllRootMailboxes
)

$gateway = Join-Path $PSScriptRoot 'fraktal_gateway.exe'
if (-not (Test-Path -LiteralPath $gateway)) {
  throw "fraktal_gateway.exe is not beside this script."
}

$gatewayArguments = @(
  '--plc-endpoint', $PlcEndpoint,
  '--port', $Port,
  '--security-profile', $SecurityProfile
)
if (-not $WebRoot) {
  $WebRoot = Join-Path $PSScriptRoot 'web'
}
if (Test-Path -LiteralPath (Join-Path $WebRoot 'index.html')) {
  $gatewayArguments += @('--web-root', $WebRoot)
}
if ($SecurityProfile -eq 'production' -or $SecurityProfile -eq 'secure-anonymous') {
  $gatewayArguments += @(
    '--security-policy', $SecurityPolicy,
    '--application-uri', $ApplicationUri,
    '--client-certificate', $ClientCertificate,
    '--client-private-key', $ClientPrivateKey,
    '--trust-list', $TrustList
  )
  if ($RevocationList) {
    $gatewayArguments += @('--revocation-list', $RevocationList)
  }
}
if ($SecurityProfile -eq 'commissioning-anonymous') {
  $gatewayArguments += @(
    '--commissioning-ttl-minutes', $CommissioningTtlMinutes
  )
}
foreach ($origin in $AllowOrigin) {
  $gatewayArguments += @('--allow-origin', $origin)
}
foreach ($root in $WriteRoot) {
  $gatewayArguments += @('--write-root', $root)
}
if ($AllowAllRootMailboxes) {
  $gatewayArguments += '--allow-all-root-mailboxes'
}

& $gateway @gatewayArguments
exit $LASTEXITCODE

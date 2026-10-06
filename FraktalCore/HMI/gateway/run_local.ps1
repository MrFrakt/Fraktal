# Dev-only: run the gateway straight from source against the LOCAL TwinCAT
# runtime — no install, no tray, no gateway.args. The native DLLs must sit beside
# this script (copy them once from build/gateway/windows-x64/, see below).
#
#   ads://127.0.0.1.1.1:851  -> local TwinCAT runtime (AMS loopback NetId)
#   opc.tcp://127.0.0.1:4840 -> if TF6100 is installed instead
#
# ADS ignores the OPC UA security profile, so no certs/credentials are needed.

param(
  # Local runtime endpoint. Use the loopback AmsNetId for a runtime on THIS PC.
  # If 127.0.0.1.1.1 doesn't resolve, swap in the PC's real AmsNetId from the
  # TwinCAT router (System -> AmsNetId), e.g. ads://192.168.1.6.1.1:851.
  [string]$PlcEndpoint = 'ads://127.0.0.1.1.1:851',
  [int]$Port = 8080,
  # Control root: the published Unit browse path. Without it the gateway is
  # read-only and every HMI command is refused.
  [string]$WriteRoot = 'PLC1/MAIN/PneumaticPress',
  # Serve the built Web HMI so a browser can hit http://127.0.0.1:8080/ too.
  [string]$WebRoot = ''
)

$ErrorActionPreference = 'Stop'

# The FFI resolver (ads_session_client.dart) checks the exe dir then the CWD.
# dart.exe lives in the SDK, not here, so the DLLs MUST be in the CWD = here.
foreach ($dll in 'fraktal_ads.dll', 'fraktal_opcua.dll') {
  $p = Join-Path $PSScriptRoot $dll
  if (-not (Test-Path -LiteralPath $p)) {
    Write-Host "Missing $p" -ForegroundColor Yellow
    Write-Host "Copy it from build/gateway/windows-x64/$dll (run 'dart run tool/build_gateway.dart' first)." -ForegroundColor Yellow
    exit 1
  }
}

if (-not $WebRoot) {
  $candidate = (Resolve-Path (Join-Path $PSScriptRoot '..\build\web') -ErrorAction SilentlyContinue)
  if ($candidate -and (Test-Path (Join-Path $candidate 'index.html'))) {
    $WebRoot = $candidate
  }
}

$args = @(
  'run', 'bin/fraktal_gateway.dart',
  '--plc-endpoint', $PlcEndpoint,
  '--port', $Port,
  '--write-root', $WriteRoot
)
if ($WebRoot) { $args += @('--web-root', $WebRoot) }

Write-Host "[run_local] dart $($args -join ' ')" -ForegroundColor Cyan
Write-Host "[run_local] Web HMI: http://127.0.0.1:$Port/  (WebSocket at :$Port/fraktal)" -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
  & dart @args
} finally {
  Pop-Location
}
exit $LASTEXITCODE

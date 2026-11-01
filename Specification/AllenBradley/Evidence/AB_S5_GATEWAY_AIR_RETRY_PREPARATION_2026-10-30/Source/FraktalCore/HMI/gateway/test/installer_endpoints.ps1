$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../deploy/windows/fraktal_instances.ps1')
$vectors = @(
  @('cip://127.0.0.1?slot=0&serial=601FC87B', $true),
  @('cip://localhost:44819?slot=255&serial=abcdef01', $true),
  @('cip://localhost?serial=601FC87B', $true),
  @('s7web://192.0.2.1', $true),
  @('ads://1.2.3.4.5.6:851', $true),
  @('opc.tcp://localhost:4840', $true),
  @('cip://localhost', $false),
  @('cip://localhost?serial=bad', $false),
  @('cip://localhost?serial=601FC87B&slot=-1', $false),
  @('cip://localhost?serial=601FC87B&slot=256', $false),
  @('cip://localhost?serial=601FC87B&slot=0&slot=1', $false),
  @('cip://localhost?serial=601FC87B&other=1', $false),
  @('cip://localhost?serial=601FC87B&Serial=12345678', $false),
  @('cip://user@localhost?serial=601FC87B', $false),
  @('cip://localhost/path?serial=601FC87B', $false),
  @('cip://localhost?serial=601FC87B#fragment', $false),
  @('cip://localhost:0?serial=601FC87B', $false)
)
foreach ($vector in $vectors) {
  $actual = Test-FraktalEndpoint $vector[0]
  if ($actual -ne $vector[1]) { throw "Endpoint validation differs: $($vector[0]), expected $($vector[1]), actual $actual" }
}
Write-Output "$($vectors.Count) installer endpoint cases passed."

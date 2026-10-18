[CmdletBinding()]
param([string]$OutputDirectory = '', [string]$CMake = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'Framework\Release\clock' }
if (-not $CMake) {
  $found = Get-Command cmake.exe -ErrorAction SilentlyContinue
  if ($found) { $CMake = $found.Source }
  else {
    $studio = Join-Path $env:ProgramFiles 'Microsoft Visual Studio'
    $candidates = @(Get-ChildItem -LiteralPath $studio -Directory | ForEach-Object {
      Get-ChildItem -LiteralPath $_.FullName -Directory | ForEach-Object {
        Join-Path $_.FullName 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
      }
    } | Where-Object { Test-Path -LiteralPath $_ })
    if (-not $candidates.Count) { throw 'Install the Visual Studio C++ toolchain and CMake.' }
    $CMake = $candidates[0]
  }
}
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
$sdkBins = @(Get-ChildItem -LiteralPath $sdkRoot -Directory | Where-Object {
  $_.Name -match '^10\.' -and (Test-Path -LiteralPath (Join-Path $_.FullName 'x64\midl.exe'))
} | Sort-Object Name -Descending)
if (-not $sdkBins.Count) { throw 'Install a Windows SDK with the MIDL compiler.' }
$sdkBin = Join-Path $sdkBins[0].FullName 'x64'
$env:PATH = "$sdkBin;$env:PATH"
$constants = Get-Content -LiteralPath (Join-Path $root 'Framework\Fraktal_Core\Params\PL_Fraktal.TcGVL') -Raw
$match = [regex]::Match($constants, "WINDOWS_CLOCK_SAMPLE_FILE\s*:\s*STRING\(255\)\s*:=\s*'([^']+)'")
if (-not $match.Success) { throw 'Clock sample default is missing from PL_Fraktal.' }
foreach ($architecture in @('x64', 'Win32')) {
  $platform = if ($architecture -eq 'Win32') { 'x86' } else { 'x64' }
  $build = Join-Path $OutputDirectory "build-$platform"
  & $CMake -S (Join-Path $PSScriptRoot 'windows_clock') -B $build -A $architecture
  if ($LASTEXITCODE -ne 0) { throw "Clock observer configuration failed: $platform" }
  & $CMake --build $build --config Release
  if ($LASTEXITCODE -ne 0) { throw "Clock observer build failed: $platform" }
  $destination = Join-Path $OutputDirectory "windows-$platform"
  $null = New-Item -ItemType Directory -Path $destination -Force
  Copy-Item -LiteralPath (Join-Path $build 'Release\FraktalWindowsClock.exe') -Destination $destination -Force
  $targetPlatform = Get-Content -LiteralPath (Join-Path $build 'clock.platform.json') -Raw | ConvertFrom-Json
  @{ sampleFile = $match.Groups[1].Value; schemaVersion = 1;
    minimumWindowsVersion = $targetPlatform.minimumWindowsVersion;
    compilerVersion = $targetPlatform.compilerVersion } | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $destination 'clock.defaults.json') -Encoding UTF8
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Install-TcWindowsClock.ps1') -Destination $destination -Force
  Get-FileHash -LiteralPath (Join-Path $destination 'FraktalWindowsClock.exe') -Algorithm SHA256
}

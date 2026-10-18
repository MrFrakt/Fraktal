<# Reproducible host gates, generation, optional native compile/test. #>
param(
    [Parameter(Mandatory=$true)] [string] $Output,
    [switch] $Native,
    [switch] $Bench
)
$ErrorActionPreference='Stop'
if ($Bench -and -not $Native) { throw '-Bench requires -Native' }
$gateArgs=@((Join-Path $PSScriptRoot 'fraktal_tia_gate.py'),'--output',$Output)
if ($Native) { $gateArgs+='--native' }
if ($Bench) { $gateArgs+='--bench' }
& python -B @gateArgs
exit $LASTEXITCODE

"""The one owner-approved Openness driver build every gate and bench runs.

TIA Portal's Openness whitelist holds one entry per file name, so exactly one
build of Fraktal.Tia.Cli.exe can run unattended; a rebuild needs the owner's
approval of its hash and an elevated `Enable-TiaOpenness.ps1 -WhitelistExe`.
2026-11-10: adds the PROFINET IO-system commands (io-system, add-module,
connect-io, system-constants); replaces candidate_structure_examples (ba24e6aa).
"""
from pathlib import Path

DRIVER = Path(__file__).resolve().parent/'TiaCli/bin/candidate_profinet/Fraktal.Tia.Cli.exe'
DRIVER_SHA256 = '6f9e1bf03a55d83a943811565498bb3e0c48e5270bfbe34704fe438dd68a45ec'

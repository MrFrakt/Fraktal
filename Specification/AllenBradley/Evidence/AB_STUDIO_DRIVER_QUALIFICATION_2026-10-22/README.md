# Studio driver qualification, 2026-10-22

Qualification of `FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_studio_driver.py`
— the hidden, allow-listed WM_COMMAND driver for Studio 5000 Logix Designer —
against the existing qualified tooling, on host `SoftIndVM` (Windows 11 Pro
10.0.26200), Studio v38.00.00 (`LogixDesigner.Exe` SHA-256
`FA02C3DA1ED3777B779A28CA7BF84AFB3BD7EFBFB0795AE170F7374815EEB217`,
`LogixACENU.dll` `B9384996C78012443F7C51A216D833D74F942437476AF3646F03155DB5FCDB88`,
both recorded in every run artifact). The driver implements the black-box
findings of the 2026-10-22 study (ReverseEngineerAgent
`notes/studio5000/README.md`, findings F1–F4): menu command ids read from
LogixACENU.dll, results via WM_GETTEXT, a hidden session on a disposable copy,
online command ids refused by name, no keystrokes, no focus, no SDK.

Every run opened a disposable copy in `%TEMP%\FraktalAbStudioDriver\` and
proved the caller's source hash unchanged afterwards; every Studio process
closed itself (no forced termination).

## Runs

| Artifact | What it shows |
|---|---|
| `Runs/verify_press89.json` | Verify Controller on `press89_echo38_rw.ACD` (pinned `FC9C…F97B`): 0 errors / 0 warnings, frame count buttons `0 Errors`/`0 Warnings` cross-check the Error List summary, status "Verify complete with no errors or warnings.", exit 0. |
| `Runs/capacity_driver_press89.json` | Driver Capacity capture (schema `fraktal.ab.studio-capacity-capture` v1). |
| `Runs/capacity_powershell_press89.json` | The qualified `Invoke-AbStudioCapacity.ps1` collector run side-by-side on the same pinned ACD. |
| `Runs/import_broken.json` | SDK-free L5X → ACD import (v38): dialog driven by control ids, absolute path set, `Complete - 0 error(s), 0 warning(s)`, ACD created. |
| `Runs/verify_broken_negative.json` | Negative Verify on the imported broken project: 1 error / 0 warnings, exit 1, count button cross-check consistent. Error pane format: `Error: Line 22, 'FRK_Broken_Reference_Tag': Referenced tag is undefined.` |
| `Runs/press89_broken_reference.L5X` | The negative-case input: the owner's `press89_echo38_rw.L5X` with the single first occurrence of `FRK_Press_AccessWork.HashDone := 0;` replaced by `... := FRK_Broken_Reference_Tag;` (undefined tag). SHA-256 `B0CFA0F543AB131B998C254C6576DB7A5D46EBF053B8A4A6BBEF18A18C4E1F7D`. |

## Capacity side-by-side result

Both captures pass the sealed reader `fraktal_ab_studio_capacity.normalize`
(Measured, VerifiedFit) and agree exactly with each other and with the sealed
S3A owner record method:

- Used Standard **531,432** Blocks
- Available **2,614,296** Blocks
- Total **3,145,728** Blocks
- Displayed usage **16 %**

The sealed reader, its replay fixture and its tests are unchanged; only the
collector that produces the capture is new. `fraktal_ab_studio_capacity.py`
defaults to the driver collector (`--collector driver`); the qualified
PowerShell collector remains available via `--collector powershell`.

## What changed in the tools

- **New** `fraktal_ab_studio_driver.py` (`verify` / `capacity` / `import`).
  Posts only command ids 32049 (Verify Controller) and 32023 (Controller
  Properties, cross-checked against the LogixACENU.dll menu resource and the
  per-revision qualified map), refuses every online command id by name, and
  refuses revisions whose ids were never read from a real menu resource
  (qualified: v37/v38 for verify and capacity, v38 for the import dialog).
  Adopt-and-close: every LogixDesigner pid that appears after the guaranteed
  empty baseline is closed before the run reports success, so helper
  processes cannot survive as hidden zombies (observed once during
  qualification; root-caused and covered).
- **New** `test_fraktal_ab_studio_driver.py` (pure logic, the post policy,
  revision guards, capture-shape compatibility with the sealed reader).
- `fraktal_ab_studio_capacity.py`: adds `--collector {driver,powershell}`;
  sealed normalize path untouched.
- `fraktal_ab_phase0_gate.py`: the verify stage uses the driver when the
  gate's revision is driver-qualified (v37/v38) and keeps
  `fraktal_ab_studio_verify.ps1` otherwise (bench v33, whose menu ids have
  not been dumped); `--verify-script` overrides.
- `fraktal_ab_studio_verify.ps1` and `Invoke-AbStudioCapacity.ps1` are
  unchanged and remain the qualified fallbacks.

## Limits

- v33 (1769-L24ER bench) menu ids were not available to dump; the driver
  refuses v33 rather than posting unverified ids. Qualifying v33 needs a
  Studio v33 install and a menu dump.
- The gate was not run end-to-end here (its import stage needs the licensed
  Logix Designer SDK probe, absent on this host); the verify stage dispatch
  and the driver itself are qualified separately above.
- Timing comparison (same host, same ACD): driver Verify session ≈ 40 s
  total, of which ≈ 35 s is Studio opening press89; the Verify command
  itself completes in ≈ 2 s. The SendKeys probe needs the same open time but
  additionally requires foreground focus and keystroke timing margins.

## Legal basis

Lawful use of a licensed program to determine its behaviour and achieve
interoperability with the owner's own toolchain: Directive 2009/24/EC
Art. 5(3) and Art. 6; see the workspace `AGENTS.md` framework. No protected
module was analysed, no licence check was touched, and no online command was
ever posted.

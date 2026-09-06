# Fraktal/AB S12 v38 Studio-only exploratory evidence

**Status:** **EXPLORATORY ONLY - NOT S12 ACCEPTANCE AND NOT A FROZEN BASELINE**

**Date:** 2026-08-28 through 2026-08-29

**Repository revision:**
`6989e09f7be17c218283bc47139baa8a98c85d75`

## 1. Purpose and acceptance boundary

This record captures useful offline Studio 5000 v38 evidence while the Logix
Designer SDK feature `LDSDK.EXE` is unavailable. The user explicitly deferred
formal S12 acceptance until a suitable licence is acquired.

This run does **not** satisfy the v38 S12 acceptance workflow because:

- the unchanged v33 Phase 0 regression gate was not run;
- no case was imported through the Logix Designer SDK;
- the SDK import result is therefore absent for every case; and
- an unchanged-ACD hash across each Verify operation was not measured.

Consequently, this record does not change
`AB_FROZEN_CONTRACTS_V1.json`, does not select a recommended v38 baseline, and
does not alter the accepted `1769-L24ER-QB1B` / v33 type map.

## 2. Offline target and toolchain

Studio created a disposable offline project for:

| Item | Observed value |
|---|---|
| Controller | `5069-L310ER` |
| Project revision | major `38`, minor `11` |
| L5X software revision | `38.01` |
| Studio executable | `LogixDesigner.exe` `V38.01.00` |
| Repository generator source | `fraktal_ab_s12_type_probe.py` at the repository revision above |

The Studio product operated under its displayed seven-day grace-period notice.
That notice did not provide the separate `LDSDK.EXE` feature. No activation
file, clock, search path, entitlement, or service configuration was changed.

## 3. Method

Studio v38 created the seed project and exported its full-project L5X. An
out-of-repository PowerShell transform applied the repository generator's 14
fixed candidate definitions and exact use statements to that seed, producing
one `declare` and one `use` project per candidate: 28 cases total.

The transform asserted each substitution count, parsed every output as XML,
and checked the target and revision before emitting the manifest. Each L5X was
then imported manually through Studio's **Save Imported Project As** workflow
and checked with **Logic > Verify > Controller**. Each disposable Studio
session was closed before its final ACD hash was read.

All project, ACD, L5X, manifest, and result files remained under
`%LOCALAPPDATA%\Temp\FraktalS12v38`; none entered the repository.

## 4. Original 28-case matrix

`0/0` means zero Verify errors and zero Verify warnings. Studio import passed
for all 28 cases. Every declaration case verified `0/0`.

| Candidate | Logix declaration | Exact `use` statement | Verify `declare` | Verify `use` |
|---|---|---|---:|---:|
| 8-bit signed integer | `SINT` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | 0/0 |
| 16-bit signed integer | `INT` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | 0/0 |
| 32-bit signed integer | `DINT` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | 0/0 |
| 64-bit signed integer | `LINT` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | 0/0 |
| 64-bit integer, matched operands | `LINT` | `FRK_S12_Probe := FRK_S12_Probe + FRK_S12_Probe;` | 0/0 | 0/0 |
| 32-bit float | `REAL` | `FRK_S12_Probe := FRK_S12_Probe * 1.5;` | 0/0 | 0/0 |
| 64-bit float | `LREAL` | `FRK_S12_Probe := FRK_S12_Probe * 1.5;` | 0/0 | 0/0 |
| boolean | `BOOL` | `FRK_S12_Probe := NOT FRK_S12_Probe;` | 0/0 | 0/0 |
| 32-bit bit string | `DINT` | `FRK_S12_Probe := FRK_S12_Probe AND 16#0000_FFFF;` | 0/0 | 0/0 |
| native duration | `TIME` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | **1/0** |
| native 32-bit duration | `TIME32` | `FRK_S12_Probe := FRK_S12_Probe + 1;` | 0/0 | **1/0** |
| string | `STRING` | `FRK_S12_Probe.LEN := 0;` | 0/0 | 0/0 |
| ten-element array | `DINT[10]` | `FRK_S12_Probe[0] := FRK_S12_Probe[9] + 1;` | 0/0 | 0/0 |
| mixed public UDT | `FRK_T_S12Layout` | `FRK_S12_Probe.Count := FRK_S12_Probe.Count + 1;` | 0/0 | 0/0 |

Both duration failures produced the same exact diagnostic:

```text
Error: Line 2: Instruction has incompatible date/time data types.
Complete - 1 error(s), 0 warning(s)
```

This diagnostic rejects mixing `TIME` or `TIME32` with the integer literal
`1`; it does not show that duration arithmetic itself is unavailable.

## 5. Provisional observations

Relative to the accepted v33 / 5370 evidence, this Studio-only 5380 result is
materially different:

- `LINT` declaration, integer-literal addition, and matched-operand addition
  all verify `0/0`;
- `LREAL` declaration and multiplication verify `0/0`;
- `TIME` and `TIME32` declarations verify `0/0`; and
- the reused integer-literal duration operation fails by operand type.

Four supplemental, non-matrix cases separated native duration arithmetic from
the invalid integer operand. All four imported through Studio and Verify
completed `0 errors, 0 warnings`:

| Type | Exact supplemental statement | Verify |
|---|---|---:|
| `TIME` | `FRK_S12_Probe := FRK_S12_Probe + T#1ms;` | 0/0 |
| `TIME32` | `FRK_S12_Probe := FRK_S12_Probe + T32#1ms;` | 0/0 |
| `TIME` | `FRK_S12_Probe := FRK_S12_Probe + FRK_S12_Probe;` | 0/0 |
| `TIME32` | `FRK_S12_Probe := FRK_S12_Probe + FRK_S12_Probe;` | 0/0 |

The original duration failures therefore establish only that an untyped
integer literal is not a compatible operand. Both native duration types and
both tested addition forms are accepted by this offline v38 target.

These observations are candidates for a future second baseline, not contract
facts. Formal acceptance must reproduce them after the SDK licence is restored.

## 6. Artifact hashes

| Artifact | SHA-256 |
|---|---|
| Studio v38.01 executable | `73FBE784D03C3930BC3A91EC6105904900AA23D5E19DC34A8C60EF150DA58537` |
| repository S12 generator source | `E7BEFD88E68776BF30CA331F8C878518A856BF6F3AFCCE9C43D370F4ED1F59AB` |
| v38 seed ACD | `6680DFF12A90D117D5F4B056A02B21B355E4965B65C9163831B1CC0EB88CC594` |
| v38 seed L5X | `D5D69FAE51E44B34B03EC2E8C0094D3E5658BA9E26C38E79A689F4795F62A357` |
| 28-case manifest | `7AAD090F8ED438F7444A8148FEBBAD7FD70908924635AFD4161F14A2F59035F1` |
| normalized 28-case Studio result record | `F23ABF737BA95BD147DF8F9C0CC7C01BE0745C23C4D391711C2AD3CE4DF1F97A` |
| supplemental typed-`TIME` L5X | `604A540B478FB01BC506AA79D2D5D066E8CAD2B0208839A8C2F8531AFEB2C82B` |
| supplemental typed-`TIME` final ACD | `DDEE8844DBA1396D9AAF56D2FBA1CB3FF886380B65B8FAB17FED1B068D1146AE` |
| supplemental typed-`TIME32` L5X | `244F5FA680E44436BA10CD93418E86888A0FAFA9CA1D4C610BB0521D0F8E5270` |
| supplemental typed-`TIME32` final ACD | `2AA3D94C5F4015360B3380A8AD44BC38C26AAC8685C5E40E36A358DB37A16889` |
| supplemental matched-`TIME` L5X | `5C415C08E8DAE5B9C5F946595ADC3E9840C6A717627CD1E5740C0053CC1ADC86` |
| supplemental matched-`TIME` final ACD | `41BA2E0A1DC975DC9D90FF9EC4DBD063E5ED77DF561D195740C981447F208900` |
| supplemental matched-`TIME32` L5X | `97D9FADB82DD1CB5438723EF2ADE61EC774642060527AA43734F3248FE7C703A` |
| supplemental matched-`TIME32` final ACD | `C7D7A1DFCD73A3A1ADD0E365BC95B3A02F967485BBCC65656B17AB078CCC46FD` |
| normalized four-case duration supplement record | `CEBB5500161420E166B4CEB5C531EA74266533B6C63E1CCD412C9556EEBAE70D` |

The normalized result records contain all original and supplemental L5X hashes
and final ACD hashes. Final ACD hashes establish artifact identity after close,
not unchanged input across Verify.

## 7. Required acceptance rerun

After `LDSDK.EXE` is legitimately available:

1. rerun the unchanged v33 Phase 0 gate and require every stage green;
2. regenerate the v38 seed and all cases through the approved workflow;
3. SDK-import every case and record its warnings and errors;
4. Studio-Verify every imported case while proving the input ACD unchanged;
5. rerun all four typed-literal and matched-operand duration supplements; and
6. add a second versioned frozen baseline only if the complete evidence supports it.

The repository now exposes the exact target and 32 cases as the explicitly
non-accepted `v38-5380-exploratory` profile, removing the temporary mechanical
rewrite from that rerun:

```text
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s12_type_probe.py <v38-seed.L5X> <output-directory> --profile v38-5380-exploratory
```

The default remains `v33-5370`, so the existing Phase 0 gate and frozen v33
contract are not silently redirected to the exploratory target.

### 7.1 Unlicensed reproducibility follow-up

On 2026-09-01 the profile was run against the preserved Studio-exported v38
seed. The generator accepted Studio's exact inert `MainProgram` / `MainTask`
seed shape, replaced it structurally, and emitted 32 cases: the original 28 plus
the four duration discriminators. The repository canonical L5X comparator found
all 32 generated cases equivalent to the corresponding L5X inputs used in the
Studio run (`32` equivalent, `0` different). Generator SHA-256:
`DC842C74FC0E41296041F7C389F0408BEF1233266249D495B26E5DF77927FE36`.

The regenerated L5X files remained under
`%LOCALAPPDATA%\Temp\FraktalS12v38\profile-regeneration-20260901`. They were not
imported or verified again, so this result proves offline reproducibility only
and does not change the acceptance boundary in section 1.

## 8. Safety and end state

This was offline project engineering only. No physical controller was contacted.
Controller-changing categories - download, upload/online session, controller
mode, tag write, fault clear, clock, firmware, network configuration, safety,
and SD-card operations - were all **none**.

All disposable Studio processes were closed. No proprietary ACD, L5X, result
JSON, activation data, or screenshot was added to the repository.

The active host had no `192.168.100.x` IPv4 adapter. The read-only
`192.168.100.89:44818` TCP check returned false, and the FactoryTalk Linx 6.60
browse logged `Failed to browse Fraktal_AB\192.168.100.89, status is 2.` The
physical identity and browse controls therefore could not be reproduced on
this host; neither attempt established a controller session.

## 9. Repository validation

The scoped `git diff --check` for the three files changed by this run passed,
and `AB_FROZEN_CONTRACTS_V1.json` has no diff. The full worktree
`git diff --check` remains red on pre-existing, user-owned generated TwinCAT
project changes with trailing whitespace; those files were not edited here.

No `python`, `python3`, or `py` executable is available in this host's `PATH`.
The required AB unit, specification, frozen-contract, and cross-tree Python
gates could not be run and remain part of the licensed acceptance rerun.

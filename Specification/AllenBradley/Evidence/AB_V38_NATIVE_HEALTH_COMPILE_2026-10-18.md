# L81E/v38 native health and timing: compiler/read-back evidence

Recorded 2026-10-18 on SoftIndVM. This is **offline compiler and serialization
acceptance only**, following the
[native-feature overlap audit](../AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md).
It does not qualify a physical I/O module, a running time source, retention,
clock adjustment, Echo time scaling or production scan cost. No controller
download, online session, mode change or tag write was invoked.

The append-only [payload manifest](AB_V38_NATIVE_HEALTH_2026-10-18/manifest.json)
binds the generated inputs, exports, SDK logs, tool source snapshots, host and
managed assembly hashes, test log, failed explorations and the final case matrix.
ACD files and binaries remain outside the repository. These are generated
disposable fixtures and an empty SDK seed, not uploaded application source.

## Exact scope and toolchain

| Item | Value |
|---|---|
| Controller target | `1756-L81E`, major 38, seed minor 11 (`38.011` project target) |
| Seed | Existing empty SDK-exported `C:/work/echo38_5580_seed.L5X`; immutable copy/hash in payload |
| Installed Studio file version | **38.00.00**, measured this run; older workstation inventories are not substituted |
| Offline SDK C# client | **2.1.974** |
| Build host | .NET SDK **10.0.400**, target `net8.0/win-x86`; installed x86 runtime **8.0.20** |
| SDK compiler targets | `EchoController` and `PhysicalController`; neither is an online hardware operation |
| Base revision | `fa49adcc5`; uncommitted implementation bytes are captured in `Sources/` and hashed |
| Physical/runtime acceptance | **Not claimed** |

The new `--build-readback` offline-probe mode imports, compiles and exports in
one project open. It accepts only the two named offline compiler targets,
requires a new export, preserves rejected cases and hash-checks the input.
The Python gate judges actual SDK compiler events and read-back, not an exit
code alone. Both host and managed assembly hashes are recorded because the
apphost executable alone does not identify the C# implementation.

## Results

Every final import reports **0 warnings / 0 errors**. Every exported record
width, executable ST body and task binding matches the generated source.

| Case | Echo compiler | Physical compiler | Finding |
|---|---|---|---|
| `module_local` | PASS | PASS | `MODULE.Local.EntryStatus`, `FaultCode`, `Mode` use INT; `FaultInfo` uses DINT. `MODULE.ForceStatus` uses INT with an **empty instance**. |
| `task_intervals` | PASS | PASS | TASK scan/overlap/rate reads; `MaxInterval`/`MinInterval` into two-DINT buffers and native TIME; `StartTime` into a two-DINT buffer and LINT. |
| `clock_arithmetic` | PASS | PASS | CST `CurrentValue` into LINT and two DINTs; WallClockTime `CurrentValue` into LINT; full-width LINT subtraction and assignment. |
| `invalid_attribute` | Rejected as required | Rejected as required | `FRK_NotAnAttribute` produces `RxCMP_E_AUDIT_BADATTR`, proving that the compiler checks the GSV attribute rather than merely importing it. |
| `maximum_interval_spelling` | Rejected | Rejected | `MaximumInterval` produces `RxCMP_E_AUDIT_BADATTR`. Use the compiled **`MaxInterval`** spelling on this target. |

Thus the matrix contains **six successful positive builds**, **two deliberate
negative-control rejections**, and **two spelling-discriminator rejections**.
All ten imports and read-backs complete. A rejected discriminator is a finding,
not a claim that the alternate spelling is supported.

`Local` is the configured CPU in the seed. Its compilation cannot prove an
external module's presence, connection state or runtime GSV response. The global
ForceStatus read is an installed/enabled forcing indication, not permission for
Fraktal output forcing and not a per-channel force mask.

## Corrections established by the failed runs

The payload retains the initial failures rather than rewriting them:

1. The first native probe put several ST source lines in a single L5X `Line`
   record. Import was clean but the combined task build returned
   `RxSTX_E_INVALID_FUNC`. Serializing distinct line records produces the
   successful combined task build. The fix belongs in the shared S12 serializer;
   the native probe does not maintain a second ST serializer.
2. The first MODULE group supplied `Local` to every attribute. The compiler
   returned `RxSTX_E_OPERAND_NOT_ALLOWED`, **Argument must be empty**. Giving
   ForceStatus an empty instance makes the group pass both targets; the four
   per-module reads retain `Local`.
3. The initial result classifier recognized `RxSTX` but missed genuine `RxCMP`
   compiler diagnostics. It failed closed. It now recognizes both families;
   missing activation, service failure and an absent build event still cannot
   count as a successful negative control.

## Validation and preservation

- **1,701 AB tool tests PASS**, 240.166 seconds; log in the payload.
- **33 focused S12/native-probe/native-gate tests PASS**.
- All **60 existing S12 cases** (28 v33 and 32 exploratory v38) regenerate
  **byte-for-byte unchanged** against the base revision. The multiline serializer
  fix changes only the new multiline case; the compatibility result is archived.
- The C# host rebuild succeeds with **0 errors / 0 warnings**.
- Three real host guard checks refuse source-as-export, an existing export and
  an unsupported target with exit 2, unchanged file hashes and no SDK project
  open. `host_guards.json` records the results.
- AB specification and frozen-contract gates are clean. Strict consistency
  reports **0 errors / 0 warnings**; the 74 root gate tests pass.

Every generated probe tag is read-only, task output updates are disabled, and
the fixtures contain no mailbox, credentials, plant or physical output writes.
No production generator/declaration or released PLC type was changed. Existing
press state, commissioned settings and earlier runtime acceptance retain their
recorded scope.

## Next acceptance

N1/N4 now have an exact compiler/type baseline. Next, measure the selected time
source under startup, adjustment, wrap, missed scans and Echo time scaling on an
isolated target; validate configured external-module GSV responses on the named
hardware. TASK StartTime is wall-clock based; a successful CST subtraction is
not proof of monotonic behavior. Preserve the existing one-second aggregation
semantics when comparing native interval extrema. Only then select the native
provider for production. S3's external connection-state claim remains open.

Primary references checked during this work:
[TASK attributes](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-task-object.html),
[MODULE attributes](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-module-object.html).
The measured ForceStatus instance rule and MaxInterval spelling above take
precedence over an assumption drawn from a generic help table.

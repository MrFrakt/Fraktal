# S0 canonical type probe: corrected offline preparation — 2026-10-20

Append-only, non-normative evidence. **S0 is incomplete.** This continuation
corrects the probe before its first download and prepares a new guarded
session. There were no controller writes, mode changes, downloads or fault
clears. D6/D7, the runtime type evidence and the V2 approval gate remain open.

Source commit `a1163c7c7bec21988167bc971145b1366206e9ce`, with the uncommitted
canonical-publication work described by the handover. Owner changes to
`.gitignore`, `AGENTS.md`, the Siemens archive and the existing HMI CIP edit
were left alone. No commit or push occurred.

Payload and SHA-256 inventory:
[`AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20/manifest.json`](AB_S0_CANONICAL_PROBE_PREPARATION_2026-10-20/manifest.json).
No credential file is included. Native ACDs remain in the work folders and
are referenced by hash.

## Defect and correction

`fraktal_ab_s0_canonical_probe._from_lint` constructed a LINT from its high
word and a signed low DINT. When bit 31 of the low word was set, it subtracted
2^32 from the intended value. The microsecond stimulus therefore assembled
`1792409001156160` instead of `1792413296123456`, **before** the assignment
to native `DT`. This was a generator defect, distinct from the native time
conversion S0 is intended to measure. The nanosecond vector happened not to
exercise that low-word sign bit.

The emitter now constructs the value with two positive 16-bit low halves.
Expected measurements also include the raw LINT stimulus, so acquisition can
distinguish a bad stimulus from a native conversion finding. The new regression
executes the emitted integer arithmetic for the actual timestamp vectors,
low-word sign boundaries and both signed 64-bit extrema; it also checks literal
and intermediate ranges. It failed before the correction (five failures and
four missing raw-expectation errors) and passes afterwards in the full suite.

The original `C:/work/fraktal-ab-s0-20261019/` files are preserved. Its prepared
ACD still hashes to `F7E54A1ABF1F16C0740B684971B0ECE9C4FC1C17D266A8579AAD76B098F00D19`
and is superseded for deployment.

## Corrected preparation

Current work directory:
`C:/work/fraktal-ab-s0-20261020/readiness_20edac489b6c46e2b6229c76d400e9e7/`.
The handover's `$S0_WORK` points here. The selected probe families are unchanged:
BOOLs, numbers, strings, TIME, TIME32, LTIME and LINT-to-DT/LDT assignments.

| Artifact | SHA-256 |
| --- | --- |
| `corrected_combined/s0_combined.L5X` | `F3CB9D6CA3BCAC1A7912B1B6721F46F4EC30D2FB2054BE61EA64CE8669A1D1ED` |
| `s0_probe.ACD` | `0D0F05980B2EE5E2F2CF25656327755D66DE171263C86067869E1E3E35AFEA85` |
| Original genealogy rollback ACD | `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084` |

The new session and supporting scripts are copies in this new work directory,
with anchored path substitutions to the corrected source. Current authorization
is required explicitly; the copied session's historical authorization comment
was removed. Identity, logged-out/idle configuration preflight, backup and probe
hash guards remain. Genealogy restore still opens only a copy of the hash-pinned
original `C:/work/fraktal-ab-echo-20261019/genealogy_current.ACD`.

SDK client 2.1.974, x86 .NET 8: session build reports zero warnings/errors.
The SDK `prepare-probe` operation imports, compiles, saves/reopens the new ACD
and exports read-back. Its SDK log audit is clean and the full read-back is
equivalent. Preparation makes no controller connection.

## Validation

| Check | Exact result |
| --- | --- |
| AB tools, unittest discovery from the binding tools directory | `Ran 1898 tests in 256.728s` / `OK` |
| Root specification, frozen-contract and consistency test modules | `Ran 74 tests in 1.801s` / `OK` |
| `python tools/check_ab_spec.py` | `Fraktal/AB specification gate: clean.` |
| `python tools/check_ab_contracts.py` | `Fraktal/AB frozen-contract gate: clean.` |
| `python tools/check_consistency.py --strict` | `0 error(s), 0 warning(s) across inventory, localization, parity, readsurface` |
| v38 `EchoController` offline build | exit 0, clean import/build SDK audit, full read-back equivalent |
| v38 `PhysicalController` offline build | exit 0, clean import/build SDK audit, full read-back equivalent |
| Prepared ACD read-back | `Equivalent: true`, zero inventory/executable/initializer differences |

Two tooling failures are preserved:

- `corrected_compile/result.json` reports `ConformsToExpectations: false`.
  Both native builds succeeded and both embedded full read-back comparisons
  report `Equivalent: true`. The auxiliary `v38_native_gate.project_model`
  concatenates members across independent UDT declarations; Studio reordered
  those declarations, changing that flattened list without changing any owned
  member. `corrected_native_validation.json` records clean SDK audits and the
  full, owner-aware `fraktal_ab_readback.compare` result for each target. The
  auxiliary helper was not changed and its failed result was retained.
- After the AB suite exited 0, the outer log-display runner could not print
  U+FFFD through the host's cp1252 console (`UnicodeEncodeError`). The AB log
  remains intact. The remaining checks were then run with JSON-escaped display
  output; `after_fix_gate_summary.json` records their successful results and
  `gate_runner_failure.json` records the display failure.

## Live readiness and remaining work

At 21:55:50 and 22:04:09 America/Mexico_City on 2026-10-20, the FactoryTalk
Logix Echo Service was **Stopped** and no process listened on port 44818.
The read-only identity guard exited 1 with `Echo identity acquisition failed`.
`EchoControl.exe inspect` failed with gRPC `Unavailable` / server unavailable;
its full error output is retained. Consequently current controller identity,
mode, fault state, keyswitch, scanning and HMI login could not be established.
No new `preflight.json` was created.

The handover requires the owner to start the service from elevated PowerShell:
`Start-Service "FactoryTalk Logix Echo Service"`, then log out of the HMI.
Recheck listener ownership (`EmulateControlLogix5580`), exact identity
(`127.0.0.1`, slot 0, serial `601FC87B`, product 288, firmware 38.11), mode,
fault state and Unit MANUAL/idle with CurrentLevel 0 before recording preflight.

Backup/upload, probe deployment with Program/Run changes, measurement, genealogy
restoration and the document-restore/31-regression tag writes still need current
owner authorization. A fault clear, if needed, is a separate authorization.
Use this corrected session, not the original prepared probe. A second probe
download for the size/naming/access questions also remains a separate decision.

Runtime measurement, Capacity Estimate, scan-time measurement, genealogy
restore/31 checks and final live checks were not attempted because Echo was
unavailable and current controller-change authorization was pending. HMI
validation was not required: this continuation changes no HMI code. No D6/D7
decision or frozen V2 contract is inferred from the offline compiler results.

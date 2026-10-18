# L81E/v38 native task, clock and local-module runtime observations

2026-10-18; continuation of the [native compiler probes](AB_V38_NATIVE_HEALTH_COMPILE_2026-10-18.md)
and [SignalTower acceptance](AB_SIGNAL_TOWER_2026-10-18.md). This is measured
Echo evidence, not production time-source or physical-I/O qualification.

## Result

The instrumented tower fixture passes both v38 compiler targets, native
read-back, the 31 live tower/Part regression checks, configuration restoration,
and a 75-second read-only native timing observation. The native TASK and clock
attributes now have steady-state runtime evidence on the exact L81E Echo
target. Local MODULE attributes return data without faulting this controller.
Production health acquisition/calculations remain unchanged.

The owner explicitly answered **“Download and run the checks”** to the request
naming local Echo `601FC87B`, replacement download, saved configuration restore,
31 regression checks and a 75-second timing observation. The exact local
identity/process guard runs immediately before each mode change and download.
No fault clear, clock setting, Echo scaling change or hardware operation occurred.

## Exact target and artifacts

| Item | Value |
|---|---|
| Device | `127.0.0.1:44818`, slot 0, Emulate 5580 Controller |
| Identity | serial `601FC87B`, product code 288, firmware 38.011 (`38.11` in CIP) |
| Echo controller | `FraktalPhase0`, GUID `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd` |
| Declaration | `fraktal_ab_tower_demo`, 1756-L81E/v38, no external I/O modules |
| Manifest | major 5, `EA7BCE24FDA311EB`, config revision 15367118 |
| Generated observer L5X SHA-256 | `27C9781FD6FC740B09A13B3F81C7E34C9FF6DAC78A6A027E8100A12ABB923CFF` |
| Prepared ACD SHA-256 | `A9434AFDEE6991D537D418CE8CBE83333908BF0C580846D753706E7FCF8D9F7C` |
| Correlated post-download ACD SHA-256 | `1A671A38015165E847521D55EED8307437F6E234FA66AC30B8E449E0AA195BAC` |
| Previous program backup SHA-256 | `F3477BAA47B393F84D660AFC3FD694C1286C6B38A08762FE8CC575A2E5C6E843` |

ACDs remain outside the repository in
`C:/work/fraktal-ab-native-observer-20261018/`. The backup's executable bodies,
inventory and SFC graph match the preceding tower source. Its runtime values
are naturally different from authored defaults; they are not compared as
initial-value preservation. The input seed remains unchanged.

## Ownership and native reuse

`fraktal_ab_native_observer.py` generates the ordinary tower fixture from the
empty seed, then adds one read-only `FRK_T_NativeObserverV1` record and a final
JSR in the existing periodic task. All original executable bodies and authored
initial values are asserted preserved, apart from that final call. Neither the
manifest, mailbox, normal gateway projection nor production health provider
gains a field or feature. Output updates remain disabled.

The 216-byte record holds native GSV TASK Rate, LastScanTime, MaxScanTime,
OverlapCount, MaxInterval, MinInterval and StartTime; CST and WallClockTime
CurrentValue; synchronization/fault status; and Local MODULE EntryStatus,
FaultCode, FaultInfo, Mode and controller-wide ForceStatus. Native INT, LINT
and two-DINT buffers retain their actual widths. A bounded revision brackets
publication. The collector rejects partial/mixed revisions, wrong schema,
signature/task rate, failed acquisition, restart and saturated counters.
It never calls a controller write.

Source growth is 4,116 ST bytes, 62 terminators and 73 lines, with no RLL rung
or AOI added. The generic DINT/SINT size estimator excludes this native record;
its reported zero data delta does **not** include the measured 216-byte record.
These are source/wire measurements, not compiled-memory or capacity figures.

[Rockwell TASK documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-task-object.html)
distinguishes task interval extrema from execution time and identifies StartTime
as a wall-clock value. The
[CST reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/instruction-set/input-output-instructions/access-the-cst-object.html)
allows synchronization adjustments by ramp or immediate setting. Neither
native source is treated as a proven adjustment-independent elapsed clock.

## Validation

- Full AB suite: **1,803 passing tests**, 254.702 seconds. The wrapper's later
  UTF-8 log display failed on Windows-encoded help text; the test subprocess
  returned zero and the preserved log contains `Ran 1803 ... OK`.
- Final observer suite: **11 passing tests**, including the subsequently added
  CLI refusal case. Tests cover full-width clocks, signed low-word assembly,
  torn/odd publications, transport failures, backwards clocks, restart,
  transient observed faults, read-only collection and source preservation.
- Root suites: **74 passing tests**; AB specification, frozen-contract and
  strict cross-artifact consistency gates clean. Whitespace check clean.
- Studio 38.00 / SDK 2.1.974: EchoController and PhysicalController builds pass;
  prepared ACD reopens and builds. Import summaries: zero warnings/errors.
- Prepared, physical and post-download exports match **43 executable bodies,
  20,446 authored initial values and 21 SFC steps**. No executable/value/graph
  difference. PhysicalController is an offline compiler target only.
- **31/31 live checks pass**: ten tower/configuration/gating cases plus seven
  Part/recovery cases in each ST/SFC/LD rendition. Full disconnected lamp-test
  interval, adopted fault, handled decision and one-reset recovery still pass.
- Ordinary live-document restore completes; all five documents retain their
  values and match the reopened saved medium. Policy, session and stimuli restore.

## Native timing observation

`observation_01.json` records **7,500 scans** over **74.998686 host seconds**,
with zero collector writes, no observed controller fault and no negative clock
deltas. Two forward wall-clock minute transitions were observed.

| Measurement | Observed value |
|---|---|
| Native configured task period | 10,000 us |
| Native TASK lifetime interval extrema | 9,998..10,002 us |
| CST progression during observation | 75,000,000 us |
| WallClockTime / task StartTime progression | 74,999,999 us each |
| Mean CST progression per scan | 10,000 us |
| Simulated/host elapsed ratio | approximately 1.000018 at the existing setting |
| Sampled legacy period range | 9,998..10,002 us |
| Observer-lifetime CST sample interval range | 9,002..11,068 us |
| Local MODULE raw state | EntryStatus `16384` (`0x4000`), FaultCode/FaultInfo 0 |
| ModuleMode / ForceStatus | 1 / 0 |
| Synchronization quality | unsynchronized, reported explicitly |

Both extrema sets cover their respective lifetimes since initialization,
including the preceding regression checks; they are **not** the one-second
Fraktal measurement window. The wider CST range is consistent with reading a
clock at the end of a scan after variable execution work. This observation does
not isolate all causes of that range and does not prove a defective CST source.
Replacing task-period data with the spacing of late-scan reads would need to
account for that sampling position.

## Final state and remaining gates

Echo remains **Run, fault-free, MANUAL/idle**, all simulation inputs zero,
no active lamp test, all tower outputs off, no active Part, no ordering failure,
and logged out with the original access policy restored. All five configuration
documents match their reopened medium. The final read advances from scan 21,284
to 21,327; native maximum execution time is 1,177 us with zero overlap count.
Fixture counts are Good 9 / Scrap 4 / Cycle 13 after the download and test matrix;
this is not counter/download-retention evidence. The instrumented fixture remains
loaded and uses the existing tower declaration for its gateway.

N4 now has exact-target **steady-state native acquisition** evidence. Clock
adjustments, 32-bit/wider wrap, induced missed scans, changed Echo simulation
speed, paused/resumed execution and window/reset semantics remain open before
production replacement. N1 has only healthy **Local CPU** acquisition here;
external configured module inhibit/disconnect/fault/recovery needs physical
hardware. N2 native-alarm provider feasibility remains the next independent
native-overlap item. Device carriers, resource producers, genealogy and physical
commissioning remain separate port gaps.

The immutable [payload manifest](AB_NATIVE_TIMING_2026-10-18/manifest.json)
binds sources, generated/read-back projects, compiler logs, comparisons,
authorization scope and live JSON. Credentials and ACD backups are excluded.

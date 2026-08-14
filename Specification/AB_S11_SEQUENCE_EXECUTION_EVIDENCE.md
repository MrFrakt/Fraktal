# Fraktal/AB S11 — Sequence execution, ordering, and ST/SFC parity evidence

**Spikes:** S11 lifecycle/sequence call shape; S4 native-SFC round-trip coverage

**Result:** **S11 PASS — the named v33 target executed both generated sequence
forms from one graph declaration with identical step traces, identical scan
counts, the intended one-scan command/result latency, module-before-sequence
ordering, simultaneous-branch legs, and `SFR` reset/re-entry. S4's native-SFC
gap is closed; S4 remains OPEN on its other constructs.**

**Date:** 2026-08-13

## 1. Baseline and safety boundary

The target is the R1 controller `1769-L24ER-QB1B/A`, firmware `33.014`, serial
`7036B510`, at `192.168.100.89:44818`, reached for download through the proved
USB route `Backplane\16`. Studio 5000 Logix Designer v33 and the Logix Designer
SDK `2.00.00` / C# client `2.0.861` were used.

The user explicitly authorized this download and confirmed that the bench was
still isolated with all physical I/O disconnected. The fixture inhibits the
embedded discrete-I/O module, disables task output updating, and contains no
physical-I/O operand. The pre-download dialog was read and correlated before
the confirmation was issued: project `FraktalPhase0`, connected controller
`FraktalPhase0`, type `1769-L24ER-QB1B/A CompactLogix 5370`, path
`Backplane\16`, serial `7036B510`, `No Protection`, and the notice that Remote
Run would change to Remote Program. Studio reported `Download complete with no
errors or warnings.` and the controller was returned to Remote Run.

No firmware, fault-clear, clock, controller-network, safety, SD-card, or
physical-I/O operation occurred. The only controller-changing operations were
the authorized download, its mode change and return to Remote Run, and the
fixed vector's writes to two fixture inputs, both cleaned and verified.

### 1.1 A stale browse name is not controller identity

Studio's **Who Active** tree labelled the slot-16 node
`16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1` — the project the controller held
*before* the S1 work — even after an explicit Linx refresh. A direct symbolic
read proved the controller was actually running the S2 fixture at that moment,
and Studio's own pre-download dialog then reported the connected controller as
`FraktalPhase0`. The FactoryTalk Linx browse label is therefore a cached
discovery string and **shall not** be used as live project identity. The
pre-download dialog and direct CIP reads are the identity authority. This is a
new finding; it is recorded in the interface catalog.

## 2. One declaration, two generated execution forms

[`fraktal_ab_s11_fixture.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s11_fixture.py)
holds a single graph declaration and emits both AB §3.5 forms from it:

```text
N10  (entry)              -> T10: Result = 10
  simultaneous diverge
    leg 1: N30            leg 2: N40
  simultaneous converge   -> T50: Leg1Result = 30 AND Leg2Result = 40
N50  (terminal)
```

- **ST reference form.** `FRK_S11_SeqSt` is a sequence AOI carrying the Core
  §6.8 `CASE Seq.Step OF` skeleton, nested by the owner AOI `FRK_S11_Owner`,
  which calls the root module AOI `FRK_S11_Module` first and the sequence
  second.
- **Program-owned native SFC form.** `FRK_S11_SfcChain` is a generated SFC
  routine. The generated wrapper `FRK_S11_SfcRunner` issues `SFR` on the
  start, reset and Program→Run initialization edges and `JSR`s the chart only
  while the owner command is BUSY, after the same root module AOI has run
  unconditionally.

Both forms drive the same `FRK_T_S11Ctx` contract, publish steps through the
same `FRK_Seq_Step` service AOI, and consume intent through the same module
AOI. Every chart action is a single non-Boolean **N (NonStored)** action whose
ST body calls only the sequence service and writes generated intent — it never
calls a public module AOI and never `JSR`s.

Controller settings the fixture declares and the export preserved:
`SFCExecutionControl="CurrentActive"`, `SFCRestartPosition="InitialStep"`,
`SFCLastScan="DontScan"`. `DontScan` is deliberate: Rockwell's automatic
postscan reset would otherwise become a second latch authority beside Core.

The ST form carries one extra internal state (`20`) for the fork that the chart
holds structurally in its branch. It is not a Core step, records no trace
entry, and is excluded from the parity comparison for that reason.

## 3. Offline gate

| Stage | Result |
|---|---|
| generated full-project L5X | `59B2CE3BF775DE0107F6868EFDD0093154CA1D92F7310224C69C23F3B6E02A3E` |
| SDK import summary | `Warnings="0" Errors="0"`; log gate clean, `SaveAsAsync` succeeded |
| converted v33 ACD | `E9BD76C1B52FC3ED789AD29374E0971411B3DD03CEE3CEB8AD0CDB3700F845B8` |
| Studio v33 **Verify Controller** | `0 errors`, `0 warnings`, `Verify complete with no errors or warnings.`, input hash unchanged, closed cleanly |
| export pass 1 | `E0C9B0F836BFAEA42BA9D9BC695F00920F030E6E74C6F76BD0A7C91BF0A9D1B8` |
| export pass 2 | `B512BAC27354A095EE3830C34592F86DC84CE125F4547C53076BDBA2534D7F2F` |
| both canonical documents | `2A3F09BAF7336FCBE5D9F2530F3A4125EFF3A3578D8B475DFA4DED719BA5616D` |

**These hashes belong to the artifact that ran.** The fixture declared its SFC
step, action and transition tags without an explicit `ExternalAccess`, and
Studio wrote its default `Read/Write` on export. Nothing was lost and the
controller executed exactly that access, but the later S4 construct census
flagged the generated document as differing from its own export, so the
generator was corrected to state the attribute. A regeneration therefore
differs from the hashes above by exactly those ten tag attributes; the executed
behavior recorded below is unaffected.

A generated chart is therefore accepted by the real v33 semantic gate, not only
by SDK import. Note the contrast with the TwinCAT binding, where a
machine-emitted chart XML is prohibited because it fails with an `SFCStepType`
cascade: on Logix/L5X, generated SFC is a supported source form.

Studio also raised no error or warning for a terminal step with no outgoing
transition. That is what the binding needs: Core owns the terminal state and
the wrapper's `SFR` performs re-entry, so the chart requires no `Stop` element.

## 4. Chart fidelity (the S4 native-SFC claim)

The ordinary canonical comparator answers "did this document change", which
cannot compare a generated declaration against a Studio-derived export: Studio
legitimately renumbers element IDs. The new
[`fraktal_ab_sfc_roundtrip_compare.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_sfc_roundtrip_compare.py)
builds an ID-independent model — steps and their initial flag, actions with
qualifiers and bodies, transition condition text, branch type/flow, and the
link topology re-expressed over element names — plus the controller SFC
settings, and requires agreement. It fails closed if a chart's branches cannot
be named from resolved neighbours rather than reporting a comparison it did not
make.

| Comparison | Result |
|---|---|
| generated declaration vs pass-1 export | equivalent |
| pass-1 export vs pass-2 export | equivalent |

Inspection of the export confirms what survived unchanged: four steps with
their `NonStored` actions and ST bodies, both transition expressions, both
`Simultaneous` branches with one leg per Core branch, every directed link, the
`SFR` target `N10`, the `JSR` parameters, the three controller SFC settings,
and the `SFC_STEP` / `SFC_ACTION` / transition `BOOL` program tags — which
Studio materialised from the bare tag declarations the generator emitted.

This closes S4's native-SFC coverage. S4 stays OPEN for the constructs it still
does not cover: generated reset targets beyond the proven `SFR`, schedules, and
generated manifest/mailbox records.

## 5. Physical execution

[`fraktal_ab_s11_execute.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s11_execute.py)
required the exact serial, an explicit arm flag, and a full fixture fingerprint
before its first write. It writes only `FRK_S11_Command` and
`FRK_S11_ResetRequest` and accepts no caller-selected tag or value.

The fingerprint itself carries two of the claims. While the fixture was idle
the root module AOI's scan counter advanced for both forms — it is
unconditional — while the wrapper's `JSR` counter did not move, because the
chart is called only while BUSY. Neither private AOI instance tag was
browsable.

| Case | Measured, both forms |
|---|---|
| step trace | `[10, 1030, 2040, 50]` — the declared graph, legs encoded `branch*1000 + step` |
| scans from start edge to Done | **4**, equal for ST and SFC, and equal to the predicted value |
| intent→result latency | **1 scan**, with zero late consumptions |
| execution order within a scan | module AOI order `1`, sequence order `2`; never violated across either run |
| `SFR` per start/reset edge | exactly **1** |
| `JSR` calls per run | **5** — one per BUSY scan, none afterwards |
| trace overflow | `0` |
| in-controller parity flag | `1` |

The controller measured the scan counts itself; the probe did not infer them
from CIP polling. The two forms are therefore not merely functionally similar,
they are **scan-for-scan identical** on this target.

After `SFR`, both contexts cleared their traces and completion, the reset
counter advanced, and the second run produced an identical trace in an
identical number of scans with the run counter advanced. Both writable inputs
were restored to zero and verified. The 10 ms periodic task with a 500 ms
watchdog ran throughout without a fault.

`CurrentActive` behaved as AB §3.5 requires: newly activated steps do not run
in the scan that activates them, which is exactly what produces the documented
four-scan walk rather than an unbounded traversal in one scan.

## 6. Post-download binding

A post-download SDK export was compared against the pre-download export. The
strict canonical comparator correctly reported a difference, and
`fraktal_ab_target_binding_compare.py` accepted exactly and only the documented
target stamps:

| Field | Change |
|---|---|
| `Controller/@MinorRev` | `11 -> 14` |
| `Controller/Modules/Module[@Name='Local']/@Minor` | `11 -> 14` |
| `Controller/@ProjectSN` | `16#0000_0000 -> 16#7036_b510` |

Normalized both ways to
`2A3F09BAF7336FCBE5D9F2530F3A4125EFF3A3578D8B475DFA4DED719BA5616D` — the same
canonical hash as the verified pre-download project. No logic or structural
drift accompanied the download.

## 7. What this settles, and what it does not

Settled for the pinned v33 baseline:

- native SFC is a viable generated source form on Logix; the ST/LD reference
  form is not forced to carry sequences alone;
- the AB §3.5 runner order — root module AOI first, `SFR` on the declared
  edges, `JSR` only while BUSY — produces the intended one-scan command/result
  loop and it is exactly one scan, not "about one";
- reset and re-entry through `SFR` are deterministic and repeatable, with Core
  owning the latches and no reliance on Rockwell postscan;
- a simultaneous divergence runs one numbered `FRK_SequenceCtx` leg per Core
  branch without two writers sharing a result; and
- both generated forms are interchangeable at the observable Core contract.

Not settled by this evidence:

- **generated Ladder** as the third §6.8 form is untested here; only ST and
  native SFC were executed;
- **alternative (selection) branches, jumps, and private sub-chains** are not
  in this minimal graph;
- **error, abort, hold and mode-exit edges** are declared in AB §3.5 but only
  the start, reset and Program→Run edges were exercised;
- **prescan and AOI postscan routines** remain disabled (`ExecutePrescan`
  false); the binding's claim is that it does not depend on them, and that
  claim is proved only for the Program→Run initialization edge through `S:FS`;
- **production-sized charts** — the plan deliberately forbids starting there,
  and nothing here bounds step, action or branch counts; and
- **scan-time and watchdog margins** under a realistic module tree, which
  belong to S3/S5.

No production runtime implementation is authorized by this evidence. R2 is
advanced but not complete, and R3–R6 remain open.

## 8. Commands

```powershell
python fraktal_ab_s11_fixture.py <empty_v33.L5X> <fixture.L5X>
Fraktal.Ab.OfflineProbe.exe <fixture.L5X> --export <fixture.ACD>
python fraktal_ab_sdk_log_gate.py <sdk.log> --require SaveAsAsync --require-clean-import
powershell -NoProfile -ExecutionPolicy Bypass -File fraktal_ab_studio_verify.ps1 `
  -Revision 33 -Project <fixture.ACD> -ExpectedErrors 0 -ExpectedWarnings 0
Fraktal.Ab.OfflineProbe.exe <fixture.ACD> --export <pass1.L5X>
Fraktal.Ab.OfflineProbe.exe <pass1.L5X>  --export <roundtrip.ACD>
Fraktal.Ab.OfflineProbe.exe <roundtrip.ACD> --export <pass2.L5X>
python fraktal_ab_l5x_compare.py <pass1.L5X> <pass2.L5X>
python fraktal_ab_sfc_roundtrip_compare.py <fixture.L5X> <pass1.L5X>

# controller-changing; current explicit authorization only
python fraktal_ab_s11_execute.py 192.168.100.89 --expect-serial 7036B510 `
  --timeout 5 --settle 2 --execute-fixture

python fraktal_ab_target_binding_compare.py <pass1.L5X> <postdownload.L5X> `
  --serial 7036B510 --major-revision 33 --source-minor 11 --target-minor 14
```

The Studio download itself is not packaged as a repository tool and shall stay
that way: it was driven visibly, with the pre-download identity read and
correlated immediately before the confirmation.

## 9. Handoff state

The controller retains the memory-only S11 fixture in Remote Run with both
writable inputs at zero and PTP disabled/unsynchronized. The S2 fixture is gone
(`FRK_S2_ScanCount` now returns a path segment error). No Studio process
remains, the post-session CIP identity probe matched serial `7036B510` and
firmware `33.014`, and the FactoryTalk Linx browse of
`Fraktal_AB\192.168.100.89` succeeded.

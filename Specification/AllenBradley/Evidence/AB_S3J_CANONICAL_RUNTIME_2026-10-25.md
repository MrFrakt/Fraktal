# S3j canonical fieldbus - native fixture acceptance passes; genealogy restored

Client date: 2026-10-25, America/Mexico_City. The owner answered
**"Approve guarded S3j retry"** to
`call_ed20ad8878394150906050569c5b70de:0`, confirming the exact image and
bounded scope in the [retry preparation](AB_S3J_CANONICAL_RETRY_PREPARATION_2026-10-25.md).
**All guarded retry stages pass. S3j native acceptance passes on the local
sampled-word genealogy/Echo fixture. Genealogy is restored, all 31 baseline
regressions and final checks pass.** Authorization is consumed and the working
authorization is false. No commit or push; frozen V2 remains inactive.

The [earlier failed attempt](AB_S3J_CANONICAL_ATTEMPT_2026-10-25.md) is preserved.
Its root-reference declaration defect was corrected without changing PLC bytes,
the contract, comparison rules, proof budget or write vectors. The formerly
unequal adopted-fault capture passes live in this retry.

## Scope and exact image

Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0,
Remote keyswitch. The PLC owns V6.5 DataProducts and the fieldbus topology;
the generic reader discovers source Symbol, Template and logical type/view
metadata without a station declaration or Core-type dispatcher.

The disposable catalog has three nodes and twenty channels: Discrete_IO
parent, Discrete_IO.I with twelve channels and Discrete_IO.O with eight.
It adds **327 typed paths**. Identity/address spelling stays exact, logical
counts hide unused native slots, and the node split follows the approved
word-node correspondence. Its TypeId explicitly names sampled controller words.
No physical I/O module is configured and task output updates are disabled.

- Pristine downloaded ACD SHA-256:
  `285BF972C5FD781C315F670CFEEED8AC01D566791DB84E4B17125CC9B8CC3212`.
- Generated source SHA-256:
  `2F0B2CE73C2ECB69B1DD7F32BB1AE1D66550811A0EF49C1D65E9AE2C7A753EEA`.
- Native V6.5 ContentHash:
  `5CB700B26E0F3C48AE65FB06CB30E8BC62BDF536A0B710FBE898C9E8577C1231`.
- Fresh backup SHA-256:
  `AB80A62E4F1E9CB8898A121A1E7096F626FEF126D10D19559732B8841004ACA2`.
- Immutable genealogy original remains
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
  Rollback opens a hash-checked copy only. The deploy-attempt record binds the
  pristine candidate pin; SDK Save mutates its opened deployment copy, while
  the pristine review copy stays unchanged.

## Native results

| Gate | Result / output |
|---|---|
| Retry seal / current source bindings / helper and image pins | Pass; 449 preparation artifacts and 368 sources |
| No competing driver / fresh service, listener, identity, fault, keyswitch and dump guards | Pass |
| MANUAL normalization / preflight | Already MANUAL/idle; zero normalization writes, logged out and five documents equal |
| Fresh backup / SDK Save As audit / baseline access | Pass |
| File-bound download-gate replica | All comparisons pass |
| Program/download/Run / SDK audit / strict read-back / effective access | Pass |
| Candidate regressions | **41 / 41**: 31 inherited, two Access and eight configuration/provider cases |
| Candidate paired captures | **87 / 87**, including decision, held, fault, sequence, reset, Access and configuration surfaces |
| Simulated I/O cases | **9 / 9**, exactly 80 fixed DINT writes including restoration, confined to the eight FRK_Press_SimIo leaves |
| I/O restoration | Eight original source values restored exactly; **10 / 10** paired captures including restoration |
| Idle equivalence | **4,295 typed paths**, zero value/type differences |
| Generic acquisition | **4,295 values, seven modules**, expected V6.5 identity, not truncated |
| Independent replay | **98 / 98**: 87 candidate, ten I/O and idle; raw fragments, frame slices, legacy inputs, independent provider/word reference, values and types agree |
| Coherence proof | **2-29 of 100 polls**, within the unchanged five-second budget; four 4,000-byte reader sockets, one outstanding request each |
| Candidate TASK, twenty samples | LastScan **937 us median**, 936-995 us; cumulative max **8,466 us**; zero overlaps; **1,534 us margin** under 10,000 us |
| Genealogy rollback / SDK audit / access / exact guard | Pass |
| Baseline regressions | **31 / 31** |
| MANUAL cleanup / final checks / preflight equality | Pass: Run, no fault, scanning, MANUAL/idle, logged out, not restoring, policy restored, five saved/live documents equal |
| Baseline TASK, twenty samples | LastScan median **99 us**, cumulative max **1,167 us**, zero overlaps |
| Dumps before / after | None / none |
| Fault clears / clock changes / power operations / hard kills | **0 / 0 / 0 / 0** |
| Failed or repeated retry stages | **0**; all 21 candidate/rollback driver stages exit 0 |

The fixed word vectors cover operational, one channel fault, inhibited,
offline, input-only, output-only, unknown fault validity, signed words and
an ineffective unregistered-gate claim. Every snapshot equals the independent
legacy topology projection plus the approved word-node mapping and Core types.
The separate controller force owner remains closed; a source-record claim
cannot grant force authority. This profile registers no OUTPUT_FORCING gate.
No raw output, motion stimulus, force-owner or configuration write is added
by the word actor. The inherited 41-case fixture retains its approved writes.

Snapshot size is a live logical view of occupied arrays. The 4,295 idle paths
are not an instruction to publish unused capacity, nor a subtraction from an
older run's differently occupied history/event tables. Per-state path/value/type
equivalence is the acceptance test. The complete 327-path product is present.

## Memory, sizes and evidence binding

Exact-image automatic Studio Capacity remains **1,743,080 used / 1,402,648
available / 3,145,728 total Blocks** (55% displayed), **+89,648** versus the
accepted R1/R2 image. The pristine source/image hashes are unchanged, binding
both v38 compiler/read-back/access results and the measured Capacity from
preparation; those offline native builds were not needlessly repeated.

Captured native record sizes:

| Record | Bytes |
|---|---:|
| Press canonical root | 134,720 |
| Declared topology product | 43,048 |
| Independent sampled-word source | 32 |
| Migration observation frame | 216,872 |

The frame requires **55 fragments**. It is an acceptance instrument; shipping
S4 must implement per-row/group coherence and on-demand identity/read tiers.
The 8,466 us maximum is cumulative across this download and fixture workload.
R1/R2's 9,829 us included its retained Program/Run/calendar session, so these
peaks are not isolated measurements of the same operation. No task period,
feature, validation or proof rule was relaxed.

All 368 prepared source bindings matched through the native session and before
documentation updates. The **2,249 AB tests** remain bound by unchanged code.
The post-session **74 root tests**, AB spec/contracts, strict consistency and
whitespace gates pass; Runtime/post_* logs contain exact outputs. Two working
documents then record this result: the plan and inactive V2. Their before/after
hashes and final copies are archived explicitly. The V2 stage-status entry for
S3i was also brought up to date with its already-sealed calendar/retention pass.
No HMI changes occurred; Flutter is not applicable.

## Remaining work and next stage

S3j is accepted only for this sampled-word genealogy fixture. Real-module
identity/offline proof and press ST/SFC/LD equivalence remain at S3 final;
electrical, physical retention and security acceptance remain S7. No shipping
direct-write or physical-I/O claim follows from Echo.

Next: **S3k**, the approved 133 remaining frozen paths: 126 mailbox/report,
five production fields and two Features flags, with the R4 table-driven
dispatcher and its own value/type, memory, scan, build/read-back and guarded
native gates. Then finish S3 press acceptance, S4 generic Dart desktop client,
S5 Dart gateway/installer/tray, S6 migration/legacy retirement/persistence and
host-event ownership, and S7 physical/CIP Security acceptance. Persistence
medium after the S6 probe, gateway station write postures, S7 hardware and
commit/push policy remain owner decisions.

Runtime: `C:/work/fraktal-ab-s3j-20261024/runtime_79f53ad4ffbf46ca9943cb350f09912d/`.
Session: `C:/work/fraktal-ab-s3j-20261024/prepare_d93d8292dbb4425d9eba04ba75cd110c/`.
Append-only payload: [manifest](AB_S3J_CANONICAL_RUNTIME_2026-10-25/manifest.json).
No credential file or ACD binary is archived. Owner Siemens archive changes,
the first failed run and all earlier sealed evidence remain untouched.

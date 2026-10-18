# AB optional local Part carrier — 2026-10-18

Non-normative, append-only evidence. Base commit `fa49adcc5`, with exact dirty
source snapshots, logs and artifact hashes in the
[payload manifest](AB_LOCAL_CARRIER_2026-10-18/manifest.json).
This records source, executable model and offline compiler acceptance; no
controller download, online write, gateway restart or physical test occurred.

## Implemented boundary

- An opt-in `Application.part_carrier` currently accepts the typed local
  BY_POSITION provider only. ProviderKind=1/ProviderIdx=1 is private binding
  dispatch; Core CarrierKind=2 is published. Unknown/missing provider state
  faults the consuming Unit with CARRIER_READ_FAILED or CARRIER_WRITE_FAILED.
- PLC-owned bounded ASCII UID, Part presence, result verdict/reason/stamp and
  scaled signed-DINT measurement records. Static names, units, limits, target
  and scale resolve from the hash-validated declaration; measured values and
  tolerance flags are sampled and retained by the PLC. Namespace + startup
  epoch words + exhaustion-checked serial form the local UID. Re-entry while
  the part remains present preserves identity; a new receive clears old results.
- One shared AOI implements receive/start/record/processed/aborted for ST,
  SFC and ladder. Record overflow faults without a partial append. The local
  provider captures the identity it supplied and rejects a different identity
  on result write with PART_ID_MISMATCH. A full bounded result is copied into
  provider state before counters or events. Invalid/unattributed NOK and
  exhausted verdict counters fault RESULT_RECORD_REJECTED.
- Canonical received/started/processed/aborted host events retain PLC identity,
  verdict, reason and sampled time/quality. Reset/mode-change/abort entry closes
  a present part before clearing Unit state; fault entry closes it after chain
  dispatch. Presence gates repeated abort emission. The last UID/result remains
  published after Present drops. Manual removal uses a declared aborted boundary.
- The result owner increments exactly one OK/NOK/REWORK counter after successful
  write; extra GoodCount/ScrapCount marks are refused in a carrier-enabled app.
  The handled ram-failure path emits one processed NOK plus the canonical NOK
  event and never counts that part as good in the new fixture.
- Generic Part/result/record projection, optional grouped reads and odd/even
  metadata-bracketed acquisition. Invalid/torn snapshots fail rather than appear
  as a healthy empty part. Carrier/service stores remain private; Part is read-only
  and outside recipe/configuration writes. Carrier namespace/record definitions
  participate in the validated manifest hash.
- Host physical schema V2 adds bounded UID storage with new UDT/append/Unit AOI
  names. The logical host contract remains unchanged. V1 non-part declarations
  retain their exact output. Part identity cannot leak into a non-part event.
- Whole-cycle testing exposed the ladder model's missing v38 native instruction
  spellings. The generator and model now consume one authoritative spelling map;
  the model retains false-rung suppression and rejects unknown instructions.

## Native overlap review

Native AOIs/UDTs provide execution and typed by-reference storage; the existing
GSV clock/quality source is reused. The
[v38 AOI parameter reference](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/add-on-instructions/edit-an-add-on-instruction/add-on-instruction-definition-editor---parameters.html)
documents complex InOut parameters. Fraktal owns the portable identity/result
contract, write-before-event policy, verdict counting and coherent projection.
No second SFC runtime, alarm state machine or vendor device communication stack
was added. Native alarm-provider and external-module/time-source runtime gates
remain separate. The S12 DINT encoding is explicit; broader native STRING/LREAL
support is not inferred for any other target.

## Native compiler/read-back result

Disposable declaration `fraktal_ab_part_demo.py`, derived from the previous
host fixture: all three AUTO renditions, 16-event ring, four result slots, two
measurement definitions (applied dwell setting and simulated ram position).
Fictitious identity remains OFFLINE-ONLY; this is not a deployment declaration
or a registered hardware leg.

Exact target seed: **1756-L81E 38.011**, no physical I/O, 10 ms periodic task,
output updates disabled. Studio **38.00**, SDK **2.1.974** and the existing
repository offline host. Both rows below are offline compiler targets.

Accepted L5X SHA-256:
`49C6C33EC270ABC5798B41231F8046527A755A3C5FD91AD99013F4C1CE07A263`.

| Check | EchoController | PhysicalController |
|---|---|---|
| SDK Open / Build / Save As events | PASS | PASS |
| Import warnings / errors | **0 / 0** | **0 / 0** |
| Construct census, descriptions, access/type/task settings | equal | equal |
| SFC executable graph: 21 steps | equal | equal |
| ST/RLL executable bodies: 41 | all equal | all equal |
| Authored initial values: 20,339 | all equal | all equal |
| Input unchanged | yes | yes |

Current source regenerates the accepted L5X byte-identically. Intermediate
candidates 01–03 also built on the Echo compiler while scope was being completed;
only final candidate 04 is the acceptance artifact preserved here.

## Regression and cost

- **1,774 AB tests PASS**, 243.201 seconds, including 20 new traceability tests.
  Tests execute the generated AOI algorithm and all three complete AUTO cycles,
  including handled ram failure; they also exercise signed epoch encoding,
  re-entry, identity mismatch, read/write failure, exhaustion, result ordering,
  counter consistency, reset/mode/abort behavior, coherent reads and generic
  projection. This is an executable model, not controller runtime evidence.
- **74 root gate tests PASS**. AB specification/frozen-contract gates clean;
  strict cross-binding consistency: zero errors/warnings; whitespace check clean.
  Expected negative CLI usage output, existing socket ResourceWarnings and
  asyncio slow-task diagnostics remain in the raw test log; no test was skipped
  to obtain acceptance.
- Existing physical, Echo and V1-host generated type/AOI/tag/program/task sections
  are byte-identical. The V1 host fixture still regenerates SHA-256
  `81B5DE52A046750DBB5195BD3F5A4B83DDC0C74A345B33BCAA30879897C9F75A`.
- Against the same 16-event/all-three-rendition host fixture before Part:
  **+8,052 declared data bytes**, **+12,351 ST source bytes**, **+206 statement
  terminators**, **+309 ST lines**, **+3 ladder rungs**. This includes three new
  sequence boundaries, provider/result storage, UID columns and updated reason/
  manifest content. Source estimates exclude AOI storage/native objects and are
  not compiled memory or a hardware capacity acceptance result.

## Remaining limits

No RFID/DataMatrix/MES carrier transport, externally supplied expected identity,
nonempty genealogy, physical retention or global UID uniqueness under clock
replay/download is claimed. Local results are controller memory plus the bounded
host stream; downloads reset initialization. Live delivery, browser rendering,
target restart/clock behavior and durable recovery still require runtime gates.
The carrier-off production/bench declarations remain unchanged; they do not
acquire these guarantees. In particular, the legacy press's unconditional
GoodCount mark at N999 still needs a separate carrier-off NOK counting correction;
the new carrier fixture removes that mark and proves verdict-owned counting.
Part lifecycle events currently reach HostEvents; full TC3 §8.3 message-log parity
is still open. Tool/material producers and SignalTower/LAMP_TEST remain open.
This does not mark the AB port complete or qualify the physical v33 L24ER bench.

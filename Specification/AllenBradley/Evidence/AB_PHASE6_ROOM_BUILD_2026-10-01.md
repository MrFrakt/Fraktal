# Fraktal/AB Phase 6 item 0 — manifest room, offline build

**Date:** 2026-10-01, America/Bogota. **Stage:** generated; owner Studio import,
Verify and download, followed by controller readback, are pending.

The bench baseline was read before this item: controller `7036B510` at
`192.168.100.89`, `1769-L24ER-QB1B/A` firmware `33.014`, carried the coherent
55,160-byte press52 manifest; the gateway was ready and S3 passed 6/6.
This item performed no controller writes or download.

## Build and bounds

The committed declaration and generator emitted `C:\work\press53.L5X` from
`C:\work\seed_v33.L5X`. The parent repository revision is `692481b`.

| Property | Generated value |
|---|---|
| File SHA-256 | `7E35230B1C07E0837B15E5A6BB83ED6DDB5FCE5DB15920AB5866D8CBB541A0EC` |
| ContentHash | `4FD8961CE0AA3E17` |
| ConfigRevision | `5232790` |
| Fields | 485 / 768 |
| Localization | 460 / 768 |
| Manifest bytes, including header | 79,736 |
| Byte budget | 98,304 (96 KiB) |

Both capacities rise from 512 to 768: Fields adds 8,192 bytes, Localization
16,384 at the current key width. The template inherits the same bounds and
also emits a 79,736-byte manifest, with Fields 299/768 and Localization
371/768. No per-station capacity wiring was introduced.

The budget accommodates these capacities with keys up to 80 characters
(98,216 bytes). Against [S7's measured cost curve](AB_S7_MANIFEST_EVIDENCE.md),
this build projects to about 534 ms at a 500-byte connection and 112 ms at
4000 bytes; the whole budget projects to about 658 ms and 138 ms. These are
estimates. Full controller readback must establish the enlarged manifest's
actual byte count, coherence, row equality and read time after download.

## Offline verification

The new pressure tests exceed the old bounds on both declarations: the press
reaches Fields 685 and Localization 660, the template Fields 599 and
Localization 671, and both generate valid manifests. Longer keys are exercised
through a real editable capability. Table overflow and byte-budget overflow
are rejected before an output file exists; the exact budget is accepted.

Those negatives exposed a pre-existing defect: the generator reported the
manifest's size and truncation but did not refuse either at generation. It
now gates output using the same manifest evidence it returns.

XML comparison against the actual `C:\work\press52.L5X` permits changes only
to `FRK_Press_MfHeader`, `FRK_Press_MfFields` and
`FRK_Press_MfLocalization`. Every other project element is equal, including
all executable bodies, UDTs, I/O and task configuration. The ST/SFC/LD graph
readback also matches the declaration: 18 AUTO steps and 21 transitions each.

- AB suite: 1292 tests, exit 0.
- Focused manifest/reader/template suite: 89 tests, exit 0.
- Consistency: 0 errors, 0 warnings; its suite passes 32 tests.
- Mutations: 9/9 killed. They undo either capacity raise, restore or overraise
  the byte budget, remove either generator refusal, exclude the budget boundary,
  skip Fields overflow, or omit the cost of the new slots.

Gates used `-B` with a fresh `PYTHONPYCACHEPREFIX` after automatic approval
review blocked cache deletion. Mutations changed imported code in child memory
only; repository source was never temporarily mutated.

The [JSON record](AB_PHASE6_ROOM_BUILD_2026-10-01.json) contains the generator
report, complete comparison, mutation results and gate summary.

## Deployment and claim

The recorded posture is the v33 legacy zone-and-conduit bench, write-enabled
by the owner's recorded decision. Phase 6 will widen the operations available
through that surface to sets, login and shelving; this capacity item introduces
none of those routes. The write-enabled claim remains owed until S9 passes.

The handover assigns Studio import, Verify and download to the owner on the
licensed desktop. Import `C:\work\press53.L5X` in Studio 5000 v33, run Verify
Controller, download to serial `7036B510`, and restart the gateway. The owner's
`done` authorizes the declared verification harness writes on that controller.
First read the complete manifest: expect `passed: true`, `bytesRead: 79736`,
FieldsCapacity and LocalizationCapacity both 768. Then check gateway readiness
and S3 before the armed regression set. The matching ContentHash alone cannot
confirm this download, because capacity is excluded from that hash.

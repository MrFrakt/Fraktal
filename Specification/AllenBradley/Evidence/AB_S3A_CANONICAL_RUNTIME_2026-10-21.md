# AB S3a Unit-core publication: runtime acceptance, 2026-10-21

S3a passes its explicit 94-path subset on local Echo serial 601FC87B.
Generic discovery uses the controller's Symbol/Template objects and V6.1
manifest, without a runtime station declaration. All paths, values and types
match the legacy oracle, including four active-decision pairs. Genealogy is
restored; candidate and restored-baseline regressions pass 31/31 each.
Shipping V1 remains active, V2 is an approved target, and S3b-S7 remain open.

This append-only record supersedes the pending runtime status in
[preparation evidence](AB_S3A_CANONICAL_PREPARATION_2026-10-21.md).
Raw outputs, retained failures, sources and hashes accompany this report in
[the payload manifest](AB_S3A_CANONICAL_RUNTIME_2026-10-21/manifest.json).
No native ACD or credential file is archived. No commit or push was made.

## Authorization and artifacts

Target: 127.0.0.1 slot 0, Emulate 5580 Controller, product 288, revision 38.11,
serial 601FC87B. Service/listener and exact identity guards pass before each
controller operation. The owner answered "Approve this guarded S3a session"
for the named image, fresh backup, Program/download/Run, document restores,
candidate/baseline regressions, four read-only active-decision captures,
equivalence/scan measurements and genealogy rollback. No fault clear was
authorized or performed.

Preparation folder:
`C:/work/fraktal-ab-s3a-20261021/prepare_0d22cab49f6e4aeeb6fa005ef0f4f9be/`.
Runtime folder:
`C:/work/fraktal-ab-s3a-20261021/runtime_efed1b59b4d14c0dabdc5c66c143dffc/`.

- Generated source: 83443758841A5B5F8D334106079EB8B041F2FF3E3419DB99564108532E361095.
- Prepared candidate pin: F1D24CA83A3A452E02402AD7604A373B592909A55AA4858F510111A54A7EE79F.
- Candidate after SDK saves: DADA856EF119F05DEFB29FE8BCB2F894A59A80274F4E279D42C0256C70D10AA3.
- Fresh backup: AAF439152C2DDD9DEE978C1A831A58F3A6DBD6632910B3665C5668B8461403EE.
- Immutable genealogy original: D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084.

The original genealogy ACD was never opened by the SDK. Rollback opened only
a fresh verified copy; the original hash remains unchanged. The candidate's
original pin is retained. Its saved ACD must not be repinned or redeployed as
the original prepared artifact.

## Capacity and native scan observations

The owner supplied the S3a Studio Capacity screenshot. Values are transcribed
in capacity_review.json; screenshot pixels remain in chat. The displayed unit
is **Blocks**. The prior-stage baseline is the sealed S2 candidate measurement.

| Image | Displayed usage | Used Standard | Available | Total blocks |
|---|---:|---:|---:|---:|
| S2 candidate | 23% | 745,244 | 2,400,484 | 3,145,728 |
| S3a candidate | 25% | 817,476 | 2,328,252 | 3,145,728 |

S3a fits and adds **72,232 blocks**. Neither genealogy's 22% nor the inert
probe's 69% is substituted for the preceding stage.

Twenty native GSV TASK samples per final timing record report:

| Image/window | LastScanTime range, us | Median, us | Cumulative MaxScanTime, us | Overlaps |
|---|---:|---:|---:|---:|
| Prior S2 accepted observation | 109-110 | 109 | 1,177 | 0 |
| S3a after failed/retried candidate fixture | 110-111 | 110 | 1,178 | 0 |
| Restored genealogy after baseline fixture | 99-100 | 99 | 1,167 | 0 |

S3a-minus-S2 observed median and maximum are both +1 us. S3a-minus-restored
genealogy observations are +11 us. These are separate downloads/workloads,
with the disclosed extra paired reads and partial fixture retry, not isolated
publication-cost measurements. HealthProbe and CanonicalTiming agree.

## Acceptance and retained failure

Fresh backup, deployment and rollback exit 0. SDK audits are clean: Save As
for the upload (SDK operation "Open Project From Controller"), and Download /
Change Controller Mode / Save As for both downloads. Candidate read-back is
equivalent for 76 UDTs, seven AOIs, 117 controller tags, 44 executable bodies
and 23,064 authored initial values. R6 top-level and all 18 canonical
type/member access audits pass. Rollback read-back matches genealogy:
58 UDTs, seven AOIs, 109 tags, 42 bodies, 21,926 authored initial values.

Generic acquisition reports 94 values and seven modules. Press is a measured
5,296-byte record. The V6.1 hash is
1E4B991CB3328C858823F8755D8B279BECDF9F5E0FF61E4D131A6BA8790D4546,
revision 31766929; the V5 oracle remains 6DEC4C1DC2F7F78A. Idle comparisons
report comparedPaths=94, typedPaths=94, differences=[], typeAcceptance=true.
Each idle run rejects one changed window and closes on its second attempt.
Only the five explicit D2 corrections are permitted; S3a exercises three
array families and records their 15 concrete path shifts.

The first candidate fixture completes 18 passing rows, then refuses its third
active-decision capture: no equal-even generation spans the paired reads in
100 attempts. Its first two pairs pass all 94 paths/types. The failed capture
establishes no value comparison. Cleanup restores inputs, policy and logout.
No mismatch is relabeled as equivalent and the retry budget is not increased.

Inspection identifies capture-metadata deep copies, legacy decoding and raw
hex conversion inside the proof window. The read-only harness is corrected:
owning legacy readers first warm caches and establish the request plan;
between generation samples it performs only the planned wire reads and
retains their response objects. After an equal-even generation closes the
window, it copies metadata, decodes and compares those accepted responses.
Rejected responses are discarded. Synthetic tests prove the payload is not
inspected inside the window, rejected values do not survive a retry, and
duplicate/empty read plans refuse before I/O. PLC source and the proof are
unchanged. The original helper version is archived alongside the corrected one.

The candidate fixture retry passes 31/31 rows, five-document restore, cleanup
and all four active-decision pairs: tower decision plus NOK in ST/SFC/LD.
Those pairs close after 35, 19, 48 and 71 attempts respectively, with nonempty
prompts and exact 94-path/type equivalence. Baseline then passes 31/31 after
rollback and five-document restore. Actual regression output is **80 rows**:
18 partial + 31 accepted candidate + 31 accepted baseline. The partial run
is retained, not counted as a completed 31-row acceptance. No model is created.

The bounded acquisition window remains a measured scaling constraint for
later surfaces; future work must preserve the proof and reject exhausted
windows. Decision.Timeout/SourcePath remain an explicit full-Core gap.

## Capacity algorithm requested by the owner

The owner requested an estimation algorithm to avoid repeated manual asks.
The new offline tool models reserved data capacity and ST code growth, derives
blocks/model-unit slopes from hash-bound Studio records, and reports an
empirical planning budget with margin. Unsupported allocation/controller
changes refuse. It does not assume Blocks equal bytes or claim a measured gate.
See [method and usage](../AB_CAPACITY_FORECAST_METHOD_2026-10-21.md).

Training uses only genealogy and S2. Held-out S3a predicts 826,044 used blocks
versus 817,476 measured: +8,568 blocks, **+1.0481%**. Its planning budget is
1,023,731 blocks including reserve, above the held-out measurement. S3a can
now train subsequent forecasts, but one held-out surface cannot establish a
universal error bound. Automatic measurement/replacement-gate qualification
remains open. The forecast explicitly sets measured=false and
acceptanceGateSatisfied=false.

The first prototype observation file omitted an explicit ACD-binding field;
the final input adds it and final CLI validation passes. Both files/results
are retained. The installed SDK API documentation was inspected; no documented
Capacity query was found. No Studio window was visible to this session.

## Verification and final state

- AB discovery: `Ran 1973 tests in 256.009s` / `OK`.
- Root gates' tests: `Ran 74 tests in 1.847s` / `OK`.
- Estimator tests: `Ran 10 tests in 0.017s` / `OK`.
- Spec/contracts gates pass; strict consistency reports zero errors/warnings.
- CR-at-EOL whitespace gate passes.
- Both v38 compiler/read-back gates remain bound to the exact unchanged PLC
  source in preparation evidence; only read-only host harness/estimator code
  changed during this runtime session.
- No HMI code changed in this work. Flutter gates are inapplicable; no Flutter
  SDK was selected. Physical controller/CIP Security acceptance remains S7.

All eight prior evidence payloads verify: 890 artifacts. The first integrity
script assumed every historical manifest had a report field; that schema
error is retained and the corrected verifier passes without modifying history.

Final checks pass: Run, not faulted, Remote keyswitch, advancing scan,
MANUAL/idle, logged out, not restoring, original access policy and all five
saved documents equal live. The original preflight verifies again. This
completes S3a at the stated subset; S3b offline preparation is next.

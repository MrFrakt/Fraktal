# S6 consumer classification and first harness migration

Non-normative WP6.1/WP6.2 working record, 2026-11-02. Entry commit
`8cd2060f1591bd31bd8c0c4ba7857598fe7c5f38` is the accepted S5 exit. V1 stays
active; this work changes no generated PLC layout or controller image.

## Classification scope

The executable inventory is
`FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_legacy_consumers.py`. It parses
Python syntax without importing any surveyed module, records source hashes,
imports and importers, and refuses unknown affected module kinds or missing
explicit retirement artifacts. Its output is the
[classification](AB_S6_CONSUMER_CLASSIFICATION_2026-11-02.json).

The initial preview reproduced 107 direct syntax references (54 tools and 53
tests), with 291 modules in their import closure. After the first migration
below, the current inventory has:

| Measure | Count |
|---|---:|
| Python modules surveyed | 383 |
| Direct legacy references | 106: 53 tools, 53 tests |
| Legacy import closure, including direct references | 292 |
| Classified Python modules | 307 |
| Unaffected Python modules | 76 |
| Explicit non-Python retirement artifacts | 3 |
| Unclassified affected modules | 0 |

The closure is a conservative syntax graph, including imports inside functions.
It can grow when a test is added even though a runtime dependency disappears.
The migrated harness's fresh-process test separately verifies that decoding
loads no declaration, generator, station, Python gateway or projection module.
These two measurements answer different questions; neither substitutes for the
other.

| Role | Python modules | Planned action |
|---|---:|---|
| RT | 6 | Retire the Python runtime projection/gateway at WP6.7 |
| MO | 37 | Final sealed replay at WP6.3, then retire at WP6.7 |
| GN | 2 | Collapse generated storage at WP6.6 |
| AD | 4 | Re-home host services at WP6.5 |
| HX | 33 | Migrate station reads or verify standalone engineering probes |
| UT | 137 | Review canonical-structure assertions as owners change |
| HL | 88 | Replace legacy dependencies; retire only proven exclusive helpers |

Classification also includes explicitly named retirement owners that contain
no old read call, and their importers. This adds pure migration oracles that
the original 107-reference census alone would miss. The MO naming rule includes
the existing `fraktal_ab_press_s3k_equivalence` as well as `fraktal_ab_s*`
oracles. First-match precedence keeps oracle `*_execute` files and their tests
out of HX. Generator/adapter unit tests remain UT.

The three additional RT artifacts are `tools/requirements-gateway.txt` and the
two old HMI `live_ab_gateway_test.dart` / `live_ab_command_test.dart` files.
Nothing is deleted now. The inventory records unresolved dynamic-import sites
for review, and does not turn absent static importers into permission to delete
a possible CLI entry point. Final replay and a fresh import census still gate
retirement.

## Plan corrections from the source audit

The plan's broad HX rule also selects nine files with no legacy station-read
dependency: `fraktal_ab_phase0_execute`, `fraktal_ab_reference_execute`,
`fraktal_ab_s11_execute`, `fraktal_ab_s12_execute`, `fraktal_ab_s16_execute`,
`fraktal_ab_s2_execute`, `fraktal_ab_s7_execute`,
`fraktal_ab_s9_coherence_fixture` and `fraktal_ab_s9_execute`.
These are standalone engineering/ABI probes, not an old station projection to
rewrite. Keep their HX role, record `verify-canonical-or-standalone-probe`, and
review their existing fixture-specific bytes/serial/arm guards. Do not invent
a canonical manifest for a historical isolated fixture or waive its checks.
This clarifies migration scope; no wire contract or acceptance gate changes.

## First WP6.2 migration: S9 repository contract

`fraktal_ab_s9_contract.py` now decodes a sealed canonical acquisition through
the S1 reader. The default is S5's committed `generic_capture.json.gz`;
`--capture` permits another strict canonical capture. It no longer constructs
station data through the declaration, projection, their unit-test builders or
the Python gateway. This is offline replay, not a live reader or an unsecured
write path.

The default replay exactly matches the sealed S5 values/types on 5,264 paths,
with the same content hash and seven modules. Three other accepted captures
also preserve their independent frozen expected values/types. Invalid manifests
remain refused. No station-specific coercion or missing-value fallback is added.

The same five Dart test files run against both the historical S9 adapter fixture
and the canonical capture. All **124 cases have identical passing verdicts**.
The contract assertions, ordering/refusal/ambiguous-commit checks, quality checks
and wrap checks are unchanged.

The comparison exposed an existing test-double timing error: a saved gateway
document declares `responseProcessingMs`, while the fake RPC previously returned
it instantly. The production `processing <= elapsed RPC` guard correctly refused
that replay. The fake now waits the declared duration, rounded up to timer
resolution. It preserves source ages, values, quality and the production guard.
Both fixture versions then pass the same assertions. The initial refusal logs
are retained, including an early result-parser failure on non-object JSON output.

Validation passed: 13 focused Python tests; 124 canonical contract cases;
124 historical and 124 canonical cases with identical case-set/verdict replay;
802 default HMI tests with 12 existing skips; locked dependencies and analyzer;
2,370 full AB tests; 74 root tests; AB specification/contracts and strict
consistency. The accepted S5 source regenerates byte for byte, and both v38
targets pass fresh offline builds, readbacks and SDK-log audits. The
[offline evidence](Evidence/AB_S6_CLASSIFICATION_S9_OFFLINE_2026-11-02.md)
records exact outputs and retained failures. No controller read, write,
download, mode or power operation was performed for this work.

## Remaining S6 work

This completes the classification and one offline harness migration, not S6.
Live harness discovery selection, coherent canonical reads, the remaining HX
owners and their helper/test consumers still need migration and replay. The
legacy rollback path stays until the approved O6 switch at S6-Q. The previously
recorded baseline START refusal remains a harness-readiness follow-up.

Then run the final MO/pinned-image/capture replay before any generator collapse;
inventory the approved O4 host-service addition following V6.10; implement the
O5 host FileMedium adapter; collapse storage and remove legacy Frame/services,
observation frame, projection and Python gateway; update gates/documents and
activate V2 only behind S6's exit gates. O1 remains one commit/push per stage
exit. S6 has not exited, so these changes remain uncommitted. S7 stays deferred.

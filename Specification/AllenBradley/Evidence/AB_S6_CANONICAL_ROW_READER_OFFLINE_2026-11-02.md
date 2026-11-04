# S6 canonical row reader — offline progress

2026-11-02, America/Mexico_City; entry commit `8cd2060f1`. This is a second
WP6.2 checkpoint, not S6 exit or live harness acceptance. No controller read,
write, download, mode, fault-clear, clock or power operation runs here.

The [reader review](../AB_CANONICAL_PUBLICATION_S6_LIVE_READER_REVIEW_2026-11-02.md)
describes `open_row_reader`, shared manifest-shape discovery and the canonical
row reader. The exact serial precedes discovery. Only an absent manifest
permits legacy selection; present invalid/ambiguous manifests refuse. A strict
S1 bootstrap validates metadata and discards its values. Every returned leaf
and occupancy count comes from fresh read services under its published owner.
Mixed owners, frozen/invalid progress, torn/late reads, invalid types/handles
and out-of-bounds/count selections yield no values. Protocol 1 keeps the strict
scan-period window; protocol 2 uses its own published bound with independent
progress. The 20-attempt/one-second limits and production HMI policies remain.

All 5,264 occupied S5 leaves replay through complete row/count proofs with exact
values/types. Twenty-seven focused tests pass, including wire/serial/manifest
refusals, fresh-value selection, independent progress, odd/torn retries, wrap,
window/deadline boundaries and no legacy imports. The first test run failed on
nonexistent Busy/Done paths and an incomplete Template fake; that tooling
failure is preserved and corrected against actual published paths.

Full AB discovery passes 2,397 tests; the same 124 canonical Dart contract
cases and all 74 root tests pass. AB spec/contracts and strict consistency pass.
The earlier 2,397-test suite also passed. Final review then made indexed
path spelling exact, rejecting aliases such as [00]; focused tests and a new
full suite pass on the final source, whose 385 Python module hashes stay fixed
throughout that run. Both full logs remain archived.
The prior full HMI result remains 802 passed/12 existing skips, with unchanged
Dart production/test sources; it is not a fresh full HMI run. Flutter/Dart:
3.47.5/3.13.4, C:/work/fraktal-toolchains/flutter-3.47.5.

Accepted S5 source regenerates byte-identically, SHA-256
979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162. Both v38 targets pass fresh offline builds/readbacks
and SDK-log audits. No original genealogy ACD is opened. The unchanged exact
image retains its earlier 66% Capacity result; no new runtime/Capacity claim.

The refreshed census has 385 surveyed Python modules, 309 classified plus three
additional artifacts, zero unclassified, 106 direct legacy references and 294
conservative import dependents. No extra HX owner is claimed migrated. The
fixture audit records 47 Unit members and three literal root-leaf matches;
that is not a semantic correspondence or a request to publish private fields.
No existing fixture assertion, write surface or cleanup is changed.

The [WP6.4 host-service inventory](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_REVIEW_2026-11-02.md)
records ConfigSets, ConfigProvider, LiveDocuments and HostEvents owners, current
wire/storage limits and durability/access/delivery requirements under approved
O4/O5. Native descriptor/chunk layouts and adapter implementation remain open;
no V6.11 type or host process is emitted by that inventory.

Read-only host inspection at 2026-11-02T23:27:08.2507450Z finds the Echo service
Stopped and no 44818 listener. No service operation is attempted. Native
fallback/discovery, active row performance and workload equivalence are unrun.
The last accepted controller rollback remains the dated S5 record, not a new
observation of the controller's image or mode.

Next is bounded row-body packet batching, then press lifecycle/public-assertion integration with separately accounted
fixture-only observations and unchanged sealed verdicts. Other HX migrations,
WP6.3 replay, host services, collapse, retirement, S6-Q and V2 activation remain.
S6 has not exited; no commit/push under O1. Physical S7 remains deferred.

Payload manifest SHA-256: 4249C7C37806DB885755B657581DA9269F7B824C22F087DF60DCF5715DBE36EF.
No credentials, ACD/L5X, binaries or caches are archived; earlier evidence is
unchanged and the failed run remains preserved.

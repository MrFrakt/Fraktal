# S6 classification and first canonical harness replay

Offline progress, 2026-11-02 (America/Mexico_City). Entry commit `8cd2060f1`.
This record completes WP6.1 and the first offline WP6.2 harness migration.
S6 has not exited. There is no controller access, new download, schema/layout
change, retirement, baseline switch or V2 activation.

The [consumer review](../AB_CANONICAL_PUBLICATION_S6_CONSUMER_REVIEW_2026-11-02.md)
and [classification](../AB_S6_CONSUMER_CLASSIFICATION_2026-11-02.json) describe
the first-match inventory: 383 Python modules surveyed, 307 classified plus three
explicit non-Python retirement artifacts, 76 unaffected and zero unclassified.
The initial preview has 107 direct references/291 import dependents. After S9's
direct projection dependency is removed, there are 106 direct references and 292
conservative import dependents, including new tests and lazy engineering
imports. A fresh-process replay proves the migrated harness loads none of the
declaration/generator/station/projection/gateway modules. Nine standalone HX
probes retain their specific ABI guards for review. No files are deleted.

S9 now uses the S1 canonical decoder on sealed native captures. Its default
replay matches all 5,264 values/types of the accepted S5 document; three other
accepted captures also match their frozen expected values/types. Invalid
manifests still refuse. The same shared Dart contract passes all 124 cases on
both the historical adapter fixture and canonical capture with identical
case sets/verdicts. These are offline contract replays, not a claim that two
different station states have equal values.

The old instant-RPC fake wrongly replayed a saved responseProcessingMs larger
than its observed RPC duration. The production guard correctly refused all
seven AB contract setups; their errors and an early result-parser failure are
retained. The fake now waits the declared duration, rounded up to timer
resolution. Source ages, values, quality, assertions and production freshness
rules are unchanged. Both historical and canonical fixtures then pass.

Passed gates: 13 focused Python tests; 124 canonical Dart cases; 124 historical
and 124 canonical cases with identical verdicts; 802 full HMI tests with 12
existing skips; analyzer; locked dependencies; 2,370 full AB tests by discovery;
74 root tests; AB specification/contracts; strict consistency. Flutter 3.47.5 /
Dart 3.13.4 at C:/work/fraktal-toolchains/flutter-3.47.5.

Accepted S5 source regenerates byte-identically, SHA-256
979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162.
Both v38 targets pass fresh offline builds/readbacks and SDK-log audits.
No controller is accessed and the original genealogy ACD is never opened.
The exact-image Capacity measurement remains 66% on the unchanged image; no
new capacity or native-runtime result is inferred. This verifies the current
S5 source pin, not WP6.3's remaining final replay of all historical pins/oracles.

Next: live harness discovery selection and coherent canonical readers, then
the remaining HX/helper/test migrations and final sealed MO replay before
generator changes. Host services, storage collapse, retirement and activation
remain open; the inherited baseline START refusal remains a readiness follow-up.
O1 permits one commit/push per stage exit; S6 work stays uncommitted. S7 remains
deferred under O2.

Payload manifest SHA-256: 3B4DFD3FA80270B0F944431C9748FF4A9F43FA5EB2A6263103A64EE0EDF17057.
No credentials, ACD/L5X, binaries or caches are archived. Failed investigations
remain preserved. No acceptance assertion, type, value or limit is weakened.

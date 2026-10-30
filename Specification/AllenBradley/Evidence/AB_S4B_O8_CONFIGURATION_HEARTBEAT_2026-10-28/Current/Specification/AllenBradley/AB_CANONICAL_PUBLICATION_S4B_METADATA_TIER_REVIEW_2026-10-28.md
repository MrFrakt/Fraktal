# S4b: CIP configuration fallback read tier — owner decision requested

**Owner-approved and implemented offline; native qualification remains open.**
Reply to `call_a7b096025e8b4393802914b727457fab:0`:
“Approve CIP configuration heartbeat (Recommended)”. The optional CIP-only
capability now passes three fresh exact-source profile rehearsals;
see the [qualification](Evidence/AB_S4B_O8_CONFIGURATION_HEARTBEAT_2026-10-28.md).
No new native session is run by that record. Echo remains on genealogy.

## Decision and exact effect

Allow the generic desktop CIP reader to use its already declared metadata
heartbeat for activation-static configuration containers that the PLC publishes
but its configuration pages do not replace. This changes their delivery latency:
currently fast Good/expiry is 1/3 seconds; proposed metadata period/Good/expiry
is **5/7.5/15 seconds**. An aged row still loses its payload. The counters,
even/equal proof, complete I/O window below 10 ms, 20-attempt/one-second budget,
and fast station liveness remain unchanged.

The [enumerated inventory](AB_S4B_METADATA_TIER_PATHS_2026-10-28.json) contains
**230 candidate leaves** in the sealed genealogy capture, before any exact
manifest replacements are hydrated:

| Existing configuration container | Candidate leaves |
|---|---:|
| Alarm metadata (`Meta`) | 186 |
| Available model identities | 8 |
| Command catalog | 18 |
| Mode policy | 8 |
| Nameplate | 10 |

This uses the existing `OpcUaFieldTier` classification and container list.
Unknown leaves stay fast. Status, module identity, capability leaves, counters,
active alarms, current steps, live OEE, and Access/Policy stay fast. Exact
manifest replacements retain their existing exclusion/overlay behavior.
Unconsumed implementation definitions remain excluded. No values, types,
array bounds, PLC symbols, access masks, or write capabilities change.

For production, expose an optional transport read-policy capability and enable
it only in the generic CIP client. The shared repository consumes that capability;
it contains no station declaration or CIP type check. Other transports keep their
current policy. Reconnecting wrappers must delegate the capability and invalidate
the tier signature if it changes. The provisional experiment applied to budgeted
transports generally; that broad implementation was reverted and is not proposed
for shipment.

PLC-side masking remains authoritative. The configuration read service still
requires fresh owner-version headers and discards cached plaintext/policy on
revision or session changes. This proposal does not permit a client to retain
an unreadable value or to issue a command on unsecured CIP.

## Why this requires a decision

The plan §3 explicitly prohibits changing a "tier rule" to make a gate pass.
The frozen tier rule therefore cannot be changed as a routine optimization.
Approval would amend that invariant only for the enumerated configuration-container
fallback policy, through the existing generic classifier. It would not amend the
station freshness, proof, retries, access, or native acceptance gates.

The approved S4b configuration review already separates metadata/value freshness
from station liveness. `OPCUA_TRANSPORT.md` treats these containers as configuration
normally served outside cyclic reads. AB's fully published tree exposes some
containers that its configuration service does not re-serve; the conservative
fallback currently reads them every fast sweep. This proposal supplies a bounded,
visible metadata age for that case rather than omitting their data.

## Measurements and limits

Three consecutive provisional profile rehearsals, seeds 8/7/9, completed all
**31 views, seven modules and three bus nodes**, with maximum mapped ages
**393.105 /433.729 /423.702 ms**. Both read-only action refusals passed and the
peer recorded no writes. The debug comparison reproduced STALE after Overview.
Their immutable source copies and raw results are in
`C:/work/fraktal-ab-s4b-scheduling-20261028/offline_01/profile_23` through
`profile_25` and `debug_02`.

Those three passes used the provisional fallback. They **do not qualify the
current source** and authorize no native preparation. The fallback was reverted
on review of the invariant. Subsequent original-tier profiles 26–28 fail LIVE
coverage; smaller packet-encoding overhead and an overdue-poll microtask experiment
did not resolve the failure. The microtask experiment is also reverted. All failed
runs remain recorded; Echo preflights pass before and after every run.

Other retained work is independent: exact native row batching/count deduplication,
planning and decoding outside neighboring proof windows, small coherent discovery
headers, bounded background operations, version-validated configuration caching,
atomic tier installation, and a trace correction that keeps timing fields out of
configuration descriptors. These preserve the original tier policy.

This is synthetic-peer evidence, not native E7 or a claim that the proposal alone
completes S4b. It does not establish physical-controller performance or trigger O7.

## Choices and next gate

**Decision: choice 1 approved.** Implement the CIP-only capability, then require
fresh exact-source rehearsals and every native gate. The provisional passes do
not substitute for qualification of that implementation.

1. **Approve the configuration-container heartbeat policy (recommended).**
   Implement the CIP-only capability, test other transports remain unchanged,
   rerun the full offline gates and three consecutive profile rehearsals on the
   final source, then prepare S4b-Q under the existing Echo standing authorization.
2. **Keep the existing fast fallback.** Continue the bounded reader work under
   the present invariant. If that cannot satisfy the declared profile, prepare
   a separate review for PLC-owned row revisions/buffering (S4 coherence option B).
   No buffer contract or new image is authorized by this choice.

Either path still requires S4b-Q E1–E9 together: original candidate writes and
restoration, all independent read comparisons, profile desktop and scan, then
genealogy rollback and 31 baseline cases. The candidate remains
`30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`,
with transferred 65% Capacity; no PLC image is changed by this proposal.

Echo standing authorization O3 already covers guarded controller sessions.
This question concerns the read-tier contract, not another download approval.
S5, S6, the later browser checklist and deferred S7 physical gates remain open.

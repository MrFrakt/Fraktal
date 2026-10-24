# S3h Core type contract review

**Owner approved on 2026-10-23:** “Approve S3h corrections and offline work”
(`call_f7da50b3655c43e4be6d7145b8b02c9b:0`). S3g is complete on Echo and genealogy is restored.
This draft covers the next stage's finite contract amendment and offline work;
it grants no controller-changing authority. V2 remains inactive.

S3h adds 278 consumed legacy paths: Part/genealogy 40, HostEvents 220,
Nameplate 10, SignalTower seven and MachineState one. Cumulative legacy
coverage becomes 4,288 of 4,437 paths; 149 remain for later surfaces. With a
full event ring, the canonical page totals would be 3,950 / 3,900 / 3,550.
These are inventory forecasts, not runtime acceptance.

The [plan §1](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md) currently permits
the five D2 bounds and approved finite S3f/S3g corrections. Actual Core DUT/FB
declarations require another **36 enumerated type corrections**:

| Paths | Legacy logical type | Proposed Core type | Owning declaration |
|---:|---|---|---|
| 16 | Int32 | UInt32 | `HostEvents/Ring[1..16]/Sequence`, `ST_HostEvent.Sequence : UDINT` |
| 3 | Int32 | Int16 | `HostEvents/Count`, `Capacity`, `RingHead`, `FB_HostEventPublisher` outputs |
| 17 | String | DateTime | `Part/Result/Stamp` and `HostEvents/Ring[1..16]/Stamp`, owning Core `DT` members |

The [machine-readable inventory](AB_CANONICAL_PUBLICATION_S3H_INVENTORY_2026-10-23.json)
lists all 278 paths, frozen values, old/proposed types and authoritative source
hashes. **Only these 36 paths may change type.** The other 242 added paths
retain exact values/types; the existing accepted surfaces retain their rules.

One value consequence is explicit within those same 36 paths: an unset
`Part/Result/Stamp` currently returns the empty string. Canonical DateTime uses
`0` when unset, as the qualified generic reader already does. Populated UTC
timestamps must retain their exact existing value and precision. Host events
already require a valid timestamp; empty ring slots remain omitted. There is
no additional dependent-value allowance, coercion, tolerance or ignored path.

The existing AB-only genealogy counts/capacities and HostEvents delivery
metadata keep their binding semantics and logical types. This includes the
sequence/epoch rollover and producer ownership; this draft does not change an
append algorithm or expand its domain. Enum ordinals remain DINT. Measurement
values/limits/targets remain exact LREAL/Double, computed by the PLC from the
existing measurement owner and its engineering scales.

The consumed bounds remain four result rows, two parent slots and sixteen
event slots. The event ring publishes its occupied physical slots using the
PLC-published count, as selected by the owner in S3a. No new D2 bound exception
is proposed. Parents and event fields clear exactly as the existing providers
do; historical parents are never reconstructed by a client. Nameplate identity
comes from the declaration and is initialized in the PLC. One existing owner
continues to classify MachineState and drive SignalTower outputs.

After approval: implement the independent S3h reference and versioned native
records; prove empty/populated Part timestamps, scaled Double measurements,
receive/result/abort/genealogy clearing, partial/full/wrapped host rings,
captured resource/model text and tower/classification behavior. Run the full
offline gates, both v38 builds/read-backs, exact-image automatic Capacity,
then separately seek current authorization for native acceptance/rollback.
The whole-scan proof remains 100 attempts/five seconds; no feature or validation
is removed to fit. No commit or push is authorized.

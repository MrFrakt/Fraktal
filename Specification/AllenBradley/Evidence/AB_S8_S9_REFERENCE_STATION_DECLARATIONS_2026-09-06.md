# Fraktal/AB S8 + S9 — reference-station declarations (2026-09-06)

**Spikes:** S8 endpoint and conduit security (legacy-posture leg) · S9
repository and mailbox conformance (freshness/budget leg)

**Result:** **Two named remainders are now discharged as declarations against
already-measured costs: the v33 bench's legacy zone-and-conduit posture with a
declared Security Level, and the reference station's freshness thresholds and
poll budgets. Both spikes remain OPEN on their other inputs.**

**Date:** 2026-09-06

**Repository revision at start:**
`6989e09f7be17c218283bc47139baa8a98c85d75`

**Scope and boundary.** This record contains **no new hardware measurement**
beyond one read-only re-confirmation of CIP Security absence (§2.1). It derives
declarations from measurements already recorded in
[`AB_S1_CIP_DATA_PATH_EVIDENCE.md`](AB_S1_CIP_DATA_PATH_EVIDENCE.md),
[`AB_S7_MANIFEST_EVIDENCE.md`](AB_S7_MANIFEST_EVIDENCE.md) and
[`AB_S9_COHERENCE_EVIDENCE.md`](AB_S9_COHERENCE_EVIDENCE.md), under the
decisions frozen in
[`AB_S8_S9_DECISION_RECORD.md`](AB_S8_S9_DECISION_RECORD.md).
No download, mode change, tag write, fault clear, clock set, firmware
operation, network configuration, safety operation or SD-card operation
occurred. The workstation this ran from is recorded in
[`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md);
that machine cannot perform any v33 online operation, which is precisely why
these two documentation-only remainders were the available work.

**A declaration is not a conformance claim.** Nothing here proves an
implementation. It fixes the numbers and the posture an implementation will be
audited against, so that "declared per deployment" stops being an unfilled hole.

---

# Part A — S8 legacy zone-and-conduit posture for the v33 bench

## A.1 Why the legacy posture, restated from measurement

`AB_S8_S9_DECISION_RECORD.md` D1 makes CIP Security on firmware v37+ the
recommended posture and zone-and-conduit the supported legacy posture. Which
one this controller is *entitled* to is a hardware property, and it was
measured, not inferred.

### A.1.1 Re-confirmation on 2026-09-06

`fraktal_ab_security_probe.py` was re-run read-only against the serial-guarded
target from the new workstation. The result is identical to 2026-08-14:

| CIP object | Class | `cipStatus` | Implemented |
|---|---|---|---|
| CIP Security | `0x5D` | `0x05` path destination unknown | `false` |
| EtherNet/IP Security | `0x5E` | `0x05` path destination unknown | `false` |
| Certificate Management | `0x5F` | `0x05` path destination unknown | `false` |

`cipSecurityAvailable: false`, `cipSecurityObjectsImplemented: []`. The device
answers the session and refuses all three classes, so this is a positive
absence, not a timeout. **The legacy posture is therefore mandatory for this
controller, not chosen for convenience.**

## A.2 Declared zones and conduits (IEC 62443)

The reference station is the Phase 0 bench: one controller, one engineering
host, no I/O, no line network, no plant uplink.

| Zone | Members | Trust rationale |
|---|---|---|
| **Z-CTRL** — control zone | `1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`, at `192.168.100.89/24` | Lowest-capability member sets the zone's ceiling. The controller can neither authenticate a peer nor encrypt a session (§A.1), so every protection in this zone is external to it. |
| **Z-ENG** — engineering zone | the engineering workstation and, when it exists, the Fraktal gateway host | Holds Studio/SDK, the repository tools, and all project source. Compromise here is equivalent to controller compromise, because it holds download authority. |

| Conduit | Endpoints | Protocol | Control |
|---|---|---|---|
| **C-EIP** | Z-ENG → Z-CTRL | EtherNet/IP explicit messaging, TCP/UDP `44818` | The only production data path. Physically segregated `192.168.100.0/24` with no default gateway on the controller (`gateway 0.0.0.0`, confirmed 2026-09-06). Unauthenticated by construction — **the network is the control**. |
| **C-ENG** | Z-ENG → Z-CTRL | USB device path / Studio virtual `Backplane\16` | Engineering-only, per D5 a **separate conduit**. Carries download and mode-change authority. Not present in a production deployment. |

**No conduit crosses into a business, plant or internet zone.** If a deployment
adds one, this declaration is void and shall be rewritten before that link is
made; it is not extended by analogy.

## A.3 Declared Security Level

Against IEC 62443-3-3, for **Z-CTRL** on this controller family:

| Item | Declaration |
|---|---|
| **SL-T (target)** | **SL 1** |
| **SL-C (capability, controller)** | **SL 0** for every requirement whose enforcement must occur *in the controller* |
| Basis | The controller implements none of CIP objects `0x5D`/`0x5E`/`0x5F` (§A.1). It cannot identify or authenticate a human or software peer (FR 1), cannot enforce use control on a CIP request (FR 2), and offers no session integrity or confidentiality (FR 3, FR 4). |
| How SL-T 1 is met at all | Entirely by **compensating controls in the zone and conduit**, never by the device: physical segregation of `192.168.100.0/24`, absence of any route off that subnet, engineering-host control of the C-ENG conduit, and the read-only initial claim (D2) which means no write surface is exposed to authenticate. |

**Declared explicitly, so it cannot be read past:** this station meets SL-T 1
*only while it stays segregated*. It does not meet SL 2 and cannot be made to,
because SL 2 requires the device to authenticate its peer and this device has
no mechanism to do so. **A deployment needing SL 2 or above shall change
hardware to a CIP-Security-capable family at firmware v37 or above** — it shall
not be granted an exception against this record. That is the D1 consequence
applied to a concrete station.

## A.4 Residual risk, accepted knowingly

| Risk | Why it is not mitigated here | Accepted because |
|---|---|---|
| Any host on `192.168.100.0/24` can issue arbitrary CIP requests | The controller authenticates nothing | The subnet is physically isolated with no I/O and no uplink; the bench is a test target |
| CIP traffic is neither encrypted nor integrity-protected | No `0x5E` object | No credential or process secret traverses C-EIP; the claim is read-only |
| Download authority rests on workstation trust alone | No controller-side use control | C-ENG is engineering-only and each controller-changing operation requires current explicit authorization plus an exact serial/firmware check |

## A.5 What S8 still owes after this record

**S8 remains OPEN.** This discharges *the legacy leg* — the documented zone,
conduit and declared Security Level that D1 named as the alternative to a CIP
Security demonstration. Still owed:

- a demonstrated CIP Security configuration on a v37+ capable controller, if
  and when such hardware exists (it does not on any surveyed workstation); and
- the generated allow-list audit run against a *generated production* L5X. The
  auditor `fraktal_ab_access_audit.py` exists and runs, but there is no
  production artifact to audit until R4–R6 close.

---

# Part B — S9 reference-station freshness thresholds and poll budgets

## B.1 What is being declared, and against what

D2 fixes that the three read tiers are TC3's, and that **freshness thresholds
and poll budgets are declared per deployment against that station's measured
cost** — never fixed per binding. The inputs it named now all exist:

| Input | Measured value | Source |
|---|---|---|
| Whole-manifest cold read, 500 B connection | **292.9 ms** (317 / 293 / 293) | S7 |
| Whole-manifest cold read, 4000 B connection | **61.6 ms** (85 / 60 / 62) | S7 |
| Header-only steady-state poll | **31.6 ms** @ 500 B, **37.1 ms** @ 4000 B | S7 |
| Per-read fixed overhead floor | **~4.7 ms** | S7 |
| Concurrent PLC reader sessions | 1, 2, 4, 8, 12, 16 all pass; 16-reader max **262.793 ms** | S1 |
| Recommended concurrent readers | **four** | S1 |
| Identity round trip from the engineering host | median **19.6 ms**, max **69.4 ms** | 2026-09-06 addendum §7 |
| TC3 interactive reference | ~15 ms snapshot, ~86 ms mode-change round trip | D2 |

**The reference station** is one controller, one gateway, one manifest of
43,728 bytes, on the segregated subnet declared in Part A.

## B.2 Declared connection size

**4000 bytes.** S7 measures the whole-manifest read at 61.6 ms there versus
292.9 ms at 500 bytes — a 4.75× improvement for a configuration change. The
500-byte figure is S1's *conservative floor*, retained as the fallback a station
declares when its path cannot negotiate larger, not as the reference value.

## B.3 Declared tier assignment and poll budgets

| Tier | Contents | Declared poll period | Declared freshness threshold | Headroom against measurement |
|---|---|---:|---:|---|
| **Live/fast** | manifest header (revision/coherence token), root status, active command/result | **100 ms** | **300 ms** (3 missed polls) | header poll costs 37.1 ms → **37 %** of period |
| **Slow** | module rows, nameplates, operations, diagnostics summary | **1000 ms** | **3000 ms** | largest slow table (Fields, 16,384 B) 107.9 ms → **11 %** of period |
| **On-demand / excluded** | localization, rationalization, optional profiles, full manifest re-read | none — fetched on revision change or explicit request | **not applicable**; served value carries its own timestamp | full re-read 61.6 ms, amortized to zero in steady state |

**Derivation of the live/fast period.** The binding constraint is the header
poll at 37.1 ms. A 100 ms period leaves 63 % idle on the single reader that owns
the fast tier, which absorbs the 69.4 ms worst-case latency observed on this
network path without the period overrunning. Going to 50 ms would put the header
poll at 74 % of period and leave no room for that worst case — **50 ms is
therefore declared out of budget for this station**, not merely undesirable.

**Derivation of the freshness thresholds.** Three consecutive missed polls, per
tier. This is the fail-closed rule from D2 and Core §11.2: a value older than
its threshold is presented as stale and **never** silently as current.

## B.4 Declared reader budget

| Reader | Owns | Concurrency cost |
|---|---|---|
| R1 | live/fast tier | 1 session |
| R2 | slow tier | 1 session |
| R3 | on-demand and full-manifest re-read | 1 session |
| *(reserve)* | headroom for a second client or a retry-until-stable re-read | 1 session |

**Four concurrent reader sessions**, which is exactly S1's recommendation.
S1 proved 16 readers pass, so this declaration sits far inside the measured
envelope; the reserve exists so a coherence retry (§B.5) never has to preempt a
live-tier poll.

## B.5 Interaction with the coherence guard

S9's measured guard is retry-until-stable, and it converges **whenever the
mutation interval exceeds the guarded read window**. At the declared 4000-byte
connection the guarded whole-manifest window is ~61.6 ms, so the declaration
carries an explicit obligation:

> A reference-station manifest whose content mutates faster than **once per
> ~62 ms** is outside this declaration. The guard stays fail-closed — S9 proved
> it never accepts a torn snapshot — but it may fail to converge, and the
> station shall then either slow its manifest mutation or re-declare its
> budgets against a fresh measurement.

That is stated as a limit rather than buried, because a non-converging guard is
a stall, not a wrong value, and an operator needs to know which one they have.

## B.6 What S9 still owes after this record

**S9 remains OPEN.** This discharges *the freshness/poll declaration* named in
"What remains owed". Still owed, unchanged:

- coherence-token behaviour end to end, reconnect discovery, quality codes and
  timestamp mapping;
- the AB adapter passing the shared adapter-agnostic repository contract suite
  (D3) — implementation work gated behind R0–R6; and
- the mailbox matrix and the five crash boundaries, owed **only when writes are
  enabled**. The claim remains **read-only** (D2); no agent may switch it.

---

## C. Status after this record

| Gate/spike | Before | After |
|---|---|---|
| S8 | OPEN — posture decided, partly evidenced | OPEN — **legacy leg discharged**; CIP Security demonstration and production allow-list audit still owed |
| S9 | OPEN — design decided, coherence proved | OPEN — **freshness/budget leg discharged**; contract suite, quality/timestamp, reconnect still owed |
| R6 | OPEN | OPEN — unchanged; R6 needs S8 complete |
| R4, R5 | OPEN | OPEN — unchanged; blocked on tooling per the 2026-09-06 addendum |

No readiness gate changes state on this record, and no implementation is
authorized by it.

## D. Controller-changing operations this session

**None.** The only controller interaction was the fixed-vector read-only CIP
Security capability probe in §A.1.1, serial-guarded to `7036B510`.

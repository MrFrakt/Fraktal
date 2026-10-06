# Fraktal/AB — S8 and S9 decision record

**Status:** decisions settled; **both spikes remain OPEN** because deciding a
posture is not evidence that it was implemented

**Date:** 2026-08-14

This records the decisions taken for the security spike (S8) and the repository
and mailbox conformance spike (S9), and the reasoning behind each, so that a
later reader can tell which parts were chosen and which parts were derived from
Core. Where a decision narrows the remaining work, it says so; where it does
not, it says that too.

---

## S8 — Endpoint and conduit security

### D1 — CIP Security recommended, zone-and-conduit legacy

**Decision.** CIP Security on a capable controller at **firmware v37 or above**
is the recommended posture. The IEC 62443 zone-and-conduit arrangement remains
supported as the **legacy** posture for families that cannot offer CIP Security,
including the `1769-L24ER-QB1B` at v33 used for all Phase 0 evidence.

**Why.** Only CIP Security makes the controller itself authenticate its peer.
The legacy posture is not equivalent: the network is the control, and the
project must declare that risk knowingly rather than inherit it.

**Consequence that must not be lost.** The recommended baseline is *not* the
baseline the evidence was measured on. S2, S4, S11 and S12 each state that a
different family or revision reruns the spike, and the S12 type map is a
property of this controller — a v37+ family may offer `LREAL` and a native
`TIME`, which would change the generated contract. A project pinning v37+ owes a
rerun of the target-specific spikes on that target. This is now written into
AB §2.1 so it cannot be read past.

### D2 — Read-only initial claim, writes as an explicit switch

**Decision.** The initial claim is read-only. Writes are enabled at the gateway
by configuring a write root — no controller download, because the generated
allow-list already gives root mailboxes read/write. **Any new AB project shall
be asked explicitly** whether it is read-only or write-enabled, and the answer
recorded.

**Why this is compliant rather than a relaxation.** Core §11.2 attaches the
authentication obligation to *command-capable* transports and separately
requires that "a projection that is read-only shall state that restriction
explicitly". A read-only deployment has no write surface to authenticate, so a
lighter posture on a segregated line is proportionate. The moment a write root
exists the transport is command-capable and Core §14 applies unrelaxed:
authenticated principals, least-privilege roles, and **anonymous or
unauthenticated write is prohibited**. The switch that enables writes is the
same switch that arms the requirement.

This mirrors TC3, where the gateway's `--write-root` already decides whether a
browser may command a PLC, and the PLC applies its own §7.6/§7.7 gates
regardless.

### D3 — Client identity: the TC3 two-state rule, plus a read-only state

**Decision.** Adopt TC3 §11.1's rule — anonymous is permitted "only for a
controlled commissioning activity", production requires authenticated
sign-and-encrypt with least privilege — and add the read-only production state
between them:

| State | Client authentication | Permitted |
|---|---|---|
| Commissioning | anonymous permitted | controlled, time-bounded, recorded |
| Read-only production | anonymous permitted on a declared isolated conduit | reads and diagnostics; no write root |
| Write-enabled production | authenticated, least-privilege roles | operator / maintenance / engineering |

**Why not stricter.** A production line network is normally already segregated
from office and wireless networks, and on the legacy posture the controller
transport is unauthenticated no matter what the gateway does. Demanding
certificate enrolment for a read-only viewer would add ceremony without closing
the actual hole. **Why not looser:** roles restrict but never decide — the PLC
remains the access authority, so a gateway role can only narrow what the
controller would already have permitted.

### D4 — Secrets and rotation: Core §14.2/§14.3, as TC3 does

**Decision.** Endpoints, credentials and keys are configuration or secret-store
values, never literals in generated code, L5X, customization exports or version
control, and never logged. Rotation is change-managed under Core §13/§14.3 with
a named owner; the audit log records privileged actions without credential
values.

**Why.** These are already Core `shall`s. There was no binding-specific decision
to make beyond confirming Fraktal/AB inherits them unchanged.

### D5 — Engineering access is a separate conduit

**Decision.** Studio 5000 access stays off the gateway conduit. The Phase 0
path — USB at `Backplane\16` — already satisfies Core §14.1's requirement that
the engineering conduit be access-controlled and "not permanently open on the
production network"; a routed engineering VLAN reachable on demand is the
alternative. The gateway conduit carries the repository protocol and nothing
else, and is never a path to download, online edit or firmware.

**Convenient consequence.** If the open Ethernet-engineering question is
resolved by formally scoping engineering to USB, that decision also discharges
this one.

---

## S9 — Repository and mailbox conformance

### D1 — Bound the mailbox payload to one unfragmented write

**Decision.** The request payload **shall** fit a single unfragmented connected
write at S1's conservative 500-byte connection size.
`FRK_MAX_MAILBOX_ARGUMENTS` is *derived* from that rule rather than chosen for
expressiveness. Test the single-slot design first; two-slot/seqlock remains the
named fallback if atomicity fails.

**Why.** A payload larger than the connection size fragments across CIP
transactions, and a controller scan can fall between fragments. The commit
marker still gates action, so the design is likely to survive — but "likely" is
not a contract, and removing the fragmentation removes the argument entirely.
An operation needing more carries an operation ID plus a bounded argument set;
large payloads are a staged configuration write, never a command.

Worth noting: this is TC3's design too — "writes all request arguments first and
writes `Sequence` last … prevents a scan from consuming a mixture of old and
new". A defect found here is a defect in both bindings.

**The bound does not retire the underlying question, and an open verification
item now says so in both bindings.** Bounding the AB payload removes
fragmentation for AB; it does nothing for TC3, which has no equivalent bound.
The shared assumption — every argument visible to the scan before the commit
marker is — has never been tested against a batched, segmented or reordered
transport write, whether that is an ADS sum-write, a TF6100 multi-node write, or
a CIP payload crossing the connection size. Both bindings shall test segmented
request writes, out-of-order argument commits, and a scan deliberately
interleaved between the argument and sequence writes before a writable
deployment. The item is recorded in AB §7.7, TC3 §3.10 and the frozen contract's
open-holes list so it cannot be lost, and the fallback — two-slot or seqlock —
would apply to both bindings.

### D2 — Tiers are TC3's; freshness and budgets are per deployment

**Decision.** Adopt the existing three read tiers — live/fast, slow, and
on-demand/excluded — with the gateway intersecting every client's slow and
on-demand sets before changing tier setup, exactly as the shipped gateway does.
Freshness thresholds and poll budgets are **declared per deployment** in the
binding record against that station's measured cost, not fixed per binding.

**Why.** A binding does not get to invent a tier vocabulary: the HMI classifies
once and every adapter obeys, or the generic-HMI objective fails. And a single
global freshness number would be wrong everywhere — the honest artefact is the
cost model plus a per-station declaration. The inputs now exist: S1's four-reader
and 500-byte ceiling, and S7's 293 ms / 62 ms manifest read with a ~32 ms header
poll. TC3's measured ~15 ms snapshot and ~86 ms mode-change round trip are the
reference for what "interactive" should feel like.

### D3 — Parity means the shared contract suite, not an A/B rig

**Decision.** "Parity with the TC3 adapter" is **semantic**, proven by making
the AB adapter pass the same adapter-agnostic repository contract suite the
existing adapters satisfy. Equal latency is explicitly **not** required. A
Beckhoff bench is **not** a prerequisite for S9.

**Why.** What Core actually requires (O8, §3.10) is that one generic HMI renders
any binding with no per-station code — the HMI binds one repository interface
and adapters swap in behind it. So the observable contract must be identical:
envelope fields, quality transitions and their fail-closed defaults, tier
classification, discovery and configuration revision handling, mailbox
commit/acknowledgement ordering, no-replay on reconnect. Latency is a different
matter: ADS is Beckhoff's native fast path and CIP is not, so requiring equal
numbers would be arbitrary. AB latency is recorded, not matched.

**This removes a resource blocker** that would otherwise have gated S9 on
hardware availability.

### D4 — Crash testing scoped to the five replay-capable boundaries

**Decision.** Not an exhaustive crash matrix. The boundaries that can produce a
replay or a double-act are tested: crash after payload write and before commit;
after commit and before the acknowledgement is observed; after observation and
before local completion; reconnect holding a stale in-flight sequence; and
sequence wrap. Because the initial claim is read-only, this work is owed when
writes are enabled, not before.

**Why these five.** Core §11.3 states the property that must hold — "reconnect
shall not replay an unacknowledged write" — and Core §1.1 O10 adds that a lost
connection "queues nothing and resumes cleanly rather than replaying stale
actions". Those two sentences define exactly which boundaries matter. "Every
boundary" was the spike's wording, not Core's requirement.

### D5 — Redundancy out of scope, consequence accepted explicitly

**Decision.** One supervised gateway instance per PLC, matching TC3. Redundancy
is out of scope for the initial claim. The availability consequence is accepted
in writing rather than omitted: a gateway restart removes the operator interface
*including diagnostics* until it returns, while the machine keeps running,
releases hold and safety is untouched.

**Why.** Nothing in Core requires redundancy, and AB §11.2 already forbids two
independently configured writers. A deployment that needs redundancy must first
supply the single-writer lease/failover design that clause demands — which is a
real design task, not a configuration flag.

---

## What remains owed

These decisions narrow both spikes; they do not close either.

**S8 still owes evidence** of the chosen configuration: either a demonstrated
CIP Security setup on a v37-or-above capable controller, or the documented zone,
conduit and declared Security Level for a legacy deployment, plus an audit of
the generated allow-list.

**S9 still owes** the coherence-token behaviour, the declared freshness and poll
budget for a reference station, reconnect discovery, quality codes, timestamp
mapping, and the AB adapter passing the shared repository contract suite. The
mailbox matrix and the five crash boundaries are owed only when writes are
enabled.

Neither spike's decisions authorize implementation. R4–R6 remain open.

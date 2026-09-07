# Fraktal/AB R6 — security readiness gate

**Gate:** R6 security — the controller zone/conduit, writable-tag allow-list,
gateway identity/TLS/role model, secret handling, and update lifecycle

**Result:** **PASS for the declared read-only initial claim on the named v33
bench.** Every element R6 names now exists as a decided, recorded artifact
rather than an intention: the zone/conduit layout and its declared Security
Level, an allow-list audit that has actually been run against the two fixtures
this binding downloads, the three-state client identity model with the
transport's weakness stated in writing, secret handling inherited unchanged
from Core, and an update lifecycle that is a reproducible regeneration gate
plus a recorded rollback path. **This gate does not claim CIP Security, and it
does not clear writes.** Both are named below as what would have to be proved
before either is claimed.

**Date:** 2026-09-06

**Repository revision at start:** `b74602c`

**Scope:** assembly and audit of existing artifacts, plus two offline allow-list
audits. No controller-changing operation occurred for this record. No
activation identifier, credential, licence key, controller key or secret value
is recorded here.

## 1. What R6 asks, and what answers it

R6 is one row in the readiness table: "S8 records the controller zone/conduit,
writable-tag allow-list, gateway identity/TLS/role model, secret handling, and
update lifecycle." Five elements. Each is answered below by an artifact that
already exists and has been exercised, not by a promise.

| Element | Answer | Where |
|---|---|---|
| Controller zone/conduit | zones `Z-CTRL` / `Z-ENG`, conduits `C-EIP` / `C-ENG`, declared **SL-T 1 / SL-C 0** | [`AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md`](AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md) |
| Writable-tag allow-list | audit tool exists **and was run** against both downloaded fixtures; both conform | §3 below, [`fraktal_ab_access_audit.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_access_audit.py) |
| Gateway identity / TLS / roles | three-state client identity model; read-only initial claim with no write root | §4 below, AB §11.2.1, decision record D3 |
| Secret handling | Core §14.2/§14.3 inherited unchanged; no literals, no logging, change-managed rotation | §5 below, decision record D4 |
| Update lifecycle | reproducible regeneration gate (R4) plus a recorded rollback path | §6 below |

## 2. The posture, stated plainly

The Phase 0 controller is a `1769-L24ER-QB1B` at firmware `33.014`. It
implements **none** of CIP Security objects `0x5D`/`0x5E`/`0x5F` — that is
measured, not assumed ([`AB_S8_SECURITY_EVIDENCE.md`](AB_S8_SECURITY_EVIDENCE.md)).
So the recommended posture, CIP Security on v37 or above, is **not available on
this hardware**, and the legacy zone-and-conduit posture applies.

That posture is supported but it is explicitly the weaker one. **The network is
the control**, the CIP transport itself is unauthenticated, and the declared
Security Level is **SL-T 1 with SL-C 0** — with SL 2 recorded as *unreachable
on this controller family*, rather than as an exception someone signed off. A
gate that recorded "security: PASS" without that sentence would be recording
the opposite of the truth.

**The initial claim is read-only**, which is what makes the posture
proportionate rather than merely tolerated: Core §11.2 attaches the
authentication obligation to command-capable transports, and there is no write
root configured. What R6 passes is therefore a *bounded* claim, and §7 records
exactly what re-arms the full obligation.

## 3. The writable-tag allow-list, audited rather than asserted

AB §11.2.1 requires the controller-side allow-list to be **generated and
audited**: public data read-only, root mailboxes read/write, everything else
`None`. The audit is fail-closed by construction — a tag the caller does not
classify is not given the benefit of the doubt, it must be `None`, because an
unclassified readable tag is exactly the surface the allow-list exists to
remove.

It has now been run against **both** projects this binding has actually
downloaded to the bench:

| Project | Tags audited | Findings | Verdict |
|---|---:|---:|---|
| S16 command-handshake fixture | 11 | 0 | `Conforms: true` |
| R5 disposable reference suite | 16 | 0 | `Conforms: true` |

In both, the Add-On Instruction instance tags (`FRK_S16_AxisInst`,
`FRK_S16_ModeInst`, `FRK_Ref_ModuleInstA/B`, `FRK_Ref_ModeInst`) carry
External Access `None` and are classed unclassified — they are private
instance storage and the audit confirms none of it is reachable from the wire.
The evidence counters are `Read Only`. The command tags are `Read/Write`.

**One honest gap this audit exposes, recorded rather than smoothed over.** Both
fixtures declare their context UDT tag (`FRK_S16_Ctx`, `FRK_Ref_CtxA/B`) as
`Read/Write`, so the audit can only pass them in the **mailbox** class. A
production allow-list would want the context as `Read Only` public data with
writes confined to the declared command tags. That is a property of these
disposable fixtures, not of the rule, and it is why §7 still owes the audit
against a generated *production* L5X. Passing it in the mailbox class here is
accurate about what the fixture declares; it is not a claim that a production
context may be writable.

## 4. Gateway identity, TLS and roles

Client identity follows TC3's two-state rule with the read-only claim inserted
as an explicit third, weaker state (decision record D3):

| State | Client authentication | Permitted |
|---|---|---|
| Commissioning | anonymous permitted | controlled, time-bounded, recorded activity only |
| **Read-only production — the current claim** | anonymous permitted on a declared isolated conduit | reads and diagnostics; **no write root configured** |
| Write-enabled production | authenticated principals, least-privilege roles | operator / maintenance / engineering |

Two properties matter more than the table:

1. **Roles restrict but never decide.** The PLC remains the access authority, so
   a gateway role can only narrow what the controller would already have
   permitted. A role model that could *widen* access would be a defect.
2. **Engineering access is a separate conduit** (D5). Studio 5000 access stays
   off the gateway conduit entirely — the Phase 0 path is USB at
   `Backplane\16`, which satisfies Core §14.1's requirement that the
   engineering conduit not be permanently open on the production network. The
   gateway conduit carries the repository protocol and nothing else, and is
   **never** a path to download, online edit or firmware. Every download in
   this project's evidence, including the S16 and reference-suite downloads,
   went over that separate USB conduit under explicit authorization.

**TLS is not claimed on the controller leg and cannot be.** Plain CIP explicit
messaging provides no authenticated or encrypted session, and this controller
implements no CIP Security object. TLS therefore belongs to the gateway's
northbound interface, where the repository protocol is served; it is not a
property of the `C-EIP` conduit. Saying otherwise would misdescribe the
measured hardware.

## 5. Secret handling

Inherited from Core §14.2/§14.3 unchanged, as TC3 does (decision record D4):
endpoints, credentials and keys are configuration or secret-store values, never
literals in generated code, L5X, customization exports or version control, and
never logged. Rotation is change-managed under Core §13/§14.3 with a named
owner; the audit log records privileged actions without credential values.

This is observed in practice by this repository, not merely restated: the
access runbook forbids committing ACD files, uploaded PLC source, tag values,
screenshots containing application logic, activation details or credentials;
every probe in the toolchain reports values as shape and status with
`values_redacted: true`; and the workstation records deliberately omit the
activation host-lock identifier and all key material while still recording
which feature was absent.

## 6. Update lifecycle

The lifecycle R6 asks for has two halves, and both now exist as artifacts.

**Regeneration.** `fraktal_ab_phase0_gate.py` regenerates every fixture from a
seed the SDK creates, imports each through the SDK with a gated log, exports and
re-imports and re-exports each requiring canonical equality, runs a
generated-versus-exported construct census, and — with `--verify` — puts each
project through Studio v33 **Verify Controller**. It runs from a clean checkout.
That is the update path: a change is made in the generator, and the whole set is
regenerated and re-verified rather than edited in place. Evidence:
[`AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md`](AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md).

**Rollback.** Every download in this project's evidence records the artifact
hash, the exact target identity checked immediately beforehand, and the path
back. The S9 coherence fixture's rollback path is recorded in
[`AB_S9_COHERENCE_EVIDENCE.md`](AB_S9_COHERENCE_EVIDENCE.md) and was
deliberately preserved, not executed, across the S16 download; the S16
fixture's own downloaded artifact is hash-identified and reproducible from the
gate. Rollback here means *regenerate the previous fixture from its generator
and download it under fresh authorization* — not restoring a saved binary of
unknown provenance.

**Downloads are never automatic.** No part of this toolchain can download. The
gate performs no online operation, the Studio Verify script performs no online
operation and refuses a project inside the repository, and every executor's
write surface is a fixed list of `FRK_*` fixture tags with a serial guard, a
fixture fingerprint and an explicit arm flag. A download is a human act under
current explicit authorization, with the target identity re-read immediately
before it.

## 7. What R6 does not claim, and what would change it

1. **CIP Security is not claimed.** It is unavailable on this controller family
   and firmware, measured. A deployment that needs the recommended posture
   needs v37+ capable hardware and a demonstrated configuration.
2. **SL 2 is not claimed** and is recorded as unreachable on this family rather
   than as a signed exception.
3. **Writes are not cleared.** The claim is read-only with no write root. The
   moment a write root is configured the transport becomes command-capable and
   Core §14 applies without relaxation: authenticated principals,
   least-privilege roles, and anonymous write prohibited. Because that switch
   changes the obligations of the whole deployment, AB §11.2.1 requires the
   question to be asked explicitly per project and the answer recorded — it is
   not inherited silently.
4. **The allow-list audit against a generated production L5X is still owed.**
   §3 audited the two disposable fixtures, which is what exists to audit today;
   it also exposed that those fixtures declare their context `Read/Write`.
5. **The S9 mailbox matrix is owed when writes are enabled** — duplicate and
   out-of-order sequences, the five replay-capable crash boundaries, DINT wrap,
   secret clearing and PLC refusal. The initial claim being read-only is
   precisely why that work is not done yet, and precisely why enabling writes
   is not a configuration flip.

## 8. Status

| Item | State |
|---|---|
| Controller zone/conduit and Security Level | declared, recorded |
| Writable-tag allow-list | audited on both downloaded fixtures, `Conforms: true` |
| Gateway identity / roles | three-state model recorded; read-only claim active |
| Secret handling | Core §14.2/§14.3 inherited, observed in practice |
| Update lifecycle | regeneration gate plus recorded rollback path |
| **R6** | **PASS for the declared read-only claim on the named v33 bench** |

No conformance claim is made beyond that bounded scope. Enabling writes, or
claiming the recommended CIP Security posture, reopens this gate.

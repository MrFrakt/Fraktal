# Fraktal/AB S8 — Security posture evidence (partial)

**Spike:** S8 endpoint and conduit security

**Result:** **OPEN — the posture is decided and two of its inputs are now
measured rather than assumed: the Phase 0 controller has no CIP Security
capability at all, and the allow-list audit AB §11.2.1 requires now exists and
runs. The chosen configuration itself is still unproven, and the recommended
v37+ posture cannot be tested on available hardware.**

**Date:** 2026-08-14

## 1. Scope of this record

AB §11.2.1 settles the *posture*: CIP Security on firmware v37 or above is
recommended, the IEC 62443 zone-and-conduit arrangement is the supported legacy
posture, and the initial claim is read-only with writes switched on at the
gateway. The reasoning is in
[`AB_S8_S9_DECISION_RECORD.md`](AB_S8_S9_DECISION_RECORD.md).

Deciding a posture is not evidence that it was implemented. This document
records what could be established on the available v33 hardware.

## 2. The Phase 0 controller has no CIP Security capability

Previously this was an inference from product literature. It is now a
measurement.

[`fraktal_ab_security_probe.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_security_probe.py)
issues `Get_Attribute_Single` against exactly the three CIP Security object
classes and nothing else. It exposes no arbitrary class, instance, attribute or
service input, has no write path, and does not attempt to configure, enable or
negotiate anything — it asks whether the objects exist.

Against `1769-L24ER-QB1B/A`, firmware `33.014`, serial `7036B510`:

| CIP object | Class | Status | Meaning |
|---|---|---|---|
| CIP Security | `0x5D` | `0x05` | path destination unknown — class not implemented |
| EtherNet/IP Security | `0x5E` | `0x05` | path destination unknown — class not implemented |
| Certificate Management | `0x5F` | `0x05` | path destination unknown — class not implemented |

The controller answers the session and refuses all three classes, so this is a
positive absence rather than a timeout: the device is reachable and states that
the objects are not there.

**Consequence.** The recommended posture is unavailable on this hardware. Any
deployment on this controller family runs the **legacy zone-and-conduit
posture**, where the network is the control, and must declare that in the
binding record together with its target Security Level (Core §14.1). This is
also why the recommended baseline moved to v37+: it is the first baseline where
the recommended posture exists at all.

## 3. The allow-list audit now exists and runs

AB §11.2.1 requires the controller-side allow-list to be "generated and
audited". Generation belongs to a future generator; the audit is available now,
and building it first means "audited" cannot quietly mean "someone looked".

[`fraktal_ab_access_audit.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_access_audit.py)
reads an offline L5X — it never contacts a controller — and judges every
controller tag against exactly one class: declared **mailbox** shall be
`Read/Write`, declared **public** shall be `Read Only`, and **everything else
shall be `None`**.

The rule is applied fail-closed in two ways that matter:

- **Nothing is inferred from a name.** A tag the caller did not classify is not
  given the benefit of the doubt; it must be `None`. An incomplete invocation
  therefore fails loudly instead of silently approving a project.
- **An omitted `ExternalAccess` is not treated as `None`.** Studio writes its
  own default on export, so an absent attribute is an unproven write surface.

### Demonstrated against the S7 manifest fixture

Auditing the S7 manifest fixture with its manifest tables declared public:

| | |
|---|---|
| Tags audited | 13 |
| Conforming | 12 |
| Reported write surface | `FRK_S7_BumpRevision` |
| Verdict | **does not conform** |

That result is correct and is the point of running it. `FRK_S7_BumpRevision` is
the spike's own revision-bump input; it is a genuine write surface that a
production manifest would not contain. The audit flagging a Phase 0 fixture as
non-conforming is evidence the tool is not vacuous — a spike fixture is not a
production artifact, and the gate says so rather than waving it through.

## 4. What S8 still owes

- **The recommended posture is untested.** No CIP Security configuration has
  been demonstrated, because no capable controller is available. This is
  deferred until v37+ hardware exists; it is a hardware dependency, not an
  analysis gap.
- **The legacy posture is not yet documented for a real deployment.** The zone
  definition, the conduit list with protocol/direction/policy per Core §14.1,
  and the declared target Security Level are project artifacts that do not yet
  exist for any Fraktal/AB station.
- **The audit has no production project to run against.** It has been proved
  against a Phase 0 fixture only. The generated allow-list it is meant to police
  will not exist until the generator does.
- **Client authentication, roles, rate limiting and audit logging are unbuilt.**
  They are owed only when a write root is configured (AB §11.2.1), and the
  initial claim is read-only.
- **Engineering-conduit separation is satisfied in practice but not documented.**
  Phase 0 uses USB at `Backplane\16`, which meets Core §14.1's requirement that
  the engineering conduit not be permanently open on the production network;
  the open Ethernet-engineering question would formalise it either way.

## 5. Commands

```powershell
# read-only capability probe; fixed classes, no write path
python fraktal_ab_security_probe.py 192.168.100.89 --expect-serial 7036B510

# offline allow-list audit
python fraktal_ab_access_audit.py <project.L5X> `
    --public FRK_Manifest --mailbox FRK_RootMailbox
```

No controller-changing operation was performed for this record. The probe is
read-only and the audit never opens a connection.

# Supplementary S0 session — prepared, not authorized

Local Echo only: 127.0.0.1 slot 0, serial 601FC87B, Emulate 5580 product 288,
firmware 38.11, keyswitch Remote. A fault clear is a separate authorization.
The service and listener process, exact identity, fault status and keyswitch
are checked by `scripts/guard_echo.py`. No service configuration is changed.

Prepared artifact `s0_probe.ACD`, SHA-256:
`A468BA121687AF6C1502B04936EE4A347B7525A4430809E58B972A2BF5B88A25`.
Generated source SHA-256:
`796A56D6CEA3191A34967B3AD7A26351620D634D02D27E3CA488912ABAAB0669`.

Review `capacity_review.ACD` in Studio, preserving the pinned `s0_probe.ACD`.
The review copy initially has the same SHA-256. Obtain the owner's Capacity
Estimate Data/Logic and I/O used/capacity and explicit fit confirmation. Disk
file size, source counts and declared tag bytes are not a Capacity Estimate.

Only after the owner explicitly authorizes this session, record the answer in
new `authorization.json` using the template and exact ACD hash; also record the
reported Capacity result in new `capacity_review.json`. Templates are proposals,
not approvals. The executable refuses downloads without both recorded gates.

Preflight was recorded once in `preflight.json`. Do not overwrite it. The SDK
session verifies it before backup/deploy and refuses a logged-in HMI or changed
documents/policy. If it differs, stop and prepare a fresh session; retain this
evidence. Every run below needs a new log/output name and SDK log audit.

From the repository root, `$S0S` denotes this work folder:

```powershell
$S0S = 'C:/work/fraktal-ab-s0-supplementary-20261020/prepare_da41a9b11aad4d10938044fdcdcb4005'
& "$S0S/session/bin/Debug/net8.0/win-x86/S0Session.exe" backup
& "$S0S/session/bin/Debug/net8.0/win-x86/S0Session.exe" deploy-probe
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s0_supplementary_measure.py --expect-serial 601FC87B --output <new-measurement.json.gz>
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s0_supplementary_access.py --expect-serial 601FC87B --execute-fixture --output <new-access.json>
& "$S0S/session/bin/Debug/net8.0/win-x86/S0Session.exe" restore-genealogy
$env:FRAKTAL_AB_DECLARATION = 'fraktal_ab_genealogy_demo'
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_genealogy_execute.py --execute-fixture --expect-serial 601FC87B --credential-file C:/work/fraktal_echo38_access_fixture.json --output <new-regressions.json>
```

Audit backup `Save As` (SDK upload is named `Open Project From Controller`),
and successful deploy/restore operations with `fraktal_ab_sdk_log_gate.audit_log`.
Measurement is read-only. The access vector attempts DINT writes only to:

- `FRK_S0S_AccessRO.Readback`
- `FRK_S0S_AccessRO.HmiRequest`
- `FRK_S0S_AccessRW.Readback`
- `FRK_S0S_AccessRW.HmiRequest`

No application consumes these inert values. Every changed value is restored in
`finally`, including a successful write whose response was lost. RO-parent /
RW-child behavior is a finding. No arbitrary tag/value/host option exists.
The vector performs at most four stimulus and four restoration writes.

Once deployment has been attempted, restore genealogy even if a measurement
fails. Restore uses a newly created copy checked against immutable original
`genealogy_current.ACD`, SHA-256
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
The original is never opened through the SDK. A matching deployment-attempt
record permits rollback after an interrupted download; identity/fault/mode
guards still apply. Existing exports and evidence cannot be overwritten.

After the five-document restore and 31 regressions, repeat read-only final
checks: Run, not faulted, advancing scan, MANUAL/idle, logged out, not restoring,
original policy/inputs, and all five saved documents equal live. Preserve every
failure and raw capture. Never archive credentials.

Only runtime measurements settle native fragmentation, effective access and
LREAL precision. The largest **single UDT** accepted offline is 2 MiB; the
controlled 2 MiB + 4-byte import is rejected. This is not a global array-tag
limit, runtime fit, physical-controller or CIP Security acceptance.

# Fraktal/AB S12 v38 preflight - SDK licence blocker

**Status:** **BLOCKED - the v38 processor catalogue is visible, but licensed
SDK project operations fail before a seed can be created**

**Date:** 2026-08-26

**Repository revision at start:**
`355c6f1ef7e3b4436739054fb3f624f93ad4eb99`

## 1. Purpose and boundary

The v38 handoff required two ordered checks:

1. reproduce the complete v33 Phase 0 regeneration gate without silently
   changing its baseline; then
2. if that remains green, create an offline v38 project for a 5380/5580 family
   and rerun the S12 declaration/use matrix.

The SDK and Studio operations in this record were offline. The end-of-session
controls used only the fixed read-only EtherNet/IP identity probe and FactoryTalk
Linx browse. No download, mode change, tag write, fault clear, clock set,
firmware operation, network configuration, safety operation or SD-card
operation occurred.

## 2. Installed toolchain

| Item | Observed value | SHA-256 |
|---|---|---|
| Studio v33 | `V33.00.00` | `B1ADC6962DC04863FFD032D3721791B1FD4E7643A6E95AE8A091503001EDE41F` |
| Studio v38 | `V38.02.00` | `04BCD760E23435F6708BA131D502418BD064FB83D6458F2E56100E1A38A8209B` |
| SDK service | `LdSdkServer.exe` `2.2.1109.0`, service `Running` / `Automatic` | `AB0CD1C59F85241789ACAB57F0F94A0ADD16267C299C7CBF734B73910CB41170` |
| C# client package | `RockwellAutomation.LogixDesigner.CSClient.2.2.1109.nupkg` | `BE450699732D7C23DD3C5CA14C954071D64A752A5F5C9FE550CD788111644D25` |
| FactoryTalk Linx CLI | `6.60.00`, file version `6,60,00,213` | `996E50AB125CA175473033785C97FC74319DA4076866C3663785A1BD9FA1B785` |
| .NET SDK | `10.0.400`; `net10.0/win-x86` build target | n/a |
| rebuilt repository probe | client `2.2.1109`, `net10.0/win-x86` | `9362843C2934CFD7ED003ACC03148F2377475D4287A1B96BBE65ADA0CB525086` |

The current Rockwell example and the repository probe both build successfully
for `win-x86`. This settles only client compilation and architecture; it does
not prove an SDK project operation is licensed.

## 3. Processor enumeration control

The installed SDK 2.02 C# example called `GetProcessorTypesAsync` successfully:

| Revision | Exit | Processor rows | Required observations |
|---|---:|---:|---|
| 33 | 0 | 93 | `1769-L24ER-QB1B` remains present |
| 38 | 0 | 106 | `1769-L24ER-QB1B` remains present; 5380/5580 candidate families are listed |

The v38 result includes `5069-L310ER` and `1756-L81E`, so the catalogue contains
the class of target the proposed offline S12 rerun needs. Enumeration is not a
CIP Security capability proof and says nothing about `TIME`, `LREAL`, `LINT`
arithmetic or UDT layout.

## 4. Required v33 regression result

The exact required command was run:

```powershell
python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_phase0_gate.py
```

It stopped at stage 1, before producing `seed_v33.ACD`:

```text
ERROR [phase0-gate] offline probe failed (3762504530)
OperationFailedException: No valid license.
```

The initial repository binary used the historical client `2.0.861`. To exclude
a client/service version mismatch, the probe was then rebuilt against the
installed `2.2.1109` client as `net10.0/win-x86`. The unchanged v33 gate and a
direct `CreateNewProjectAsync(33, '1769-L24ER-QB1B', ...)` call returned the
same `No valid license` result. No seed or project file was created by either
attempt.

This is not a v33 controller-family rejection: `GetProcessorTypesAsync(33)`
still lists the controller. It is not evidence that Studio v33 is broken,
either. The repository's offline Studio wrapper opened the preserved
upload-derived ACD, ran **Verify Controller** at v33, reported `0 errors` and
`0 warnings`, left SHA-256
`B3A1291ACDBFBD1A84C95354D550FB9A6FC6E908D766789508F8EFB2B83C8B60`
unchanged, and closed Studio cleanly.

The blocking boundary is therefore the SDK entitlement required for project
creation/import, not Studio v33 availability or the 32-bit client build.

### 4.1 Activation diagnosis

FactoryTalk Activation `5.02.00.0052` is installed and its service is running.
The following read-only checks narrowed the generic client exception to a
missing feature rather than a service or client failure:

- the FactoryTalk Diagnostics event is raised under the SDK service account
  (`LOCAL SERVICE`) and says the seven-day grace period has expired and that
  activation of `LDSDK.EXE` was unsuccessful;
- the local FlexNet server log records the corresponding `LDSDK.EXE` checkout
  as `UNSUPPORTED` with `No such feature exists`;
- the activation directory contains no issued `LDSDK.EXE` feature; all local
  text matches are rejection-log entries; and
- Rockwell's installed SDK 2.02 system requirements state that Logix Designer
  SDK requires a Professional Edition licence or toolkit to activate.

`FTACmdUtility version` completed successfully. Its read-only `searchpath -g`
and `listAvailable -e` commands returned code `30` (`Current user not allowed`)
from the non-elevated session. No elevation was attempted, no activation search
path was changed, and no activation was obtained, borrowed, returned, renewed,
rehosted or imported.

The supported recovery is therefore to make a valid Professional Edition or
toolkit entitlement that includes `LDSDK.EXE` available to this workstation,
then rerun the v33 regression. Reinstalling SDK binaries or restarting the
already-running services cannot create the absent licensed feature.

## 5. Decision and next executable step

The regression rule forbids silently accepting a changed SDK baseline while
the v33 gate is red. No v38 seed was created, the S12 matrix was not generated
or imported, and `AB_FROZEN_CONTRACTS_V1.json` was not changed.

After the Logix Designer SDK licence/entitlement is restored:

1. rebuild the repository probe against client `2.2.1109` for `win-x86`;
2. rerun the exact v33 Phase 0 gate and require every stage green;
3. enumerate revision 38 again and select the declared 5380/5580 baseline;
4. create the v38 seed, generate every S12 declaration/use case, SDK-import
   each, and Studio-Verify every imported case; and
5. add a second baseline to the frozen contract only if the verified answers
   differ. Never replace the 5370/v33 entry.

## 6. What this record does not settle

- It does not establish any v38 type-map result.
- It does not prove CIP Security on any enumerated family.
- It does not test SDK 2.02 `BuildAsync` or whether it still accepts the known
  invalid ST body.
- It does not authorize a recommended-baseline change in Part III.
- It does not close S12 for a second family, S15, or any readiness gate.

## 7. End-of-session read controls

After Studio closed, no `LogixDesigner` process remained. Three fixed
EtherNet/IP identity samples matched `1769-L24ER-QB1B/A`, firmware `33.014`,
serial `7036B510`, and endpoint `192.168.100.89:44818`; the fixture continued
to report PTP disabled and unsynchronized. FactoryTalk Linx 6.60 then reported
`Browse Fraktal_AB\192.168.100.89 successfully`.

Controller-changing categories for this session: **none**.

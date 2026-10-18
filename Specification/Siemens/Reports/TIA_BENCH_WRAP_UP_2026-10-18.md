# Siemens bench and HMI wrap-up (2026-10-18)

The separate FraktalBench simulator exchanges ordinary I/O with the physical
1214C. The final bridge/topology work is on main in `bbfc534ca`; the shared HMI
Disconnect action is on main in `1a7561ab4`. The full TIA port and physical
bench acceptance remain incomplete.

## Operator connection and observed state

| Target | Address / role | October 18 observation |
|---|---|---|
| FraktalBench, CPU 1516 | X1 `192.168.0.20`; HMI/engineering X2 `169.254.212.61` | RUN; three topology nodes operational; bridge connected |
| Physical 1214C | `192.168.0.10`; ordinary I/O companion | LinkHealthy TRUE; OutputsEnabled FALSE |
| Original Fraktal, CPU 1516 | `169.254.212.49` and `192.168.1.1`; separate saved image | RUN; all three topology nodes offline, without a physical bridge |

The user confirmed that the offline HMI tree was connected to the original
Fraktal at `.49`. The bench SDK observation at approximately 04:18Z recorded
450,554 accepted frames, zero rejected frames and a healthy link. A new strict
generic HMI repository test against `.61` passed with three operational nodes,
14 fresh inputs and 10 output channels whose quality remained FALSE. This was
an endpoint mismatch, not evidence that the working bridge had disconnected.

After restarting the updated HMI, an ADMIN can use **Settings > Station >
Disconnect**, then connect to **`s7web://169.254.212.61`**. This uses the existing
connection owner to dispose the old repository and open the prefilled wizard.
The HMI stays disconnected while that wizard is open until Connect is pressed;
normal saved-connection behavior at the next application startup is unchanged.
Preferences and existing Unit-assignment validation are preserved. The feature
is shared by all HMI transports. No equipment command is sent by Disconnect.

The button change passed 21 focused widget/localization/connection tests,
Flutter analysis and a Windows debug build. The new regression checks disposal,
no automatic retry while in setup, a different endpoint and preference retention.
The user subsequently reported that it seems fine; this does not add a separate
visual UI or electrical/motion acceptance claim.

## Certificate reference

The live HTTPS leaf certificate at `169.254.212.61` was re-read on October 18
and matched the saved SHA-256 pin:

```text
1abd979172a7c7884e961f3c95e386f59f68b23f3edc59f8cda26b2243bd1867
```

In TIA V20, identify the assigned certificate under **CPU Properties > General >
Web server > Security**, then export that certificate from **Protection &
Security > Certificate manager > Export certificate**, choosing DER format.
Hash the DER file, for example:

```powershell
certutil -hashfile "C:\path\WebServer.der" SHA256
```

The Windows Thumbprint field may show SHA-1. The certificate's signature
algorithm is also separate from its SHA-256 fingerprint. Use the Web server
leaf certificate for this HMI pin. Renewal or replacement requires a newly
verified value. Siemens documents the [Web server assignment](https://docs.tia.siemens.cloud/r/en-us/v20/functional-description-of-s7-1500-cpus-s7-1500/setting-the-operating-behavior-s7-1500/protection-security-s7-1500/certificate-manager-s7-1500/certificates-for-the-web-server-s7-1500)
and [certificate export](https://docs.tia.siemens.cloud/r/en-us/v20/functional-description-of-s7-1500-cpus-s7-1500/setting-the-operating-behavior-s7-1500/protection-security-s7-1500/certificate-manager-s7-1500/exporting-certificates-s7-1500).

## SiemensAgent and cross-binding draft

Updated these authoritative local SiemensAgent notes:

- `siemens-kb/tia-automation/press-bench-network-and-topology.md`: final targets,
  transport scope, owner actions complete, endpoint diagnosis, Disconnect,
  certificate workflow and remaining acceptance limits.
- `siemens-kb/tia-automation/INDEX.md`: discovery entry for those lessons.
- `siemens-kb/tia-automation/capabilities.md`: measured operator follow-up and
  boundary between completed work and proposed ports.

The derived `C:\Projects\SiemensAgent\data\siemens.db` was reindexed after an
online SQLite backup. All 44 curated documents validate; three changed; integrity
is `ok`; project, block, symbol, cross-reference, I/O-map and general-knowledge
table counts were preserved. That local SiemensAgent directory is not a Git
repository. The [versioned knowledge snapshot](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_BENCH_WRAP_UP_2026-10-18/packaging.json)
therefore records the three changed notes and index verification in Fraktal.
SQLite files, credentials, private keys, saved projects and simulator storage
are excluded.

The snapshot has five payloads plus its checksum manifest: six files,
44,337 bytes. `SHA256SUMS.txt` has SHA-256
`c4da137e3994e9f9514889f39ec5c7e307ba60b99e17b7f7df02570f61ccf04c`.
This snapshot records knowledge maintenance, not another PLC runtime gate.

The [cross-binding lessons draft](../../Reports/TIA_BENCH_CROSS_BINDING_LESSONS_2026-10-18.md)
separates already-shared HMI work from selective TC3/AB follow-ups: active target
identity, channel validity provenance, consumed publication size, sibling topology
discovery, outage acceptance and transport/certificate commissioning. It includes
candidate wording for review. No normative specification or TC3/AB PLC source
was changed by this wrap-up.

## Remaining boundaries

Physical output gates remain FALSE; Q1.0/Q1.1 remain hard FALSE. The bridge
publishes local output demands without remote applied-output feedback, so DQ
quality remains FALSE even with healthy communications. Ordinary E-stop/button
mirrors do not establish a validated safety result.

P8 native PROFINET health/forcing, applied-output feedback, electrical mapping,
withdrawal timing and physical motion/SAT remain open. Other TIA roadmap phases
also remain open; this ordinary I/O bridge is not P12 cross-controller Line
transport. The [remaining-features plan](TIA_REMAINING_FEATURES_PLAN_2026-10-15.md)
remains the phase authority. The [October 17 report](../Evidence/TIA_PRESS_BENCH_TOPOLOGY_2026-10-17.md)
retains the native compile/read-back, deployment, stability and recovery results;
its evidence was not rewritten for this wrap-up.

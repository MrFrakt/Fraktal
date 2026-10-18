# Echo local-carrier download and idle runtime — 2026-10-18

Append-only, non-normative evidence for the owner's current authorization:
"logix echo is back online, you can download", followed by explicit
"Clear the fault and download". The additional question followed AGENTS.md
§3a because the controller was already faulted. This authorization is historical
after this session and does not authorize future controller changes.

The [payload manifest](AB_ECHO_LOCAL_CARRIER_DOWNLOAD_2026-10-18/manifest.json)
binds the exact logs, preflight, SDK helpers and read-only acceptance results.
No framework or generator code changed during this deployment. The source and
previous full regression/compile evidence remain
[AB_LOCAL_CARRIER_2026-10-18](AB_LOCAL_CARRIER_2026-10-18.md).

## Exact target and artifact

- Local FactoryTalk Logix Echo **1756-L81E / ControlLogix 5580 emulator**,
  firmware **38.011**, address **127.0.0.1:44818**, slot **0**.
- CIP serial **601FC87B**, Echo GUID **91dec7d6-8ac3-45c9-ab2e-0d039c7006fd**,
  controller **FraktalPhase0**, chassis **FraktalPhase0Chassis**.
- CIP identity/product/firmware/serial and the local Echo listener process were
  checked before every controller-changing operation. Echo's public SDK also
  checked GUID/serial/loopback address before virtual keyswitch updates.
- Declaration **fraktal_ab_part_demo**, including all three AUTO renditions,
  local BY_POSITION provider, four result slots, two measurement definitions,
  16-event host ring and deliberately fictitious fixture nameplate. No physical
  I/O is declared; task output updates remain disabled.
- Regenerated L5X SHA-256:
  `49C6C33EC270ABC5798B41231F8046527A755A3C5FD91AD99013F4C1CE07A263`,
  identical to the previously accepted source. Manifest major **5**, content hash
  **75A1C353B12DF14F**.

## Preparation and recovery

The old controller was communicating but already faulted; its scan counter stayed
at **35902**. The old published fault flags were zero and stale, so those values
were not treated as evidence that the controller was healthy. The SDK positively
reported Faulted and Remote keyswitch. A full SDK upload was saved before changes:

`C:/work/fraktal-echo-deploy-20261018/echo_before.ACD`

SHA-256 `883C95ECA946AA2E30F3466F44292BAC56851EDFF1B99417E86E70C4BEA0A04B`.
Its companion L5X is retained there too. These backup payloads remain local and
are not copied into the repository evidence. The original fault cause was not
established; the uploaded code/data and observed fault state were preserved.

The candidate L5X imported with **zero warnings/errors**, converted into a fresh
ACD and compiled successfully for EchoController. ACD read-back matched the
source construct/settings inventory, 21-step SFC graph, **41 executable bodies**
and **20,339 authored initial values**. Prepared ACD SHA-256:
`0B2D3E4212AD32733C660B8787F065C2958B22F9C117D08362A48F1B40902565`.

The initial SDK Program-mode request was rejected with
`RxE_CONTROLLER_FAULTED`; no download occurred in that attempt. After the owner's
additional authorization, Echo's public API client **4.0.1437** operated the
virtual keyswitch. The Program/Remote/Program/Remote route left the fault latched;
Program/Run/Program/Remote then cleared it. The final SDK state confirmed
IsFaulted=false and the keyswitch was restored to Remote. Rockwell documents
keyswitch clearing in [v38 Clear faults](https://www.rockwellautomation.com/en-pr/docs/studio-5000-logix-designer/38-00/contents-ditamap/studio-5000-logix-designer/controller-properties/clear-faults.html)
and the Program/Run/Program route in
[Common Procedures PM001](https://support.rockwellautomation.com/ci/fattach/get/155681/0/filename/1756-PM001C-EN-P.pdf).
The logged sequence and observed result, rather than the documentation alone,
are the acceptance evidence for this Echo instance.

The existing Logix Designer SDK **2.1.974** then downloaded the prepared ACD,
saved the correlated project and entered **Run**. SDK Download, Save and Change
Controller Mode succeeded. The correlated ACD after download is:

`C:/work/fraktal-echo-deploy-20261018/part_traceability.ACD`

SHA-256 `5333A1DAAC05F70EEFD017DB25275619AC0321D61B507A4BE4CB601D610A3C3B`.
The SDK's correlated local post-download L5X still matches the same 41 bodies
and 20,339 authored values. This is not a second full upload from the controller.

## Read-only runtime acceptance

After download, serial-guarded CIP reads against the selected declaration proved:

| Check | Observed result |
|---|---|
| Controller | SDK Run; Echo IsFaulted=false; keyswitch Remote |
| Task progression | scan counter **1850 → 1875** across 250 ms; later **8004** |
| Unit | Error=0, Running=0, ordering violations=0 |
| Native health | MajorFaultBits=0, MinorFaultBits=0 |
| Live manifest | major 5; exact declared content hash **75A1C353B12DF14F** |
| Part | schema 1, coherent even revision, Present=false |
| Host ring | physical schema 2, nonzero startup epoch, Failed=0 |
| Generic projection | **4193 nodes**, **7 modules**, Part/host/nameplate facets readable |

No operator mailbox commands, sensor injections or arbitrary tag writes were
performed. Idle acceptance does not execute the part lifecycle, ST/SFC/LD
production cycles, NOK/rework recovery, carrier failure, browser rendering,
retention or restart/durable-sink acceptance. Those remain separate runtime
gates; the earlier executable model results do not become live results here.

The gateway must select `FRAKTAL_AB_DECLARATION=fraktal_ab_part_demo` for this
image. The default carrier-off declaration has a different manifest. Gateway
configuration and HMI processes were not changed; the live Python projection
was selected in the read-only probe process. The direct-CIP HMI spike remains
major-4-only and cannot be used to claim support for this major-5 image.

The controller was left in Run with the Unit idle and no controller fault.
No production controller, firmware, network address or gateway write policy was
changed. One-off online helpers remain separate from the offline-only probe.

# TIA bench lessons for TwinCAT and Allen-Bradley (draft, 2026-10-18)

Follow-up: the [AB continuation](../AllenBradley/AB_TIA_FOLLOWUP_2026-10-18.md)
records the shared active-endpoint display and AB per-direction sample-validity
change. The [v38 native-feature audit](../AllenBradley/AB_V38_NATIVE_FEATURE_AUDIT_2026-10-18.md)
also carries forward TIA's native-reuse review. The original review below keeps
its proposal/acceptance boundary; these follow-ups do not close L1-L6 wholesale.

This is a non-normative review and proposed follow-up list. It does not change
Core, the bindings, released types or controller programs. The measured source
is the [Siemens bench report](../Siemens/Evidence/TIA_PRESS_BENCH_TOPOLOGY_2026-10-17.md)
and its immutable payload, committed in `bbfc534ca`. The shared HMI Disconnect
button is already committed in `1a7561ab4`; it applies to every transport through
the existing connection owner. No separate TC3 or AB disconnect implementation
is needed.

## What the bench exposed

Two running simulators published the same PressDemo identity. The original
Fraktal had an offline topology; the separate FraktalBench had a healthy link
to the physical 1214C. The operator was viewing the original endpoint. Reading
both controllers' topology and testing the normal HMI repository distinguished
this target mismatch from a transport defect. The user confirmed the old HMI
endpoint and requested an explicit way to disconnect and change it.

The connected bench also exposed three different facts: the bridge was healthy,
its input values were fresh, and physical output authority was disabled. Output
demands were available without feedback proving the physical applied output
image. Consequently its three nodes can be operational while DQ channel quality
remains FALSE. Making every indicator green would lose that distinction.

## Draft updates and acceptance criteria

| ID / priority | Proposed update | TwinCAT / Allen-Bradley treatment | Acceptance before claiming a port |
|---|---|---|---|
| L1 / first | Show the active endpoint and available controller identity in connection/settings UI; retain the new admin Disconnect action. | Shared HMI follow-up. TC3 identity should include the ADS NetId/port or OPC UA target; AB should distinguish the gateway URL from its controller/route and available CIP identity. Reuse existing adapter metadata rather than inventing another module identity. | Two controllers with identical root names remain distinguishable. Disconnect disposes the old session, cancels retries, and opens setup; a new endpoint is used only after Connect. Existing Unit assignment validation and credential isolation still apply. |
| L2 / first | Document each channel value's source and validity separately from link health and output authority. | TC3 already separates per-node bus state from Control On/safety. Review `FB_IoTopologyPublisher.M_SetNodeState`, which currently assigns all channel qualities from LinkOk, before adding a bridge with finer validity. AB `topology()` already distinguishes unread/faulted I/O and projects controller output words; document that source and do not treat it as electrical actuation feedback. These are review targets, not proven defects on the existing native buses. | With output authority disabled, valid input samples can remain Good. Link loss withdraws stale claims. A demand-only source is never presented as confirmed remote applied-output feedback. Preserve existing native bus semantics; introduce any necessary new contract additively and with versioning. |
| L3 / next | Measure discovery and cyclic publication against consumed nodes/channels. | TC3 currently allocates 64 nodes x 16 channels in released Core types, while static identity already uses the manifest. Measure the remaining browse/read surface before proposing a compatible profile. AB already emits declared modules/channels; preserve that behavior. Siemens's generated 3 x 14 shape is an example, not a replacement ABI. | Record allocation, discovered paths and active/inactive view read counts for small and larger stations. Unused capacity does not become recurring transport work. Do not shrink a released array or duplicate types per project without a compatibility design. |
| L4 / next | Retain standalone topology beside the Unit forest without exposing private siblings. | TC3 already publishes `GVL_PressFieldbus.Topology` through an instance marker. AB already emits a sibling `PressFieldbus/Topology`; its projection tests cover placement. The Siemens Web API discovery/read-tier fix is already in the shared client. Carry the regression scenario across adapters rather than copying the S7 browse algorithm. | Discover sibling topology, resolve channel-to-module links, enforce selected-root scope, and exclude raw I/O, references and force storage. Check both initial and refreshed reads with two roots. |
| L5 / next | Qualify outage/recovery through the same generic HMI and transport used by the operator. | Reuse shared repository assertions; supply TC3 ADS/OPC UA and AB gateway fixtures. Each binding owns its native reconnect and output-withdrawal rules. | Observe input freshness, missing/returned nodes and command availability through link loss and restoration. No command is queued or replayed. Communication recovery does not establish permission to resume motion. Preserve saved controller state and unrelated stations. |
| L6 / commissioning | Record transport roles, target guards, certificate source and the actual diagnostic evidence. | Keep Siemens's controller-initiated dual-stream workaround within the S7 endpoint. Do not transfer TSEND_C/TRCV_C, PLCSIM bindings or port constants into TC3/AB. For TC3 OPC UA or an HTTPS/WSS AB gateway, identify the correct service certificate; plain ADS/EtherNet/IP paths do not acquire an S7 Web API pin requirement. | A run names the deployed controller, route and service, then checks protocol state/counters and application freshness. Packet metadata is not presented as captured packet/drop evidence. Certificate renewal is an explicit trust update; certificate hash and signature algorithm are not conflated. |

L1's Disconnect portion is complete. Its active-target display is a proposal.
L2-L6 are targeted review/acceptance work, not automatic implementation tasks or
claims that the existing TC3/AB acceptance gates have regressed.

## Candidate wording for later specification review

These paragraphs are proposals only; reconcile them with Core section 10.5.1,
the HMI connection rules and each binding before adopting normative wording.

> Connection settings should expose the active transport endpoint and the
> available target identity. An authorized Disconnect action should close the
> current session and return to endpoint setup through the connection owner.
> It should not issue an equipment command or schedule an automatic reconnect.

> The adapter should identify whether an output value is a local demand, a
> controller process-image value or remote applied-output feedback. Node link
> state, channel validity and output permission should remain distinguishable.
> The meaning and provenance of Good quality should be documented per source.

> Discovery and cyclic reads should scale with the declared or consumed
> station surface. A smaller publication profile should preserve the binding's
> released schema and existing manifest/live split.

These mostly clarify existing O4/O9, quality and connection rules. Add a new
requirement only if the current normative text does not already cover it.

## Source locations for the follow-up

- Shared UI: [Settings](../../FraktalCore/HMI/lib/ui/settings_dialog.dart),
  [connection owner](../../FraktalCore/HMI/lib/ui/connection_bootstrap.dart),
  [disconnect regression](../../FraktalCore/HMI/test/settings_disconnect_test.dart).
- Shared transport: [Web API discovery](../../FraktalCore/HMI/packages/fraktal_opcua_client/lib/src/webapi_session_client.dart),
  [read tiers](../../FraktalCore/HMI/lib/data/opcua_field_tier.dart).
- TC3: [publisher](../../FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Connectivity/FB_IoTopologyPublisher.TcPOU),
  [topology type](../../FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs/ST_FieldbusTopology.TcDUT),
  [capacity constants](../../FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL),
  [published press instance](../../FraktalCore/PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo/01_PneumaticPress/Io/GVL_PressFieldbus.TcGVL).
- AB: [topology projection](../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_projection.py),
  [existing topology tests](../../FraktalCore/PLC/Allen-Bradley/tools/test_fraktal_ab_projection.py),
  [read-only identity probe](../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py).

No TC3/AB PLC source changed for this review. Their compiler/runtime acceptance
is required when an actual binding change is implemented, not inferred from
the Siemens observations.

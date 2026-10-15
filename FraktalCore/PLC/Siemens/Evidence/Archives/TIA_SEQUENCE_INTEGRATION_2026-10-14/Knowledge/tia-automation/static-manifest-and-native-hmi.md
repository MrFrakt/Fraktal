# Static manifest and native HMI - TIA V20 / Advanced7

Scope: Fraktal generator0.5, simulated1516-3 V3.0, FrkS12 TCPIP169.254.212.49,
Advanced7 with API5 compatibility library; native Web API Api.Version5,
process-data mask24 and the original certificate pin. **[measured]**

- Core-derived ST_ConfigPage/Entry compile without narrowing their fields. A
  shared FC pager clears all16 reused slots, counts the whole deterministic walk
  and copies only the requested window. Typed FC parameters supply the module
  tree; no stored object references or full manifest buffer are required.
  Two roots each serve246 entries in16 pages for12 module scopes. **[measured]**
- INT_TO_STRING/DINT_TO_STRING emit a leading `+`. Strip it from array indices
  before building canonical fragments such as Catalog/Catalog[6]/Label. Typed
  numeric ValueText may retain it: the unchanged HMI parser handles it.
  Native catalog hydration/command rendering passed. **[measured]**
- Catalog/CatalogCount can be ExternalAccessible/Visible/Writable=False while
  PLC typed FCs still read them. Native reads return200; root mailbox pages serve
  their values at the existing generic HMI paths. ConfigRev is read-only;
  attempted native mutation returns205. **[measured]**
- LDT_TO_ULINT(DTL_TO_LDT(RD_SYS_T output)) is accepted by this V20/1516 compiler.
  The opaque low32 milliseconds seed ConfigRev; guarded STOP/RUN changes it and
  a fresh page carries that revision. This does not prove synchronized UTC or
  retained generations when a clock read fails. **[measured]**
- DATA_READ serves the page metadata with Readable=False/ValueText='' below the
  root's requirement. Peer policy remains independent. Capabilities stay closed
  (empty WriteKey, revision0, Writable=False). No config writer/provider is
  established by this test. **[measured]**
- The production Web API/gateway/repository/mapper/widget path loads two roots,
  maps24 modules and hydrates492 entries. A rendered Instant button advances the
  independently observed native command counter once; peer mode changes remain
  isolated. The test uses a memory-only operations display preference of NONE:
  PLC access remains enforced, but a login provider is not implemented.
  **[measured]**
- ConfigPage and Report are acknowledged request payloads. The HMI excludes them
  from cyclic tiers and captures release replies at their acknowledgement. The
  repository's assigned fast tier changes4278->1314 of8070 discovered leaves;
  this is a tier assignment, not a measured wire-rate guarantee. **[measured]**
- Real-network widget checks need LiveTestWidgetsFlutterBinding. Fake bindings
  strand async click callbacks and leave fake WebSocket/read-tier timeouts after
  dispose. Load real text/icon fonts for readable PNGs. The final live test
  completes cleanly with the production widgets and no fake timer bypass.
  **[measured]**

Final gates: native manifest241/241, routing120/120, native HMI live test passes;
117 blocks/41 interfaces canonical native reimport/compile/export0/0;
production114/41 compiler-only0/0;116 Siemens tools,123 HMI tests,33 consistency
tests pass. Earlier failed harness/cleanup/disk runs are retained in the evidence.
Temporary Flutter compiler caches were compressed without changing their bytes;
automatic approval review rejected deletion. **[measured]**

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/
TIA_STATIC_MANIFEST_HMI_2026-10-11.md. Current saved image/project:
LOCALAPPDATA/Fraktal/TiaStations/Manifest_Runtime_20261011/FrkS12/FrkS12.ap20.
No physical controller, approved driver, credential, pin or installed SDK changed.

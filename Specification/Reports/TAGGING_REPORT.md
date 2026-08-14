# Phase-1 tagging report — [TC3] clauses after the pass


## Part I (Core)

- L32: 8. **Portable.** The normative model — tiers, contracts, state machines, diagnostics, routing — is platform-neutral; each PLC platform is served by a *binding*
- L36: **Platform-tagging convention (O8).** Clauses specific to the TwinCAT 3 binding — compiler pragmas/attributes, `REF=`/`__QUERYINTERFACE`, `FB_init` ordering (§3
- L112: - The project **shall** be held in text-diffable form under version control; binary-only storage is not acceptable. (Storage forms per binding — [TC3]: TC3 §2.5
- L125: - **PTP (IEEE 1588) is the primary source.** Where the network and devices support it, the station clock **shall** be disciplined by PTP — over the fieldbus's d
- L212: This is the standard composite pattern: an interface array drives heterogeneous children, and a **capability query** upcasts to the richer interface only where
- L315: - **should** be checkable by clients via the Optional/Mandatory ModellingRule and by PLC code via the capability query ([TC3]: `__QUERYINTERFACE`, TC3 §3.2).
- L323: **(a) Exposure by deployed root.** Exposure begins at explicit deployed instances and standalone published data; reusable type definitions are not globally enabled.
- L343: - Any archetype is a **type**. To duplicate, instantiate it again and inject identity + HAL mapping at instantiation (**constructor injection**; the injected `N
- L345: - **Nested children use a `Setup(...)` method, not constructor injection.** Constructor injection suits top-level, compile-time-fixed wiring; but a parent **sha
- L646: A module's OPC UA browse name **shall** equal the `Name` passed at instantiation/`Setup` (§3.11; [TC3]: the `FB_init` `Name`, TC3 §4.8), which **shall** match t
- L680: - **Framework / base types are ST only.** `FB_Module`/`FB_Unit`/`FB_EquipmentModule`/`FB_ControlModule`, the `I_*` interfaces, the step-chain base, `FB_PermIntl
- L709: - **Framework & tooling.** Tests **shall** be written with the binding's xUnit framework and executed in CI by its headless runner, which emits JUnit-format res
- L848: **(a) Self-diagnosing modules.** Every module **shall**, each scan, compute a single first-out reason it is not `Done` and publish it as `OutImm.Diagnostic` (fi
- L1182: - **Fieldbus & device health.** Fieldbus master state, lost frames, slave errors, and distributed-clock sync (`FIELDBUS_MASTER_FAULT`, `DC_SYNC_LOST`) surface p
- L1215: - Safety functions **shall** be implemented in the certified safety system of the binding ([TC3]: Beckhoff TwinSAFE — TwinSAFE Logic plus safe I/O over FSoE / S
- L1248: - **Lifecycle.** The safety system (§9.1; [TC3]: TwinSAFE, TC3 §9) **shall** be designed, implemented, and validated per the functional-safety lifecycle of ISO
- L1261: - The binding defines the primary fieldbus ([TC3]: EtherCAT — TC3 §10.1). The fieldbus master(s), topology, and distributed-clock settings **shall** be document
- L1281: Fieldbus and controller diagnostics — lost frames, slave errors, distributed-clock sync loss, watchdog — **shall** surface as System alarms (§8.6) with a `Reaso
- L1342: - The binding's OPC UA server **shall** publish the module tree per §3.10 — explicit deployed-root and standalone-data markers, reference exclusions, filtered symbols, and

## Part II (TC3)

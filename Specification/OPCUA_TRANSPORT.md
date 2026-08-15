# Fraktal OPC UA transport

This document defines the deployment boundary behind the generic HMI
`PlcRepository`. It does not change the module contract.

On a Windows/TwinCAT host the native default is now **ADS**, not direct OPC UA —
it is the faster native path and needs no TF6100 server. OPC UA remains a
first-class, selectable HMI transport for remote and non-Beckhoff PLCs. ADS is a
drop-in `OpcUaSessionClient` that emits the identical `fraktal.opcua.snapshot.v1`
document, so the mapper, config-manifest, and mailbox contracts apply unchanged
to both direct transports. Read-tier behavior is capability-negotiated: the
current direct ADS/OPC UA clients provide targeted/tiered reads, while the Web
gateway currently relays a complete server-side snapshot. The ADS
transport is specified in `ADS_TRANSPORT_MIGRATION.md`; the summary is below.

## Platform routing

| Flutter target | Transport | Implementation |
|---|---|---|
| Windows (TwinCAT) | direct **ADS** (native default) | `fraktal_ads.dll` (TcAdsDll) through `dart:ffi` in the `fraktal-ads` isolate |
| Windows (remote / non-Beckhoff) | direct OPC UA or the gateway | native `ws`/`wss` client; open62541 through `dart:ffi` |
| Linux / Android | Fraktal WebSocket gateway | native `ws`/`wss` client; direct C ABI remains source-compatible where packaged |
| Web | Fraktal WebSocket gateway | browser WebSocket client; the gateway owns the OPC UA session |

Browsers shall never attempt raw OPC UA TCP. Every transport delivers the same
flat `fraktal.opcua.snapshot.v1` document to `OpcUaSnapshotMapper`, so discovery
and UI behavior cannot drift by platform or by transport.

## ADS transport (native Windows/TwinCAT default)

The native Windows client may connect over ADS with an `ads://<AmsNetId>:<port>`
endpoint (default `ads://127.0.0.1.1.1:851`, the local runtime; the wizard seeds
it and the operator confirms the machine's AmsNetId). It is a `dart:ffi` client
in the dedicated `fraktal-ads` isolate over `fraktal_ads.dll`, which wraps
Beckhoff's `TcAdsDll` using Beckhoff's own headers so struct/datatype layout is
version-correct. The build **self-skips** when not on Windows or when `TcAdsDll`
is absent, so the HMI falls back to OPC UA and non-TwinCAT builds are unaffected.

- **Discovery** is a datatype-table walk: `SYM_UPLOADINFO2` (`0xF00F`) sizes the
  symbol and datatype tables, `SYM_DT_UPLOAD` (`0xF00E`) uploads the datatype
  table (members reference their type by namespaced name, e.g.
  `Fraktal_Core.ST_ModuleStatus`, resolved recursively), and `SYM_UPLOAD`
  (`0xF00B`) lists top-level symbols; each `MAIN.*` / fieldbus symbol is expanded
  to leaves. The resulting flat path set feeds the **unchanged** mapper —
  `MAIN.PneumaticPress.Status.State` becomes `PLC1/MAIN/PneumaticPress/Status/State`
  (synthetic `PLC1/` prefix, dots→slashes), the same identity the OPC UA snapshot
  emits.
- **Reads** use value handles (`SYM_HNDBYNAME` `0xF003` → `SYM_VALBYHND` `0xF005`
  → `SYM_RELEASEHND` `0xF006`). The whole fast tier is read in **one** round trip
  by the ADS sum-command `SUMUP_READ` (`0xF080`); a per-symbol path is kept as a
  fallback for runtimes that lack the sum service. Measured: steady-state snapshot
  **~15 ms** (vs ~2.3 s reading 1.6k symbols individually).
- **Writes** are typed handle writes; mode-change round-trips **~86 ms median**
  through the production repository path — the metric the OPC UA path only reached
  after the read-tier work, and with none of the TF6100 licensing/TOFU/handle-pool
  (`0x710`) failure classes.
- **Read tiers** map directly: the fast/slow tiers are read every snapshot (ADS
  is fast enough that the slow-tier heartbeat is not required), and the
  **excluded** set (config manifest + on-demand drill-down + fieldbus) is never
  read cyclically — it is served by targeted `readValues` calls, identical to the
  OPC UA excluded tier.

ADS is Beckhoff-specific by design: it is the native fast path, while OPC UA stays
the portable multi-brand path so a future Siemens/Rockwell PLC integrates by
pointing the same HMI at `opc.tcp://…`. Reconnect-on-router-loss and
first-snapshot handle batching are tracked as hardening in
`ADS_TRANSPORT_MIGRATION.md` §11.

## Native ABI

The native library exports create/connect/disconnect, snapshot, typed write and
error functions from `native/opcua/fraktal_opcua_bridge.h`. open62541 1.4.12 and
Mbed TLS 3.6.6 are pinned and vendored with their licenses. All native calls run
in the `fraktal-opcua` Dart isolate; the Flutter UI isolate never performs a
blocking browse/read/write.

The ABI exposes `frk_opcua_connect_secure` with an explicit profile, policy URI,
application URI, client certificate, private key, optional private-key
password, server/CA trust list, and optional revocation list. Secure profiles
force `SignAndEncrypt`; reconnect
reuses the same material and may not downgrade. Private-key bytes are cleared
after open62541/Mbed TLS configures the client. Credentials are process inputs,
not endpoint/query data or HMI settings JSON.

Four deployment profiles are defined:

| Profile | Channel / identity | Rule |
|---|---|---|
| `production` | trusted certificate + `SignAndEncrypt` + named TF6100 user | Default; required for a network-connected production cell |
| `secure-anonymous` | trusted certificate + `SignAndEncrypt` + Anonymous token | Transitional commissioning only; preserves channel and application authentication |
| `commissioning-anonymous` | `None` + Anonymous | Troubleshooting/initial bring-up; gateway warns and auto-stops after a bounded TTL |
| `isolated-anonymous` | `None` + Anonymous | Explicit exception for one physically isolated, unrouted PLC/HMI deployment |

Missing production material is a startup failure. A failed secure connection
shall never retry with a weaker profile. Anonymous namespace/write rights shall
be least-privilege. A network-connected production target shall disable the
Anonymous/None exception after commissioning. A permanent isolated exception
requires documented physical/network controls and ownership.

The direct Windows `opc.tcp` wizard path intentionally remains Anonymous/None
and logs a security warning; it is only for commissioning, troubleshooting, or
the isolated exception. The cross-platform production path is `wss` through the
gateway, so PLC credentials and OPC UA private keys remain under a dedicated
gateway service identity.

## Online-change resilience

A TwinCAT PLC **online change** reloads the TF6100 Data Access namespace and
commonly tears the OPC UA session down. The native client is driven by explicit
service calls (no open62541 event loop), so it recovers deliberately, not via
auto-reconnect:

- **Session loss** — every snapshot checks the live channel/session/connect
  status; if it degraded, the client reconnects with the cached endpoint and
  clears the cached NodeId map, then re-browses. This is transparent: no command
  is queued across the gap, and the HMI returns to `LIVE` as soon as the session
  is back (a `STALE`/`DOWN` blip only if the reconnect itself fails).
- **Structural change with a surviving session** — reads against cached NodeIds
  that no longer resolve (`BadNodeIdUnknown`/`BadNodeIdInvalid`) are counted; a
  surge (≥20 % of cached variables gone) invalidates the discovery cache so the
  next snapshot re-browses the fresh tree (added/removed/renamed symbols).
- **Writes** issued during the brief reconnect window are rejected, not queued
  (§14); the operator re-issues once the HMI is `LIVE` again.

Reconnect attempts are naturally throttled by the connect timeout and the shared
in-flight refresh, so a PLC that is genuinely down cannot starve the isolate.

## Snapshot

```json
{
  "protocol": "fraktal.opcua.snapshot.v1",
  "nodeCount": 123,
  "truncated": false,
  "namespaces": [
    "http://opcfoundation.org/UA/",
    "urn:BeckhoffAutomation:Ua:PLC1"
  ],
  "values": {
    "PLC1/MAIN/PneumaticPress/Status/Name": "PneumaticPress",
    "PLC1/MAIN/PneumaticPress/Status/ModuleType": 1
  },
  "dataValues": {
    "PLC1/MAIN/PneumaticPress/OutImm/Pressure": {
      "status": 0,
      "type": "Double",
      "value": 4.2,
      "sourceTimestampUs": "1784613600123456",
      "serverTimestampUs": "1784613600124000"
    }
  }
}
```

`dataValues` is an additive v1 field carrying the OPC UA `DataValue` quality,
runtime scalar type, value when encodable, and optional timestamps. Timestamps
are Unix microseconds encoded as decimal strings so JavaScript cannot lose
64-bit precision. `values` remains the compatibility/discovery surface and
contains only Good-quality scalar values. A client may retain a Bad or Uncertain
tag from `dataValues` so an imported binding survives a transient fault, but it
shall render that tag unavailable and shall not chart or write from the stale
payload. Good status codes are classified by their OPC UA severity bits, not by
testing only for the literal zero status.

The mapper recognizes a module only through `Status : ST_ModuleStatus` and
builds its HMI identity from published `Status.Name` values. Server-specific
prefixes such as `PLC1/MAIN` do not enter the Fraktal identity.
`namespaces` is diagnostic metadata read from the standard OPC UA
`Server/NamespaceArray`: if the PLC namespace is present while `Objects` exposes
only `Server`, the connected identity lacks browse rights; if it is absent, the
TF6100 Data Access NodeManager/TMC configuration was not loaded.

Native discovery is breadth-first and cached once per OPC UA session. Breadth
first ordering guarantees that shallow root contract/mailbox nodes are found
before implementation detail when a server publishes a large tree. Value nodes
are subsequently read in bounded service batches; the 500 ms repository refresh
does not recursively browse the namespace again. `truncated=true` means the
configured discovery cap was reached and is a commissioning defect: narrow the
published namespace or revise the contract-aware projection after measuring it,
instead of silently treating a partial tree as complete.

TF6100 may expose references held by recipe catalogs, I/O drivers, or control
coordinators as additional navigable paths to the same FB. The snapshot may
carry those values. `Status.Name` is a qualified dotted identity, so the mapper
accepts a candidate when its final browse-name segment equals the final segment
of `Status.Name`, deduplicates every module by the complete identity, and builds
parentage from the dotted identity prefix. Among multiple same-identity
candidates it selects the shallowest path; discarded aliases are logged as
`opcua-aliases-discarded`. This implements Part II §3.10's rule that a
reference/owner alias is not another deployed module/root.

### TF6100 commissioning access

The direct native HMI and the gateway's `commissioning-anonymous` /
`isolated-anonymous` profiles use Anonymous with `SecurityPolicy=None`. The
following Anonymous setup applies only to those explicit exception profiles.
Production and `secure-anonymous` instead require a trusted client application
certificate and a matching `SignAndEncrypt` endpoint; production additionally
requires a named least-privilege TF6100 user.

TF6100 5.x (TwinCAT 4026) first requires a **one-time Trust-On-First-Use
initialization** before it publishes any Data Access namespace; until then an
`Objects` browse shows only `Server` and `Initialization` and the HMI reports
zero root Units. Initialize once from the OPC UA Configurator over a **secured**
endpoint (`Basic256Sha256` / `SignAndEncrypt`) with a `UserName` admin identity —
a credential token cannot be sent over a `None` channel. Initialization then
**disables the Anonymous token**, so the anonymous commissioning access below must
be re-added afterward. On a usermode/standalone runtime the server lacks rights to
create its admin OS user during init; pre-create that account in Windows first.
Full procedure and the local-PC quick path are in
`FIRST_PROJECT_AGENT_GUIDE.md` §7.0 / §11.

In the OPC UA Configurator connected to the **remote PLC**, open **Security** and:

1. Edit the existing Anonymous user and assign it to the built-in **Users**
   group. Configurator versions that offer only Guests, Users, and
   Administrator should use **Users**; do not create a second Anonymous user
   or grant Administrator for HMI data access.
2. In the Users group's namespace/default access, add
   `urn:BeckhoffAutomation:Ua:PLC1` with Browse, ReadAttribute, and ReadValue.
   Namespace browse permission is required so `PLC1` and `MAIN` are visible;
   granting access only at the root Unit cannot expose hidden ancestors.
3. If node permissions are used, add the deployed root Unit with depth `-1` for
   inherited Browse/Read. Add Write only for its `HmiRequest` subtree.
4. Activate the changed server configuration and restart/reload TF6100 before
   retrying the HMI.

When the server trace accepts `AnonymousIdentityToken`, prints `Roles assigned
to session` without any role entries, and returns only `Server` from an
`Objects` browse, these rights have not reached the active server configuration.

For TwinCAT TMC-Filtered publication, every deployed root Unit declaration is
explicitly marked with `{attribute 'OPC.UA.DA' := '1'}`. The marker is inherited
by the root's children and makes the intended forest explicit. Fraktal does not
use TwinCAT's definition-level enable marker because it also publishes
undeployed instances and reference aliases. A separately published GVL value
places the marker immediately before that variable, not before `VAR_GLOBAL`.
After activating a changed PLC project, restart/reload TF6100 so it imports the updated
`Port_<ADS port>.tmc`; an authorized identity browsing `Objects` shall then see
the configured Data Access device and a direct `MAIN/<Root>` path.

The inherited root marker must not publish implementation-only pointer,
interface-reference, or `REFERENCE TO` storage. Mark those fields with
`{attribute 'OPC.UA.DA' := '0'}` (or keep their owner outside the published
subtree). An `Unsupported datatype ... UXINT` importer entry means TF6100 skipped
such a pointer-like leaf. Fix an application-owned path and reload the TMC; the
Beckhoff system leaf `TwinCAT_SystemInfoVarList._AppInfo.TComSrvPtr` is outside
the Fraktal contract and can be ignored when the application namespace and roots
otherwise import correctly.

The native browser reads `NodeCount` and each active `ChannelCount` before it
enqueues the fixed topology arrays. Unused `Nodes[]` and `Channels[]` elements
therefore do not consume the browse/read budget. A snapshot carrying
`truncated=true` is rejected by both the gateway and HMI; gateway `/readyz`
remains degraded and no operator repository reaches `LIVE`. Raising the browse
cap is not an acceptance fix.

## WebSocket gateway protocol

The Web client sends:

```json
{"protocol":"fraktal.opcua.gateway.v1","id":1,"method":"snapshot","params":{}}
{"protocol":"fraktal.opcua.gateway.v1","id":2,"method":"write","params":{"path":"...","valueType":"boolean","value":true}}
{"protocol":"fraktal.opcua.gateway.v1","id":3,"method":"writeBatch","params":{"writes":[{"path":".../HmiRequest/Kind","valueType":"int32","value":4},{"path":".../HmiRequest/Sequence","valueType":"uint32","value":19}]}}
{"protocol":"fraktal.opcua.gateway.v1","id":4,"method":"discoverPaths","params":{}}
{"protocol":"fraktal.opcua.gateway.v1","id":5,"method":"setReadTiers","params":{"revision":7,"slow":[41,42],"excluded":[90,91],"refreshSlow":false}}
{"protocol":"fraktal.opcua.gateway.v1","id":6,"method":"readValues","params":{"revision":7,"indices":[90,91]}}
```

The gateway replies:

```json
{"id":1,"ok":true,"result":{"protocol":"fraktal.opcua.snapshot.v1","values":{},"dataValues":{}}}
{"id":2,"ok":true,"result":true}
{"id":4,"ok":true,"result":{"revision":7,"nodeCount":1234,"paths":["PLC1/MAIN/Unit/Status/State"]}}
```

The gateway shall enforce origin/TLS/authentication policy, preserve browse
paths and values exactly, serialize writes in request order, and never replay a
write after reconnecting.

The gateway relays `dataValues` without normalizing status codes, types, or
timestamps. Native and Web HMIs therefore make the same quality decision from
the same server result.

`discoverPaths` returns the complete stable path vector plus a revision.
`setReadTiers` uses indices into that vector instead of repeating long browse
strings; stale revisions, duplicates, overlap, and out-of-range indices fail
closed. `readValues` accepts at most 512 unique indices per request. Clients
split larger logical reads into bounded calls and merge the results. A tier
profile accepts at most 20,000 indices and the whole request remains bounded to
256 KiB. The first snapshot on a connection includes the discovery vector;
after tier setup, cyclic snapshots carry an empty `paths` list so static browse
strings are not retransmitted. A rediscovery increments the revision and clears
every connection's profile before new tiers can be installed.

One gateway owns one native PLC session, so connection-local tier mutations
cannot be applied independently at that layer. The server therefore applies the
intersection of every connected browser's slow and excluded sets: a path is
slowed or omitted only when all clients agree. A new or not-yet-configured
browser temporarily requests the full live surface. This costs bandwidth during
bootstrap but cannot make an existing operator view stale or incomplete.

The reference service is `FraktalCore/HMI/gateway`. It builds as a headless
Windows or Linux executable and shares the same native client package as the
Windows HMI. Its OPC UA profile is explicit and production is the default. The
process binds only to loopback. With `--web-root`, it also serves the matched
compiled Web HMI from the same listener. Release Web builds derive
`ws://`/`wss://<page-origin>/fraktal`, avoiding a second endpoint setting or a
separate static server. Browser and native Windows/Linux/Android clients use the
same protocol; the native client validates `wss` with the platform trust store
and may present a deployment-provisioned mTLS certificate/key or protected
bearer token. Such identity material is rejected for `ws` and is never stored in
the HMI connection-settings JSON. A remote client shall reach the service
through a same-host reverse proxy that terminates trusted TLS, authenticates
ordinary HMI access and the WebSocket upgrade, preserves `Origin`, and proxies
both HTTP and WebSocket traffic to loopback. The service checks exact configured
remote browser origins as a second boundary; origin checking is not
authentication. Installation and acceptance are specified in
`WEB_HMI_GATEWAY_DEPLOYMENT.md`.

Every gateway write is type-checked, globally serialized, attempted once, and
restricted to a published root `HmiRequest` subtree. Deployment may further
restrict reads/discovery with repeatable `--read-root` subtrees and eligible
Unit write roots with `--write-root`; the reference service is read-only until
at least one root is configured (an all-root commissioning override is
explicit). Invalid protocol versions, binary/oversize
requests, non-mailbox paths, and unapproved origins are rejected before OPC UA.
One HMI request uses `writeBatch`: all fields belong to one mailbox, paths are
unique, and `Sequence : uint32` is the final write. The entire batch holds the
global write serializer, so another HMI cannot interleave fields. A standalone
`Sequence` write is rejected. The gateway remembers the last observed/committed
sequence per mailbox and rejects a duplicate or skipped commit, preventing two
HMI clients from consuming one another's acknowledgement.

The gateway sends WebSocket Ping frames every 2 s. Native clients also enable a
2 s Ping/Pong watchdog; browser clients rely on the server heartbeat because
the browser WebSocket API does not expose control frames. A missing Pong closes
the socket. Snapshot transport failures reconnect with jittered exponential
backoff (250 ms to 5 s), but writes are never queued or replayed. The first
failed snapshot makes the HMI `STALE` and removes the operator shell; 5 s
without a good snapshot makes it `DOWN`. Cold-start connection failures retry
automatically (500 ms to 5 s) while the connection editor remains available
after the normal 30 s gate.

`/livez` reports process liveness. `/readyz` returns HTTP 200 only when the last
OPC UA operation succeeded and HTTP 503 after an observed OPC UA failure.
`/healthz` is the backward-compatible JSON summary. None returns PLC data.

## Config manifest — obscured static publication (Core §3.10.2)

Activation-static configuration is deliberately **excluded from the cyclic
OPC UA tree** with `{attribute 'OPC.UA.DA' := '0'}` and served on demand
through the request mailbox instead. This keeps the published address space
(and the server's per-node ADS handle load) proportional to the *live* data:

| Obscured (manifest- or never-served) | Stays cyclically published |
|---|---|
| `Catalog`/`CatalogCount` (manual commands) | `Status/*` (discovery identity) |
| `AvailableModels`/`AvailableModelCount` | PLCopen outputs, counters, step, mode |
| `ModePolicy`, `StallTime` | `SupportedModes/RunStylesPublished` |
| `Nameplate`, `AlarmLog Meta/MetaCount` | `ParCfg`/`StationCfg` (editable fields) |
| `ST_BusNode` identity (Name/TypeId/Address/ParentIdx/ChannelCount…) | `ST_BusNode.State`, `LinkOk` |
| `ST_IoChannel` identity/capability (Name/Address/Path/ModulePath/Dir/Kind/Unit/Forceable…) | channel values/Forced/Quality/FaultActive/Diagnostic |

**Protocol.** The root Unit publishes `ConfigRev : UDINT` (seeded from boot
time, incremented on config writes, model changes, and re-activation) and
answers `E_HmiRequestKind.QUERY_CONFIG` (`IntValue` = page index) by filling
`HmiResponse.ConfigPage` — a bounded window whose read projection begins with
`{Scope, Item, ValueText}`. `Scope` is the dotted module identity (`'#Fieldbus'` for the bus
topology); `Item` reproduces the server's array naming
(`Catalog/Catalog[2]/Label`, `Nodes/Nodes[3]/Channels/Channels[5]/Name`) so a
generic client rebuilds the exact browse path it would otherwise have read.
The enumeration is produced by a deterministic walk (`I_ConfigSource.
M_AppendConfig`: base facets once in `FB_ModuleBase`, children recursed by the
composite base, Unit facets appended, projects may append — the press demo adds
its fieldbus topology via `F_AppendTopologyConfig`). `FB_ConfigPager` counts the
walk and stores only the requested window, so no full manifest buffer exists.

An entry is writable only when its append-only capability tail is complete:
`WriteKey`, non-zero `WriteRevision`, `ConfigKind`, `ValueType`, `Writable`,
`RequiresReady`, optional `Minimum`/`Maximum`, `Unit`, `LabelKey`, and optional
pipe-separated exact `EnumDomain`. Missing or conflicting metadata fails closed.
`WRITE_CONFIG` transports `TargetPath=Scope`, `NameValue=WriteKey`,
`IntValue=WriteRevision`, and `TextValue=candidate`; direct writes to `Item` are
not part of the contract. The PLC owning handler rechecks access, owner, revision,
type, domain/range, state, and transactional recipe invariants.

**Parameter sets (Core §3.8b).** Three append-only kinds carry the set-level
operations: `SAVE_CONFIG_SET = 27` and `LOAD_CONFIG_SET = 28` (`TextValue` = set
name, `NameValue` = `ModelCode` for a model set, empty for a station set), and
`LIST_CONFIG_SETS = 29` (`IntValue` = page index, answered in the same paged
response shape as `QUERY_CONFIG`). All three are gated by `CONFIG_SET` — a model
set additionally by `CHANGEOVER` — and require the root `READY`. A load is staged
and all-or-nothing, so a rejection names the offending `(Scope, WriteKey)` in
`HmiResponse.Diagnostic` and changes nothing. The root publishes
`PersistPending`/`PersistFailed` and the restore outcome cyclically beside
`ConfigRev`, because *this value is live* and *this value will survive the next
restart* are different claims and an operator is entitled to both.

**HMI behavior.** The repository fetches all pages when a forest is live and
the `ConfigRev` signature is new (startup, reconnect to a restarted PLC,
config write, changeover), synthesizes flat browse-path values from the
entries, and overlays them **under** the live snapshot before mapping. The
snapshot mapper receives typed configuration capabilities beside that read-value
overlay; facets and views remain transport-agnostic (the
mailbox works identically over the gateway). A server that publishes no
`ConfigRev` (older PLC library) is treated as fully published and never
queried. Absent manifest data degrades to empty facets, never an error.

## Native read tiers (direct ADS / OPC UA)

The direct native client reads the discovered contract at three rates, so the
2 Hz snapshot only pays for always-visible data. A single classifier
(`opcua_field_tier.dart`) is the source of truth; the bridge stays generic
(fast/slow read lists + an excluded set + targeted reads) and the mapper is
unchanged. The bridge emits the full discovered path list once per discovery so
the client can classify paths it never reads.

| Tier | Read rate | Data (examples) |
|---|---|---|
| **fast** | every snapshot (500 ms) | tiles, PLCopen state, counters, current step, active alarms (`AlarmLog/Active` — the global banner), OEE snapshot, live cycle profile, Unit `SystemHealth`/`TimeQuality`, and semantic `SignalTower` state |
| **slow** | once + ~2 s heartbeat | always-visible but slow-changing facets published redundantly on every module: `Safety`, `ControlPower` (read-only §9 status mirrors — display lag is bounded by the heartbeat; the PLC safety authority is unaffected) |
| **on-demand** | only while the owning view is visible | drill-down rings/trends read via a targeted batch call, never cyclically: per module — `AlarmLog/Ring`, `Profiler/History`/`StepStats`, `OeeTrend`, `Part/Result/Records`, command `Timing`; and the fieldbus I/O tree (`GVL_<Project>Fieldbus.Topology` state/values) |
| **config** | manifest (above), never cyclic | activation-static identity (`OPC.UA.DA := '0'`) |

On-demand data is grouped by **activation scope**: a module's drill-down data
scopes to its owning root Unit's browse base; the fieldbus tree shares a reserved
scope. `PlcRepository.setModuleDetailActive(rootPath, bool)` and
`setFieldbusViewActive(bool)` gate them — `AppState` activates the selected
root's scope while a module detail is shown, and the fieldbus page activates its
scope on mount/dispose. Sim treats both as no-ops; direct and gateway clients
apply the same classifier and targeted-read behavior.

**Gateway parity status.** The gateway preserves discovery, the config manifest,
mailbox ordering/acknowledgement, root scoping, PLC-side access checks, and the
same HMI-owned tier classifier as direct clients. Its bounded `discoverPaths`,
`setReadTiers`, and `readValues` operations make Web cyclic traffic proportional
to the consumed fast surface after the one-time bootstrap. Production acceptance
shall still measure a representative large forest through the packaged gateway;
source/protocol parity is not latency evidence for a particular IPC or TF6100
configuration.

**Why this shape.** The bounded history/trend arrays and the per-module
safety/power facets otherwise dominate the cyclic read (thousands of nodes) and
make TF6100 grow its ADS handle pool each poll (`AdsIncreaseDynSymPool`, a
`0x00000710` handle burst), which stalls the single native worker isolate and
delays interactive commands — measured mode-change latency dropped from ~1.1 s
median to ~50 ms once the fast tier shrank from ~6.9k to ~2.7k nodes. Interactive
mailbox commands also mark the repository busy so the periodic refresh yields the
worker to the command's small acknowledgement reads (Core §14). The manifest's
fieldbus topology base is resolved from the discovered path set (its live members
are on-demand and absent from cyclic values).

OPC UA does not call IEC methods. Every root Unit publishes one
`HmiRequest : ST_HmiRequest` input and one `HmiResponse : ST_HmiResponse`
output. The client writes all request arguments first and writes `Sequence`
last. The Unit consumes each new sequence once, invokes the same gated methods
used by PLC callers, clears `Secret`, then publishes `AckSequence` last.

This commit marker prevents a scan from consuming a mixture of old and new
arguments and gives native and gateway clients identical acknowledged writes.
The HMI seeds its next sequence from the published request/ack values on every
application start. It reserves the sequence before attempting the batch, so an
ambiguous disconnect can never cause that command number to be reused.

`E_HmiRequestKind` is append-only across PLC and HMI. Core `0.3.0.0` appended
`LAMP_TEST := 26`; it carries no arbitrary output path or duration. The Unit base
rechecks `MANUAL` authorization and idle state, starts its configured bounded
semantic tower test, and acknowledges the exact sequence. A client never writes
individual lamp/horn members.

Core `0.4.0.0` also publishes each Unit's `HostEvents` object as a bounded ring
(`Ring`, `RingHead`, `Count`, `Capacity`, `Wrapped`). It is read-only,
event-produced PLC data—not a command surface—and its ring belongs to the
on-demand tier. Clients derive traversal from the published `Capacity`, whose
current TC3 binding value is 32. `E_HostEventKind` is append-only and ordinal-identical in PLC and
HMI. A north-bound client uses `Sequence` for ordering and must retain
`TimeSynchronized`, `Verdict`, and `ReasonCode` rather than flattening quality or
result semantics.

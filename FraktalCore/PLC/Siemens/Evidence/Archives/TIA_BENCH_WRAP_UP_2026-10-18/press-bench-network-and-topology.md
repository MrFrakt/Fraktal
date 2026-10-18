# Live press bridge and scoped topology (2026-10-17)

The requested separate bench setup is operational. Source/evidence commit
`bbfc534ca669c414a9a5a9094e73c0c6b39f46a8` was pushed to main and independently verified
on origin/main on 2026-10-18. Do not repeat the completed owner binding/trace
actions or rebuild the approved Openness driver. **[measured]**

## Saved targets and connection

- FraktalBench: persistent CPU 1516, RUN/TCPIP, X1=192.168.0.20/24 and
  X2=169.254.212.61/16. Global mode TCPIPMultipleAdapter. IE1 maps to Ethernet1,
  index 9, Intel82574L #2, Windows 192.168.0.123/24, MAC 00:0c:29:76:ad:09;
  IE2/IE3 zero. HMI endpoint s7web://169.254.212.61.
- Physical: CPU 1214C DC/DC/DC,6ES7 214-1AG40-0XB0,FW4.7.3,192.168.0.10/24.
  It now accepts two controller-initiated streams:24001 receives demands,
  24002 publishes inputs. Both final programs use native TCP type 11.
- Original Fraktal: CPU 1516 RUN/TCPIP,169.254.212.49+192.168.1.1, maps0/0/0,
  saved Press_Complete_20261015 image and storage preserved. It was briefly
  powercycled once for the global mode change after quiescence proof; never
  claim uninterrupted RUN or unchanged volatile counters. It stayed RUN
  during all later bench-only recovery and physical software downloads.

The controller initiates BOTH existing TCP streams; the physical companion
listens on both ports. Common FB_IoBridgeEndpoint owns role/port selection.
No PC relay or different frame protocol was introduced. **[measured]**

Project authority: Examples/PressIoBridge/00_System/io.json schema 2.
physical_send_port replaces schema 1's simulator_receive_port, same 24002;
the generation gate requires distinct valid physical listener ports. The
native ST_IoBridgeConfig and 32-byte version 1 wire layout are unchanged.
Schema renaming changes metadata only: all actual SCL bytes are identical to
the compiled candidates; build_io_map.schema 1.json preserves the exact map
used by their original manifests. **[measured]**

Private work/evidence:
%LOCALAPPDATA%/Fraktal/TiaSpikes/Press_Bench_20261017.
Final bench=native05_controller_connect; physical=physical06_controller_connect.
Current public packages=current_public02 and physical_public02.
Final software downloads=download03_controller_bench and
 download04_controller_physical (21:57:26Z), user-management keep, existing TLS
trust, no TOFU. Physical driver/raw tags/gates were byte-asserted unchanged;
only shared transport connection setup changed. Original Fraktal received no
program download. **[measured]**

Saved projects:
TiaStations/Press_IoBridge_Press1500_20261015/FrkS12/FrkS12.ap20;
TiaStations/Press_IoBridge_1214C_20261015/FrkSpikeS2.ap20.
The bench's X2 Web API needed UseWebServerForInterface=True in hardware06.
Its pin is TiaStations/FraktalBench.webapi.pin, SHA256
1abd979172a7c7884e961f3c95e386f59f68b23f3edc59f8cda26b2243bd1867.
Physical pin remains192.168.0.10.webapi.pin, SHA256
5b7cbc6ccbe886e5c2fb099ca1f231de14d791a0c93b69f56a892d2f32829581.
Existing DPAPI credentials are FrkS12.web.secret and FrkSpikeS2.webapi.secret;
no credentials/certificate files belong in the archive. Private local admin
bootstrap was reused only after stripping it exactly reproduces the public
composition. Omit entire30_PressDemoComposition.scl and nativeFB_FraktalMain
XML/SCL, retain whole-file hash witnesses. **[measured]**

## Verified behavior and scope

Topology derives from the approved map plus module ownership, sized 3 nodes x 14
maximum channels (24 actual). Main still makes 3 calls. Generic Web API discovery
and read-tier fixes retain a standalone Topology beside roots, not another
Unit; private siblings remain hidden. All 14 inputs include ControlOn/E-stop
ordinary mirrors. The evaluated two-hand slot remains gatedFALSE until wiring
is verified; ordinary buttons do not create a safety result. **[measured]**

DI quality follows Connected independently of physical PeerEnabled. DQ is the
local demand, not applied physical feedback, so DQ Quality staysFALSE. Forcing
is absent/private. OUTPUT_MAPPING_CONFIRMED and EVALUATED_TWO_HAND_WIRED remain
FALSE; Q1.0/Q1.1 hardFALSE. No equipment/motion command or config change was
issued; HMI QUERY_CONFIG is ordinary read-mailbox traffic. **[measured]**

Both final programs pass two software compile stages 0 errors/0 warnings.
Bench 630 canonical/169 FB-type interfaces/73 DB interfaces match native exports.
Public review excludes the one private bootstrap, leaving 629/168/73.
Physical 5-source replay matches 9 code/type objects; owner verifier checks
10 canonical/4 interfaces/1 retained DB interface. Normal press 286 sources,
bridge 289; GRAPH 19/4/6/4 and LD 198 networks/192 calls remain. The two known bench
hardware-security warnings remain; R6 is not closed. **[measured]**

The strict generic HMI check runs the intended index-projected production
client/repository code with pinned HTTPS, passes 3 operational nodes,14 fresh DI,
10 unconfirmed DQ, expected electrical tags/owners, no forcing, and zero equipment
commands/config changes. Logs hmi_connected01 and hmi_recovered01 both pass.
link_stability01:150 samples,0 unhealthy,AcceptedFrames 1074 to 1718,0 rejected.
Bench power-off makes physical LinkHealthy=FALSE,OutputsEnabled=FALSE;
restoring the same saved bench returns RUN and passes strict HMI again without
operator reset. Original remained RUN throughout (link_loss_off/on01).
**[measured]**

Temporary transport recovery statuses were observed during fresh physical
HTTPS diagnostic sessions and are retained. Do not infer full load/latency
qualification from sequential Web API observations or the steady sample.
P8 native PN health/forcing, applied DQ feedback and physical motion/SAT remain
open, as do other roadmap phases. This is no P12 Line-transport claim.
**[measured scope]**

## Completed diagnostics and reusable findings

Owner SetNetInterfaceBindings succeeded 21:30:14Z; exact before/after identities
match in network_bindings_20261017_213014_187.jsonl. Owner's 20-second Packet
Monitor completed packet_trace_20261017_214717_221, removed its own filters,
and preserved the CPUs. ETL has metadata events only; counters show traffic
through Siemens filter. Do not fabricate individual ETL packet events.
**[measured]**

Old physical-initiated return path: valid-checksum SYNs reached guest .20:24002
and mapped MAC but received no response. Outbound stream established and sent
466592 bytes. Npcap capture transport_capture01.pcap and summary preserve this.
Public/Private Windows firewall profiles were alreadyOFF; none changed.
This does not establish an internal driver drop cause or justify blaming the
external VM bridge. **[measured]**

Online TCP-type/reset trial was inconclusive (COM_RST not consumed while TCON
pending), then fields restored to17/FALSE. A fresh type 11-only native04 candidate
compiled/downloaded but still failed incoming path. Final controller-initiated
streams succeed. Failed attempts stay preserved. **[measured]**

API7 CommunicationInterface is READ-ONLY and derives from global mode. Global
NetworkMode cannot change while instances run. SetNetInterfaceBindings requires
elevation. Invoke-TiaPressBench.ps1 and Enable-TiaPressBenchNetwork.ps1 guard
saved identities and mappings; neither switches global mode. Never unregister,
recreate or delete saved storage while debugging. Bench engineering download
uses target 1 X2/.61, but --confirm-target is first configured address .20;
SDK guards and S7 identity observation check both. **[measured/API]**

Keep offline compiles and full downloads sequential. No new whitelist needed:
unchanged driver candidate_structure_examples/Fraktal.Tia.Cli.exe SHA256
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
Unrelated HMI/auth/TLS/mobile/gateway/AGENTS/doc edits remain unstaged. Main
commit/push authorization persists. **[working discipline]**

References: Specification/Siemens/Evidence/TIA_PRESS_BENCH_TOPOLOGY_2026-10-17.md;
FraktalCore/PLC/Siemens/Examples/PressIoBridge/README.md;
Siemens TCON_IP_v4, TRCV_C and PLCSIM multiple-adapter API manuals.

Final intended-index gates:271Siemens tool tests,581full HMI tests with12opt-in
skips,Flutter analysis with no issues,consistency/contracts/lint all pass.
Measured Flutter3.47.6/Dart3.13.5; pubspec.lock byte-unchanged. The earlier strict
live HMI runs used byte-identical staged Dart sources. **[measured]**

## 2026-10-18 operator endpoint diagnosis and Disconnect

The user's offline tree was connected to s7web://169.254.212.49, the original
Fraktal. The user confirmed that endpoint. Read-only SDK inspection showed
all three original topology nodes State=0/LinkOk=FALSE, while all three saved
FraktalBench nodes were State=4/LinkOk=TRUE. Bench protocol observations at
04:18Z: Connected=TRUE,LinkHealthy=TRUE,AcceptedFrames=450554,RejectedFrames=0;
physical Web API:LinkHealthy=TRUE,OutputsEnabled=FALSE. Do not diagnose a
transport fault from an offline tree before identifying the HMI target.
**[measured + user-confirmed endpoint]**

A fresh strict repository/client test on FraktalBench passed on October18:
3 operational nodes,14 fresh DI,10 DQ with qualityFALSE,zero equipment commands
or configuration changes. Private observations remain under
TiaSpikes/Press_Bench_20261017/hmi_reported_offline_20261018_01.json and
physical_reported_offline_20261018_01.jsonl. This is not a new electrical or
motion acceptance run. Earlier sealed evidence remains unchanged.
**[measured]**

Shared HMI commit 1a7561ab45bd824db00d7385370e00743a47891b was pushed/verified
on main. Settings > Station > Disconnect is available to ADMIN. It reuses the
existing guarded connection owner, disposes the old repository and returns to
the prefilled endpoint wizard. It stays disconnected while the wizard is open;
Connect explicitly creates the next session. The admin rule and saved UI/Unit
preferences remain. The next normal application startup retains its existing
saved-connection behavior; no new persistent manual-disconnect policy was added.
The control is shared by TC3,AB andTIA; do not implement transport-specific
copies.21 focused tests pass,including disposal/no-auto-retry/new-endpoint
regression;Flutter analysis clean;Windows debug build succeeds.
**[measured source/build/widget tests]**

Restart/rebuild an older HMI executable to see the new button. For this bench,
connect to s7web://169.254.212.61. User subsequently said it seems fine; a separate
visual UI acceptance or physical bench acceptance is not inferred from that.

## Web API certificate fingerprint workflow

The live HTTPS leaf certificate at169.254.212.61 was re-read on October18 and
its SHA256 matched the saved known pin:
1abd979172a7c7884e961f3c95e386f59f68b23f3edc59f8cda26b2243bd1867.
This value identifies the Web server certificate, not the Openness driver file.
**[measured]**

TIA V20:CPU Properties > General > Web server > Security identifies the assigned
server certificate. Under Protection & Security > Certificate manager,right-click
that certificate > Export certificate > DER. Calculate its SHA256 with:

    certutil -hashfile "C:\path\WebServer.der" SHA256

Hash the DER certificate bytes. A Windows Thumbprint field may show SHA1;
the certificate signature algorithm is a different field. Certificate renewal
or replacing the saved project may require an explicit new verified pin. Keep
credentials and private keys out of reports and Git. **[help + measured pin]**

Official V20 references:
- https://docs.tia.siemens.cloud/r/en-us/v20/functional-description-of-s7-1500-cpus-s7-1500/setting-the-operating-behavior-s7-1500/protection-security-s7-1500/certificate-manager-s7-1500/certificates-for-the-web-server-s7-1500
- https://docs.tia.siemens.cloud/r/en-us/v20/functional-description-of-s7-1500-cpus-s7-1500/setting-the-operating-behavior-s7-1500/protection-security-s7-1500/certificate-manager-s7-1500/exporting-certificates-s7-1500

## Cross-binding follow-up

Fraktal Specification/Reports/TIA_BENCH_CROSS_BINDING_LESSONS_2026-10-18.md
contains proposed target-identity display,channel-validity provenance,publication
budget and adapter recovery/discovery acceptance work. Shared Disconnect and
Web API topology fixes are already implemented. TC3 already has per-node bus
health and manifest identity;AB already emits only declared I/O. Review those
implementations before deciding a change is needed; do not transplant Siemens
network bindings,TCP instructions,ports or certificate policy. No TC3/AB PLC
source or normative standard was changed by the wrap-up. **[review/proposal]**

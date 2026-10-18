# Live press I/O bridge and scoped topology (2026-10-17)

The separate saved **FraktalBench** CPU 1516 now exchanges ordinary I/O frames
with the physical **1214C**. The generic HMI repository discovers three
operational topology nodes, 14 fresh DI channels and 10 DQ channels whose
quality deliberately remains unconfirmed. Both physical output commissioning
gates remain FALSE; no equipment command or motion test was issued.

The [sealed payload](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_PRESS_BENCH_TOPOLOGY_2026-10-17/packaging.json)
preserves the native exports, deployment/network observations, HMI results,
source snapshot and private-file omission witnesses. Earlier evidence is
unchanged. This is the topology/ordinary-I/O slice of P8; native PROFINET health,
forcing, physical output feedback and motion/SAT acceptance remain open.

The seal contains 3,990 payloads plus its checksum manifest
(3,991 files, 77,238,786 bytes). SHA256SUMS.txt has SHA-256
`738c2a34132f08ff232a08f86960fe1f8497335cbe040a71af756f16d029163a`. Private bootstrap source/XML/SCL files are omitted
whole; the public native remainder verifies independently.

## Runtime and network

The physical CPU is the owner-confirmed 1214C DC/DC/DC, 6ES7 214-1AG40-0XB0,
FW 4.7.3 at 192.168.0.10/24. FraktalBench has X1=192.168.0.20/24 on the physical
LAN and X2=169.254.212.61/16 for local engineering/HMI. Its X1 maps to Ethernet1,
Windows index 9,192.168.0.123/24; other bench mappings remain zero. The HMI
endpoint is `s7web://169.254.212.61`. The existing transport credential and
certificate pin remain outside Git.

PLCSIM Advanced 7 uses Multiple Adapter mode. The owner successfully applied
Siemens SetNetInterfaceBindings at 21:30:14Z. The physical adapter's binding and
both CPU identities/mappings were checked before and after. The guarded setup
scripts retain the saved instances and reject unexpected targets or adapters.
Bench X2 Web API access was explicitly enabled in its hardware configuration.
The two existing development hardware-security warnings remain recorded;
this is not R6 qualification.

The original Fraktal retains its saved Press_Complete_20261015 image, storage,
169.254.212.49+192.168.1.1 addresses and zero physical mappings. It was briefly
powered off/on once for the global network-mode change, after Busy/persistence
quiescence checks. Its volatile scan state restarted; uninterrupted RUN is not
claimed. It stayed RUN during the later bench-only connection/recovery work.
No program was downloaded to the original Fraktal.

The bridge controller now initiates both TCP streams. The 1214C listens on 24001
for demands and 24002 for input publication. The common endpoint owns the role
and port selection; project drivers supply their role and I/O image. This uses
the existing TSEND_C/TRCV_C instructions and unchanged 32-byte, version 1 wire
protocol. TCP connection type 11 follows Siemens' recommended current form.
The project I/O map is schema 2: `physical_send_port` replaces the misleading
`simulator_receive_port` name, with the same 24002 value. Duplicate or invalid
physical listener ports fail before generation. Native SCL bytes are identical
before and after this metadata rename; the original schema 1 build input is
preserved beside the current schema 2 replay.

## Topology and encapsulation

The generic topology generator takes Core types/enums and the project catalog.
The press declaration joins the approved io.json tags/terminal addresses with
module ownership. It sizes the publication to 3 nodes and 14 maximum channels per
node (24 actual channels), validates the join, and emits identity separately
from cyclic value/health assignments. The existing output routine calls that
publisher; Main still has three calls. There is no project HMI screen or new
project per-scan service obligation.

The generic Web API discovery and read-tier filter now retain a standalone
Topology DB beside Unit roots in the PLC container. It is not another Unit;
private siblings remain excluded. The logical I/O image and forcing members
remain private. All 14 inputs cross the bridge, including Control On feedback
and the ordinary E-stop mirror. The additional evaluated two-hand slot remains
gated FALSE until its wiring is verified; ordinary buttons do not synthesize it.

DI freshness follows the validated round trip independently of the physical
output-enable flag. DQ BoolValue is the local demand, not physical applied-output
feedback, so DQ Quality remains FALSE. The HMI offers no force capability.
OUTPUT_MAPPING_CONFIRMED and EVALUATED_TWO_HAND_WIRED remain FALSE, with Q1.0
and Q1.1 hard FALSE. The physical driver, raw mapping and output-gate source
bytes are unchanged by the transport update. Physical electrical mapping,
withdrawal timing and safety behavior are not qualified by these observations.

## Verification and deployment

Both final programs pass two software compile stages with 0 errors/0 warnings.
The bench has 630 canonical objects,169 FB/type interfaces and 73 DB interfaces
matched against native exports. Whole-file omission of the existing private
FB_FraktalMain bootstrap leaves 629 objects/168 interfaces/73 DB interfaces that
can be independently rechecked in the public payload. The physical package
replays 5 sources and matches 9 code/type objects; the broader owner verifier also
checks its 10 canonical objects,4 interfaces and retained DB interface. Normal
press generation replays 286 sources; the bridge profile replays 289. GRAPH
AUTO 19/HOME 4/CHANGEOVER 6/LoadPosition 4 and LD 198 networks/192 calls are preserved.

The exact intended-index projection passes all 271 Siemens tool tests,
all 581 HMI tests (12 opt-in skips), Flutter analysis with no issues, repository
consistency, Siemens lint and candidate contracts. The two strict live HMI runs
are invoked separately. Flutter 3.47.6/Dart 3.13.5 and the unchanged dependency
lock are recorded; unrelated working-tree HMI/auth/mobile edits are excluded.

The approved Openness driver was not rebuilt. Downloads selected the named
bench via X2 and the identified physical 1214C via PG/PC interface 2. Both final
updates were software-only with user-management keep and existing TLS trust.
The physical HTTPS certificate pin is unchanged. No uncertain download was
replayed, and offline compiles finished before downloads began.

The strict live HMI test runs the intended staged repository/client code,
uses pinned HTTPS, and passes with all 3 nodes operational, 14 fresh DI, 10 unconfirmed
DQ, correct electrical tags/module links, and no forcing. It records zero
equipment commands/configuration changes; ordinary QUERY_CONFIG reads still
use the shared mailbox. A 150-sample steady-state observation has 0 unhealthy
samples, advancing accepted-frame counts 1074 to 1718 and 0 rejected frames.

A bench-only power-off makes the physical bridge report LinkHealthy=FALSE
and OutputsEnabled=FALSE. Restoring the same saved bench returns RUN and
passes the strict live HMI test again without an operator reset. The original
Fraktal remains RUN throughout this recovery test. Brief transport recovery
statuses observed alongside fresh physical HTTPS diagnostic connections are
retained; full communications-load/latency acceptance is not inferred from the
steady-state sample or sequential Web API reads.

## Diagnostic history and limits

The original arrangement established the bench-to-physical send stream, but
the physical-to-bench TCP SYNs received no response. A bounded Npcap trace
proved valid-checksum requests reached the guest's mapped MAC. The owner's
Windows Packet Monitor run recorded component counters through the Siemens
filter; its ETL contained only metadata events, so it does not identify an
internal driver drop cause. Windows reported the active Public firewall profile
already OFF; no firewall setting was changed.

An online type/reset diagnostic was inconclusive because COM_RST was not
consumed during pending connection establishment; its fields were restored.
A fresh, compile-checked type 11-only candidate also failed the incoming path.
The final arrangement makes the controller initiate both existing streams and
passes the observed round-trip/recovery gates. It does not establish why that
PLCSIM passive incoming path failed. Failed attempts and the successful owner
binding/trace are preserved, with no fabricated capture events.

Native-first review: OUC instructions own TCP connections, RUNTIME supplies the
endpoint clock, and the common Fraktal protocol adds the required bounded
image admission, echo freshness and neutral rearming. The topology is generated
from declared ordinary I/O; it does not simulate or substitute PROFINET health.
P8 PN health/forcing, applied-output feedback and physical acceptance remain
open, together with the other roadmap phases.

Siemens references: [connection parameters](https://docs.tia.siemens.cloud/r/en-us/v20/editing-devices-and-networks/configure-networks/communication-via-connections/working-with-connections/using-open-user-communication-s7-1200-s7-1500-s7-1500t/connection-parameters-s7-1200-s7-1500-s7-1500t/connection-parameters-with-structure-according-to-tcon_ip_v4-s7-1200-s7-1500),
[TRCV_C connection/reset behavior](https://docs.tia.siemens.cloud/r/en-us/v20/open-user-communication-s7-1200-s7-1500/trcv_c-establishing-a-connection-and-receiving-data-s7-1200-s7-1500/trcv_c-establishing-a-connection-and-receiving-data-s7-1200-s7-1500),
and [mapped PLCSIM interfaces](https://docs.tia.siemens.cloud/r/simatic_s7_1500_et_200mp_manual_collection_enus_21/comprehensive-information/cpu-function-manuals/s7-plcsim-advanced-api/examples/applications/example-communication-via-tcp/ip-in-multi-adapter-network-mode-non-promiscuous-mode).

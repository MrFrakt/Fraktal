## Command binding - option A implemented offline

The owner chose **A** (question `call_f17f50e248404825813327f8477a84f4:0`):
a compact typed Core payload, PLC-side routing, one owner and a temporary
legacy Frame adapter. The [V6.6 wire draft](AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md)
holds the endpoint, commit/acknowledgement and refusal tables. The choice is
not a download authorization and does not enable a station's gateway writes.

The payload Template carries three DINT envelope fields and the nine exact Core
arguments: string widths 255/160/255/32/32, native BOOL BoolValue and UInt32
DurationMs bits. A separately writable DINT commit follows the payload write.
A hashed CommandBindings row publishes every endpoint, the 4,000-byte
connection and 1,024-byte payload bounds, and the read role `CommandOnly`;
CommandOperations publishes a disposition for all 39 Core kinds. The client
encoder uses Template offsets and attribute 1 only, never a station map.

The PLC resolves module identities, configuration keys and revision, force
channels and values, and live model codes from its own generated facts, then
calls the released access/release owner once. Stale revisions and foreign
roots keep the owner's named refusals; unknown keys, modules, channels and
models resolve to no ordinal and are refused by name. A strict DINT parser
accepts only full integral text. Simultaneous legacy and typed commits are both
consumed and refused; a stale serial is refused without sampling its payload.
First scan baselines visible commits. Transport Secret/TextValue bytes,
including those beyond LEN, are wiped on every path before acknowledgement.

The set-service status is published only to a logged-in session holding the
config-set gate, for the matching accepted sequence and a bounded name; values
appear only where the data class is readable. Cyclic acquisition, the
observation frame and persisted captures never read the typed payload, its
private sample, the staged services or the on-demand reply.

ConfigSet/ConfigProvider staging and the legacy Frame/Sequence ingress remain
discoverable until their S6 replacements. Their native writers keep the
released encoding and their own acknowledgement.


# Ordinary I/O bridge endpoint

`bridge.scl.in` implements one shared transport for the physical I/O companion
and the simulated controller. It has no Unit, command lifecycle, press sequence
or mapped address. The owning project injects its private config, boot counter,
signals and enable. `FB_IoBridgeProtocol` owns admission, sequence/echo tracking,
watchdog and neutral rearming; `FB_IoBridgeEndpoint` owns asynchronous TCP jobs,
immutable send buffers, elapsed clock and connection recovery.

The generator pins instruction versions from the qualified native exports.
The project-owned map, raw tag table and final output permit live in
[`Examples/PressIoBridge`](../../Examples/PressIoBridge/README.md). The press
client uses its existing input routine, so no new per-scan call belongs in Main.
All transport storage is private; published engineering status is read-only.

This is ordinary process-image transport on the bench LAN, independent of the
hardwired safety circuit. The native protocol fixture under `Tests/IoBridge`
has no physical I/O. Runtime fieldbus, physical withdrawal timing and safety
acceptance require commissioning of the actual companion and bench.

# Closed history on reference S7-1500 - measured 2026-10-12

Fraktal generator0.12 opts actual Unit scopes into private LOCAL_RETAIN closed
rings. Core capacity64 and event fields derive from the reference contract. Retain
only selected consumers against CPU retained memory, independently of program/data
memory. Native export proves Rows/Commissioned Retain and external exclusions;
private read/write200, readonly published write205. Version/identity/header and
per-record checksums validate the image whole. Truncated persists after rejection
and overflow. Active/WAIT_RESET alarms and control state remain volatile; no full
alarm restart policy or physical abrupt-loss claim is made.

Canonical CRC bytes derive from Core F_Crc32; helpers are shared by access/history.
Event encoding follows all Core fields, UTF-16 characters and64-bit timestamps.
Close commits before the event callback. Startup never replays callbacks. Repeated
raises against a full active list commit overflow only once, avoiding a per-scan
retained rewrite. Explicit test clear retains an empty complete ring.

TIA V20 FC inputs must use bare String, not String[80]: the fixed length caused
Invalid data type, with cascading uncompiled-block messages. KeepOnError plus a
native compile exposed detail missing from the ordinary import exception. Stored
DB fields may still have explicit String widths. The native Web API rejected the
first non-ASCII WString fixture write with -32602; a test-only PLC routine creates
characters with UINT_TO_WCHAR. Do not infer that ordinary remote Unicode writes
are qualified from successful retention/readback.

Qualification:174 final history checks;1165 successful native assertions across
the continuation;155 tools/35 consistency; clean runtime and offline press native
compiles.76 access/config/set/CRC native sources remain byte-identical after the
last overflow guard. Press107 sources, GRAPH19/HOME4, optional LAD161networks/155calls.
Current projects Alarm_Persistence_Runtime_20261012 and
Alarm_Persistence_Press_Offline_20261012. Owner Fraktal RUN, keeper12728 (previous
Access_Persistence keeper script), TCPIP,169.254.212.49+192.168.1.1, maps0 unchanged.
Existing candidate_structure_examples driver only; no new whitelist/build.
See C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_ALARM_HISTORY_2026-10-12.md.

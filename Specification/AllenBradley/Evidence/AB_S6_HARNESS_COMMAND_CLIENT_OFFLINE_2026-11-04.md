# S6 harness command client (O11) — offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the uncommitted
S6 working tree. This implements the shared client that O11 (plan §6.3) selects.
No harness uses it yet; the switch happens in WP6.6 together with O10. No
controller, Echo service or PLC source is touched.

## Client

`fraktal_ab_harness_commands.py` sends one request per `writeBatch` to a
loopback, write-enabled gateway. A request is the nine Core `HmiRequest`
arguments, absent ones at their Core zero value, then `Sequence`. This is the
order and value types of the HMI repository (`opcua_repository.dart`).

- Malformed roots, unknown fields, and wrongly typed or out-of-range values
  refuse before any I/O.
- Only `ws://` URLs on a loopback host are accepted, carrying a loopback
  `Origin`. The reference gateway refuses a missing origin. URLs with
  credentials or a query refuse; remote access remains behind the
  authenticated proxy.
- A gateway refusal is a reply (`ok`/`result` false). A transport failure or
  a reply for another request closes the client for good, because the commit's
  outcome is unknown. Nothing is queued, retried or replayed.
- `command()` reads the controller's committed request and acknowledgement
  through the caller's reader, in one protocol-1 row on the S5 image. It
  writes only after the previous request is acknowledged. It reserves
  `request + 1` (UInt32 wrap) and observes the acknowledgement through that
  reader, never through the gateway under test.
- String capacities, roots and permissions remain the gateway, transport
  and PLC's to enforce. No Core table is duplicated in the client.

## Checks

- 16 focused tests pass. A drift guard parses the Dart repository's write list
  and requires the client's argument order and types to equal it. A real
  `websockets` loopback server receives the loopback origin and one JSON
  request. The import graph has no station, generator, declaration, projection,
  gateway, mailbox or pylogix module.
- `mutate_commands_01.py` catches four mutations: `Sequence` written first,
  no close after a failure, no settled-acknowledgement check and no origin.
  The original passes. An earlier scratch run gave the same result and was not
  logged to a file.
- `gateway_writebatch_check_01.py` drives the **real** Dart
  `FraktalGatewayServer` (write root `Press`) over a recording upstream:
  - it accepts the client's origin and request;
  - it forwards exactly the ten writes in order with the client's types;
  - a repeated sequence returns `result: false`;
  - root `Other` is refused with "outside the allowed HmiRequest scope".

  The verdict is in `Gates/gateway_writebatch_01.log`.

`Investigation/run_gates_01.py` ran the gates sequentially into create-only
`Gates/` records (`gate_summary_01.json`):

- 16 command-client and 35 row-reader focused tests pass with ResourceWarnings
  as errors; the mutation check passes.
- Full AB discovery: **2,421 tests pass** (879 s), with all Python module
  hashes unchanged during the run.
- The 85 root tests now include the merged TIA-contract module. The AB
  specification and frozen-contract gates and strict consistency (0/0) pass.
  They run after this checkpoint's plan and review edits.

## Boundary

The client has not commanded a controller. Native use, the harness switch,
WP6.6, WP6.7's move of the `websockets` pin and S6-Q remain. S6 has not exited;
nothing is committed under O1.

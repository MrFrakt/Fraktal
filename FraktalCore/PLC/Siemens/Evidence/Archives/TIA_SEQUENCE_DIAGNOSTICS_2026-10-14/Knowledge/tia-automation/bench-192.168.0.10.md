# Bench controller 192.168.0.10

| Item | Value | How known |
|---|---|---|
| CPU | SIMATIC S7-1200 **CPU 1214C DC/DC/DC**, `6ES7 214-1AG40-0XB0` | SZL 0x0011 [measured 2026-10-08] |
| Firmware | **V4.7.3** (SZL record index 7: `56 04 07 03`) | [measured] |
| Hardware revision bytes | `00 0d` (records 1 and 6) | [measured] |
| MAC | 8c-f3-19-b8-3f-4d (Siemens OUI) | ARP [measured] |
| Open ports | 102 only (80/443/4840/502 closed) before the Fraktal test image; that image adds 2000 | TCP probe [measured] |
| Negotiated S7 PDU | 240 | [measured] |
| Engineering route | workstation NIC `Ethernet1` 192.168.0.123/24 | [measured] |
| Field I/O | none connected | owner statement |
| Use | free for Fraktal/TIA spikes: download / stop / reset permitted | owner, 2026-10-08 |

## Current state (2026-10-08, after the Fraktal/TIA S2 runs)

- Runs the **Fraktal/TIA S2 test image** (cylinder CMs, Unit, SCL chain, self-test).
  The test image serves its result table on **TCP port 2000** (read-only for the host).
- Hardware config downloaded from the station project
  `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20`: confidential-data
  protection **off**, access control **Disabled** (classic, full access), PG/PC
  communication **secure only** with that project's certificate. **Use that project**
  (or answer the TLS trust question) to connect; a new project will be refused.
- PG/PC interface in TIA: `Intel(R) 82574L Gigabit Network Connection` #2.
- **Since 2026-10-08 evening:** access control `EnabledWithAccessControlViaAccessLevel`;
  anonymous user = `PLCAdministrator` (full access without login — bench only); web
  server on, HTTPS 443 open / 80 closed, project certificate `PLC-1/Webserver-2`
  (pinned SHA-256 `5b7cbc6c…`, pin file `%LOCALAPPDATA%\Fraktal\TiaStations\192.168.0.10.webapi.pin`);
  UMAC user `fraktal` with `WebReadTags|WebWriteTags` only (password DPAPI-protected in
  `TiaStations\FrkSpikeS2.webapi.secret`). OPC UA still off (4840 closed).
- Downloads now need `--set um=keep|update|reset` and `--set protection=` (empty) —
  the first one into this posture used `um=reset` + `--accept-lower-protection`.
- CPU clock never set (`DTL` year reads 2012; no NTP).

Identify again (read-only):

```
python C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools\s7_probe.py ident --host 192.168.0.10
```

Consequences for programs on this bench: no S7-GRAPH, no references, no named value
types, no LTIME/LDT; 150 KB for code + data together; OPC UA server needs the "Basic"
licence and is limited to ~1,000 monitored items, so the Fraktal default is the
licence-free Web API. See `s7-1200-vs-1500.md`, `plc-communication-options.md`.

Project evidence lives in the Fraktal repository:
`Specification/Siemens/Evidence/TIA_R1_PLATFORM_BASELINE_2026-10-08.md`.

## State 2026-10-09 (from the S11 semantics record)

- Runs the **S2 + S11_Scl test image**: 19/19 rows (cases 1-17, 29 safe startup,
  30 local invalid-index error). It is still served on TCP 2000, and the Web API
  (pinned HTTPS 443, user `fraktal`) is unchanged. Evidence:
  `C:\Projects\Fraktal\Specification\Siemens\Evidence\TIA_S11_SEMANTICS_2026-10-09.md`.
- Classic S7comm STOP (`s7_bench_mode.py`, Snap7 layout) is **refused with 16#8104**,
  and the CPU stays in RUN. The CPU's own web start page offers STOP/RUN forms
  (`POST /CPUCommands`) to a user holding `WebChangeOperatingMode`. Native mode-control
  runs were in progress on 2026-10-09 (folder `TIA_S11_NATIVE_2026-10-09`, no record
  yet). **Before relying on any user's rights, list them** (`umac-user --list`): a
  temporary mode right must be removed afterwards, and its restore is part of that
  open work.
- UMAC users: `fraktal` (`WebReadTags`, `WebWriteTags`, the gateway user) and
  `fraktal-diag` (`WebAllowDiagnostics`, memory page). Their passwords are DPAPI files in
  `%LOCALAPPDATA%\Fraktal\TiaStations\`. Never print them.
- The station project is still `FrkSpikeS2`. Its certificate is the only one the CPU trusts.

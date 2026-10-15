from pathlib import Path
import json
WORK=Path(__file__).resolve().parent;REPO=Path('C:/Projects/Fraktal')
g=json.loads((WORK/'60_gate_summary.json').read_bytes())
rows='\n'.join('| '+name+' | '+str(count)+' passed |' for name,count in g['native'].items())
report=f"""# TIA retained event delivery - 12-13 October 2026

Generator 0.14 qualifies selected-Unit event queues and real SQLite delivery on
the reference simulated S7-1500. Receipts have a dedicated metadata-only mailbox,
independent of the operator command channel. SQLite commits before a receipt;
retries deduplicate stable identities. The continuation also fixes a measured
active-alarm timing checkpoint interruption. The wired GRAPH/ST press compiles
offline. The work began on 12 October; qualification timestamps use UTC.

## Images and ownership

Current runtime: %LOCALAPPDATA%/Fraktal/TiaStations/Event_Delivery_Runtime_20261012/FrkS12/FrkS12.ap20.
Offline press: Event_Delivery_Press_Offline_20261012/FrkS12/FrkS12.ap20.
Owner Fraktal/CPU1516/TCPIP remains RUN, addresses 169.254.212.49 and 192.168.1.1,
physical mappings 0. Keeper PID 12728 remains the earlier Access_Persistence keeper;
do not stop/unregister it. The explicitly whitelisted candidate_structure_examples
binary is unchanged, SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
Credentials remain DPAPI/environment protected; no plaintext secrets are logged.
No physical press/controller mutation is part of this qualification.

alarm_delivery scopes select distinct history-consuming Units, with a canonical
deployment UUID and capacity bounded by Core MAX_ALARM_RING. The fixture uses
StationA, StationA.Satellite and StationB with eight entries each; the press uses
PressDemo with 32. Only selected consumers allocate retained images/anchors and
readonly head views; only their owning roots allocate receipt slots. Shared alarm
services capture immutable come/close records and own boot/validation/annunciation.
Application code adds no cyclic or reset call. Main remains three calls.

## Delivery and authority

A readonly head contains the complete Core ST_AlarmEvent, stable token and checksum.
The collector checks snapshot coherence and canonical field encoding, including
UTF-16, 64-bit timestamps and time-quality flags. A versioned SQLite database with
a full-synchronous rollback journal commits the record before any receipt. The
token is the primary key: identical repeats are accepted once; conflicting or
damaged durable records are refused. A failed database write sends no receipt.
After a lost reply, reconnection reads the current head and never replays the old
request sequence. Both failure points before and after PLC receipt acceptance are
qualified with actual SQLite persistence/reopen and native PLC state.

FRK_EventDeliveryReceipt exposes only typed metadata arguments and readonly replies.
Its commit sequence is sampled once by the owning root frame. It has no operator
command vocabulary and cannot commit a partially staged START in HmiRequest. Root
sessions, modes, control commands and hardware outputs remain independent. Receipt
permission requires ENGINEER and any configured higher DATA_WRITE threshold.
Foreign roots, unknown/prefix scopes, stale identity/checksum and invalid schema
are refused. Receipt audit records stay local and are muted only for their own
outbox, avoiding a delivery feedback loop. Automated receipts do not refresh an
operator session's idle timeout. The collector never performs application login
or logout; independent service authentication/unattended deployment remains open.

Whole-image owner/schema/epoch/cursor/count/order/event/CRC checks precede publication.
Corrupted queues remain private and produce an ordinary localized LOW/SYSTEM
AUTO_RESET message, using prototype reason 11002 from event_delivery.json.
An explicit engineering discard advances an independently validated identity epoch
and retains the loss marker. Invalid anchors cannot be discarded into reused IDs.
Overflow preserves older records and records dropped new entries; identities do
not wrap. This is bounded delivery of accepted records, not unlimited history.

## Corrected timing checkpoint

The first history regression rejected a full 16-entry manual active image after
STOP/RUN. Startup inspection identified timing checksum failure at slot 15: STOP
interrupted elapsed/checksum writes. The private recovery image advances to schema
2. Clock updates write the inactive elapsed/CRC bank, then commit its selector last.
Boot validates the committed pair; no event text hash/header generation is updated
per timer scan. Corrupt committed timing still rejects the image. Schema 1 is
rejected as a changed layout; no unmeasured in-place migration is claimed.

The preserved reproducer failed at its first cycle before the fix. Twelve final
STOP/RUN cycles each restored all 16 active manual events with zero integrity
findings. Full recovery/duration/close-journal regression also passes. Arbitrary
physical torn writes, instruction-level lifecycle transaction failure and
changed-layout/full-download retention remain separate commissioning gates.

## Qualification

| Native suite | Result |
|---|---:|
{rows}

Final successful native assertions: **{g['native_assertions']}**, plus the twelve
full-table checkpoint cycles. Siemens tools **{g['tools']}**, consistency
**{g['consistency']}**, HMI **{g['hmi']}** with **{g['hmi_skips']}** opt-in skips pass.
Runtime compile/download and both offline press checkpoints have zero errors and
warnings. Native export proves private retained images/markers, nonretained
runtime/receipt state, readonly views/replies and external exclusions. TIA lint,
consistency and whitespace gates pass.

The **120-source** press replay matches native GRAPH AUTO 19/HOME 4 and four LAD
examples with 161 networks/155 calls. GRAPH/ST stays wired; optional ST/LAD twins
remain uninstantiated. The press was compiled offline, not physically commissioned.

## Preserved findings and evidence

Initial compiler failures exposed String[255]'s native limit and WString-to-String
request comparisons. Explicit exact conversion fixed the prototype; dedicated
receipts now use their own bounded target type. Native UDINT_TO_STRING produces
leading plus signs; one owning formatter creates canonical decimal identities.
The first capacity assertion ignored setup drops; the final test checks additional
loss against its retained baseline. A misplaced localization map entry failed
Flutter compilation, was corrected, and the complete HMI suite passed. A full-table
stress test deliberately left manual alarms active; explicit reset establishes the
next fixture baseline. The earlier shared operator-mailbox receipt prototype is
superseded because independent writers could interleave. All raw interrupted and
superseded runs remain evidence, never edited into passing results.

[Immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_EVENT_DELIVERY_2026-10-12/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_EVENT_DELIVERY_2026-10-12/SHA256SUMS)
contain final/superseded native logs, imports/exports, SQLite payloads, probes/JUnit,
checkpoint diagnosis/repetitions, tool/HMI results, graph readback and source
snapshots. Earlier evidence remains unchanged. Next work is project-selected
configuration/access media and remaining sequence frontier/config/provider/module
scope, with independent event-service authentication and physical commissioning
still open.
"""
p=REPO/'Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md';assert not p.exists();p.write_text(report,encoding='utf-8',newline='\n')
print(p)

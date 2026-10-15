from pathlib import Path
import json
WORK=Path(__file__).resolve().parent;g=json.loads((WORK/'60_gate_summary.json').read_bytes())
kb=Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation')
text=f"""# Retained event delivery and timer checkpoint interruption - measured 12-13 October 2026

**[measured]** Generator 0.14 selects history-consuming Unit scopes, a bounded
capacity and canonical deployment UUID. Private LOCAL_RETAIN images/anchors and
readonly head views allocate only for actual consumers. Reference fixture uses
StationA/StationA.Satellite/StationB, eight entries each; press PressDemo, 32.
Shared alarm lifecycle captures complete come/close snapshots and owns restore,
validation and annunciation; projects add no scheduling/reset call.

**[measured]** SQLite adapter validates complete Core record CRC, commits a
full-synchronous rollback-journal transaction before receipt, and deduplicates
its stable primary-key token. Repeated identical records survive reopen once;
conflicting/damaged identities and failed writes prevent receipt. Lost replies
before and after native PLC acceptance reconnect by reading the current head,
without replaying the old request sequence. UTF-16, 64-bit timestamps and time
quality fields match the actual native producer CRC.

**[measured]** Use the dedicated FRK_EventDeliveryReceipt capability, one slot per
root with selected consumers. It has SchemaVersion/arguments/commit Sequence and
readonly matching AckSequence/Accepted. It has no operator command vocabulary;
its namespace is independent of HmiRequest/HmiResponse. A staged uncommitted
START remains uncommitted through a delivery receipt. The earlier shared-root
mailbox prototype is superseded because independent writers could interleave.
Receipt authority is at least ENGINEER and the configured DATA_WRITE level.
Root ownership, exact head identity/checksum and complete image checks prevent
foreign/stale receipts. Receipt audit stays local, outside its own delivery queue;
receipts do not extend an operator's idle timer. Independent service credentials/
unattended hosting remain open; the collector never changes application login.

**[measured]** Whole-image schema/identity/epoch/cursor/order/event/CRC validation
precedes publication. Corrupt storage stays private and raises localized LOW/
SYSTEM AUTO_RESET reason 11002, declared once in event_delivery.json. Engineering
discard requires a valid independent anchor, advances its epoch and preserves
loss indication. Invalid anchors cannot be discarded into reused IDs. Overflow
preserves old records, counts dropped new records and remains visible. Sequence
allocation refuses wrap. Capacity is bounded; do not claim unlimited history.

**[measured]** Full-table active-alarm regression exposed a STOP interruption
between elapsed and CRC writes (startup check 7, slot 15). Private recovery schema
2 uses two timing banks: write the inactive pair, then publish its selector last.
Read/validation follows the committed bank; corrupted committed values still fail
closed. No event text hash/header generation per timer scan. Twelve consecutive
STOP/RUN cycles preserve all 16 manual events with no integrity finding. Schema 1
is rejected as a changed layout. No in-place migration/full-download or arbitrary
physical torn-write guarantee is claimed. Keep the earlier 0.13 evidence immutable.

**[measured]** TIA String maximum 254 matters for new adapter temporaries. Mapped
request TargetPath/TextValue were WString; exact round-trip conversion avoided
narrowing aliases in the prototype. Dedicated receipts now have their own bounded
scope type. Native UDINT_TO_STRING adds a leading plus; one formatter removes it
for canonical identity segments. Capacity tests compare additional drops against
retained setup counts. Full-table stress leaves manual latches active: reset those
explicitly before the next fixture. A misplaced localization-map entry failed
Flutter compilation, was corrected, and the complete suite passed.

**[measured]** Final native {g['native_assertions']} assertions plus twelve full-table cycles;
Siemens tools {g['tools']}, consistency {g['consistency']}, HMI {g['hmi']}/{g['hmi_skips']} opt-in skips. Runtime and
both offline press compile checkpoints zero errors/warnings. Native exports prove
retention/external flags. Press 120-source replay, GRAPH AUTO 19/HOME 4 and four
LAD examples 161 networks/155 calls unchanged; Main three calls, GRAPH/ST wired,
optional ST/LAD twins uninstantiated. Physical press acceptance is still open.

Current projects Event_Delivery_Runtime_20261012 and
Event_Delivery_Press_Offline_20261012 under local TiaStations/FrkS12. Owner Fraktal/
CPU1516/TCPIP/RUN, 169.254.212.49 +192.168.1.1, physical maps 0. Keeper PID 12728
remains the earlier Access_Persistence keeper; preserve it and never unregister.
Unchanged explicitly whitelisted candidate_structure_examples, SHA256
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74. No rebuild or
new whitelist. Existing DPAPI credentials stay private.

Evidence C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_EVENT_DELIVERY_2026-10-12.md
and its separate immutable archive bind raw interrupted/superseded runs and final
gates/source snapshots. Next selected configuration/access media, remaining
sequence frontier/config/provider/module scope, independent event-service auth
and physical commissioning. UTC qualification/work IDs retain the start date.
"""
p=kb/'retained-event-delivery.md';assert not p.exists();p.write_text(text,encoding='utf-8',newline='\n')
p=kb/'INDEX.md';s=p.read_text(encoding='utf-8');a='| `manual-alarm-recovery.md` |';assert s.count(a)==1;s=s.replace(a,'| `retained-event-delivery.md` | Dedicated receipt mailbox, SQLite commit/deduplication, banked timing checkpoint correction and native qualification |\n'+a);p.write_text(s,encoding='utf-8',newline='\n')
mem=Path('C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory')
latest=f"""- Latest Siemens state (2026-10-13 local; continuation began 12th): generator 0.14
  selected retained event delivery, dedicated metadata receipt mailbox, SQLite
  commit-before-receipt/idempotent storage. {g['native_assertions']} final native assertions +12 full-table
  restarts, tools {g['tools']}/consistency {g['consistency']}, HMI {g['hmi']}/{g['hmi_skips']} skips, runtime/press native 0/0.
  Active private image schema 2 fixes interrupted timer pairs using two banks;
  schema 1 rejected as layout change. Current Event_Delivery_Runtime_20261012;
  offline Event_Delivery_Press_Offline_20261012, 120 sources, wired GRAPH 19/4/ST,
  Main three calls. Preserve Fraktal RUN/keeper 12728 in earlier Access_Persistence
  work dir. Unchanged approved candidate_structure_examples. Latest report/archive
  TIA_EVENT_DELIVERY_2026-10-12 (UTC/start date). Next selected config/access media,
  remaining frontier/config/module scope; independent service auth still open.

"""
p=mem/'MEMORY.md';p.write_text(latest+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
p=mem/'project-siemens-port.md';s=p.read_text(encoding='utf-8');s+='\n\n## 2026-10-13 local continuation: retained event delivery (generator 0.14)\n\n'+text.split('\n',1)[1];p.write_text(s,encoding='utf-8',newline='\n')
print('Updated owner-authorized Siemens KB and project memory from final measured gates.')

from pathlib import Path
import json
w=Path(__file__).resolve().parent;r=Path('C:/Projects/Fraktal');g=json.loads((w/'19_gate_summary.json').read_bytes())
rows='\n'.join('| '+name+' | '+str(count)+' passed |' for name,count in g['native'].items())
body=f'''# TIA S16 load-memory mechanism - 13 October 2026

Native READ_DBL/WRIT_DBL transfer gates pass on the reference simulated S7-1500
(CPU1516, TIA V20, PLCSIM Advanced V7). Optimized Byte arrays work with ordinary
banks and UNLINKED banks stored only in load memory. Their exact payloads survive
STOP/RUN and simulated PowerOff/PowerOn. The existing config/access/alarm services
pass regression without source changes. This is the native instruction leg of S16;
the keyed document medium and its consumer binding are the next implementation.

## Images and scope

Current diagnostic project is
%LOCALAPPDATA%/Fraktal/TiaStations/Load_Memory_Only_Runtime_20261013/FrkS12/FrkS12.ap20.
The ordinary-bank project is Load_Memory_Runtime_20261013/FrkS12/FrkS12.ap20.
Both are copies of the qualified Event_Delivery_Runtime_20261012 project, preserving
its engineering identity/security. The owner remains Fraktal/CPU1516/TCPIP/RUN,
169.254.212.49 +192.168.1.1, physical adapter mappings zero. Keeper PID12728 remains
active in the earlier Access_Persistence work directory. The approved
candidate_structure_examples executable is unchanged; no rebuild or whitelist.

Generator 0.14 and production framework code are unchanged. Native SCL comparison
with the prior event-delivery export confirms 321 baseline files byte-identical;
only F_ConfigBenchObserve.scl gains the test fixture call. The separate 120-source
wired GRAPH AUTO/HOME plus ST permissive press is unchanged and remains the
previously compiled offline Event_Delivery_Press_Offline_20261012 image. Optional
ST/LAD examples stay uninstantiated; Main remains three calls in that press.

## Measured transfer behavior

The fixture has four private 64-byte arrays: source, two banks and read destination.
Requests stage Kind/Seed, commit Sequence last and receive AckSequence/Accepted at
completion. Native REQ is TRUE once, then FALSE while polling BUSY. Sources stay
stable until completion. Invalid kinds and staged requests without a new sequence
perform no native transfer. Test diagnostics are readonly.

For ordinary optimized DBs, WRIT_DBL changes load-memory bytes while leaving the
bank's current RAM unchanged. Deliberately replacing that RAM with another value
and clearing the destination still reads the saved bytes. Two distinct patterns
isolate the banks; replacement of A leaves B intact. A wrapping byte pattern also
matches a complete native 64-byte CRC independently computed with Python zlib.
Both slots restore exactly after STOP/RUN and simulated power. Observed call counts
are recorded per operation; these establish actual asynchronous polling at this
scope, not a hardware timing or endurance guarantee.

The observed IsOnlyStoredInLoadMemory attribute is readonly through the attribute
API. A derived native XML import first set it TRUE with Optimized layout retained.
The resulting native SCL export identified UNLINKED. A second source-based import
using that keyword compiled cleanly, re-exported TRUE/Optimized, and passed the
load-only runtime gate. RAM access is removed for those banks. The helper asserts
each substitution and preserves the remaining native declaration bytes.

The ordinary-to-UNLINKED image transition/full download returned bank A to its
zero start values before the second gate rewrote it. This observed transition is
not preservation across a changed image. Confirmed-loss markers and document
validation still belong to the future consumer/medium integration.

Private buffer reads refuse Web API code200; diagnostic writes refuse205 in both
variants. Credentials use the established DPAPI/environment wrapper and are not
logged. Every write/restart/download guards the exact owner and zero physical
mappings. No physical controller mutation or instance unregistration is involved.

## Qualification

| Native suite | Result |
|---|---:|
{rows}

Total successful native assertions: **{g['native_assertions']}**. All three native
compile checkpoints report zero errors/warnings. Siemens tools **170** and
consistency tests **35** pass; TIA lint, cross-artifact consistency and whitespace
checks are clean. HMI code is unchanged in this continuation. Final normalization
returns the roots to MANUAL, logs out both sessions and verifies startup/RUN.

## Next adapter and boundaries

Config, named config sets, users and root policy currently use LOCAL_RETAIN.
The next LOAD_DB adapter needs consumed-size private documents, bounded tickets
advanced by consumer polling, keys, schema/generation/CRC, newest-valid selection
across two slots, confirmed loss versus unreadable storage, retry and a bounded
flash write rate. Reuse typed config validation/staging and existing write/Start/
login restore gates; the confidential user table must remain private. Live
acceptance and durable completion retain their distinct meanings. Application
code must acquire the medium through the generated owner path without another
cyclic scheduling call. Both-slot order, damaged/missing/unreadable images and
failed writes require native qualification before switching a deployed consumer.

This byte-transfer gate does not qualify a complete I_PersistMedium, physical
flash endurance, arbitrary torn writes or full-download/changed-layout retention.
The existing event-service authentication and other provider/frontier/module
work remain open.

[Immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LOAD_MEMORY_2026-10-13/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LOAD_MEMORY_2026-10-13/SHA256SUMS)
bind plans, native imports/exports, probes/JUnit, regression logs and source
snapshots. Previous evidence is preserved.

Primary instruction contracts:
[READ_DBL](https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/data-block-functions-s7-1200-s7-1500/read_dbl-read-from-data-block-in-the-load-memory-s7-1200-s7-1500)
and [WRIT_DBL](https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/data-block-functions-s7-1200-s7-1500/writ_dbl-write-to-data-block-in-the-load-memory-s7-1200-s7-1500).
The UNLINKED syntax and behavior above derive from this native readback/run.
'''
p=r/'Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md'
with p.open('x',encoding='utf-8',newline='\n') as f:f.write(body)
print(p)
kb=Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation')
text=f'''# Native load-memory transfer - measured 13 October 2026

**[measured]** TIA V20/simulated CPU1516/PLCSIM Advanced V7 supports READ_DBL and
WRIT_DBL with optimized Byte arrays. Independent ordinary DB RAM/load values and
UNLINKED load-only banks pass125/118 checks. Private 64-byte buffers, exact full
CRC, two-slot isolation, replacement, STOP/RUN and PowerOff/PowerOn qualify. REQ
is TRUE once then FALSE while polling BUSY; keep the source stable until done.
Only successful completion acknowledges the test request. Staged arguments
without a new sequence are inert. Invalid kinds issue no native operation.

**[measured]** WRIT_DBL changes load memory without changing the target current
RAM. Altered current bank RAM does not alter later READ_DBL results. Native
IsOnlyStoredInLoadMemory is reported readonly by the observed attribute API;
derived native XML proves TRUE plus Optimized layout. Its SCL export gives the
UNLINKED keyword. Reimporting the source, compile and readback/runtime all pass.
Remove ordinary RAM access for a load-only bank. The fixture helpers assert every
substitution and preserve native declaration bytes. PRIVATE payload reads refuse
Web API200, readonly diagnostics refuse205. The variant transition/full download
returns A to zero start values: do not infer changed-image preservation.

**[measured]** Generator0.14/framework unchanged:321 baseline native files are
byte-identical; only F_ConfigBenchObserve gains the test call. Current project
Load_Memory_Only_Runtime_20261013/FrkS12/FrkS12.ap20; ordinary variant
Load_Memory_Runtime_20261013. Prior Event_Delivery_Runtime project and offline
120-source wired GRAPH/ST press remain available. Owner Fraktal RUN/CPU1516/
TCPIP/169.254.212.49 +192.168.1.1/maps0; preserve keeper12728 in earlier
Access_Persistence work dir. Approved candidate_structure_examples unchanged.
Use the exact --driver and protected DPAPI/environment wrapper. Never unregister.

**[measured]** {g['native_assertions']} native assertions total (243 new transfer checks plus config,
access, state/alarm and manual recovery regressions); three compile checkpoints
0errors/0warnings; tools170/consistency35, lint/consistency/whitespace clean. HMI
unchanged. Final normalization MANUAL/logged-out/inactive, owner RUN.

**[planned]** The native instruction leg of S16 is complete at this scope.
Current config/set/user/policy adapters remain LOCAL_RETAIN. Next shared keyed
LOAD_DB medium: bounded tickets driven by consumer polling, private documents,
schema/generation/CRC/two slots, confirmed loss versus unreadable/retry, write-rate
limit and existing config/Start/write/login restore gates. Newest-valid slot order,
damaged/missing/unreadable images and failed writes need native qualification
before a consumer switches. Full I_PersistMedium and physical flash/endurance/
torn-write/changed-image guarantees remain open. Evidence:
C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md.
'''
with (kb/'load-memory-transfer.md').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
p=kb/'INDEX.md';s=p.read_text('utf-8');a='| `retained-event-delivery.md` |';assert s.count(a)==1;s=s.replace(a,'| `load-memory-transfer.md` | Native optimized/UNLINKED load-memory transfer, restart/privacy gates and next document-medium integration |\n'+a);p.write_text(s,encoding='utf-8',newline='\n')
mem=Path('C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory')
latest=f'''- Latest Siemens continuation (2026-10-13): S16 native load-memory transfer
  qualified:125 ordinary/118 optimized UNLINKED checks, {g['native_assertions']} assertions with config,
  access/state/alarm/recovery regressions; three native0/0 compiles, tools170/35.
  Generator0.14/framework unchanged;321 baseline native files identical, only test
  observer changed. Current Load_Memory_Only_Runtime_20261013, prior ordinary and
  Event_Delivery projects retained. Offline120-source GRAPH/ST press unchanged.
  Preserve Fraktal RUN/keeper12728/physical maps0, exact approved driver unchanged.
  Latest report/archive TIA_LOAD_MEMORY_2026-10-13. Next shared keyed LOAD_DB
  document medium +consumer restore/durability; current consumers LOCAL_RETAIN.

'''
p=mem/'MEMORY.md';p.write_text(latest+p.read_text('utf-8'),encoding='utf-8',newline='\n')
p=mem/'project-siemens-port.md';p.write_text(p.read_text('utf-8')+'\n\n## 2026-10-13: S16 load-memory transfer gate\n\n'+text,encoding='utf-8',newline='\n')
print('Updated authorized KB and project memory.')

from pathlib import Path
repo=Path('C:/Projects/Fraktal');kb=Path('C:/Projects/SiemensAgent/siemens-kb/tia-automation');memory=Path('C:/Users/Siemens/.claude/projects/c--Projects-Fraktal/memory')
def replace(p,old,new):
 t=p.read_bytes().decode('utf-8').replace('\r\n','\n');assert t.count(old)==1,(p,old);p.write_bytes(t.replace(old,new).encode('utf-8'))
replace(kb/'station-and-model-config.md',
 '  plus1skip and33 consistency tests pass. Native editor proof is recorded in the\n  dated evidence when complete.',
 '  plus1skip passed before the refresh fix; the final suite passes571 with8 opt-in\n  skips.35 consistency tests pass. The live Admin editor writes21, independently\n  reads it from the PLC, verifies inactive-model isolation and restores10.\n  The mapper uses valid current scalar readings while preserving declared\n  visibility/levels/bounds; the field used to retain the cached manifest value.\n 23 native checks also prove blocking restore/one acknowledgment/Start release.')
replace(kb/'verified-gotchas.md',
 '[station/model config](station-and-model-config.md). **[measured]**',
 '[station/model config](station-and-model-config.md). **[measured]**\n\nConfig metadata and current values have separate lifetimes: a live scalar reading\nmay replace the cached value while its declared visibility, permissions and bounds\nremain authoritative. Ignoring that reading left an accepted Preset21 edit showing\n10 until a full metadata refetch. The focused mapper/repository32 and live editor\ngates pass after correction; guarded bench display refresh6058ms. **[measured]**')
replace(memory/'project-siemens-port.md',
 '  fixture Admin session to prove the editor. Pending final screenshot/result is\n  recorded in TIA_CONFIG_TRANSACTIONS evidence before freeze.',
 '  fixture Admin session proves the editor. Live73 PASS:24 modules/556 entries,\n  typed Preset21/save/native read/inactive-model isolation/restore10, fault/reset.\n  Cached config values ignored newer live readings; mapper fixes that within\n  declared capability.32 focused tests and final571 HMI tests/8 opt-in skips pass.\n 35 consistency tests pass; readsurface resolves dynamic capability to declared\n  Scope/Item/ValueText and still rejects unexplained reads.23 blocking-restore\n  native checks prove config-loss Start refusal and one-ack release. Final76\n  owner RUN, roots/nested READY/MANUAL, sessionsNONE, no active alarms, defaults\n  restored, MODEL_A; StationA historical restore loss remains acknowledged.')
replace(memory/'MEMORY.md',
 '- Latest Siemens slice: generator0.7 state/alarm96+nested23, auth122, HMI fault/reset,148/45 roundtrip; restored saved Fraktal RUN after VM reboot, hidden API keeper required; older12 reports/18 manifests absent. See project-siemens-port.md and the dated state/alarm evidence.',
 '- Latest Siemens slice: generator0.8 station/model config120 +blocking restore23, access122, state/alarm96;190/52 reimport,183/52 production compile0/0. Live typed editor/fault-reset passes,571 HMI/8 opt-in skips,135 tools/35 consistency. Config_Runtime, Fraktal RUN/keeper1748 preserved; older12 reports/18 manifests absent. Next named station/model config sets. See project-siemens-port.md and dated config evidence.')
replace(repo/'Specification/Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md',
 '| Source analysis/lint/consistency |analysis clean; lint/consistency0;33 consistency tests |25,47,48,52 |',
 '| Source analysis/lint/consistency |analysis clean; lint/consistency0; final35 consistency tests |25,47,48,52,77,79-81 |')
replace(repo/'Specification/Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md',
 'The final live run takes3minutes.',
 'The final live run takes3minutes.78 preserves the initial readsurface rejection\nof the dynamic field name; the gate now resolves that exact capability loop to\nits published Scope/Item/ValueText authority and still rejects unexplained dynamic\nreads (35 tests).')
print('Final measured facts recorded in report, knowledge base and memory.')
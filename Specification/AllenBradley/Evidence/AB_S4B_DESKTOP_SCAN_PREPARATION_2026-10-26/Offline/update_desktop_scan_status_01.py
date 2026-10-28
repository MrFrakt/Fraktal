from pathlib import Path
import json

W=Path(__file__).parent
R=Path('C:/Users/SoftIndVM/Fraktal')
S=R/'Specification/AllenBradley'
ui=json.loads((W.parent/'desktop_fixture_06/result.json').read_bytes())
assert ui['passed'] and not ui['live'] and not ui['desktopLiveAccepted']
assert len(ui['modules'])==7 and len(ui['fieldbusNodes'])==3 and len(ui['shots'])==31
assert ui['fixtureClientWriteCalls']==0
path=S/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md'
text=path.read_text(encoding='utf-8')
needle='**Latest, 2026-10-26: S4b reader passes functionally; scan review and desktop remain open.**'
assert text.count(needle)==1
new='''**Latest, 2026-10-26: functional reader proof sealed; desktop/early-scan follow-up prepared offline.**
The [reader runtime](Evidence/AB_S4B_READER_RUNTIME_2026-10-26.md) passes all
41 candidate checks, 87 replays, 902 entirely Good samples, four configuration
pages/1,100 oracle comparisons and 5,407-path idle/generic acquisition. Its
one 10,033 us /one-overlap TASK finding and desktop live acceptance remain
open. Genealogy, five original documents, all 31 baseline/final checks and
preflight are restored. The completed approval is consumed.

The same production repository/UI now also renders a captured-native fixture
through seven modules and three fieldbus nodes: **31 views**, correct tab
selection, no layout exception, read-only banner, start/login refusals and
zero client write calls. This is static rendering proof, not a live connection
or freshness claim. Failed helper compile/navigation/async-output runs and an
analyzer unused import are retained; the final helper/replay and analyzer pass.
No shipping HMI or PLC code changed. The pinned 647-test Flutter result (12
skipped), Windows/analyzer/lockfile and 2,336 AB tests transfer by unchanged
production source bindings; root gates and 74 tests pass again.

The [desktop/scan preparation](Evidence/AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26.md)
uses a fresh copy of unchanged ACD `7D75E86E…DEF056BF` (65% Capacity). It adds
read-only fixed TASK scalar polling at nominal 100 ms before download through
candidate timing, retaining temporary read errors and counter transitions.
The real desktop factory/repository/UI runs after the unchanged 41-case
fixture and observer, before idle acquisition/timing. It keeps genuine source
quality and freshness; captured-fixture substitutions are disabled in live
mode. Seven failure-injected workflow/monitor tests and all authorization
refusals pass; monitor/UI errors still lead to guarded genealogy cleanup.
The parent stops monitoring before rollback. No added PLC write vectors,
counter/fault clears, clock/power/vendor-state operations or policy relaxation.
This fresh session is not authorized. V2/Part III inactive; nothing committed.

**Earlier, 2026-10-26: S4b reader passes functionally; scan review and desktop remain open.**'''
path.write_text(text.replace(needle,new),encoding='utf-8')
path=S/'AB_FROZEN_CONTRACTS_V2.json'
value=json.loads(path.read_bytes())
v=value['manifestV68']
v.update(preparation='Evidence/AB_S4B_DESKTOP_SCAN_PREPARATION_2026-10-26.md',
    qualificationRunner='C:/work/fraktal-ab-s4b-20261025/desktop_scan_01/qualification_session_v2.py',
    currentSessionAuthorized=False,retryNativeSessionAuthorized=False,
    desktopFixtureProof=dict(passed=True,live=False,modules=7,fieldbusNodes=3,views=31,
        clientWriteCalls=0,source='Captured native values/pages; static rendering fixture, not freshness proof'),
    desktopFollowup=dict(prepared=True,authorized=False,shippingProductionSourcesUnchanged=True,
        taskPollMs=100,taskMonitorBeginsBeforeDownload=True,taskMonitorStopsBeforeRollback=True,
        liveDesktopUsesProductionFactory=True,additionalPlcWriteVectors=0,
        workflowAndMonitorTests=7,existingAuthorizationRefusals=16,readonlyHelperRefusals=2))
with path.open('w',encoding='utf-8',newline='') as stream:
    json.dump(value,stream,indent=2,ensure_ascii=False)
    stream.write('\n')
print(json.dumps(dict(updated=True,authorized=False,desktopFixturePassed=True,desktopLiveAccepted=False,scanReviewPassed=False)))

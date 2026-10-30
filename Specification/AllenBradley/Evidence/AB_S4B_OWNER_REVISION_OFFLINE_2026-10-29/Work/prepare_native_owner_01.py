"""Create a fresh V6.10 session only after the sealed offline prerequisite."""
from pathlib import Path
import hashlib,json,urllib.parse
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
OLD=Path('C:/work/fraktal-ab-s4b-q-20261029/session_01')
D=W.parent/'session_01'
E=R/'Specification/AllenBradley/Evidence/AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
m=json.loads((E/'artifact_manifest.json').read_bytes())
assert m['offlineGatesPassed'] and m['desktopPrerequisitePassed'] and m['observerPeerPassed']
for relative,pin in m['sourceSha256'].items():assert sha(R/relative)==pin.upper(),relative
PIN='84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC'
SOURCE='22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06'
assert sha(W/'canonical_owner_01.ACD')==PIN and sha(W/'canonical_owner_01.L5X')==SOURCE
assert not D.exists();D.mkdir();(D/'scripts').mkdir();(D/'session').mkdir()
names=['audit_access.py','candidate_equivalence.py','candidate_regressions_v2.py','desktop_coverage.py',
 'ensure_manual_baseline.py','ensure_manual_candidate.py','login_busy_witness.py','part_read_diagnostics.py',
 'pre_restore_guard.py','restore_original_medium.py','run_logged.py','task_monitor.py','scripts/guard_echo.py',
 'scripts/preflight.py','session/Program.cs','session/S4bSession.csproj','build_native_desktop.py',
 'desktop_profile.py','configuration_comparison.py','replay_fixture.py','check_native_read_gates.py',
 'measure_timing.py','offline_checks_01.py','qualification_session_v2.py','readonly_stages.py',
 'session_ready.py','host_cpu_monitor.ps1','workflow_checks_01.py']
for name in names:
    source=(W/name) if name in ('audit_access.py','configuration_comparison.py') else OLD/name
    raw=source.read_text(encoding='utf-8').replace(OLD.as_posix(),D.as_posix())
    raw=raw.replace('30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5',PIN)
    raw=raw.replace('60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E',SOURCE)
    raw=raw.replace('fraktal_ab_genealogy_s4b_demo','fraktal_ab_genealogy_s4b_owner_demo')
    if name=='candidate_regressions_v2.py':
        assert raw.count('equivalence_gate=equivalence.run,')==1
        raw=raw.replace('from pathlib import Path','from functools import partial\nfrom pathlib import Path',1)
        raw=raw.replace('equivalence_gate=equivalence.run,',
            'equivalence_gate=partial(equivalence.run,application_factory=candidate.application),')
    if name=='candidate_equivalence.py':
        raw="""from functools import partial
import sys
sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
import fraktal_ab_s4b_equivalence as gate
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_genealogy_s4b_owner_demo as candidate
if __name__=='__main__':raise SystemExit(shared.main(partial(gate.run,application_factory=candidate.application),description=gate.__doc__))
"""
    with (D/name).open('x',encoding='utf-8') as f:f.write(raw)
for source,name in [(W/'canonical_owner_01.ACD','s4b_read_view.ACD'),(W/'canonical_owner_01.L5X','s4b_read_view.L5X'),
    (W/'capacity_auto_01.json','capacity_review.json'),(OLD/'desktop_expected_inventory.json','desktop_expected_inventory.json'),
    (W/'prepared_compare_01.log','canonical_prepared_compare.json')]:
    with (D/name).open('xb') as f:f.write(source.read_bytes())
with (D/'canonical.sha256').open('x') as f:f.write(PIN+'\n')
template=json.loads((OLD/'authorization.template.json').read_bytes())
assert not template['CurrentOwnerApproved'] and all(not template[k] for k in ['DownloadAuthorized','BackupUploadAuthorized','MailboxOrTagWritesAuthorized'])
template.update(CanonicalSha256=PIN,SourceSha256=SOURCE,
    Scope='V6.10 owner-revision qualification: fresh guarded backup/MANUAL/Program/download/Run; five-document restore and unchanged 41 candidate cases; read-only observer, 87-pair replay, independent four-page configuration, 5407-path equivalence/acquisition, strict 31-view desktop and TASK timing; genealogy copy rollback, exact original documents, 31 baseline cases and final checks. O3 applies after seal. No fault/TASK clears, clock, power or vendor-state operations.')
with (D/'authorization.template.json').open('x') as f:json.dump(template,f,indent=2)
path=H/'.dart_tool/package_config.json';config=json.loads(path.read_bytes())
for package in config['packages']:package['rootUri']=urllib.parse.urljoin(path.resolve().as_uri(),package['rootUri'])
with (D/'dart_package_config.json').open('x') as f:json.dump(config,f,indent=2)
with (D/'offline_inputs_01.json').open('x') as f:json.dump(dict(controllerChanges=0,authorized=False,
    acdSha256=PIN,sourceSha256=SOURCE,offlineManifestSha256=sha(E/'artifact_manifest.json')) ,f,indent=2)
print(json.dumps(dict(prepared=str(D),authorized=False,controllerChanges=0)))

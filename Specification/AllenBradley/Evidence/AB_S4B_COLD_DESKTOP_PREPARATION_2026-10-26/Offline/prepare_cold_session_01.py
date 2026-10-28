from pathlib import Path
import json
import shutil
import subprocess
import sys

W=Path(__file__).parent
OLDW=Path('C:/work/fraktal-ab-s4b-20261025/offline_01')
OLD=OLDW.parent/'desktop_scan_continue_01'
PINS=json.loads((W/'prepared_pins_01.json').read_bytes())
source=(OLDW/'prepare_root_diagnostic_01.py').read_text(encoding='utf-8')
replacements={
    "\nD = W.parent / 'retry_root_diagnostic_01'":"\nD = W.parent / 'session_01'",
    "\nOLD = W.parent / 'retry_template_01'":f"\nOLD = Path({OLD.as_posix()!r})",
    "\"D=W.parent/'retry_root_diagnostic_01'\"":"\"D=W.parent/'session_01'\"",
    "W / 'canonical_read_view_01.ACD'":"W / 'canonical_cold_01.ACD'",
    "W / 'canonical_read_view_01.L5X'":"W / 'canonical_cold_01.L5X'",
    "W / 'qualification_checks_v2.py'":f"Path({(OLDW/'qualification_checks_v2.py').as_posix()!r})",
    '7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF':PINS['acdSha256'],
    'missing_approval_cli_root_diagnostic_01':'missing_approval_cli_cold_01',
    'missing_approval_sdk_root_diagnostic_01':'missing_approval_sdk_cold_01',
    'root_diagnostic_authorization_checks_01.json':'cold_authorization_checks_01.json',
    "W / 'root_diagnostic_authorization_checks.py'":"W / 'cold_authorization_checks_01.py'",
    'productionSourcesUnchanged=True':'productionSourcesUnchanged=False',
}
for before,after in replacements.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(OLDW/'prepare_root_diagnostic_01.py'),'exec'),{'__file__':__file__})
D=W.parent/'session_01'
for name in ('task_monitor.py','session_ready.py'):
    shutil.copyfile(OLD/name,D/name)
for origin,name in ((W/'desktop_launcher_template.py','desktop_readonly.py'),
    (W/'desktop_coverage_template.py','desktop_coverage.py'),
    (W/'desktop_diagnostic_qualification_test.dart','desktop_diagnostic_qualification_test.dart'),
    (OLDW.parent/'desktop_fixture_06/result.json','desktop_expected_inventory.json')):
    shutil.copyfile(origin,D/name)
old_acd='7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF'
old_source='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F'
for path in [*D.glob('*.py'),D/'session/Program.cs']:
    text=path.read_text(encoding='utf-8')
    path.write_text(text.replace(old_acd,PINS['acdSha256']).replace(old_source,PINS['sourceSha256']),encoding='utf-8')
(D/'canonical.sha256').write_text(PINS['acdSha256']+'\n',encoding='utf-8')
capacity=json.loads((W/'capacity_auto_01.json').read_bytes())
with (D/'capacity_review.json').open('w',encoding='utf-8') as stream:json.dump(capacity,stream,indent=2)
approval=json.loads((D/'authorization.template.json').read_bytes())
approval.update(CanonicalSha256=PINS['acdSha256'],SourceSha256=PINS['sourceSha256'])
approval['OwnerCapacityConfirmed']={key:capacity[key] for key in
    ('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')}
approval['Scope']+=' Cold first-scan view formatting is deferred behind invalid publication with full buffer clearing; retained access masking stays immediate. Desktop qualification requires LIVE/nonempty complete coverage and records refresh/forest diagnostics.'
with (D/'authorization.template.json').open('w',encoding='utf-8') as stream:json.dump(approval,stream,indent=2)
(D/'canonical_prepared_compare.json').rename(D/'template_previous_compare.json')
with (D/'canonical_prepared_compare.json').open('x',encoding='utf-8') as stream:
    result=subprocess.run([sys.executable,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_readback.py',
        str(W/'canonical_cold_01.L5X'),str(W/'prepared_readback_01.L5X')],stdout=stream,stderr=subprocess.STDOUT)
assert result.returncode==0
checks=W/'cold_authorization_checks_01.py'
text=checks.read_text(encoding='utf-8')
assert text.count("spec=importlib.util.spec_from_file_location")==1
checks.write_text(text.replace("spec=importlib.util.spec_from_file_location","sys.path.insert(0,str(D))\nspec=importlib.util.spec_from_file_location"),encoding='utf-8')
print(json.dumps(dict(prepared=True,authorized=False,controllerChanges=0,**PINS)))

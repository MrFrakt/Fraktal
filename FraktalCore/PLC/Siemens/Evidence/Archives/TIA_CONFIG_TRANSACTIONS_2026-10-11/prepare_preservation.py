"""Read-only preservation audits and metadata before freezing this measured slice."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

REPO = Path('C:/Projects/Fraktal')
WORK = Path(__file__).resolve().parent
ACCESS = REPO / 'Specification/Siemens/Evidence/TIA_ACCESS_SESSIONS_2026-10-11'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    data = (json.dumps(value, indent=2) + '\n').encode('ascii')
    path = WORK / name
    if path.exists():
        assert path.read_bytes() == data, 'Preserved audit differs: ' + name
    else:
        with path.open('xb') as stream:
            stream.write(data)


prior = json.loads((ACCESS / '22_prior_inventory.json').read_bytes())
checked = []
for relative, expected in prior['prior_files'].items():
    path = REPO / relative
    assert path.is_file() and digest(path) == expected, relative
    checked.append(relative)
assert len(checked) == 134
access_checked = []
for line in (ACCESS / 'SHA256SUMS').read_text('ascii').splitlines():
    expected, relative = line.split('  ', 1)
    path = REPO / relative
    assert path.is_file() and digest(path) == expected, relative
    access_checked.append(relative)
assert len(access_checked) == 3360
save('61_prior_preservation.json', {
    'older_available_files': len(checked), 'access_sha_bindings': len(access_checked),
    'unchanged': True, 'older_reports_absent': prior['referenced_reports_missing'],
    'older_18_manifests_absent_not_reverified': True,
    'checked_older_paths': checked, 'checked_access_paths': access_checked,
    'access_manifest_sha256': digest(ACCESS / 'SHA256SUMS'),
})

state = REPO / 'Specification/Siemens/Evidence/TIA_STATE_ALARMS_2026-10-11'
state_paths=[]
for line in (state/'SHA256SUMS').read_text('ascii').splitlines():
    expected,relative=line.split('  ',1)
    assert digest(REPO/relative)==expected, relative
    state_paths.append(relative)
assert len(state_paths)==3179
save('62_state_preservation.json',{'unchanged':True,'state_sha_bindings':len(state_paths),'manifest_sha256':digest(state/'SHA256SUMS')})
driver=REPO/'FraktalCore/PLC/Siemens/tools/TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe'
assert digest(driver)=='e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33'
save('63_driver_preservation.json',{'unchanged':True,'sha256':digest(driver)})
print(json.dumps({'older_available_unchanged':len(checked),'access_sha_bindings':len(access_checked),'state_sha_bindings':len(state_paths),'driver_unchanged':True}))
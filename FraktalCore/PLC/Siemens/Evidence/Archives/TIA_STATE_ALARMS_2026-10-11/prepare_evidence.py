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
save('40_prior_preservation.json', {
    'older_available_files': len(checked), 'access_sha_bindings': len(access_checked),
    'unchanged': True, 'older_reports_absent': prior['referenced_reports_missing'],
    'older_18_manifests_absent_not_reverified': True,
    'checked_older_paths': checked, 'checked_access_paths': access_checked,
    'access_manifest_sha256': digest(ACCESS / 'SHA256SUMS'),
})

driver = REPO / 'FraktalCore/PLC/Siemens/tools/TiaCli/bin/candidate_s11_enumeration/Fraktal.Tia.Cli.exe'
driver_hash = digest(driver)
assert driver_hash == 'e455ee93e616c4788001b07830164da92b72e3817d6a90c90e03d98937026f33'
save('41_preservation_metadata.json', {
    'driver_sha256': driver_hash, 'runtime_project': str(Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/Alarm_Runtime_20261011/FrkS12/FrkS12.ap20'),
    'compiler_project': str(Path(os.environ['LOCALAPPDATA']) / 'Fraktal/TiaStations/Alarm_Verify_20261011/FrkS12/FrkS12.ap20'),
    'native_state_alarm': 96, 'nested_alarm': 23, 'postboot_nested_alarm': 23,
    'auth_regression': 122, 'earlier_routing_candidate': 120,
    'native_blocks_interfaces': [148, 45], 'production_blocks_interfaces': [142, 45],
    'hmi_passed': 570, 'hmi_skipped': 1, 'tools_passed': 128, 'consistency_tests_passed': 33,
    'keeper_pid': int((WORK / '36_keeper.pid').read_text()), 'keeper_must_remain_alive': True,
    'new_whitelist_or_driver_build': False, 'physical_target_mutation': False,
    'staged_committed_pushed': False,
})

changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=REPO).decode().splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=REPO).decode().splitlines()
rows = []
for relative in sorted(set(changed + untracked)):
    if not (relative.startswith('FraktalCore/PLC/Siemens/') or relative.startswith('FraktalCore/HMI/')):
        continue
    path = REPO / relative
    if not path.is_file():
        continue
    data = path.read_bytes()
    assert b'\r\n' not in data, 'Authored CRLF: ' + relative
    if path.suffix in ('.scl', '.udt', '.db', '.plan') or path.name.endswith('.scl.in'):
        assert data.isascii(), 'Authored non-ASCII SCL: ' + relative
    rows.append({'path': relative, 'sha256': digest(path), 'lf': True})
for name in ('final_state.py', 'restore_saved_instance.ps1'):
    data = (WORK / name).read_bytes()
    assert data.isascii() and b'\r\n' not in data
save('48_final_authored_source_checks.json', {'checked': len(rows), 'rows': rows})
save('32_preflight_failure.json', {
    'scope': 'read-only after VM reboot', 'registered_instances': 0,
    'https': 'TimeoutError: timed out', 'target': '169.254.212.49:443',
    'recovery': 'saved owner Fraktal persistence; no download or explicit unregister',
})
print(json.dumps({'available_older': len(checked), 'access_bindings': len(access_checked),
                  'authored_files': len(rows), 'driver_unchanged': True}))

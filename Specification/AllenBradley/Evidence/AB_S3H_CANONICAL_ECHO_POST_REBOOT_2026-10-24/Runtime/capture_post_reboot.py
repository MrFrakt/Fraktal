"""Read-only post-reboot readiness, startup logs and existing source bindings."""
from pathlib import Path
import datetime
import hashlib
import json
import sqlite3
import subprocess

R = Path(__file__).parent
PREVIOUS = Path('C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb')
P = PREVIOUS.parent / 'diagnostic_0b74f072e0d74c7c97531e07dec70898'
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
VENDOR = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo')
CONTROLLER = VENDOR / 'Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    with (R / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

host_command = r'''
$ErrorActionPreference='Stop'
$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -eq 44818} | ForEach-Object {
    [pscustomobject]@{address=$_.LocalAddress;port=$_.LocalPort;pid=$_.OwningProcess;process=(Get-Process -Id $_.OwningProcess).ProcessName}
})
$emulators=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'EmulateControlLogix5580.exe'} | Select-Object ProcessId,Name)
[pscustomobject]@{
    capturedUtc=[DateTime]::UtcNow.ToString('o')
    lastWindowsBootUtc=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
    service=(Get-Service 'FactoryTalk Logix Echo Service').Status.ToString()
    listeners=$listeners
    emulators=$emulators
} | ConvertTo-Json -Depth 5 -Compress
'''
process = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', host_command],
                         check=True, text=True, capture_output=True)
host = json.loads(process.stdout)
save('host_readiness_01.json', host)
state = json.loads((R / 'echo_inspect_post_windows_reboot_01.log').read_text())
assert state['SerialNumber'] == 0x601FC87B
assert state['ControllerGuid'] == '91dec7d6-8ac3-45c9-ab2e-0d039c7006fd'
assert state['Address'] == '127.0.0.1' and state['Slot'] == 0
assert state['FirmwarePackageVersion'] == dict(Major=38, Minor=11, Subminor=0)

service_lines = (VENDOR / 'logfile.log').read_text(encoding='utf-8', errors='replace').splitlines()
startup = [line for line in service_lines if line.startswith('2026-10-24 ') and any(word in line for word in (
    'Starting Echo Service', 'Personalized license is active', 'Echo Service is ready',
    'Initializing ControllerSupervisor', 'Restoring controllers', '91dec7d6-8ac3-45c9-ab2e-0d039c7006fd',
))]
assert any('exited unexpectedly with exit code 1' in line for line in startup)
with (R / 'service_startup_excerpt_01.log').open('x', encoding='utf-8') as f:
    f.write('\n'.join(startup) + '\n')
output = (CONTROLLER / 'output.log').read_text(encoding='utf-8', errors='replace').splitlines()
with (R / 'emulator_startup_excerpt_01.log').open('x', encoding='utf-8') as f:
    f.write('\n'.join(line for line in output if line.startswith('2026-10-24 ')) + '\n')

metadata = []
for relative in ('pwrDown.dat', 'pwrDown.inf', 'FaultRecord.bin',
                 'sd/RockwellAutomation/601FC87B/Faults/FaultDump.dmp'):
    path = CONTROLLER / relative
    stat = path.stat()
    row = dict(path=relative, bytes=stat.st_size,
               modifiedUtc=datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc).isoformat(),
               archived=False)
    if path.suffix != '.dmp':
        row['sha256'] = sha(path)
    metadata.append(row)

bindings = json.loads((PREVIOUS / 'initial_source_verification.json').read_text())
for relative, expected in bindings['sha256'].items():
    assert sha(ROOT / relative) == expected, relative
for relative, expected in bindings['diagnosticBindings'].items():
    assert sha(P / relative) == expected, relative
assert sha(P / 's3h_canonical.ACD').upper() == bindings['preparedAcdSha256']
assert not (P / 'deploy_attempt.json').exists()
assert not (P / 'echo_before_s3h.ACD').exists()
approval = json.loads((P / 'authorization.json').read_text())
assert approval['CurrentOwnerApproved'] and approval['ReadTimingDiagnosticsAuthorized']
assert approval['ApprovalQuestion'] == 'call_b76d12f2f038411386f83c339fcd94e0:0'

database = Path('C:/ProgramData/Rockwell/FTDiagnostics/FTDiagBuffer.sqlite')
with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=2) as connection:
    connection.execute('PRAGMA query_only=ON')
    buffer_count = connection.execute('SELECT count(*) FROM cache').fetchone()[0]
save('diagnostics_buffer_observation_01.json', dict(
    readOnly=True, databasePath=str(database), bufferRows=buffer_count,
    qualification='This local buffer alone does not establish whether other FactoryTalk Diagnostics destinations contain messages.',
    databaseArchived=False, messageValuesExported=False))

dump = json.loads((R / 'emulator_dump_metadata_01.json').read_text())
stack = json.loads((R / 'emulator_stack_01.json').read_text())
prior_dump = json.loads((PREVIOUS / 'emulator_dump_metadata_01.json').read_text())
prior_stack = json.loads((PREVIOUS / 'emulator_stack_01.json').read_text())
offsets = lambda rows: [frame['offset'] for frame in rows['frames'] if Path(frame.get('module', '')).name.lower() == 'libcomms.dll']
result = dict(
    capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    ownerReportedWindowsReboot=True, host=host, target=state,
    controllerReady=False, diagnosticApprovalConsumed=False,
    diagnosticApprovalQuestion=approval['ApprovalQuestion'],
    diagnosticNativeDownloadAttempted=False, controllerChangingOperations=0,
    plcDownloads=0, tagWrites=0, modeCommands=0, faultClears=0, clockChanges=0,
    powerStateChanges=0, controllerDefinitionChanges=0,
    stateFilesMetadataOnly=metadata, nativeMemoryDumpArchived=False,
    startupException=dump['exception'],
    sameExceptionCodeAndModuleOffset=(dump['exception']['code'] == prior_dump['exception']['code'] and
                                    dump['exception']['moduleOffset'] == prior_dump['exception']['moduleOffset']),
    libCommsFrameOffsets=offsets(stack), sameLibCommsFrameOffsets=offsets(stack) == offsets(prior_stack),
    underlyingCauseConfirmed=False, sourceBindingsUnchanged=len(bindings['sha256']),
    diagnosticBindingsUnchanged=len(bindings['diagnosticBindings']),
    preparedAcdSha256=sha(P / 's3h_canonical.ACD'),
    initialMetadataProbeCorrection='Root/FaultDump.dmp was absent; the existing reader uses the correct sd/RockwellAutomation/601FC87B/Faults/FaultDump.dmp path.',
)
save('post_reboot_observation_01.json', result)
print(json.dumps({key: result[key] for key in (
    'controllerReady', 'diagnosticApprovalConsumed', 'controllerChangingOperations',
    'sameExceptionCodeAndModuleOffset', 'sameLibCommsFrameOffsets',
    'sourceBindingsUnchanged', 'diagnosticBindingsUnchanged')}))

"""Bind the owner's external crash diagnosis without copying any memory dump."""
from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).parent
source=Path('C:/Users/SoftIndVM/Documents/ReverseEngineerAgent')
note=source/'notes/studio5000/echo_crash_re_2026-10-24.md'
log=source/'logs/ghidra_libcomms10.log'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
text=log.read_text(encoding='utf-8')
assert 'CMP dword ptr [ESI],0x1' in text and 'FUN_da50c280(*_DAT_dba1a6dc,0xf8006148' in text
reference=R/'Reference';reference.mkdir()
for src in (note,log):
    with (reference/src.name).open('xb') as out:out.write(src.read_bytes())
module=Path('C:/Program Files (x86)/Rockwell Software/FactoryTalk Logix Echo/Firmware Packages/979cf5b0-3243-581d-819c-2c9f87041c39/libComms.dll')
assert sha(module)=='3bbef14d20e182ddffb0a1a8e2c72ca7dadffd5df5f6667528812b64efaefb9b'
controller=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
dumps=[dict(path=p.relative_to(controller).as_posix(),bytes=p.stat().st_size,
            modifiedUtc=datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat())
       for p in sorted(controller.rglob('*.dmp'))]
result=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    readOnly=True,controllerChanges=0,reportPath=str(note),reportSha256=sha(note),ghidraLogSha256=sha(log),
    installedLibCommsSha256=sha(module),reportedFaultRva='0x50C2A4',
    faultInstructionAndLoggingCallCorroborated=True,
    mechanism='Unchecked trace-context pointer on the expected-length I/O error-logging path, per decompiled code and matching native exception/frames.',
    triggerAttribution='The external report attributes the triggering short restore read to power-down state corrupted after the earlier forced service shutdown. This session did not reproduce that corruption.',
    operationalRules=['No hard-kill of emulator/service on controller fault; allow orderly shutdown.',
                      'Inspect controller dump folders after a controller fault and before any later reboot.',
                      'Retain new diagnostic artifacts; any movement/removal of vendor state or dump files is outside this download session.'],
    externalColdBootScriptExecutedByThisSession=False,vendorBinariesModified=False,nativeDumpArchived=False,
    observedAfterExternalRecovery='Exact controller was reachable and not faulted, but two raw Symbol reads returned empty lists; the genealogy baseline was therefore restored before original S3h guards.',
    currentDumpFilesMetadataOnly=dumps)
with (R/'reverse_engineering_review_01.json').open('x') as out:json.dump(result,out,indent=2)
with (R/'dumps_before_candidate_01.json').open('x') as out:
    json.dump(dict(capturedUtc=result['capturedUtc'],readOnly=True,dumpFiles=dumps),out,indent=2)
print(json.dumps(dict(reviewed=True,reportSha256=sha(note),loggingNullDereferenceCorroborated=True,currentDumpFiles=len(dumps),controllerChanges=0)))

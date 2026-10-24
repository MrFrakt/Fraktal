from pathlib import Path
import datetime,hashlib,json,re
R=Path(__file__).parent;P=R.parent/'diagnostic_0b74f072e0d74c7c97531e07dec70898'
base=Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo')
root=base/'Controllers/91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lines=(base/'logfile.log').read_text(errors='replace').splitlines()
selected=[line for line in lines if line.startswith('2026-10-23 ') and re.search(
 r'PRESHUTDOWN|91dec7d6-8ac3-45c9-ab2e-0d039c7006fd|Personalized license is active|Service is ready',line)]
with (R/'echo_service_startup_excerpt_01.log').open('x',encoding='utf-8') as f:f.write('\n'.join(selected)+'\n')
with (R/'emulator_output_snapshot_01.log').open('xb') as f:f.write((root/'output.log').read_bytes())
state=json.loads((R/'echo_full_inspect_post_restart_01.log').read_text())
assert state['ErrorCode']=='ClosedExternally' and state['IsEnabled'] and not state['IsFaulted']
assert not (P/'deploy_attempt.json').exists() and not (P/'backup.sha256').exists()
pins=json.loads((R/'initial_source_verification.json').read_text());ROOT=Path('C:/Users/SoftIndVM/Fraktal')
for n,pin in pins['sha256'].items():assert sha(ROOT/n)==pin,n
for n,pin in pins['diagnosticBindings'].items():assert sha(P/n)==pin,n
files=[]
for name in ('pwrDown.dat','pwrDown.inf','FaultRecord.bin','sd/RockwellAutomation/601FC87B/Faults/FaultDump.dmp'):
 p=root/name;s=p.stat();row=dict(path=name,bytes=s.st_size,modifiedUtc=datetime.datetime.fromtimestamp(s.st_mtime,datetime.timezone.utc).isoformat(),archived=False)
 if name!='sd/RockwellAutomation/601FC87B/Faults/FaultDump.dmp':row['sha256']=sha(p)
 files.append(row)
report=dict(capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),restartPassed=False,
 restartApprovalQuestion='call_37bd66c3442340b08084fd7b2deb2ce5:0',restartApprovalConsumed=True,
 disableApplied=True,enableRequested=True,enableFailedDuringEmulatorStartup=True,observedPowerFlagSequence=[True,False,True],
 postState=state,diagnosticApprovalQuestion='call_b76d12f2f038411386f83c339fcd94e0:0',diagnosticApprovalConsumed=False,
 diagnosticExecuted=False,plcDownloads=0,tagWrites=0,modeCommands=0,faultClears=0,clockChanges=0,
 sourceBindingsUnchanged=159,diagnosticBindingsUnchanged=2,stateFilesMetadataOnly=files,
 startupException=json.loads((R/'emulator_dump_metadata_01.json').read_text())['exception'],
 underlyingCauseConfirmed=False,controllerDefinitionDeleted=False,stateFilesModifiedByAgent=False,
 nativeDumpArchived=False,credentialFilesArchived=False)
with (R/'restart_failure_01.json').open('x') as f:json.dump(report,f,indent=2)
with (R/'restart_authorization_consumed_01.json').open('x') as f:
 json.dump(dict(consumed=True,approvalQuestion=report['restartApprovalQuestion'],
  reason='One authorized disable/re-enable attempted; emulator exited with code 1 during enable; no repeat authorized',
  originalDiagnosticApprovalConsumed=False,capturedUtc=report['capturedUtc']),f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('stateFilesMetadataOnly',)},indent=2))

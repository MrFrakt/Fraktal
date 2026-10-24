"""Fixed S3h fixture with read-only timing evidence; acceptance stays unchanged.

The inherited fixture owns every controller write. This wrapper records wire
timing and, after a failed acquisition only, reads the existing TASK mirrors.
No protocol, read plan, comparison, poll/time budget or fixture vector changes.
"""
from pathlib import Path
import gzip,json,sys,time

TOOLS=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0,str(TOOLS))
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_paired_socket_reads as sockets
import fraktal_ab_s3h_fixture_execute as fixture

TASK_TAGS=tuple('FRK_Press_'+owner+'.'+leaf for owner,leaves in (
 ('CanonicalTiming',('Scan','LastScanUs','MaxScanUs','OverlapCount')),
 ('HealthProbe',('Samples','TaskLastScanUs','TaskMaxScanUs','TaskOverlapCount')))
 for leaf in leaves)


def instrument(scan,comm,tags,generation,*,destination,**options):
    if destination.exists():raise ValueError('new diagnostic evidence required')
    started=time.perf_counter_ns();polls=[];windows=[];last_frames=[]
    original_acquire=sockets.acquire
    report=dict(readOnly=True,acceptanceChanged=False,controllerWritesAdded=0,
        timingOverhead='perf_counter_ns calls and bounded in-memory timing rows inside original window; gzip/JSON outside proof',
        taskReadsOnlyAfterFailure=True,frameScope='last attempted acquisition; not an accepted snapshot')
    def stamp():return (time.perf_counter_ns()-started)/1000
    def generation_read():
        before=stamp();value=generation();after=stamp()
        polls.append(dict(startUs=before,endUs=after,generation=value))
        return value
    def acquire(channels,plans):
        nonlocal last_frames
        before=stamp();responses=original_acquire(channels,plans);after=stamp()
        windows.append(dict(startUs=before,endUs=after,elapsedUs=after-before))
        last_frames=(plans,responses)
        return responses
    sockets.acquire=acquire
    try:
        pair=scan(comm,tags,generation_read,**options)
        report.update(acquisitionPassed=True,stateEvidence=pair['stateEvidence'])
        return pair
    except Exception as error:
        report.update(acquisitionPassed=False,error=f'{type(error).__name__}: {error}',attempts=getattr(error,'attempts',[]))
        # No other acquisition is outstanding here: the original owner has
        # completed/closed every socket before returning or raising.
        try:
            task=comm.Read(list(TASK_TAGS))
            report['taskAfterFailure']=[dict(tag=r.TagName,status=str(r.Status),value=r.Value) for r in task]
        except Exception as diagnostic_error:
            report['taskReadError']=f'{type(diagnostic_error).__name__}: {diagnostic_error}'
        raise
    finally:
        sockets.acquire=original_acquire
        report.update(generationPolls=polls,readWindows=windows)
        if last_frames:
            plans,replies=last_frames
            report['lastAttemptFrames']=[dict(connection=i,plan={k:v for k,v in item.items() if k!='request'},
                status=reply[0],rawHex=reply[1].hex()) for i,(plan,group) in enumerate(zip(plans,replies,strict=True))
                for item,reply in zip(plan,group,strict=True)]
        # Evidence I/O must never mask the original acquisition result/error.
        try:
            with destination.open('xb') as f:f.write(gzip.compress(json.dumps(report,allow_nan=False).encode(),mtime=0))
        except Exception as file_error:
            print('diagnostic evidence write failed: '+str(file_error),file=sys.stderr)


def main():
    workspace=Path(__file__).parent
    approval=json.loads((workspace/'authorization.json').read_text())
    if (approval.get('CurrentOwnerApproved') is not True
        or approval.get('ReadTimingDiagnosticsAuthorized') is not True
        or approval.get('Serial')!='601FC87B'
        or approval.get('CanonicalSha256')!=(workspace/'canonical.sha256').read_text().strip()
        or approval.get('FaultClearAuthorized') is not False
        or approval.get('ClockSetAuthorized') is not False):
        raise SystemExit('current exact-image diagnostic session authorization required')
    if '--output' not in sys.argv:raise SystemExit('--output is required by diagnostic wrapper')
    destination=Path(sys.argv[sys.argv.index('--output')+1])
    if destination.exists():raise SystemExit('new fixture output required')
    original_scan=shared._scan_reads;counter=0
    def observed(comm,tags,generation,**options):
        nonlocal counter
        counter+=1
        path=destination.with_name(destination.stem+f'_window_diagnostic_{counter:03}.json.gz')
        return instrument(original_scan,comm,tags,generation,destination=path,**options)
    shared._scan_reads=observed
    try:return fixture.main()
    finally:shared._scan_reads=original_scan


if __name__=='__main__':raise SystemExit(main())

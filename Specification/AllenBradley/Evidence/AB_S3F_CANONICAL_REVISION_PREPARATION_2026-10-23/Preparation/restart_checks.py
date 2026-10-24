"""Read-only checks around the separately authorized retained Program/Run cycle."""
from pathlib import Path
import argparse,json,os,subprocess,sys
W=Path(__file__).parent


def compare(before,after):
    for key in ('records','banks','codes','active','mode','policy','page'):
        if before[key]!=after[key]:raise ValueError('retained restart changed '+key)
    for value in (before['revision'],after['revision']):
        if type(value) is not int or not 1<=value<=2147483646:raise ValueError('invalid revision')
    if before['revision']==after['revision']:raise ValueError('retained restart repeated revision')


def snapshot():
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
    sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
    from pylogix import PLC
    import fraktal_ab_part_execute as fixture
    import fraktal_ab_projection as projection
    import fraktal_ab_press_execute as execute
    import fraktal_ab_models as models
    import fraktal_ab_genealogy_demo as demo
    import fraktal_ab_genealogy_s3f_demo as candidate
    import fraktal_ab_s3f_fixture_execute as s3f
    import fraktal_ab_canonical_reader as reader
    subprocess.run([sys.executable,str(W/'scripts/guard_echo.py')],check=True)
    app=demo.application()
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
        comm=fixture.Guarded(native,0x601FC87B,app);comm.guard()
        unit=execute.read_unit(comm);authority=projection.read_access(comm)
        if (unit is None or unit['Mode']!=app.manual_mode or any(unit[k] for k in ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest'))
            or authority is None or authority['CurrentLevel']!=0 or authority['LoginBusy']):raise ValueError('retained restart requires MANUAL/idle/logout')
        if projection.read_document(comm)['liveConfig'].restoring:raise ValueError('configuration still restoring')
        document,capture=reader.read_document(comm,expect_serial='601FC87B')
        if capture['manifest']['contentHash']!=s3f.expected_manifest(candidate.application()):raise ValueError('wrong S3f publication')
        if document['values'][app.name+'/HmiResponse/ConfigPage/Revision']!=document['values'][app.name+'/Status/ConfigRev']:
            raise ValueError('page revision differs from live configuration')
        codes=models.read(comm,app)
        if not codes:raise ValueError('model catalogue missing')
        records=projection.read_records(comm);banks=projection.read_models(comm,len(codes));policy=projection.read_data_access(comm,policy=True)
        if not records or any(v is None for v in records.values()) or banks is None or policy is None:raise ValueError('configuration read failed')
        return dict(records=records,banks=banks,codes=codes,active=unit['ModelOrdinal'],mode=unit['Mode'],policy=policy,
            page={p:v for p,v in document['values'].items() if p.startswith(app.name+'/HmiResponse/ConfigPage/') and not p.endswith('/Revision')},
            revision=document['values'][app.name+'/Status/ConfigRev'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('before','after'));args=parser.parse_args()
    output=W/('restart_'+args.phase+'.json')
    if output.exists():parser.error('new restart evidence required')
    value=snapshot()
    if args.phase=='after':compare(json.loads((W/'restart_before.json').read_text())['snapshot'],value)
    with output.open('x') as f:json.dump(dict(passed=True,readOnly=True,snapshot=value),f,indent=2)
    print(json.dumps(dict(passed=True,phase=args.phase,revision=value['revision'])))
if __name__=='__main__':main()

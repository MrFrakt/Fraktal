"""Generate an S3g bench image with bounded, first-scan native arithmetic checks.

The generator APIs emit the complete image; no serialized L5X body is edited.
Production declarations never enable this apparatus. Results are separate,
read-only controller tags. Profiler input changes are six fixed DINT cells,
saved and restored in the same scan before normal canonical publication.
Deploying this image requires explicit authorization for these native vectors.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch

import fraktal_ab_canonical_metrics as metrics
import fraktal_ab_canonical_publication as pub
import fraktal_ab_genealogy_s3g_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_s3g_reference as reference

BENCH=pub.PREFIX+'NativeMetricsBenchS3gV63'
VECTOR=pub.PREFIX+'NativeOeeVectorS3gV63'
VECTORS=(
    (1,2,1,2,1), (0,0,0,0,0), (4294967296,0,0,0,1000),
    (2147483648,2147483648,4294967295,1,1000),
    (100,10,1,1,1000), (1,1,0,0,0), (4294967295,1,1,0,1),
    (16777217,3,16777217,2,1), (4294967295,3,2147483648,17,1000),
)
PROFILER_CELLS=tuple((name,slot) for slot in (0,1) for name in ('StatCount','StatAvg','StatMax'))


def tag(app):return f'FRK_{app.name}_S3gNativeChecks'
def routine(app):return f'FRK_{app.name}_S3gNativeChecks'


def definitions(app,held):
    M=pub.Member
    held[VECTOR]=tuple(M(name,'LINT') for name in ('Run','Down','Good','Nok','Ideal'))
    held[BENCH]=(M('Completed','BOOL'),M('Index','DINT'),M('Inputs',VECTOR,count=len(VECTORS)),
        M('OeeResults',metrics.OEE,count=len(VECTORS)),M('StatsResults',metrics.STATS,count=2),
        M('Saved','DINT',count=len(PROFILER_CELLS)))


def initial():
    return dict(Inputs=[dict(zip(('Run','Down','Good','Nok','Ideal'),row)) for row in VECTORS])


def logic(app):
    b=tag(app);w=metrics.state_tag(app);p=gen.profiler_tag(app);index=b+'.Index'
    lines=[f'{b}.Completed := 0;',f'{w}.Wrap := 2147483647;',f'{w}.Wrap := {w}.Wrap * 2 + 2;',f'{w}.SignedEdge := {w}.Wrap / 2;',
        f'FOR {index} := 0 TO {len(VECTORS)-1} DO']
    lines += [f'{w}.{name} := {b}.Inputs[{index}].{name};' for name in ('Run','Down','Good','Nok','Ideal')]
    lines += [f'{w}.Idle := 0;',f'JSR({metrics.factor_routine(app)},0);',f'CPS({w}.Factors,{b}.OeeResults[{index}],1);','END_FOR;']
    lines += [f'{b}.Saved[{i}] := {p}.{name}[{slot}];' for i,(name,slot) in enumerate(PROFILER_CELLS)]
    for slot,count in ((0,-2147483648),(1,-1)):
        lines += [f'{p}.StatCount[{slot}] := {count};',f'{p}.StatAvg[{slot}] := 123;',f'{p}.StatMax[{slot}] := 456;']
    lines += [f'{w}.Initialized := 0;',*metrics.profiler(app)]
    lines += [f'CPS({app.name}.Profiler.StepStats[{slot}],{b}.StatsResults[{slot}],1);' for slot in (0,1)]
    lines += [f'{p}.{name}[{slot}] := {b}.Saved[{i}];' for i,(name,slot) in enumerate(PROFILER_CELLS)]
    return lines+[f'{w}.Initialized := 0;',f'{b}.Completed := 1;']


def generate(seed,output):
    app=demo.application()
    augment,tags,cyclic,routines=metrics.augment,metrics.tags,metrics.cyclic,metrics.routines
    def with_definitions(app,held):augment(app,held);definitions(app,held)
    def with_tags(app,serialize):return tags(app,serialize)+[serialize(tag(app),BENCH,initial())]
    def with_cyclic(app):return [f'IF S:FS THEN JSR({routine(app)},0); END_IF;']+cyclic(app)
    def with_routines(app):return routines(app)+[(routine(app),logic(app))]
    with ExitStack() as stack:
        for name,value in (('augment',with_definitions),('tags',with_tags),('cyclic',with_cyclic),('routines',with_routines)):
            stack.enter_context(patch.object(metrics,name,value))
        return gen.generate(app,seed,output)


def verify_result(app,result):
    """Check read-only native results against the independently versioned math."""
    if result['Completed'] is not True:raise ValueError('native checks did not complete')
    for i,vector in enumerate(VECTORS):
        row=result['OeeResults'][i];expected=reference.factors(*vector)
        expected.update(RunMs=vector[0]&0xffffffff,DownMs=vector[1]&0xffffffff,IdleMs=0)
        actual={k:(v&0xffffffff if k in ('RunMs','DownMs','IdleMs') else v) for k,v in row.items()}
        if actual!=expected or {k:type(v) for k,v in actual.items()}!={k:type(v) for k,v in expected.items()}:
            raise ValueError(f'native OEE vector {i} differs: {actual!r} != {expected!r}')
    steps=metrics.first_steps(app)
    for i,count in enumerate((2147483648,4294967295)):
        row=result['StatsResults'][i];label=row['Label'];length=label['LEN']
        text=bytes.fromhex(label['bytes']).decode('utf-8') if label.get('string') else bytes(x&255 for x in label['DATA'][:length]).decode('utf-8')
        if (row['Id'],text,row['TimeClass'],row['Count']&0xffffffff,row['Avg'],row['Maximum']) != (
                steps[i].number,'project.step.'+steps[i].name,metrics.decl.TIME_CLASSES.index(steps[i].time_class),count,123,456):
            raise ValueError(f'native profiler vector {i} differs')
    return dict(passed=True,oeeVectors=len(VECTORS),profilerHighBitVectors=2,readOnly=True)


def read_results(comm):
    """Read-only exact-image check; no fixture writes or arbitrary targets."""
    import fraktal_ab_canonical_reader as reader
    import fraktal_ab_s3f_fixture_execute as fixture
    device=comm.GetDeviceProperties()
    if device.Status!='Success' or device.Value is None or (
            str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision
            )!=('0x601fc87b','Emulate 5580 Controller','38.11'):
        raise ValueError('fixed local Echo identity guard failed')
    app=demo.application();unused,capture=reader.read_document(comm,expect_serial='601FC87B')
    if capture['manifest']['contentHash']!=fixture.expected_manifest(app):raise ValueError('S3g publication required')
    symbol=next(s for s in capture['symbols'] if s['name']==tag(app))
    response=comm.Read(tag(app))
    if response.Status!='Success' or not isinstance(response.Value,bytes):raise ValueError('native result read failed')
    result=reader.decode_record(response.Value,symbol['handle'],capture['templates'])
    return dict(verify_result(app,result),result=result,rawHex=response.Value.hex(),symbol=symbol,templates=capture['templates'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('new generated output required')
    generate(args.seed,args.output)
    return 0


if __name__=='__main__':raise SystemExit(main())

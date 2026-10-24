"""Read-only S2 migration gate on the fixed local genealogy Echo fixture.

Declaration knowledge exists only on this acceptance-oracle side. The canonical
reader discovers its data solely from PLC Symbol/Template/manifest objects.
"""
from copy import deepcopy
import argparse
import gzip
import json
import os
from pathlib import Path

from fraktal_ab_canonical_reader import read_document, snapshot
from fraktal_ab_canonical_manifest import read_manifest
from fraktal_ab_canonical_equivalence import compare_live, stable_scan_pair


def subset_paths(app):
    """Explicit S2 contract; never use actual discovered paths to choose a subset."""
    paths=set()
    for module in (None,*app.modules):
        base=app.name+('/'+module.name if module else '')+'/Status/'
        paths.update(base+leaf for leaf in ('Name','DisplayNameKey','ModuleType','State','FaultActive'))
        if (module.type_key if module else app.type_key):paths.add(base+'TypeKey')
    paths.update(app.name+'/'+leaf for leaf in ('ModeActivePublished','RunStyle','CurrentStep/StepNo'))
    if app.models:paths.add(app.name+'/Model/ModelCode')
    return paths


def oracle(app, rows, unit, contexts, codes):
    import fraktal_ab_projection as projection
    values={}
    for module in projection.modules(rows):
        base=module['base']
        values.update({base+'/Status/Name':module['identity'],
                       base+'/Status/ModuleType':module['type'],
                       base+'/Status/DisplayNameKey':module['displayNameKey']})
        if module['typeKey']:values[base+'/Status/TypeKey']=module['typeKey']
        detail=(projection.unit_status(unit,None) if module['type']==1 else
                projection.module_status(contexts[module['identity'].split('.')[-1]],app,
                                         module['identity'].split('.')[-1]))
        values.update({base+'/'+path:value for path,value in detail.items()})
    values.update({app.name+'/'+path:value for path,value in projection.model_status(app,unit,codes).items()})
    expected=subset_paths(app)
    if not expected<=values.keys():raise ValueError('projection lacks an S2 contract path')
    values={path:values[path] for path in expected}
    types={path:('Boolean' if type(value) is bool else 'String' if type(value) is str else 'Int32') for path,value in values.items()}
    if any(type(v) not in (bool,str,int) for v in values.values()):raise ValueError('unexpected S2 logical value type')
    return dict(values=values,types=types,typesSource='S2 logical contract and projection values; native legacy contexts are DINT')


def run(comm):
    # Pin this fixture before importing any legacy module with an APP singleton.
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_demo'
    import fraktal_ab_genealogy_canonical_demo as declaration
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as legacy
    import fraktal_ab_manifest_read as old_reader
    import fraktal_ab_press_execute as execute
    import fraktal_ab_projection as projection
    import fraktal_ab_models as models
    import fraktal_ab_canonical_publication as publisher
    app=declaration.application()
    device=comm.GetDeviceProperties()
    if device.Status!='Success' or device.Value is None or (
            str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision
    )!=('0x601fc87b','Emulate 5580 Controller','38.11'):
        raise ValueError('fixed local Echo identity guard failed')
    unused,seed=read_document(comm,expect_serial='601FC87B')
    expected=subset_paths(app)
    if set(seed['manifest']['annotations'])!=expected:
        raise ValueError('V6 field coverage differs from the explicit S2 contract')
    payload,status,unused=old_reader._read_raw(comm,legacy.header_tag(app))
    if payload is None:raise ValueError('legacy oracle manifest header unavailable')
    header=old_reader.decode_header(payload)
    projection.validate(header)
    if seed['manifest']['legacyContentHash']!=header['ContentHash']:
        raise ValueError('canonical manifest describes a different legacy image')
    rows={table.name:old_reader.read_table(comm,table)['rows'][:header[table.name+'Count']]
          for table in legacy.tables(app)}
    if legacy.mismatched_tables(app,header,rows):raise ValueError('legacy oracle tables differ from fixture')
    reads=[]
    class Recording:
        def Read(self,name):
            response=comm.Read(name)
            value=response.Value
            reads.append(dict(tag=name,status=response.Status,
                              rawHex=bytes(value).hex() if isinstance(value,(bytes,bytearray)) else None,
                              value=None if isinstance(value,(bytes,bytearray)) else value))
            return response
    recording=Recording()
    def generation():
        response=comm.Read(publisher.generation_tag(app))
        if response.Status!='Success':raise ValueError('PLC scan generation read failed')
        return response.Value
    def acquire():
        reads.clear()
        capture=deepcopy(seed)
        for record in capture['records']:
            response=recording.Read(record['tag'])
            if response.Status!='Success' or not isinstance(response.Value,(bytes,bytearray)):
                raise ValueError('canonical paired record read failed')
            record['rawHex']=bytes(response.Value).hex()
        unit=execute.read_unit(recording)
        contexts={m.name:execute.read_module(recording,m.name) for m in app.modules}
        codes=models.read(recording,app)
        if unit is None or any(v is None for v in contexts.values()):raise ValueError('legacy paired context read failed')
        return dict(capture=capture,legacyInputs=dict(unit=unit,contexts=contexts,codes=codes),rawReads=deepcopy(reads))
    # Warm only read caches; these samples never establish same-state proof.
    acquire()
    pair=stable_scan_pair(generation,acquire)
    # Decode/compare after closing the scan window; only controller reads need
    # to fit between the two generation samples.
    pair['canonical']=snapshot(pair['capture'])
    if set(pair['canonical']['values'])!=expected:
        raise ValueError('canonical snapshot path set differs from S2 contract')
    held=pair['legacyInputs']
    pair['projection']=oracle(app,rows,held['unit'],held['contexts'],held['codes'])
    if read_manifest(comm,seed['symbols'],seed['templates'])!=seed['manifest']:
        raise ValueError('V6 manifest changed after paired acquisition')
    trailing,status,unused=old_reader._read_raw(comm,legacy.header_tag(app))
    if trailing is None or old_reader.decode_header(trailing)!=header:
        raise ValueError('legacy manifest changed after paired acquisition')
    result=compare_live(lambda:pair)
    return dict(schema='fraktal.ab.s2-equivalence',schemaVersion=1,readOnly=True,
                serial='601FC87B',passed=result['equal'] and result['typeAcceptance'],
                comparison=result,pair=pair)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-serial',required=True,choices=('601FC87B',))
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('new evidence output required')
    from pylogix import PLC
    try:
        with PLC('127.0.0.1') as comm:
            comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,10
            report=run(comm)
    except Exception as error:
        report=dict(passed=False,readOnly=True,error=f'{type(error).__name__}: {error}',
                    attempts=getattr(error,'attempts',[]))
    opener=gzip.open if args.output.suffix=='.gz' else open
    with opener(args.output,'xt',encoding='utf-8') as stream:json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=report['passed'],error=report.get('error'))))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

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


def oracle(app, rows, unit, contexts, codes, *, expected=None, extra=None, logical_types=None):
    import fraktal_ab_projection as projection
    values={}
    catalogue={row['NumericKey']:row['PortableKey'] for row in rows['Localization']}
    for module in projection.modules(rows):
        base=module['base']
        values.update({base+'/Status/Name':module['identity'],
                       base+'/Status/ModuleType':module['type'],
                       base+'/Status/DisplayNameKey':module['displayNameKey']})
        if module['typeKey']:values[base+'/Status/TypeKey']=module['typeKey']
        detail=(projection.unit_status(unit,None) if module['type']==1 else
                projection.module_status(contexts[module['identity'].split('.')[-1]],app,
                                         module['identity'].split('.')[-1],catalogue))
        values.update({base+'/'+path:value for path,value in detail.items()})
    values.update({app.name+'/'+path:value for path,value in projection.model_status(app,unit,codes).items()})
    if extra is not None:
        values.update(extra(app,unit))
    expected=subset_paths(app) if expected is None else expected
    if not expected<=values.keys():raise ValueError('projection lacks a stage contract path')
    values={path:values[path] for path in expected}
    types={path:('Boolean' if type(value) is bool else 'String' if type(value) is str else 'Int32') for path,value in values.items()}
    if logical_types is not None:
        declared=logical_types(app,expected)
        if not declared.keys()<=expected:raise ValueError('logical type outside stage contract')
        types.update(declared)
    if any(type(v) not in (bool,str,int) for v in values.values()):raise ValueError('unexpected S2 logical value type')
    return dict(values=values,types=types,typesSource='Explicit stage logical contract and projection values; native legacy contexts are DINT')


def _scan_reads(comm, tags, generation, *, raw_sizes=None, cached_records=None):
    """Only wire reads belong inside the proof window; decode/copy afterwards."""
    tags=tuple(tags)
    if not tags or len(set(tags)) != len(tags):
        raise ValueError('paired read plan must contain unique tags')
    cached_records={} if cached_records is None else cached_records
    if not cached_records.keys()<=set(tags) or len(cached_records)==len(tags):
        raise ValueError('cached records must be a proper subset of paired tags')
    if cached_records and raw_sizes is None:
        raise ValueError('cached records require exact warmed sizes')
    for tag,response in cached_records.items():
        if response.Status!='Success' or not isinstance(response.Value,bytes) or len(response.Value)!=raw_sizes[tag]:
            raise ValueError('cached record differs from warmed size')
    if raw_sizes is not None:
        import fraktal_ab_paired_reads as batching
        # Larger legacy records first avoid stranding a partly filled batch
        # ahead of the next large record. Responses are still joined by tag.
        wire_tags=sorted((tag for tag in tags if tag not in cached_records),
                         key=lambda tag:raw_sizes[tag],reverse=True)
        read_plan=batching.plan(comm,wire_tags,raw_sizes)
        pair=stable_scan_pair(generation,lambda:dict(rawBatches=batching.acquire(comm,read_plan)))
        replies=pair.pop('rawBatches')
        # Decode only the accepted frame set after the closing generation read.
        decoded=batching.decode(read_plan,replies,raw_sizes)
        decoded.update(cached_records)
        pair['rawResponses']=[decoded[tag] for tag in tags]
        pair['readPlan']=[dict(kind=item['kind'],tags=item['tags']) for item in read_plan]
        return pair
    return stable_scan_pair(generation,lambda:dict(rawResponses=[comm.Read(tag) for tag in tags]))


def run(comm, *, application_factory=None, path_contract=None, extra_oracle=None, logical_types=None,
        additional_inputs=None):
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
    app=(application_factory or declaration.application)()
    device=comm.GetDeviceProperties()
    if device.Status!='Success' or device.Value is None or (
            str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision
    )!=('0x601fc87b','Emulate 5580 Controller','38.11'):
        raise ValueError('fixed local Echo identity guard failed')
    unused,seed=read_document(comm,expect_serial='601FC87B')
    if app.canonical_publication_stage == 2 and set(seed['manifest']['annotations'])!=subset_paths(app):
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
    def legacy_inputs(reader):
        unit=execute.read_unit(reader)
        contexts={m.name:execute.read_module(reader,m.name) for m in app.modules}
        codes=models.read(reader,app)
        if unit is None or any(v is None for v in contexts.values()):raise ValueError('legacy paired context read failed')
        result=dict(unit=unit,contexts=contexts,codes=codes)
        if additional_inputs is not None:result['additional']=additional_inputs(reader)
        return result
    # Warm caches and derive the legacy request plan through its owning readers.
    # These samples never establish same-state proof or supply accepted values.
    legacy_inputs(recording)
    tags=[record['tag'] for record in seed['records']]+[row['tag'] for row in reads]
    sizes={row['tag']:len(bytes.fromhex(row['rawHex'])) for row in [*seed['records'],*reads]}
    # V6.2 definition fragments are revision-controlled metadata. read_document
    # acquired them under equal manifest tokens; the trailing manifest check
    # below rejects any intervening update. Only live records belong inside
    # the entire-scan proof window. This is the same cache rule as V6.2, with
    # sources supplied by the PLC's bindings, never station-specific names.
    from types import SimpleNamespace
    sources={row['SourceSymbol'] for row in seed['manifest'].get('bindings',[])}
    cached={row['tag']:SimpleNamespace(Status='Success',Value=bytes.fromhex(row['rawHex']))
            for row in seed['records'] if row['tag'] in sources}
    pair=_scan_reads(comm,tags,generation,raw_sizes=sizes,cached_records=cached)
    if cached:
        pair['metadataEvidence']=dict(kind='V6.2 equal manifest revision',
            coherenceToken=seed['coherenceBefore'],sources=sorted(cached))
    responses=dict(zip(tags,pair.pop('rawResponses'),strict=True))
    class HeldReads:
        def Read(self,name):
            return responses[name]
    capture=deepcopy(seed)
    reads.clear()
    for record in capture['records']:
        response=responses[record['tag']]
        if response.Status!='Success' or not isinstance(response.Value,(bytes,bytearray)):
            raise ValueError('canonical paired record read failed')
        record['rawHex']=bytes(response.Value).hex()
    held=legacy_inputs(HeldReads())
    for name,response in responses.items():
        value=response.Value
        reads.append(dict(tag=name,status=response.Status,
                          rawHex=bytes(value).hex() if isinstance(value,(bytes,bytearray)) else None,
                          value=None if isinstance(value,(bytes,bytearray)) else value))
    pair.update(capture=capture,legacyInputs=held,rawReads=reads)
    # Decode/compare after closing the scan window; only controller reads need
    # to fit between the two generation samples.
    pair['canonical']=snapshot(pair['capture'])
    held=pair['legacyInputs']
    expected=path_contract(app,held['codes'],canonical=True) if path_contract else subset_paths(app)
    if set(pair['canonical']['values'])!=expected:
        raise ValueError('canonical snapshot path set differs from the explicit stage contract')
    pair['projection']=oracle(app,rows,held['unit'],held['contexts'],held['codes'],
                              expected=path_contract(app,held['codes'],canonical=False) if path_contract else None,
                              extra=(lambda a,u:extra_oracle(a,u,held['additional'])) if additional_inputs is not None else extra_oracle,
                              logical_types=logical_types)
    if read_manifest(comm,seed['symbols'],seed['templates'])!=seed['manifest']:
        raise ValueError('V6 manifest changed after paired acquisition')
    trailing,status,unused=old_reader._read_raw(comm,legacy.header_tag(app))
    if trailing is None or old_reader.decode_header(trailing)!=header:
        raise ValueError('legacy manifest changed after paired acquisition')
    result=compare_live(lambda:pair)
    return dict(schema='fraktal.ab.'+{2:'s2',3:'s3a',4:'s3b',5:'s3c',6:'s3d'}[app.canonical_publication_stage]+'-equivalence',schemaVersion=1,readOnly=True,
                serial='601FC87B',passed=result['equal'] and result['typeAcceptance'],
                comparison=result,pair=pair)


def main(run_gate=run, *, description=__doc__):
    parser=argparse.ArgumentParser(description=description)
    parser.add_argument('--expect-serial',required=True,choices=('601FC87B',))
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('new evidence output required')
    from pylogix import PLC
    try:
        with PLC('127.0.0.1') as comm:
            comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=0,4000,10
            report=run_gate(comm)
    except Exception as error:
        report=dict(passed=False,readOnly=True,error=f'{type(error).__name__}: {error}',
                    attempts=getattr(error,'attempts',[]))
    opener=gzip.open if args.output.suffix=='.gz' else open
    with opener(args.output,'xt',encoding='utf-8') as stream:json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=report['passed'],error=report.get('error'))))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

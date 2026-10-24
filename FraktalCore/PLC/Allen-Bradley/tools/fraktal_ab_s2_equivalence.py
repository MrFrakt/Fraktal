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
    import math
    if any(type(v) not in (bool,str,int) and not (
            type(v) is float and math.isfinite(v) and (
                app.canonical_publication_stage>=8 and types[path]=='Double' or
                app.canonical_publication_stage>=9 and types[path]=='Float'))
            for path,v in values.items()):raise ValueError('unexpected S2 logical value type')
    return dict(values=values,types=types,typesSource='Explicit stage logical contract and projection values; native legacy contexts are DINT')


def _scan_reads(comm, tags, generation, *, raw_sizes=None, cached_records=None,
                secondary_comm=None, secondary_tags=(), fragment_large=False, extra_comms=(), socket_reads=False):
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
    secondary_tags=set(secondary_tags)
    channels=[comm,secondary_comm,*extra_comms] if secondary_comm is not None else [comm]
    if extra_comms and (not fragment_large or secondary_comm is None):
        raise ValueError('extra connections require fragmented read partition')
    if len({id(c) for c in channels})!=len(channels):
        raise ValueError('each paired connection requires one distinct owner')
    live_tags=set(tags)-cached_records.keys()
    if secondary_tags and (secondary_comm is None or secondary_comm is comm or not secondary_tags<live_tags or raw_sizes is None):
        raise ValueError('secondary tags require a distinct nonempty live partition')
    if raw_sizes is not None:
        import fraktal_ab_paired_reads as batching
        # Larger legacy records first avoid stranding a partly filled batch
        # ahead of the next large record. Responses are still joined by tag.
        wire_tags=sorted((tag for tag in tags if tag not in cached_records),
                         key=lambda tag:raw_sizes[tag],reverse=True)
        if fragment_large:
            if not secondary_tags or any(c.ConnectionSize!=comm.ConnectionSize for c in channels):
                raise ValueError('fragment packet partition requires equal distinct connections')
            from fraktal_ab_paired_fragments import partition
            plans=partition(comm,wire_tags,raw_sizes,connections=len(channels))
            read_plan,secondary_plan=plans[:2]
        else:
            read_plan=batching.plan(comm,[tag for tag in wire_tags if tag not in secondary_tags],raw_sizes)
            secondary_plan=batching.plan(secondary_comm,[tag for tag in wire_tags if tag in secondary_tags],raw_sizes) if secondary_tags else []
            plans=(read_plan,secondary_plan)
        if secondary_plan and socket_reads:
            import fraktal_ab_paired_socket_reads as sockets
            if not fragment_large or len(channels)!=4:
                raise ValueError('socket multiplex requires four fragmented read owners')
            def acquire():
                return dict(rawBatches=[reply for group in sockets.acquire(channels,plans) for reply in group])
            pair=stable_scan_pair(generation,acquire,fresh_start=True)
            read_plan=[item for p in plans for item in p]
            pair['readConnections']=len(channels)
            pair['readTransport']='one outstanding read per socket; single multiplex owner'
        elif secondary_plan:
            from concurrent.futures import ThreadPoolExecutor
            # Each connection has exactly one owner. Warm the worker before
            # the proof; both acquisitions finish before its closing sample.
            with ThreadPoolExecutor(max_workers=len(channels)-1) as worker:
                for ready in [worker.submit(lambda:None) for c in channels[1:]]:ready.result()
                def acquire():
                    pending=[worker.submit(batching.acquire,c,p) for c,p in zip(channels[1:],plans[1:],strict=True)]
                    primary=batching.acquire(comm,read_plan)
                    return dict(rawBatches=primary+[reply for task in pending for reply in task.result()])
                pair=stable_scan_pair(generation,acquire)
            read_plan=[item for p in plans for item in p]
            pair['readConnections']=len(channels)
        else:
            pair=stable_scan_pair(generation,lambda:dict(rawBatches=batching.acquire(comm,read_plan)))
        replies=pair.pop('rawBatches')
        # Decode only the accepted frame set after the closing generation read.
        decoded=batching.decode(read_plan,replies,raw_sizes)
        decoded.update(cached_records)
        pair['rawResponses']=[decoded[tag] for tag in tags]
        pair['readPlan']=[{k:v for k,v in item.items() if k!='request'} for item in read_plan]
        if fragment_large:
            pair['fragmentPacketEvidence']=[dict(plan={k:v for k,v in item.items() if k!='request'},
                status=reply[0],rawHex=reply[1].hex()) for item,reply in zip(read_plan,replies,strict=True)
                if item['kind']=='fragment']
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
    def check_identity(channel):
        device=channel.GetDeviceProperties()
        if device.Status!='Success' or device.Value is None or (
            str(device.Value.SerialNumber).lower(),device.Value.ProductName,device.Value.Revision
        )!=('0x601fc87b','Emulate 5580 Controller','38.11'):
            raise ValueError('fixed local Echo identity guard failed')
    check_identity(comm)
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
    # Owners may request the same native record (for example the model catalog).
    # Acquire it once inside the scan proof; both decoders use that one sample.
    tags=list(dict.fromkeys([record['tag'] for record in seed['records']]+[row['tag'] for row in reads]))
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
    import fraktal_ab_canonical_observation as observed
    if observed.enabled(app) and seed['manifest'].get('schemaMinor',0)<2:
        raise ValueError('observation frame requires the V6.2 fragment revision')
    if sum(sizes.values())>comm.ConnectionSize*8 or observed.enabled(app):
        from pylogix import PLC
        from contextlib import ExitStack
        with ExitStack() as stack:
            observations=[]
            for unused in range(3 if app.canonical_publication_stage>=8 else 1):
                observation=stack.enter_context(PLC('127.0.0.1'))
                observation.ProcessorSlot=comm.ProcessorSlot
                observation.ConnectionSize=comm.ConnectionSize
                observation.SocketTimeout=comm.SocketTimeout
                check_identity(observation)
                if observation.Read(publisher.generation_tag(app)).Status!='Success':
                    raise ValueError('secondary read-only connection warmup failed')
                observations.append(observation)
            if observed.enabled(app):
                # Part III §3.13: the paired set changes every scan and takes
                # longer than one to read, so it is read from the PLC's latched
                # frame, under the same proof applied to the frame generation.
                def frame_generation():
                    response=comm.Read(observed.generation_tag(app))
                    if response.Status!='Success':raise ValueError('PLC observation generation read failed')
                    return response.Value
                import fraktal_ab_paired_observation as frame
                pair=frame.read([comm,*observations],frame=observed.frame_tag(app),tags=tags,sizes=sizes,
                                seed=seed,cached=cached,live_generation=generation,frame_generation=frame_generation,
                                fragment_revision=seed['coherenceBefore'][2],period_scans=observed.period_scans(app))
            else:
                pair=_scan_reads(comm,tags,generation,raw_sizes=sizes,cached_records=cached,
                                 secondary_comm=observations[0],secondary_tags=[row['tag'] for row in reads],
                                 fragment_large=app.canonical_publication_stage>=8,extra_comms=observations[1:],
                                 socket_reads=app.canonical_publication_stage>=10)
    else:
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
    return dict(schema='fraktal.ab.'+{2:'s2',3:'s3a',4:'s3b',5:'s3c',6:'s3d',7:'s3e',8:'s3f',9:'s3g',10:'s3h'}[app.canonical_publication_stage]+'-equivalence',schemaVersion=1,readOnly=True,
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

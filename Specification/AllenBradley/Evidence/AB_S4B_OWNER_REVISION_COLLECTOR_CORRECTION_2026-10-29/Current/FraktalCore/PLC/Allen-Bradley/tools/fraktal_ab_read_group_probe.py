"""S4 read-only qualification of manifest-bound small publication groups.

Development measurement, not a shipping gateway or station projection. No
declaration imports, writes, mode changes, observation frame or tag-name guesses.
"""
from collections import Counter
from pathlib import Path
import argparse
import gzip
import json
import re
import statistics
import time

from fraktal_ab_canonical_reader import decode_record, member_table, read_document, template_objects, is_string
from fraktal_ab_read_coherence import validate_rows
from fraktal_ab_canonical_manifest import read_manifest


def plan_groups(capture, max_bytes=2048):
    if type(max_bytes) is not int or not 64 <= max_bytes <= 3500:
        raise ValueError('group byte budget must be 64..3500')
    manifest=capture['manifest']
    if manifest.get('schemaMinor')!=7:
        raise ValueError('qualification requires published V6.7 coherence bindings')
    objects,sizes=template_objects(capture['templates'])
    symbols={s['name']:s for s in capture['symbols']}
    roots={name:row for name,row in symbols.items() if row.get('handle') in objects
        and any(m['name']=='Status' and m['struct'] and not m['array']
                for m in member_table(objects[row['handle']]))}
    products=manifest.get('dataProducts',[])
    expected=set(roots)|{p['CanonicalRoot'] for p in products}
    bindings=validate_rows(manifest.get('readCoherenceBindings'),expected_prefixes=expected)
    by_prefix={b['CanonicalPrefix']:b for b in bindings}
    for binding in bindings:
        symbol=symbols.get(binding['RevisionSymbol'])
        if not symbol or symbol.get('atomic')!=0xc4 or symbol.get('arrayRank',0):
            raise ValueError('revision is not a discovered DINT scalar')
    groups=[]

    def add(path,handle,prefix):
        if sizes[handle]>max_bytes:raise ValueError('row exceeds qualified byte budget: '+path)
        groups.append(dict(symbol=path,handle=handle,bytes=sizes[handle],binding=by_prefix[prefix]))
        if len(groups)>256:raise ValueError('probe group budget exceeded')

    def modules(path,handle,prefix,depth=0):
        if depth>64:raise ValueError('module depth exceeded')
        members=member_table(objects[handle])
        status=next((m for m in members if m['name']=='Status' and m['struct'] and not m['array']),None)
        if status:add(path+'.Status',status['handle'],prefix)
        for member in members:
            if not member['struct'] or member['name']=='Status':continue
            child=member_table(objects[member['handle']])
            if any(m['name']=='Status' and m['struct'] for m in child):
                if member['array']:raise ValueError('module arrays require an explicit qualification plan')
                modules(path+'.'+member['name'],member['handle'],prefix,depth+1)

    def product_row(path,handle,depth=0):
        if depth>64:return None
        members=member_table(objects[handle])
        if is_string(members) is None and 64<=sizes[handle]<=max_bytes:return path,handle
        for member in members:
            if member['struct'] and is_string(member_table(objects[member['handle']])) is None:
                found=product_row(path+'.'+member['name']+('[0]' if member['array'] else ''),member['handle'],depth+1)
                if found:return found
        return None

    for name,symbol in roots.items():modules(name,symbol['handle'],name)
    for product in products:
        source=product['SourceSymbol'];symbol=symbols.get(source)
        if not symbol or symbol.get('arrayRank',0) or symbol.get('handle') not in objects:
            raise ValueError('product source unavailable')
        selected=product_row(source,symbol['handle'])
        if selected is None:raise ValueError('no bounded structured product row')
        add(*selected,product['CanonicalRoot'])
    if not groups:raise ValueError('no qualified publication groups')
    return groups


def guarded_read(comm, group, templates, *, attempts=3, timeout=1, clock=time.perf_counter):
    if type(attempts) is not int or not 1<=attempts<=100 or not 0<timeout<=5:
        raise ValueError('invalid acquisition budget')
    start=clock();last_reason='coherence-unavailable';attempt=0
    original_timeout=comm.SocketTimeout
    def read(symbol):
        remaining=timeout-(clock()-start)
        if remaining<=0:raise TimeoutError('read-group deadline')
        comm.SocketTimeout=min(original_timeout,remaining)
        if comm.conn.SocketConnected:comm.conn.Socket.settimeout(comm.SocketTimeout)
        reply=comm.Read(symbol)
        if clock()-start>=timeout:raise TimeoutError('read-group deadline')
        return reply
    def revision():
        reply=read(group['binding']['RevisionSymbol'])
        if reply.Status!='Success' or type(reply.Value) is not int or not 0<=reply.Value<=2147483646:
            raise ValueError('invalid revision read')
        return reply.Value
    try:
        for attempt in range(1,attempts+1):
            window=clock()
            before=revision()
            if not before or before%2:continue
            reply=read(group['symbol'])
            if reply.Status!='Success' or not isinstance(reply.Value,(bytes,bytearray)):
                raise ValueError('row read failed')
            after=revision();elapsed=(clock()-window)*1000000
            if elapsed>=group['binding']['MutationPeriodUs']:
                last_reason='window-exceeds-publication-interval';continue
            if before==after and after%2==0:
                raw=bytes(reply.Value)
                if len(raw)!=group['bytes']:raise ValueError('row byte size changed')
                decode_record(raw,group['handle'],templates)
                return dict(quality='GOOD',revision=after,attempts=attempt,windowUs=elapsed,rawHex=raw.hex())
        return dict(quality='UNCERTAIN',reason=last_reason,attempts=attempt,rawHex=None)
    except (TimeoutError,OSError,ValueError) as error:
        # A failed socket is never retried or reused by the outer measurement.
        comm.Close()
        return dict(quality='BAD',reason='read-timeout' if isinstance(error,TimeoutError) else 'read-failed',
                    error=str(error),attempts=attempt,rawHex=None)
    finally:
        comm.SocketTimeout=original_timeout
        if comm.conn.SocketConnected:comm.conn.Socket.settimeout(original_timeout)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--slot',type=int,default=0)
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--iterations',type=int,default=100)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not re.fullmatch(r'[0-9A-Fa-f]{8}',args.expect_serial) or not 0<=args.slot<=255 \
            or not 20<=args.iterations<=1000 or args.output.exists():
        parser.error('exact serial, valid slot, 20..1000 iterations and new output required')
    from pylogix import PLC
    rows=[];groups=[];capture=None;failure=None
    try:
      with PLC(args.host) as comm:
        comm.ProcessorSlot,comm.ConnectionSize,comm.SocketTimeout=args.slot,4000,1
        unused,capture=read_document(comm,expect_serial=args.expect_serial)
        groups=plan_groups(capture)
        # Discovery's whole records and these cold reads are never accepted samples.
        for group in groups:
            for symbol in (group['binding']['RevisionSymbol'],group['symbol']):
                if comm.Read(symbol).Status!='Success':raise ValueError('cold type lookup failed')
        for iteration in range(args.iterations):
            for index,group in enumerate(groups):
                sample=guarded_read(comm,group,capture['templates'])
                rows.append(dict(iteration=iteration,group=index,**sample))
                if sample['quality']=='BAD':raise ValueError('failed group stops acquisition')
        if read_manifest(comm,capture['symbols'],capture['templates'])!=capture['manifest']:
            raise ValueError('manifest changed during qualification')
    except Exception as error:
        failure=dict(type=type(error).__name__,message=str(error))
    finally:
        rates=[]
        for index,group in enumerate(groups):
            accepted=[r for r in rows if r['group']==index and r['quality']=='GOOD']
            progress=len({r['revision'] for r in accepted})>1
            rates.append(dict(symbol=group['symbol'],good=len(accepted),total=args.iterations,
                              progress=progress,passed=progress and len(accepted)>=args.iterations*.95))
        report=dict(schema='fraktal.ab.read-group-qualification',schemaVersion=1,
            serial=args.expect_serial.upper(),readOnly=True,passed=failure is None and bool(rates) and all(r['passed'] for r in rates),
            failure=failure,
            scope='module Status rows and one bounded row per data product; not a complete HMI tier benchmark',
            groups=groups,rates=rates,rows=rows,metadata=capture,qualityCounts=dict(Counter(r['quality'] for r in rows)),
            goodWindowMedianUs=statistics.median(r['windowUs'] for r in rows if r['quality']=='GOOD') if any(r['quality']=='GOOD' for r in rows) else None)
    opener=gzip.open if args.output.suffix=='.gz' else open
    with opener(args.output,'xt',encoding='utf-8') as stream:json.dump(report,stream,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('metadata','rows','groups')}))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

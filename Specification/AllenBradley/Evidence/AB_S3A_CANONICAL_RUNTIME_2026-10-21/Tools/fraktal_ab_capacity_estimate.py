"""Offline, measured-baseline capacity forecast; never a Studio measurement.

Model units combine conservatively unpacked data and ST tokens. A measured
blocks/unit slope supplies the conversion: Blocks are not assumed to be bytes.
Opaque allocations must remain identical. No connection or controller writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import xml.etree.ElementTree as ET

SCHEMA='fraktal.ab.capacity-forecast'
WIDTHS=dict(BOOL=4,SINT=1,USINT=1,INT=2,UINT=2,DINT=4,UDINT=4,REAL=4,
            LINT=8,ULINT=8,LREAL=8,TIME32=4,TIME=8,LTIME=8,DT=8,LDT=8)


def _count(text):
    if text in (None,'','0'):return 1
    if not re.fullmatch(r'[1-9][0-9]*(?:[, ][1-9][0-9]*){0,2}',text):
        raise ValueError('unsupported array dimensions: '+text)
    return math.prod(map(int,re.split('[, ]',text)))


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _shape(node):
    # Documentation, initial values and engineering timestamps are not logic.
    if node.tag in ('Description','Data','RevisionNote'):return None
    attrs={k:v for k,v in node.attrib.items() if k not in
           ('CreatedDate','EditedDate','CreatedBy','EditedBy','Number')}
    return [node.tag,attrs,(node.text or '').strip(),
            [item for child in node if (item:=_shape(child)) is not None]]


def inventory(source:bytes):
    c=ET.fromstring(source).find('Controller')
    if c is None:raise ValueError('full controller L5X required')
    family=c.get('ProcessorType')
    revision=int(c.get('MajorRev','0'))
    if family!='1756-L81E' or revision!=38:
        raise ValueError('forecast currently calibrated only for 1756-L81E v38')
    types={t.get('Name'):t for t in c.findall('DataTypes/DataType')}
    active=set()
    @lru_cache(None)
    def size(name):
        if name in WIDTHS:return WIDTHS[name]
        if name not in types:return None
        if name in active:raise ValueError('recursive data type')
        active.add(name)
        offset=0
        for member in types[name].findall('Members/Member'):
            width=size(member.get('DataType'))
            if width is None:raise ValueError('opaque type inside UDT: '+name)
            alignment=min(8,width)
            offset=math.ceil(offset/alignment)*alignment+width*_count(member.get('Dimension'))
        active.remove(name)
        if not offset:raise ValueError('empty UDT')
        return math.ceil(offset/8)*8
    data=0
    opaque=Counter()
    for parent in [c,*c.findall('Programs/Program')]:
        for tag in parent.findall('Tags/Tag'):
            if tag.get('TagType')=='Alias':continue
            name=tag.get('DataType')
            count=_count(tag.get('Dimensions'))
            width=size(name)
            if width is None:opaque[name]+=count
            else:data+=math.ceil(width*count/8)*8
    st='\n'.join(line.text or '' for line in c.findall('.//STContent/Line'))
    st=re.sub(r'\(\*.*?\*\)',' ',st,flags=re.S)
    tokens=len(re.findall(r"\w+|[^\s]",st))
    fixed=[_shape(n) for path in ('Modules','Tasks','AddOnInstructionDefinitions')
           for n in c.findall(path)]
    fixed += [_shape(r) for r in c.findall('Programs/Program/Routines/Routine') if r.get('Type')!='ST']
    signature=_hash(json.dumps([dict(opaque),fixed],sort_keys=True).encode())
    return dict(sourceSha256=_hash(source),family=family,majorRevision=revision,
                modeledDataUnits=data,stTokens=tokens,score=data+4*tokens,
                fixedAllocationSignature=signature)


def _read(path):
    data=path.read_bytes()
    return gzip.decompress(data) if path.suffix=='.gz' else data


def load_observations(path):
    config=json.loads(path.read_text(encoding='utf-8'))
    samples=[]
    for row in config['samples']:
        source=_read(path.parent/row['source'])
        capacity_bytes=(path.parent/row['capacity']).read_bytes()
        if _hash(source)!=row['sourceSha256'].lower() or _hash(capacity_bytes)!=row['capacitySha256'].lower():
            raise ValueError('capacity calibration artifact hash differs')
        capacity=json.loads(capacity_bytes)
        prefix=row.get('capacityPrefix','')
        used,total,available=(capacity[prefix+k] for k in ('UsedStandardBlocks','TotalBlocks','AvailableBlocks'))
        if capacity.get('CapacityUnit')!='Blocks' or not capacity.get('OwnerConfirmedFit') or any(type(x) is not int for x in (used,total,available)) or not total>0 or not 0<=used<=total or available!=total-used:
            raise ValueError('invalid measured Capacity record')
        pin='BaselineSha256' if prefix=='Baseline' else 'CanonicalSha256'
        if capacity[pin].lower()!=row['acdSha256'].lower():
            raise ValueError('Capacity record does not bind the calibrated ACD')
        samples.append(dict(label=row['label'],features=inventory(source),used=used,total=total,
                            capacitySha256=_hash(capacity_bytes)))
    return samples


def forecast(samples,target):
    if len(samples)<2:raise ValueError('two independent measured images required')
    if any(s['features']['fixedAllocationSignature']!=target['fixedAllocationSignature'] or
           (s['features']['family'],s['features']['majorRevision'])!=(target['family'],target['majorRevision'])
           for s in samples):
        raise ValueError('uncalibrated controller, opaque storage, AOI, task, I/O or chart change')
    total=samples[0]['total']
    if any(s['total']!=total for s in samples):raise ValueError('capacity totals differ')
    ordered=sorted(samples,key=lambda s:s['features']['score'])
    slopes=[]
    for first,second in zip(ordered,ordered[1:]):
        delta=second['features']['score']-first['features']['score']
        growth=second['used']-first['used']
        if delta<=0 or growth<=0:raise ValueError('nonmonotonic calibration requires a new model')
        slopes.append(growth/delta)
    baseline=ordered[-1]
    delta=target['score']-baseline['features']['score']
    if delta<0:raise ValueError('forecast supports additive growth from latest calibration only')
    central=math.ceil(baseline['used']+delta*statistics.median(slopes))
    reserve=max(65536,math.ceil(total*.05))
    budget=math.ceil(baseline['used']+delta*max(slopes)*1.5)+reserve
    return dict(schema=SCHEMA,schemaVersion=1,readOnly=True,offline=True,
                measured=False,acceptanceGateSatisfied=False,
                target=target,capacityUnit='Blocks',baseline=baseline['label'],
                estimatedUsedBlocks=central,planningBudgetBlocks=budget,totalBlocks=total,
                planningHeadroomBlocks=total-budget,planningFits=budget<=total,
                reserveBlocks=reserve,blocksPerModelUnit=slopes,
                limitation='Empirical planning budget, not a guaranteed upper bound or Studio Capacity measurement')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('new evidence output required')
    try:
        report=forecast(load_observations(args.observations),inventory(_read(args.source)))
    except (ValueError,KeyError,TypeError,ET.ParseError) as error:
        report=dict(schema=SCHEMA,readOnly=True,offline=True,measured=False,
                    acceptanceGateSatisfied=False,error=str(error))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report))
    return 0 if 'error' not in report else 1


if __name__=='__main__':raise SystemExit(main())

"""S3j PLC-owned fieldbus product. Engineering owns identity; the HAL owns samples.

The Core array ceilings are not allocations. Nodes use the declared layout;
the homogeneous Channels stride is the largest declared word group, with each
node's ChannelCount selecting its occupied rows. No raw I/O writes occur here.
"""
from dataclasses import dataclass
import hashlib
import json
import re

import fraktal_ab_declaration as decl
import fraktal_ab_canonical_publication as pub
from fraktal_ab_canonical_unit_core import core_limit

P=pub.PREFIX
TOPOLOGY=P+'FieldbusTopologyV65'
NODE=P+'BusNodeV65'
CHANNEL=P+'IoChannelV65'
SAMPLE=P+'IoSampleV65'
WORK=P+'IoWorkV65'
DESCRIPTOR=P+'IoDescriptorV65'
SAMPLE_FIELDS=('InputWord','OutputWord','FaultWord','InputValid','OutputValid','FaultValid','ForcedWord','ForcePermitted')
BAD_MAPPING='std.error.fieldbusChannelMappingInvalid'


def enabled(app):return app.canonical_publication_stage>=12 and bool(app.io_modules)
def tag(app):
    # Static identity is read on demand. Version its binding when that identity
    # changes, so ContentHash invalidates caches without repeating identity in
    # a second manifest table. Clients discover this name; none infer it.
    fingerprint=hashlib.sha256(json.dumps(initial(app),sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    return f'FRK_{app.name}_Topology_{fingerprint}'
def canonical_root(app):return f'{app.name}Fieldbus/Topology'
def samples_tag(app):return f'FRK_{app.name}_IoSamples'
def work_tag(app):return f'FRK_{app.name}_IoWork'
def descriptors_tag(app):return f'FRK_{app.name}_IoDescriptors'
def routine(app):return f'FRK_{app.name}_CanonicalFieldbus'


@dataclass(frozen=True)
class Node:
    module: int
    name: str
    address: str
    parent: int
    channels: tuple


def nodes(app):
    result=[]
    for index,module in enumerate(app.io_modules):
        if len(module.channels)<=core_limit('MAX_NODE_CHANNELS'):
            result.append(Node(index,module.name,module.address,0,module.channels))
        else:
            parent=len(result)+1
            result.append(Node(index,module.name,module.address,0,()))
            for direction,suffix in ((decl.DIR_INPUT,'I'),(decl.DIR_OUTPUT,'O')):
                channels=tuple(c for c in module.channels if c.direction==direction)
                if channels:result.append(Node(index,module.name+'.'+suffix,module.address+':'+suffix,parent,channels))
    return tuple(result)


def validate(app):
    errors=[]
    if type(app.canonical_io_fixture) is not bool:errors.append('canonical_io_fixture must be a BOOL declaration choice')
    if app.canonical_io_fixture and app.canonical_publication_stage not in (12,13):errors.append('I/O fixture requires S3j or S3k')
    if app.canonical_publication_stage<12:return errors
    if not app.canonical_type_manifest or not app.canonical_table_driven:
        errors.append('S3j requires the accepted R1/R2 opt-ins')
    layout=nodes(app)
    if len(layout)>core_limit('MAX_BUS_NODES'):errors.append('fieldbus node count exceeds Core ceiling')
    for node in layout:
        if len(node.channels)>core_limit('MAX_NODE_CHANNELS'):errors.append('one I/O word exceeds the Core channel ceiling')
        module=app.io_modules[node.module]
        texts=[(node.name,80),(node.address,40),(module.type_id,80),(module.description_key,160)]
        if type(module.data_width) is not int or not 1<=module.data_width<=32:errors.append('canonical I/O requires a 1..32-bit sampled word')
        if module.sample_tag and (not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,39}',module.sample_tag)):
            errors.append('I/O sample binding requires one controller-scope record identifier')
        for c in node.channels:
            texts.extend(((c.name,80),(c.description_key,160),(channel_address(module,c),80),
                          (module.name+'.'+c.name,255),(app.name+('.'+c.module_path if c.module_path else ''),255),(c.unit,16)))
        if any(len(s.encode('utf-8'))>width for s,width in texts):errors.append('fieldbus identity exceeds Core UTF-8 width')
    sources=[m.sample_tag for m in app.io_modules if m.sample_tag]
    if len(set(sources))!=len(sources):errors.append('I/O modules may not alias a sampled-word owner')
    if app.canonical_io_fixture and any(not m.sample_tag for m in app.io_modules):errors.append('I/O fixture requires an explicit sample binding')
    return errors


def channel_address(module,channel):
    return f'{module.address}:{"O" if channel.direction==decl.DIR_OUTPUT else "I"}.{channel.bit}'


def products(app):
    return [dict(SourceSymbol=tag(app),CoreType='ST_FieldbusTopology',CanonicalRoot=canonical_root(app))] if enabled(app) else []


def augment(app,schema):
    if not enabled(app):return
    M=pub.Member
    capacity=max(1,max(len(n.channels) for n in nodes(app)))
    schema[CHANNEL]=(
        M('Name',pub.string_type(80)),M('DescriptionKey',pub.string_type(160)),M('Address',pub.string_type(80)),
        M('Path',pub.string_type(255)),M('ModulePath',pub.string_type(255)),M('Dir','DINT','ENUM'),M('Kind','DINT','ENUM'),
        M('BoolValue','BOOL'),M('AnalogValue','REAL'),M('Unit',pub.string_type(16)),M('Forced','BOOL'),
        M('Quality','BOOL'),M('FaultActive','BOOL'),M('Diagnostic',pub.string_type(255)),M('Forceable','BOOL'))
    schema[NODE]=(M('Name',pub.string_type(80)),M('DescriptionKey',pub.string_type(160)),M('TypeId',pub.string_type(80)),
        M('Address',pub.string_type(40)),M('State','DINT','ENUM'),M('LinkOk','BOOL'),M('ParentIdx','INT'),M('ChannelCount','INT'),
        M('Channels',CHANNEL,count=capacity,lower=1,count_path=canonical_root(app)+'/Nodes[*]/ChannelCount'))
    schema[TOPOLOGY]=(M('NodeCount','INT'),M('Nodes',NODE,count=len(nodes(app)),lower=1,count_path=canonical_root(app)+'/NodeCount'),
        M('MappingValid','BOOL'),M('MappingDiagnostic',pub.string_type(255)))
    schema[SAMPLE]=tuple(M(n,'DINT') for n in SAMPLE_FIELDS)
    schema[DESCRIPTOR]=tuple(M(n,'DINT') for n in ('NodeIdx','ChannelIdx','ModuleIdx','BitMask','Direction','Kind'))
    count=max(1,sum(len(n.channels) for n in nodes(app)))
    schema[WORK]=tuple(M(n,'DINT') for n in ('Row','Other','N1','C1','N2','C2','SourceIdx','ByteIdx','ByteValue','NodeIdx','Word','Mask'))+(
        M('Hash','LINT'),M('NameHash','DINT',count=count),M('PathHash','DINT',count=count),
        M('ModuleMasks','DINT',count=len(app.io_modules)),M('ModuleStates','DINT',count=len(app.io_modules)),
        M('NodeSources','DINT',count=len(nodes(app))),
        M('Valid','BOOL'),M('Equal','BOOL'),M('Sampled','BOOL'),M('BadDiagnostic',pub.string_type(255)))


def initial(app):
    result=dict(NodeCount=len(nodes(app)),Nodes=[],MappingValid=False)
    capacity=max(1,max(len(n.channels) for n in nodes(app)))
    for n in nodes(app):
        m=app.io_modules[n.module]
        channels=[dict(Name=c.name,DescriptionKey=c.description_key,Address=channel_address(m,c),Path=m.name+'.'+c.name,
            ModulePath=app.name+('.'+c.module_path if c.module_path else ''),Dir=c.direction,Kind=c.kind,Unit=c.unit) for c in n.channels]
        result['Nodes'].append(dict(Name=n.name,DescriptionKey=m.description_key,TypeId=m.type_id,Address=n.address,
            ParentIdx=n.parent,ChannelCount=len(n.channels),Channels=channels+[{} for _ in range(capacity-len(channels))]))
    return result


def descriptor_rows(app):
    return [dict(NodeIdx=n,ChannelIdx=i,ModuleIdx=node.module,BitMask=(1<<c.bit) if c.bit<31 else -2147483648,
                 Direction=c.direction,Kind=c.kind)
            for n,node in enumerate(nodes(app)) for i,c in enumerate(node.channels)]


def tags(app,serialize):
    if not enabled(app):return []
    rows=descriptor_rows(app)
    masks=[(1<<m.data_width)-1 if m.data_width<32 else -1 for m in app.io_modules]
    result=[serialize(tag(app),TOPOLOGY,initial(app)),serialize(work_tag(app),WORK,
        dict(BadDiagnostic=BAD_MAPPING,ModuleMasks=masks,NodeSources=[n.module for n in nodes(app)]),access='None'),
        serialize(descriptors_tag(app),DESCRIPTOR,rows or [{}],access='None',array=True),
        serialize(samples_tag(app),SAMPLE,[{} for _ in app.io_modules],access='None',array=True)]
    if app.canonical_io_fixture:
        result.extend(serialize(m.sample_tag,SAMPLE,dict(InputValid=1,OutputValid=1,FaultValid=1),access='Read/Write')
                      for m in app.io_modules if m.sample_tag)
    return result


def forcing(app):
    """There is no active registered OUTPUT_FORCING gate in this profile.

    Keep the existing mailbox refusal path, and withdraw its held state. An
    idle MANUAL Unit alone cannot create a commissioning capability.
    """
    import fraktal_ab_generate as gen
    p=f'FRK_{app.name}_Force'
    return [f'{p}Outputs := {gen.force_output_mask(app)};',f'{p}Permitted := 0;',f'{p}Mask := 0;',f'{p}Value := 0;']


def mapping(app):
    w,t,d=work_tag(app),tag(app),descriptors_tag(app)
    total=len(descriptor_rows(app));layout=nodes(app)
    lines=[f'{w}.Valid := {t}.NodeCount = {len(layout)};']
    for i,node in enumerate(layout):
        n=f'{t}.Nodes[{i}]'
        lines.append(f'{w}.Valid := {w}.Valid AND ({n}.ParentIdx = {node.parent}) AND ({n}.ChannelCount = {len(node.channels)}) AND ({n}.Name.LEN > 0) AND ({n}.Name.LEN <= 80);')
    if not total:return lines
    lines += [f'FOR {w}.Row := 0 TO {total-1} DO',f'{w}.N1 := {d}[{w}.Row].NodeIdx;',f'{w}.C1 := {d}[{w}.Row].ChannelIdx;']
    c=f'{t}.Nodes[{w}.N1].Channels[{w}.C1]'
    lines += [f'{w}.Valid := {w}.Valid AND ({c}.Dir = {d}[{w}.Row].Direction) AND ({c}.Kind = {d}[{w}.Row].Kind)',
              f' AND ({c}.Name.LEN > 0) AND ({c}.Name.LEN <= 80) AND ({c}.Path.LEN > 0) AND ({c}.Path.LEN <= 255) AND ({c}.ModulePath.LEN > 0);']
    lines.append(f'IF {w}.Valid THEN')
    # Hash each identity once. Compare bytes on a matching hash so collisions
    # never hide duplicates; ordinary comparisons do not re-scan string data.
    for field,cache in (('Name','NameHash'),('Path','PathHash')):
        lines += [f'{w}.Hash := 0;',f'FOR {w}.ByteIdx := 0 TO {c}.{field}.LEN - 1 DO',
                  f'{w}.ByteValue := {c}.{field}.DATA[{w}.ByteIdx];',f'IF {w}.ByteValue < 0 THEN {w}.ByteValue := {w}.ByteValue + 256; END_IF;',
                  f'{w}.Hash := ({w}.Hash * 31 + {w}.ByteValue) MOD 2147483647;', 'END_FOR;',f'{w}.{cache}[{w}.Row] := {w}.Hash;']
    lines += ['END_IF;','END_FOR;',f'IF {w}.Valid THEN',f'FOR {w}.Row := 0 TO {total-1} DO',f'{w}.N1 := {d}[{w}.Row].NodeIdx;',f'{w}.C1 := {d}[{w}.Row].ChannelIdx;',
              f'FOR {w}.Other := {w}.Row + 1 TO {total-1} DO',f'{w}.N2 := {d}[{w}.Other].NodeIdx;',f'{w}.C2 := {d}[{w}.Other].ChannelIdx;']
    other=f'{t}.Nodes[{w}.N2].Channels[{w}.C2]'
    for field,cache in (('Name','NameHash'),('Path','PathHash')):
        lines += [f'IF ({w}.{cache}[{w}.Row] = {w}.{cache}[{w}.Other]) AND ({c}.{field}.LEN = {other}.{field}.LEN) THEN',
                  f'{w}.Equal := 1;',f'FOR {w}.ByteIdx := 0 TO {c}.{field}.LEN - 1 DO',
                  f'IF {c}.{field}.DATA[{w}.ByteIdx] <> {other}.{field}.DATA[{w}.ByteIdx] THEN {w}.Equal := 0; END_IF;',
                  'END_FOR;',f'IF {w}.Equal THEN {w}.Valid := 0; END_IF;','END_IF;']
    return lines+['END_FOR;','END_FOR;','END_IF;']


def cyclic(app):
    return [f'JSR({routine(app)},0);'] if enabled(app) else []


def routines(app):
    if not enabled(app):return []
    w,t,d,s=work_tag(app),tag(app),descriptors_tag(app),samples_tag(app)
    lines=['IF S:FS THEN',*mapping(app),f'{t}.MappingValid := {w}.Valid;',
           f'IF {w}.Valid THEN {t}.MappingDiagnostic.LEN := 0; ELSE CPS({w}.BadDiagnostic,{t}.MappingDiagnostic,1); END_IF;', 'END_IF;']
    for i,m in enumerate(app.io_modules):
        if m.sample_tag:lines.append(f'CPS({m.sample_tag},{s}[{i}],1);')
        # Forcing has a separate owner. The new profile's gate is closed.
        lines += [f'{s}[{i}].ForcedWord := FRK_{app.name}_ForceMask;',f'{s}[{i}].ForcePermitted := FRK_{app.name}_ForcePermitted;']
    sample=f'{s}[{w}.SourceIdx]';state=f'{w}.ModuleStates[{w}.SourceIdx]';mask=f'{w}.ModuleMasks[{w}.SourceIdx]'
    lines += [f'FOR {w}.SourceIdx := 0 TO {len(app.io_modules)-1} DO',
        f'IF ({sample}.InputValid <> 1) OR ({sample}.OutputValid <> 1) OR ({sample}.FaultValid <> 1) THEN',f'{state} := 0;',
        f'ELSIF ({sample}.FaultWord AND {mask}) = {mask} THEN {state} := 0;',f'ELSIF ({sample}.FaultWord AND {mask}) <> 0 THEN {state} := 5;',
        f'ELSE {state} := 4; END_IF;','END_FOR;',f'FOR {w}.NodeIdx := 0 TO {len(nodes(app))-1} DO',
        f'{w}.SourceIdx := {w}.NodeSources[{w}.NodeIdx];',f'{t}.Nodes[{w}.NodeIdx].State := {state};',
        f'{t}.Nodes[{w}.NodeIdx].LinkOk := {state} = 4;','END_FOR;']
    total=len(descriptor_rows(app))
    if total:
        c=f'{t}.Nodes[{w}.N1].Channels[{w}.C1]'
        lines += [f'FOR {w}.Row := 0 TO {total-1} DO',f'{w}.N1 := {d}[{w}.Row].NodeIdx;',f'{w}.C1 := {d}[{w}.Row].ChannelIdx;',f'{w}.SourceIdx := {d}[{w}.Row].ModuleIdx;',
            f'{w}.Mask := {d}[{w}.Row].BitMask;',f'{w}.Word := {s}[{w}.SourceIdx].InputWord;',f'{w}.Sampled := {s}[{w}.SourceIdx].InputValid = 1;',
            f'IF {d}[{w}.Row].Direction = 1 THEN {w}.Word := {s}[{w}.SourceIdx].OutputWord; {w}.Sampled := {s}[{w}.SourceIdx].OutputValid = 1; END_IF;',
            f'{c}.BoolValue := {w}.Sampled AND (({w}.Word AND {w}.Mask) <> 0);',f'{c}.AnalogValue := 0;',
            f'{c}.FaultActive := ({s}[{w}.SourceIdx].FaultValid = 1) AND (({s}[{w}.SourceIdx].FaultWord AND {w}.Mask) <> 0);',
            f'{c}.Quality := {t}.MappingValid AND {w}.Sampled AND ({s}[{w}.SourceIdx].FaultValid = 1) AND NOT {c}.FaultActive;',
            f'{c}.Forced := ({d}[{w}.Row].Direction = 1) AND ({s}[{w}.SourceIdx].InputValid = 1) AND ({s}[{w}.SourceIdx].OutputValid = 1) AND ({s}[{w}.SourceIdx].FaultValid = 1) AND (({s}[{w}.SourceIdx].ForcedWord AND {w}.Mask) <> 0);',
            f'{c}.Forceable := 0;',f'{c}.Diagnostic.LEN := 0;','END_FOR;']
    return [(routine(app),lines)]

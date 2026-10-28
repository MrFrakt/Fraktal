"""Independent S3j oracle from the old fieldbus projection and sampled words.

This is acceptance apparatus, not a runtime client. It does not import the
canonical publisher, its descriptors, its layout function or its state logic.
"""
import fraktal_ab_projection as legacy


def values(app,samples,*,mapping_valid=True):
    if len(samples)!=len(app.io_modules):raise ValueError('one sample per declared I/O module required')
    if not app.io_modules:return {}
    io={}
    for module,s in zip(app.io_modules,samples):
        io[module.address]=dict(forced=s['ForcedWord'],forcePermitted=0)
        for key,word,valid in (('input','InputWord','InputValid'),('output','OutputWord','OutputValid'),('fault','FaultWord','FaultValid')):
            if s[valid]==1:io[module.address][key]=s[word]&((1<<module.data_width)-1)
    old=legacy.topology(app,io)
    root=app.name+'Fieldbus/Topology'
    result={root+'/NodeCount':0,root+'/MappingValid':mapping_valid,
            root+'/MappingDiagnostic':'' if mapping_valid else 'std.error.fieldbusChannelMappingInvalid'}
    for index,module in enumerate(app.io_modules,1):
        source=f'{root}/Nodes[{index}]'
        groups=[('',module.channels)] if len(module.channels)<=16 else [('',()),('.I',tuple(c for c in module.channels if c.direction==0)),('.O',tuple(c for c in module.channels if c.direction==1))]
        parent=result[root+'/NodeCount']+1
        for suffix,channels in groups:
            if suffix and not channels:continue
            result[root+'/NodeCount']+=1;n=result[root+'/NodeCount'];target=f'{root}/Nodes[{n}]'
            for field in ('Name','DescriptionKey','TypeId','Address','State','LinkOk','ParentIdx','ChannelCount'):
                v=old[source+'/'+field]
                if field=='Name':v=module.name+suffix
                elif field=='Address':v=module.address+(':'+suffix[1:] if suffix else '')
                elif field=='ParentIdx':v=parent if suffix else 0
                elif field=='ChannelCount':v=len(channels)
                result[target+'/'+field]=v
            for slot,channel in enumerate(channels,1):
                original=module.channels.index(channel)+1
                prefix=f'{source}/Channels[{original}]/';dest=f'{target}/Channels[{slot}]/'
                for path,value in old.items():
                    if path.startswith(prefix):
                        field=path[len(prefix):]
                        if field=='AnalogValue':value=float(value)
                        if field=='Quality':value=value and mapping_valid
                        result[dest+field]=value
    return result


def logical_types(paths):
    integers={'NodeCount':'Int16','ParentIdx':'Int16','ChannelCount':'Int16','State':'Int32','Dir':'Int32','Kind':'Int32'}
    flags={'MappingValid','LinkOk','BoolValue','Forced','Quality','FaultActive','Forceable'}
    return {p:integers.get(p.rsplit('/',1)[-1], 'Boolean' if p.rsplit('/',1)[-1] in flags else
                          'Float' if p.endswith('/AnalogValue') else 'String') for p in paths}

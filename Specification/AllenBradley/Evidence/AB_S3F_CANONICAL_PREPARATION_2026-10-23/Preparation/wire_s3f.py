from pathlib import Path
ROOT=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')


def edit(name,replacements):
    p=ROOT/name;raw=p.read_bytes();crlf=b'\r\n' in raw
    text=raw.decode('utf-8').replace('\r\n','\n')
    for old,new in replacements:
        assert text.count(old)==1,(name,old[:80],text.count(old))
        text=text.replace(old,new,1)
    with p.open('wb') as f:f.write(text.replace('\n','\r\n').encode('utf-8') if crlf else text.encode('utf-8'))


edit('fraktal_ab_canonical_publication.py',[
    ('(wire.STAGE, 3, 4, 5, 6, 7)','(wire.STAGE, 3, 4, 5, 6, 7, 8)'),
    ('(0, wire.STAGE, 3, 4, 5, 6, 7)','(0, wire.STAGE, 3, 4, 5, 6, 7, 8)'),
    ('S3c, S3d or S3e','S3c, S3d, S3e or S3f'),
    ("if stage>=7:reserved.add('Access')","if stage>=7:reserved.add('Access')\n    if stage>=8:reserved.update(('HmiResponse','ConfigPersist','ConfigSets','ConfigSetCount','ConfigSetDocument','ConfigSetDocumentLine','ConfigSetDocumentLines'))"),
    ("        findings.extend(access.validate(app))\n    return findings","        findings.extend(access.validate(app))\n    if stage>=8:\n        import fraktal_ab_canonical_config as config\n        findings.extend(config.validate(app))\n    return findings"),
    ('def root_type(app):\n','def root_type(app):\n    if app.canonical_publication_stage==8:return f"FRK_T_{app.name}CanonicalRootS3fV63"\n'),
    ('def header_type(app):\n','def header_type(app):\n    if app.canonical_publication_stage==8:return f"FRK_T_{app.name}CanonicalManifestS3fV63"\n'),
    ('        access.augment(app,result)\n    field_type', '        access.augment(app,result)\n    if app.canonical_publication_stage>=8:\n        import fraktal_ab_canonical_config as config\n        import fraktal_ab_config_provider as provider\n        config.augment(app,result)\n        provider.augment(app,result)\n    field_type'),
    ('    result[PREFIX+"TimingV6"]', '''    if app.canonical_publication_stage>=8:
        import fraktal_ab_config_provider as provider
        result[PREFIX+'ServiceV63']=(Member('Kind','DINT'),Member('Version','DINT'),
            Member('RequestSymbol',string_type(80)),Member('RequestMember',string_type(80)),Member('ResponseSymbol',string_type(80)))
        result[header_type(app)]+=(Member('ServicesCount','DINT'),Member('ServicesCapacity','DINT'),
            Member('Services',PREFIX+'ServiceV63',count=len(provider.services(app))))
    result[PREFIX+"TimingV6"]'''),
    ('Radix="Decimal" if member.kind in ("DINT","BOOL","LINT","LDT") else "NullType",\n                          Hidden="false",ExternalAccess="Read Only")',
     'Radix="Float" if member.kind in ("REAL","LREAL") else "Decimal" if member.kind in ("SINT","INT","DINT","BOOL","LINT","LDT") else "NullType",\n                          Hidden="false",ExternalAccess="Read/Write" if kind=="FRK_T_ConfigProviderRequestV1" else "Read Only")'),
    ('        access.initialize(app,result)\n    return result','        access.initialize(app,result)\n    if app.canonical_publication_stage>=8:\n        import fraktal_ab_canonical_config as config\n        config.initialize(app,result)\n    return result'),
    ('''                out.append(f'<DataValueMember Name="{m.name}" DataType="{m.kind}" Radix="Decimal" Value="{int(v)}"/>')''',
     '''                radix='Float' if m.kind in ('REAL','LREAL') else 'Decimal'
                encoded=str(float(v)) if m.kind in ('REAL','LREAL') else str(int(v))
                out.append(f'<DataValueMember Name="{m.name}" DataType="{m.kind}" Radix="{radix}" Value="{encoded}"/>')'''),
    ('    minor = wire.FRAGMENT_MINOR if app.canonical_publication_stage>=5', '    minor = wire.SERVICE_MINOR if app.canonical_publication_stage>=8 else wire.FRAGMENT_MINOR if app.canonical_publication_stage>=5'),
    ("**({'bindings':binding_rows} if minor==wire.FRAGMENT_MINOR else {}))", "**({'bindings':binding_rows} if minor>=wire.FRAGMENT_MINOR else {}),\n        **({'services':provider.services(app)} if minor>=wire.SERVICE_MINOR else {}))"),
    ("        header.update(FragmentRevision=0,BindingsCount=len(binding_rows),BindingsCapacity=len(binding_rows),Bindings=binding_rows)",
     "        header.update(FragmentRevision=0,BindingsCount=len(binding_rows),BindingsCapacity=len(binding_rows),Bindings=binding_rows)\n    if app.canonical_publication_stage>=8:header.update(ServicesCount=len(provider.services(app)),ServicesCapacity=len(provider.services(app)),Services=provider.services(app))"),
    ('    fields, old_hash = field_rows(app,definitions), legacy.content_hash(app)',
     '    if app.canonical_publication_stage>=8:\n        import fraktal_ab_config_provider as provider\n        import fraktal_ab_canonical_config as config\n    fields, old_hash = field_rows(app,definitions), legacy.content_hash(app)'),
    ('            *(access.tags(app,tag) if app.canonical_publication_stage>=7 else []),',
     '            *(access.tags(app,tag) if app.canonical_publication_stage>=7 else []),\n            *(config.tags(app,tag) if app.canonical_publication_stage>=8 else []),\n            *(provider.tags(app,tag) if app.canonical_publication_stage>=8 else []),'),
    ('        lines += access.cyclic(app)\n    timing', '        lines += access.cyclic(app)\n    if app.canonical_publication_stage>=8:\n        import fraktal_ab_canonical_config as config\n        import fraktal_ab_config_provider as provider\n        lines += config.cyclic(app)\n        lines += [f\'JSR({provider.routine_name(app)},0);\']\n    timing'),
])
edit('fraktal_ab_generate.py',[
    ('        result += access.routines(app)\n    return result',
     '        result += access.routines(app)\n    if app.canonical_publication_stage>=8:\n        import fraktal_ab_canonical_config as config_publication\n        import fraktal_ab_config_provider as provider\n        result += config_publication.routines(app)\n        result.append((provider.routine_name(app),provider.logic(app)))\n    return result'),
])
edit('fraktal_ab_mailbox.py',[
    ('    return f"FRK_T_{app.name}HmiRequestV3"','    return f"FRK_T_{app.name}HmiRequestV4" if app.canonical_publication_stage>=8 else f"FRK_T_{app.name}HmiRequestV3"'),
    ('''    blocks.append(_record_xml(
        app, response_type_name(app)''','''    if app.canonical_publication_stage>=8:
        import fraktal_ab_config_provider as provider
        blocks[-1]=blocks[-1].replace('</Members>',
            _member_xml('ConfigProvider',provider.INPUT,'Versioned validated store response','Read/Write')+'\\n</Members>')
    blocks.append(_record_xml(
        app, response_type_name(app)'''),
    ('''    return (f'<Tag Name="{tag_name}" TagType="Base" DataType="{type_name}" '\n''','''    if app.canonical_publication_stage>=8 and type_name==request_type_name(app):
        import fraktal_ab_config_provider as provider
        import fraktal_ab_generate as gen
        nested=gen._structure_tag('unused',provider.INPUT,provider.native_members())
        start=nested.index('<Structure DataType=');end=nested.index('</Structure>',start)+len('</Structure>')
        parts.append(nested[start:end].replace('<Structure ','<StructureMember Name="ConfigProvider" ',1).replace('</Structure>','</StructureMember>'))
    return (f'<Tag Name="{tag_name}" TagType="Base" DataType="{type_name}" '\n'''),
    ('        lines.extend(_accept(app))\n\n    by_key:',
     '        if app.canonical_publication_stage>=8:\n            import fraktal_ab_canonical_config as publication_config\n            lines.extend(publication_config.query(app))\n        lines.extend(_accept(app))\n\n    by_key:'),
])
edit('fraktal_ab_sets.py',[
    ("    return lines\n\n\ndef _text", "    if app.canonical_publication_stage>=8:\n        import fraktal_ab_canonical_config as publication_config\n        needle=f'{p}.PendingSince := FRK_{app.name}_NowTime;'\n        result=[]\n        for line in lines:\n            result.append(line)\n            if line==needle:result.extend(publication_config.pending_stamp(app))\n        lines=result\n    return lines\n\n\ndef _text")
])
print('wired stage 8')

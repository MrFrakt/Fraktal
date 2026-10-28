"""Exact guarded edits for the opt-in V6.8 publisher and reader."""
from pathlib import Path
T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
def edit(name,changes):
    path=T/name;raw=path.read_bytes();text=raw.decode().replace('\r\n','\n')
    for old,new in changes:
        assert text.count(old)==1,(name,old,text.count(old));text=text.replace(old,new)
    path.write_bytes(text.replace('\n','\r\n').encode() if b'\r\n' in raw else text.encode())

edit('fraktal_ab_declaration.py',[(
    '    canonical_read_coherence: bool = False\n',
    '    canonical_read_coherence: bool = False\n    # S4b: PLC-owned read-only configuration discovery (V6.8).\n    canonical_config_read_view: bool = False\n')])
edit('fraktal_ab_canonical_publication.py',[
    ('    findings += read_coherence.validate(app)\n','    findings += read_coherence.validate(app)\n    findings += __import__("fraktal_ab_config_read_view").validate(app)\n'),
    ('def header_type(app):\n','def header_type(app):\n    if app.canonical_config_read_view:return f"FRK_T_{app.name}CanonicalManifestV68"\n'),
    ('def header_tag(app):\n','def products(app):\n    from fraktal_ab_canonical_fieldbus import products as fieldbus_products\n    from fraktal_ab_config_read_view import products as config_products\n    return fieldbus_products(app)+config_products(app)\n\n\ndef header_tag(app):\n'),
    ('    if app.canonical_type_manifest:\n        import fraktal_ab_canonical_type_manifest as type_manifest\n',
     '    __import__("fraktal_ab_config_read_view").augment(app,result)\n    if app.canonical_type_manifest:\n        import fraktal_ab_canonical_type_manifest as type_manifest\n'),
    ('        products=fieldbus.products(app)\n','        product_rows=products(app)\n'),
    ('        if products:\n','        if product_rows:\n'),
    ('count=len(products)),)\n','count=len(product_rows)),)\n'),
    ("        __import__('fraktal_ab_read_coherence').augment(app,result)\n","        __import__('fraktal_ab_read_coherence').augment(app,result)\n    __import__('fraktal_ab_config_read_view').augment_manifest(app,result)\n"),
    ("    if app.canonical_read_coherence:minor=__import__('fraktal_ab_read_coherence').MINOR\n","    if app.canonical_read_coherence:minor=__import__('fraktal_ab_read_coherence').MINOR\n    if app.canonical_config_read_view:minor=__import__('fraktal_ab_config_read_view').MINOR\n"),
    ('        from fraktal_ab_canonical_fieldbus import products\n',''),
    ('    digest = wire.content_hash(fields,old_hash,app.canonical_publication_stage,minor=minor,\n',
     "    read_services=__import__('fraktal_ab_config_read_view').descriptors(app)\n    digest = wire.content_hash(fields,old_hash,app.canonical_publication_stage,minor=minor,\n        **(dict(read_services=read_services) if app.canonical_config_read_view else {}),\n"),
    ('    return header\n',"    if app.canonical_config_read_view:header.update(ReadServicesCount=len(read_services),ReadServicesCapacity=len(read_services),ReadServices=read_services)\n    return header\n"),
    ("            f'<Tag Name=\"{generation_tag(app)}\"", "            *__import__('fraktal_ab_config_read_view').tags(app,tag),\n            f'<Tag Name=\"{generation_tag(app)}\""),
    ("    timing = f'FRK_{app.name}_CanonicalTiming'\n","    lines += __import__('fraktal_ab_config_read_view').cyclic(app)\n    timing = f'FRK_{app.name}_CanonicalTiming'\n")])
edit('fraktal_ab_canonical_type_manifest.py',[(
    '    rows, paths = list(annotations.values()), list(exceptions.values())\n',
    "    import fraktal_ab_config_read_view as config_read\n    if config_read.enabled(app):walk(config_read.VIEW,config_read.canonical_root(app))\n    rows, paths = list(annotations.values()), list(exceptions.values())\n")])
edit('fraktal_ab_read_coherence.py',[(
    '    from fraktal_ab_canonical_fieldbus import products\n','    from fraktal_ab_canonical_publication import products\n')])
edit('fraktal_ab_canonical_observation.py',[(
    "        products=tuple(row['SourceSymbol'] for row in fieldbus.products(app))\n",
    "        from fraktal_ab_canonical_publication import products as published_products\n        products=tuple(row['SourceSymbol'] for row in published_products(app))\n")])
print('Integrated opt-in publisher; wire V6.8 normalization follows.')

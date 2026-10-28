"""Guarded V6.8 wire changes; previous serialization paths remain identical."""
from pathlib import Path
T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
def edit(name,changes):
    path=T/name;raw=path.read_bytes();text=raw.decode().replace('\r\n','\n')
    for change in changes:
        old,new=change[:2];expected=change[2] if len(change)==3 else 1
        assert text.count(old)==expected,(name,old,text.count(old));text=text.replace(old,new)
    path.write_bytes(text.replace('\n','\r\n').encode() if b'\r\n' in raw else text.encode())
edit('fraktal_ab_canonical_manifest.py',[
    ('READ_HEADER = COMMAND_HEADER | read_coherence.HEADER_FIELDS\n',
     'READ_HEADER = COMMAND_HEADER | read_coherence.HEADER_FIELDS\nREAD_SERVICE_MINOR = 8\nREAD_SERVICE_HEADER = READ_HEADER | {"ReadServicesCount","ReadServicesCapacity","ReadServices"}\n'),
    ('operations=None, read_coherence_bindings=None):\n','operations=None, read_coherence_bindings=None, read_services=None):\n',2),
    ("    if minor>=READ_MINOR:result['readCoherenceBindings']=read_coherence_bindings\n",
     "    if minor>=READ_MINOR:result['readCoherenceBindings']=read_coherence_bindings\n    if minor>=READ_SERVICE_MINOR:result['readServices']=read_services\n"),
    ('operations=operations,read_coherence_bindings=read_coherence_bindings), ensure_ascii=True,',
     'operations=operations,read_coherence_bindings=read_coherence_bindings,read_services=read_services), ensure_ascii=True,'),
    ('    if minor in (TYPE_MINOR,PRODUCT_MINOR,COMMAND_MINOR,READ_MINOR):\n',
     '    if minor in (TYPE_MINOR,PRODUCT_MINOR,COMMAND_MINOR,READ_MINOR,READ_SERVICE_MINOR):\n'),
    ('expected = (READ_HEADER if minor==READ_MINOR else',
     'expected = (READ_SERVICE_HEADER if minor==READ_SERVICE_MINOR else READ_HEADER if minor==READ_MINOR else'),
    ('COMMAND_MINOR, READ_MINOR) \\\n','COMMAND_MINOR, READ_MINOR, READ_SERVICE_MINOR) \\\n'),
    ('    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])\n',
     '''    read_services=[]
    if minor>=READ_SERVICE_MINOR:
        from fraktal_ab_config_read_view import validate_descriptors,SERVICE_FIELD
        count,capacity=record['ReadServicesCount'],record['ReadServicesCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \\
                or not isinstance(record['ReadServices'],list) or len(record['ReadServices'])!=count:
            raise ValueError('invalid read-service count/capacity')
        for row in record['ReadServices']:
            if not isinstance(row,dict) or set(row)!=SERVICE_FIELD:raise ValueError('invalid read-service row')
            read_services.append({k:text(v) if k in ('RootSymbol','CanonicalRoot') else v for k,v in row.items()})
        validate_descriptors(read_services)
    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])
'''),
    ("            **({'read_coherence_bindings':coherence_rows} if minor>=READ_MINOR else {})) \\\n",
     "            **({'read_coherence_bindings':coherence_rows} if minor>=READ_MINOR else {}),\n            **({'read_services':read_services} if minor>=READ_SERVICE_MINOR else {})) \\\n"),
    ("    if minor>=READ_MINOR:result['readCoherenceBindings']=coherence_rows\n",
     "    if minor>=READ_MINOR:result['readCoherenceBindings']=coherence_rows\n    if minor>=READ_SERVICE_MINOR:result['readServices']=read_services\n")])
edit('fraktal_ab_canonical_reader.py',[
    ('minor not in (0, 1, 2, 3, 4, 5, 6, 7):','minor not in (0, 1, 2, 3, 4, 5, 6, 7, 8):'),
    ("    roots = []\n", "    if minor<8 and 'readServices' in manifest:raise ValueError('read services require V6.8')\n    roots = []\n"),
    ('    fragments=[]\n',
     '''    if minor>=8:
        from fraktal_ab_config_read_view import validate_descriptors
        for descriptor in validate_descriptors(manifest.get('readServices')):
            if descriptor['RootSymbol'] not in roots or descriptor['CanonicalRoot'] not in decoded_roots \\
                    or descriptor['CanonicalRoot'] in roots:
                raise ValueError('read-service root/product is not published')
            view=decoded_roots[descriptor['CanonicalRoot']]
            identity=view.get('RootIdentity',{})
            if view.get('SchemaVersion')!=1 or not identity.get('string') \\
                    or bytes.fromhex(identity['bytes']).decode('utf-8')!=descriptor['RootSymbol']:
                raise ValueError('read-service view version/identity differs')
    fragments=[]
'''),
    ("                **(dict(readCoherenceBindings=manifest['readCoherenceBindings']) if minor>=7 else {}))",
     "                **(dict(readCoherenceBindings=manifest['readCoherenceBindings']) if minor>=7 else {}),\n                **(dict(readServices=manifest['readServices']) if minor>=8 else {}))")])
print('Integrated V6.8 header/hash/read-service normalization and reference replay.')

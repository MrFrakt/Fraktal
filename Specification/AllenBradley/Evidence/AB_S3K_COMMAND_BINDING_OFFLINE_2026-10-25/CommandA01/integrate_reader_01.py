from pathlib import Path
p=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_reader.py')
b=p.read_bytes();nl='\r\n' if b.count(b'\r\n')>b.count(b'\n')//2 else '\n';s=b.decode().replace('\r\n','\n')
def change(old,new):
    global s
    assert s.count(old)==1,(old[:80],s.count(old));s=s.replace(old,new)
change('minor not in (0, 1, 2, 3, 4, 5)','minor not in (0, 1, 2, 3, 4, 5, 6)')
change("    token = tuple(coherence_token(manifest))", "    if minor<6 and 'commandBindings' in manifest:raise ValueError('command bindings require V6.6')\n    token = tuple(coherence_token(manifest))")
change('    roots = []\n', '''    commands=[]
    if minor>=6:
        from fraktal_ab_command_binding import bindings as validate_commands
        commands=validate_commands(manifest.get('commandBindings'))
        if {r['PayloadSymbol'] for r in commands}&set(records):
            raise ValueError('command-only payload values are forbidden in persisted cyclic captures')
        if {r['ResponseSymbol'] for r in commands}&set(records):
            raise ValueError('on-demand command replies are not cyclic records')
    roots = []
''')
change('    if minor >= 4:\n        by_name = {}', '''    command_arguments={}
    if minor>=6:
        from fraktal_ab_command_binding import schema as command_schema
        for descriptor in commands:
            root=descriptor['RootSymbol']
            if root not in roots:raise ValueError('command binding root is not a discovered Unit')
            handle=command_schema(descriptor,symbols,objects,sizes,member_table,is_string)
            before=set(schema_rows)
            schema_walk(root+'/HmiRequest',handle,fragment=True)
            for path in set(schema_rows)-before:
                row=schema_rows[path]
                width=is_string(member_table(objects[row['handle']])) if row['struct'] else None
                command_arguments[path]=dict(readRole='CommandOnly',
                    nativeType='String' if width is not None else NATIVE_TYPES[row['atomic']],
                    **({'byteCapacity':width} if width is not None else {}))
    if minor >= 4:
        by_name = {}''')
change('                dataValues={p: dict(value=v, type=types[p], status=0) for p, v in values.items()})',
       "                dataValues={p: dict(value=v, type=types[p], status=0) for p, v in values.items()},\n                **(dict(commandBindings=commands,commandArguments=command_arguments) if minor>=6 else {}))")
change('    records = []\n    for symbol in symbols:', '''    if before.get('schemaMinor',0)>=6:
        for binding in before['commandBindings']:
            name=binding['CommitSymbol']
            tags=[t for t in reply.Value if t.TagName==name]
            if len(tags)!=1 or tags[0].Struct or tags[0].Array or tags[0].DataTypeValue!=0xC4:
                raise ValueError('command commit Symbol is not a DINT scalar')
            symbols.append(dict(name=name,atomic=0xC4,arrayRank=0))
    records = []
    for symbol in symbols:''')
# Scalar command commits have no Template; they are discovered, never sampled.
change('for r in member_table(objects[symbol["handle"]])):', 'for r in member_table(objects.get(symbol.get("handle"),SimpleNamespace(Fields=[])))):')
p.write_bytes(s.replace('\n',nl).encode())

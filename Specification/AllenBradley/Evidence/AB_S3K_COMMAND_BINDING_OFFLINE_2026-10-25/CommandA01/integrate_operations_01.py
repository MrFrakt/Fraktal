from pathlib import Path
R=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
def edit(name,changes):
 p=R/name;b=p.read_bytes();nl='\r\n' if b.count(b'\r\n')>b.count(b'\n')//2 else '\n';s=b.decode().replace('\r\n','\n')
 for old,new in changes:
  assert s.count(old)==1,(name,old[:70],s.count(old));s=s.replace(old,new)
 p.write_bytes(s.replace('\n',nl).encode())
edit('fraktal_ab_canonical_manifest.py',[
 ("COMMAND_HEADER = PRODUCT_HEADER | {'CommandBindingsCount','CommandBindingsCapacity'}", "COMMAND_HEADER = PRODUCT_HEADER | {'CommandBindingsCount','CommandBindingsCapacity','CommandOperationsCount','CommandOperationsCapacity'}"),
 ('products=None, commands=None):\n    result=', 'products=None, commands=None, operations=None):\n    result='),
 ("    if minor>=COMMAND_MINOR:result['commandBindings']=commands\n    return result\n\n\ndef content_hash", "    if minor>=COMMAND_MINOR:result.update(commandBindings=commands,commandOperations=operations)\n    return result\n\n\ndef content_hash"),
 ('products=None, commands=None):\n    raw =', 'products=None, commands=None, operations=None):\n    raw ='),
 ('products=products,commands=commands),','products=products,commands=commands,operations=operations),'),
 ("'DataProducts', 'CommandBindings')", "'DataProducts', 'CommandBindings', 'CommandOperations')"),
 ("    commands=[]\n", "    commands=[];command_operations=[]\n"),
 ("        validate_commands(commands)\n", '''        validate_commands(commands)
        from fraktal_ab_command_binding import operations as validate_operations, OPERATION_FIELD
        if record['CommandOperationsCount']!=39 or record['CommandOperationsCapacity']!=39 or not isinstance(record.get('CommandOperations'),list):
            raise ValueError('invalid command operation count/capacity')
        for row in record['CommandOperations']:
            if not isinstance(row,dict) or set(row)!=OPERATION_FIELD:raise ValueError('invalid command operation row')
            command_operations.append({k:text(v) if k=='RefusalKey' else v for k,v in row.items()})
        validate_operations(command_operations)
'''),
 ("**({'commands':commands} if minor>=COMMAND_MINOR else {}))", "**({'commands':commands,'operations':command_operations} if minor>=COMMAND_MINOR else {}))"),
 ("    if minor>=COMMAND_MINOR:result['commandBindings']=commands\n    return result", "    if minor>=COMMAND_MINOR:result.update(commandBindings=commands,commandOperations=command_operations)\n    return result")])
edit('fraktal_ab_canonical_publication.py',[
 ('from fraktal_ab_canonical_commands import descriptors\n        command_rows=descriptors(app);command_metadata=dict(commands=command_rows)',
  'from fraktal_ab_canonical_commands import descriptors,operations\n        command_rows=descriptors(app);command_operations=operations(app);command_metadata=dict(commands=command_rows,operations=command_operations)'),
 ('CommandBindings=command_rows)\n    return header', 'CommandBindings=command_rows,CommandOperationsCount=len(command_operations),CommandOperationsCapacity=len(command_operations),CommandOperations=command_operations)\n    return header')])
edit('fraktal_ab_canonical_reader.py',[
 ("        commands=validate_commands(manifest.get('commandBindings'))", "        commands=validate_commands(manifest.get('commandBindings'))\n        from fraktal_ab_command_binding import operations as validate_operations\n        validate_operations(manifest.get('commandOperations'))\n        if {r['RequestSymbol'] for r in manifest.get('services',[])}&set(records):\n            raise ValueError('staged service/request values are forbidden in persisted cyclic captures')"),
 ("    records = []\n    for symbol in symbols:", '''    if before.get('schemaMinor',0)>=6:
        forbidden={b['PayloadSymbol'] for b in before['commandBindings']}|{s['RequestSymbol'] for s in before.get('services',[])}
        planned={s['name'] for s in symbols if s.get('handle') in objects and not s.get('arrayRank',0)
                 and any(r['name']=='Status' and r['struct'] for r in member_table(objects[s['handle']]))}
        planned|={b['SourceSymbol'] for b in before.get('bindings',[])}|{b['SourceSymbol'] for b in before.get('dataProducts',[])}
        if planned&forbidden:raise ValueError('cyclic read plan includes a command or service input')
        by_handle={t['handle']:t for t in templates}
        by_name={s['name']:s for s in symbols}
        for b in before['commandBindings']:
            handle=by_name[b['PayloadSymbol']]['handle']
            by_handle[handle]['structureHandle']=template_structure_handle(comm,handle)
    records = []
    for symbol in symbols:'''),
 ('\ndef coherence_token(manifest):', '''
def template_structure_handle(comm,handle):
    """Template attribute 1, not the instance ID; never read payload bytes.

    Rockwell 1756-PM020I pp. 12, 52-53 defines this write-type parameter.
    """
    status,packet=comm.conn.send(comm._cip_message(0x03,0x6C,handle,[1]))
    if status!=0 or packet is None or len(packet)!=58:
        raise ValueError('Template structure-handle attribute read failed')
    fields=struct.unpack('<BBBBHHHH',packet[46:])
    if fields[:7]!=(0x83,0,0,0,1,1,0):raise ValueError('invalid Template structure-handle reply')
    return fields[7]


def coherence_token(manifest):''')])

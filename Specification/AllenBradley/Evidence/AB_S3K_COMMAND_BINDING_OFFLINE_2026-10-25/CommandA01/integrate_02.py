from pathlib import Path
R=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
def edit(name,changes):
    p=R/name;raw=p.read_bytes();nl='\r\n' if raw.count(b'\r\n')>raw.count(b'\n')//2 else '\n';s=raw.decode().replace('\r\n','\n')
    for old,new in changes:
        assert s.count(old)==1,(name,old[:90],s.count(old))
        s=s.replace(old,new)
    p.write_bytes(s.replace('\n',nl).encode())
edit('fraktal_ab_canonical_manifest.py',[
 ('PRODUCT_MINOR = 5','PRODUCT_MINOR = 5\nCOMMAND_MINOR = 6'),
 ("PRODUCT_FIELD = frozenset(('SourceSymbol', 'CoreType', 'CanonicalRoot'))", "PRODUCT_FIELD = frozenset(('SourceSymbol', 'CoreType', 'CanonicalRoot'))\nCOMMAND_HEADER = PRODUCT_HEADER | {'CommandBindingsCount','CommandBindingsCapacity'}"),
 ('\n         type_annotations=None, path_exceptions=None, products=None):','\n         type_annotations=None, path_exceptions=None, products=None, commands=None):'),
 ("    if minor>=PRODUCT_MINOR:result['dataProducts']=products\n    return result\n\n\ndef content_hash", "    if minor>=PRODUCT_MINOR:result['dataProducts']=products\n    if minor>=COMMAND_MINOR:result['commandBindings']=commands\n    return result\n\n\ndef content_hash"),
 ('\n                 type_annotations=None, path_exceptions=None, products=None):','\n                 type_annotations=None, path_exceptions=None, products=None, commands=None):'),
 ('path_exceptions=path_exceptions,products=products),','path_exceptions=path_exceptions,products=products,commands=commands),'),
 ('    if minor in (TYPE_MINOR,PRODUCT_MINOR):','    if minor in (TYPE_MINOR,PRODUCT_MINOR,COMMAND_MINOR):'),
 ("(PRODUCT_HEADER if minor==PRODUCT_MINOR else TYPE_HEADER) | {name for name in ('Bindings', 'Services', 'PathExceptions', 'DataProducts')", "(COMMAND_HEADER if minor==COMMAND_MINOR else PRODUCT_HEADER if minor==PRODUCT_MINOR else TYPE_HEADER) | {name for name in ('Bindings', 'Services', 'PathExceptions', 'DataProducts', 'CommandBindings')"),
 ('(MINOR, VIEW_MINOR, FRAGMENT_MINOR, SERVICE_MINOR, TYPE_MINOR, PRODUCT_MINOR)', '(MINOR, VIEW_MINOR, FRAGMENT_MINOR, SERVICE_MINOR, TYPE_MINOR, PRODUCT_MINOR, COMMAND_MINOR)'),
 ("item['Kind'] not in (1,2)","item['Kind'] not in ((1,2,3) if minor>=COMMAND_MINOR else (1,2))"),
 ('    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])', '''    commands=[]
    if minor>=COMMAND_MINOR:
        from fraktal_ab_command_binding import FIELD as CMD_FIELD, TEXT_FIELDS, bindings as validate_commands
        count,capacity=record['CommandBindingsCount'],record['CommandBindingsCapacity']
        if type(count) is not int or type(capacity) is not int or not 1<=count==capacity<=1024 \\
                or not isinstance(record.get('CommandBindings'),list) or len(record['CommandBindings'])!=capacity:
            raise ValueError('invalid command binding count/capacity')
        for row in record['CommandBindings']:
            if not isinstance(row,dict) or set(row)!=CMD_FIELD:raise ValueError('invalid command binding row')
            commands.append({k:text(v) if k in TEXT_FIELDS else v for k,v in row.items()})
        validate_commands(commands)
    legacy, digest = text(record["LegacyContentHash"]), text(record["ContentHash"])'''),
 ("**({'products':products} if minor>=PRODUCT_MINOR else {}))", "**({'products':products} if minor>=PRODUCT_MINOR else {}),\n            **({'commands':commands} if minor>=COMMAND_MINOR else {}))"),
 ("    if minor>=PRODUCT_MINOR:result['dataProducts']=products\n    return result", "    if minor>=PRODUCT_MINOR:result['dataProducts']=products\n    if minor>=COMMAND_MINOR:result['commandBindings']=commands\n    return result")])
edit('fraktal_ab_canonical_mailbox.py',[
 ("    definitions[INPUT]=(M('Sequence','DINT'),)","    definitions[INPUT]=tuple(M(n,'DINT') for n in ('Sequence','AckSequence','Accepted','DiagnosticKey','ResponseRevision','CoreSerial'))"),
 ("'Number','Negative','Digit','DigitCount','Position'","'Number','Negative','Digit','DigitCount','Position','LastDiagnostic'"),
 ("w=work_tag(app);target=app.name+'.HmiResponse';owner=mailbox.response_tag_name(app)","w=work_tag(app);target=app.name+'.HmiResponse';owner=input_tag(app)"),
 ("({w}.LastAck <> {owner}.AckSequence)","({w}.LastAck <> {owner}.ResponseRevision) OR ({w}.LastDiagnostic <> {owner}.DiagnosticKey) OR ({target}.Accepted <> ({owner}.Accepted <> 0))"),
 ("f'{w}.LastAck := {owner}.AckSequence;'","f'{w}.LastAck := {owner}.ResponseRevision;',f'{w}.LastDiagnostic := {owner}.DiagnosticKey;'"),
 ("    unit=f'FRK_{app.name}_Unit'\n    return [f'{input_tag(app)}.Sequence := {mailbox.request_tag_name(app)}.Sequence;',", "    import fraktal_ab_canonical_commands as commands\n    unit=f'FRK_{app.name}_Unit';w=commands.work_tag(app);q=input_tag(app);owner=mailbox.response_tag_name(app)\n    return [f'{q}.Sequence := {w}.OwnerSequence;',f'{q}.AckSequence := {w}.OwnerAck;',\n        f'{q}.Accepted := {owner}.Accepted;',f'{q}.DiagnosticKey := {owner}.DiagnosticKey;',\n        f'{q}.ResponseRevision := {w}.ResponseRevision;',f'{q}.CoreSerial := {w}.CoreSerial;',"),
 ("unit),f'JSR({routine(app)},0);']","unit),f'JSR({routine(app)},0);',*commands.publish_reply(app)]")])
edit('fraktal_ab_mailbox.py',[
 ('def _response(app, member: str) -> str:', '''def acknowledged_sequence(app):
    if app.canonical_publication_stage>=13:
        from fraktal_ab_canonical_commands import work_tag
        return work_tag(app)+'.OwnerAck'
    return _response(app,'AckSequence')


def _response(app, member: str) -> str:''')])
edit('fraktal_ab_sets.py',[("f'IF {response}.AckSequence = {s}.PendingSequence THEN'","f'IF {mb.acknowledged_sequence(app)} = {s}.PendingSequence THEN'")])
edit('fraktal_ab_config_provider.py',[("{mailbox.response_tag_name(app)}.AckSequence","{mailbox.acknowledged_sequence(app)}")])

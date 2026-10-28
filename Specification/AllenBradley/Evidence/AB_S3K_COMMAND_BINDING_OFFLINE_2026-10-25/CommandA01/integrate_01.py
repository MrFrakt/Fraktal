"""Anchored edits, preserving each existing file's newline convention."""
from pathlib import Path
R=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
def edit(name,changes):
    p=R/name;raw=p.read_bytes();nl=b'\r\n' if raw.count(b'\r\n')>raw.count(b'\n')//2 else b'\n'
    s=raw.decode().replace('\r\n','\n')
    for old,new in changes:
        assert s.count(old)==1,(name,old[:100],s.count(old))
        s=s.replace(old,new)
    p.write_bytes(s.replace('\n',nl.decode()).encode())
edit('fraktal_ab_canonical_publication.py',[
 ('    indices: tuple[int, ...] | None = None','    indices: tuple[int, ...] | None = None\n    access: str = ""'),
 ('CanonicalRootS3kV65','CanonicalRootS3kV66'),
 ('def header_type(app):\n','def header_type(app):\n    if app.canonical_publication_stage>=13:return f"FRK_T_{app.name}CanonicalManifestV66"\n'),
 ('        mailbox.augment(app,result)','        mailbox.augment(app,result)\n        import fraktal_ab_canonical_commands as commands\n        commands.augment(app,result)'),
 ('    result[PREFIX+"TimingV6"] =','    if app.canonical_publication_stage>=13:\n        result[header_type(app)]+=commands.manifest_members()\n    result[PREFIX+"TimingV6"] ='),
 ('    return int(kind.removeprefix(PREFIX+"String").removesuffix("V6"))','    import re\n    match=re.fullmatch(PREFIX+r"String(\\d+)(?:V6|CmdV66)",kind)\n    if not match:raise ValueError("not a canonical StringFamily: "+kind)\n    return int(match[1])'),
 ('                          Hidden="false",ExternalAccess="Read/Write" if kind=="FRK_T_ConfigProviderRequestV1" else "Read Only")','                          Hidden="false",ExternalAccess=member.access or ("Read/Write" if kind=="FRK_T_ConfigProviderRequestV1" else "Read Only"))'),
 ('    for kind, fields in definitions.items():','    if app.canonical_publication_stage>=13:\n        from fraktal_ab_canonical_commands import string_data_types\n        out+=string_data_types()\n    for kind, fields in definitions.items():'),
 ('    if app.canonical_publication_stage>=12:minor=wire.PRODUCT_MINOR','    if app.canonical_publication_stage>=12:minor=wire.PRODUCT_MINOR\n    if app.canonical_publication_stage>=13:minor=wire.COMMAND_MINOR'),
 ('    digest = wire.content_hash(fields,old_hash,app.canonical_publication_stage,minor=minor,','    command_metadata={}\n    if minor>=wire.COMMAND_MINOR:\n        from fraktal_ab_canonical_commands import descriptors\n        command_rows=descriptors(app);command_metadata=dict(commands=command_rows)\n    digest = wire.content_hash(fields,old_hash,app.canonical_publication_stage,minor=minor,'),
 ('**type_metadata, **product_metadata)','**type_metadata, **product_metadata, **command_metadata)'),
 ('    return header\n','    if minor>=wire.COMMAND_MINOR:header.update(CommandBindingsCount=len(command_rows),CommandBindingsCapacity=len(command_rows),CommandBindings=command_rows)\n    return header\n'),
 ('            *(__import__("fraktal_ab_canonical_mailbox").tags(app,tag) if app.canonical_publication_stage>=13 else []),','            *(__import__("fraktal_ab_canonical_mailbox").tags(app,tag) if app.canonical_publication_stage>=13 else []),\n            *(__import__("fraktal_ab_canonical_commands").tags(app,tag) if app.canonical_publication_stage>=13 else []),')])
edit('fraktal_ab_canonical_type_manifest.py',[
 ('    rows, paths = list(annotations.values()), list(exceptions.values())','    if app.canonical_publication_stage>=13:\n        from fraktal_ab_canonical_commands import ARGS\n        walk(ARGS,app.name+"/HmiRequest")\n    rows, paths = list(annotations.values()), list(exceptions.values())')])
edit('fraktal_ab_canonical_text.py',[
 ('        result += mailbox.literals(app)','        result += mailbox.literals(app)\n        import fraktal_ab_canonical_commands as commands\n        result += commands.literals(app)')])
edit('fraktal_ab_mailbox_frame.py',[
 ('def logic(app):\n    import fraktal_ab_mailbox as mb','def logic(app, *, legacy=False):\n    if app.canonical_publication_stage>=13 and not legacy:\n        from fraktal_ab_canonical_commands import ingress\n        return tuple(ingress(app))\n    import fraktal_ab_mailbox as mb')])
edit('fraktal_ab_mailbox.py',[
 ("if write_only and getattr(app, 'simulation_mailbox_rw', False):","if write_only and getattr(app, 'simulation_mailbox_rw', False) and app.canonical_publication_stage<13:"),
 ('        f"IF {_request(app, \'Sequence\')} <> FRK_{n}_HmiLastSequence THEN",',
  '        (f"IF {__import__(\'fraktal_ab_canonical_commands\').work_tag(app)}.Pending <> 0 THEN" if app.canonical_publication_stage>=13 else f"IF {_request(app, \'Sequence\')} <> FRK_{n}_HmiLastSequence THEN"),'),
 ('        f"FRK_{n}_HmiLastSequence := {_request(app, \'Sequence\')};",',
  '        f"FRK_{n}_HmiLastSequence := {committed_sequence(app)};",'),
 ('    if enabled:\n        import fraktal_ab_generate as gen','    if app.canonical_publication_stage>=13:\n        import fraktal_ab_canonical_commands as commands\n        w=commands.work_tag(app)\n        lines += [f"IF {w}.Error <> 0 THEN",f"CASE {w}.Error OF",\n            "2:",*_refuse(app,commands.COLLISION),"3:",*_refuse(app,commands.STALE),\n            "ELSE",*_refuse(app,commands.INVALID),"END_CASE;","ELSE"]\n    if enabled:\n        import fraktal_ab_generate as gen'),
 ('        *(["END_IF;", *access.after(app), f\'JSR({data.tag(app, "RefreshLevels")},0);\'] if enabled else []),',
  '        *(["END_IF;", *access.after(app), f\'JSR({data.tag(app, "RefreshLevels")},0);\'] if enabled else []),\n        *(["END_IF;"] if app.canonical_publication_stage>=13 else []),'),
 ('    return tuple(lines)\n\n\n# --- the localization keys',
  '    if app.canonical_publication_stage>=13:lines+=commands.after_owner(app)\n    return tuple(lines)\n\n\n# --- the localization keys'),
 ('def localization_keys() -> tuple[str, ...]:','def localization_keys(app=None) -> tuple[str, ...]:'),
 ('    return tuple(sorted(set(REFUSED.values()) | extra | set(sets.KEYS) | set(shelving.KEYS)))',
  '    if app is not None and app.canonical_publication_stage>=13:\n        from fraktal_ab_canonical_commands import KEYS\n        extra.update(KEYS)\n    return tuple(sorted(set(REFUSED.values()) | extra | set(sets.KEYS) | set(shelving.KEYS)))'),
 ('def _response(app, member: str) -> str:',
  'def committed_sequence(app):\n    if app.canonical_publication_stage>=13:\n        from fraktal_ab_canonical_commands import work_tag\n        return work_tag(app)+".OwnerSequence"\n    return _request(app,"Sequence")\n\n\ndef _response(app, member: str) -> str:')])
edit('fraktal_ab_manifest.py', [('for portable in mailbox.localization_keys():','for portable in mailbox.localization_keys(app):')])
edit('fraktal_ab_canonical_config.py',[("f'{w}.QuerySequence := {q}.Sequence;'","f'{w}.QuerySequence := {mb.committed_sequence(app)};'")])
edit('fraktal_ab_generate.py',[
 ('        result += mailbox_publication.routines(app)','        result += mailbox_publication.routines(app)\n        import fraktal_ab_canonical_commands as commands\n        result += commands.routines(app)')])

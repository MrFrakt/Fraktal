from pathlib import Path

root=Path('FraktalCore/PLC/Allen-Bradley/tools')

def edit(name,pairs):
    p=root/name
    raw=p.read_bytes(); newline=b'\r\n' if b'\r\n' in raw else b'\n'
    source=raw.decode().replace('\r\n','\n')
    for old,new in pairs:
        assert source.count(old)==1,(name,old,source.count(old))
        source=source.replace(old,new)
    p.write_bytes(source.replace('\n',newline.decode()).encode())

edit('fraktal_ab_line.py',[
 ('def state_members():\n    return (decl.scalar(\'SchemaVersion\', initial=1)',
  'def state_schema(app=None):\n    return 2 if app is not None and app.canonical_publication_stage >= 11 else 1\n\n\ndef state_type(app):\n    return f\'FRK_T_LineStateV{state_schema(app)}\'\n\n\ndef state_members(app=None):\n    return (decl.scalar(\'SchemaVersion\', initial=state_schema(app))'),
 ("decl.scalar('LineIdKey'), decl.scalar('OwnerIdKey'))", "decl.scalar('LineIdKey'), decl.scalar('OwnerIdKey')) + (\n            tuple(decl.scalar(n) for n in ('TimeSynchronized', 'SourceError')) if state_schema(app) >= 2 else ())"),
 ("decl.Record('FRK_T_LineStateV1', state_members())", "decl.Record(state_type(app), state_members(app))"),
 ("else m for m in state_members())", "else m for m in state_members(app))"),
 ("('State', 'FRK_T_LineStateV1', state, 'Read Only')", "('State', state_type(app), state, 'Read Only')"),
 ("f'{s}.UpdatedDate := FRK_{app.name}_NowDate;', f'{s}.UpdatedClock := FRK_{app.name}_NowTime;']", "f'{s}.UpdatedDate := FRK_{app.name}_NowDate;', f'{s}.UpdatedClock := FRK_{app.name}_NowTime;'] + (\n            [f'{s}.TimeSynchronized := FRK_{app.name}_HealthProbe.TimeIsSynchronized;', f'{s}.SourceError := 0;']\n            if state_schema(app) >= 2 else [])"),
 ("state.get('SchemaVersion') != 1", "state.get('SchemaVersion') not in (1, 2)")])

pairs=[
 ('(wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10)', '(wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10, 11)'),
 ('(0, wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10)', '(0, wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10, 11)'),
 ('S3g or S3h"]','S3g, S3h or S3i"]'),
 ("if stage>=10:reserved.update(('Part','HostEvents','Nameplate','SignalTower','MachineState'))", "if stage>=10:reserved.update(('Part','HostEvents','Nameplate','SignalTower','MachineState'))\n    if stage>=11:reserved.update(('Line','CurrentShift','ShiftStartedAt','ShiftEndsAt','ShiftProductionTarget',\n        'ShiftHistory','ShiftHistoryCount','ShiftHistoryTruncated','ShiftTimeSynchronized','ShiftCalendarPending','ShiftClosedSequence'))"),
 ('        findings.extend(trace.validate(app))','        findings.extend(trace.validate(app))\n    if stage>=11:\n        import fraktal_ab_canonical_line as line\n        findings.extend(line.validate(app))'),
 ('def root_type(app):','def root_type(app):\n    if app.canonical_publication_stage==11:return f"FRK_T_{app.name}CanonicalRootS3iV63"'),
 ('def header_type(app):','def header_type(app):\n    if app.canonical_publication_stage==11:return f"FRK_T_{app.name}CanonicalManifestS3iV63"'),
 ('        trace.augment(app,result)','        trace.augment(app,result)\n    if app.canonical_publication_stage>=11:\n        import fraktal_ab_canonical_line as line\n        line.augment(app,result)'),
 ('        trace.initialize(app,result)','        trace.initialize(app,result)\n    if app.canonical_publication_stage>=11:\n        import fraktal_ab_canonical_line as line\n        line.initialize(app,result)'),
 ('            *(__import__("fraktal_ab_canonical_traceability").tags(app,tag) if app.canonical_publication_stage>=10 else []),','            *(__import__("fraktal_ab_canonical_traceability").tags(app,tag) if app.canonical_publication_stage>=10 else []),\n            *(__import__("fraktal_ab_canonical_line").tags(app,tag) if app.canonical_publication_stage>=11 else []),'),
 ('        lines += trace.cyclic(app)','        lines += trace.cyclic(app)\n    if app.canonical_publication_stage>=11:\n        import fraktal_ab_canonical_line as line\n        lines += line.cyclic(app)')]
edit('fraktal_ab_canonical_publication.py',pairs)
edit('fraktal_ab_canonical_observation.py',[
 ('FRAME_STAGES = (10,)','FRAME_STAGES = (10, 11)'),
 ('return f"FRK_T_{app.name}ObservationFrameS3h"','return f"FRK_T_{app.name}ObservationFrameS3" + ("i" if app.canonical_publication_stage >= 11 else "h")'),
 ('    return tuple(result)','    if app.canonical_publication_stage >= 11 and app.line is not None:\n        import fraktal_ab_line as line\n        result += [line.tag(app, "State"), line.tag(app, "Shift")]\n    return tuple(result)'),
 ('supports only the S3h oracle stage','supports only the S3h/S3i oracle stages')])
edit('fraktal_ab_generate.py',[
 ('        result += trace.routines(app)','        result += trace.routines(app)\n    if app.canonical_publication_stage>=11:\n        import fraktal_ab_canonical_line as line\n        result += line.routines(app)')])
print('S3i integration applied; original line endings preserved')

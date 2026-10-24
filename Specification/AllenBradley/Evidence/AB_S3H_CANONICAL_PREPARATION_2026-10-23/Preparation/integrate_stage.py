from pathlib import Path
T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
p=T/'fraktal_ab_canonical_publication.py';text=p.read_text()
text=text.replace('(wire.STAGE, 3, 4, 5, 6, 7, 8, 9)','(wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10)',1)
text=text.replace('(0, wire.STAGE, 3, 4, 5, 6, 7, 8, 9)','(0, wire.STAGE, 3, 4, 5, 6, 7, 8, 9, 10)',1)
text=text.replace('S3f or S3g','S3f, S3g or S3h',1)
text=text.replace("    if stage>=9:reserved.update(('Oee','OeeTrend','OeeTrendHead','Profiler','SystemHealth'))",
    "    if stage>=9:reserved.update(('Oee','OeeTrend','OeeTrendHead','Profiler','SystemHealth'))\n    if stage>=10:reserved.update(('Part','HostEvents','Nameplate','SignalTower','MachineState'))",1)
text=text.replace('        findings.extend(metrics.validate(app))','        findings.extend(metrics.validate(app))\n    if stage>=10:\n        import fraktal_ab_canonical_traceability as trace\n        findings.extend(trace.validate(app))',1)
for what in ('Root','Manifest'):
    needle=f'    if app.canonical_publication_stage==9:return f"FRK_T_{{app.name}}Canonical{what}S3gV63"'
    assert needle in text
    text=text.replace(needle,f'    if app.canonical_publication_stage==10:return f"FRK_T_{{app.name}}Canonical{what}S3hV63"\n'+needle,1)
for needle,extra in (
    ('        metrics.augment(app,result)','        trace.augment(app,result)'),
    ('        metrics.initialize(app,result)','        trace.initialize(app,result)'),
    ('        lines += metrics.cyclic(app)','        lines += trace.cyclic(app)')):
    assert needle in text
    text=text.replace(needle,needle+'\n    if app.canonical_publication_stage>=10:\n        import fraktal_ab_canonical_traceability as trace\n'+extra,1)
needle='            *(metrics.tags(app,tag) if app.canonical_publication_stage>=9 else []),'
assert needle in text
text=text.replace(needle,needle+'\n            *(__import__("fraktal_ab_canonical_traceability").tags(app,tag) if app.canonical_publication_stage>=10 else []),',1)
p.write_text(text)
p=T/'fraktal_ab_generate.py';raw=p.read_bytes()
needle=b'        result += metrics.routines(app)\r\n'
assert raw.count(needle)==1
raw=raw.replace(needle,needle+b'    if app.canonical_publication_stage>=10:\r\n        import fraktal_ab_canonical_traceability as trace\r\n        result += trace.routines(app)\r\n',1)
p.write_bytes(raw)
p=T/'fraktal_ab_s2_equivalence.py';text=p.read_text();assert "9:'s3g'}" in text
p.write_text(text.replace("9:'s3g'}","9:'s3g',10:'s3h'}",1))
print('Stage 10 engineering hooks added; earlier-stage branches unchanged')

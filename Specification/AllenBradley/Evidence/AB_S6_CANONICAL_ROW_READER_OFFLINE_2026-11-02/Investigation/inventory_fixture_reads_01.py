"""Offline engineering audit; declaration use is confined to this inventory."""
from pathlib import Path
import ast, hashlib, json, sys

R=Path('C:/Users/SoftIndVM/Fraktal'); W=Path(__file__).parent
T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_canonical_reader as reader
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as declaration

app=declaration.application()
cap=reader.load_json(R/'Specification/AllenBradley/Evidence/AB_S5_GATEWAY_QUALIFICATION_2026-10-31/Runtime/generic_capture.json.gz')
doc=reader.snapshot(cap)
names=['fraktal_ab_press_execute','fraktal_ab_press_parity','fraktal_ab_part_execute',
       'fraktal_ab_press_canonical_execute','fraktal_ab_generate']
sources={};keys={}
for name in names:
    path=T/(name+'.py'); data=path.read_bytes();tree=ast.parse(data)
    sources[name]=hashlib.sha256(data).hexdigest().upper()
    keys[name]=sorted({node.slice.value for node in ast.walk(tree)
                      if isinstance(node,ast.Subscript) and isinstance(node.slice,ast.Constant)
                      and isinstance(node.slice.value,str)})
members=[m.name for m in gen.unit_context_members(app)]
exact=[m for m in members if app.name+'/'+m in doc['values']]
out=dict(schema='fraktal.ab.s6-fixture-read-inventory',schemaVersion=1,
    controllerAccess=False,engineeringDeclarationOnly='fraktal_ab_genealogy_s4b_owner_demo',
    sourceHashes=sources,unitMembers=members,literalCanonicalLeafMatches=exact,
    unitMembersWithoutLiteralCanonicalLeaf=[m for m in members if m not in exact],
    subscriptKeys=keys,
    limitations=['Literal spelling inventory is not a semantic correspondence or a publication request.',
                'Private fixture controls and guards must not be fabricated from Core status.',
                'No existing assertion or write/fingerprint guard changes in this checkpoint.'])
with (W/'fixture_read_inventory_01.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps(dict(unitMembers=len(members),literalMatches=exact,
    criticalPrivateNames=[m for m in ('SchemaVersion','Par_TaskPeriodMs','RunRequest','AbortRequest','ResetRequest','Running','Complete','Aborted') if m in members and m not in exact])))

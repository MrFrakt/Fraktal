"""AST/source inventory and pure V1 wire arithmetic; no declaration or I/O client."""
from pathlib import Path
import ast,hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_config_provider_wire as wire
names=('fraktal_ab_sets','fraktal_ab_set_broker','fraktal_ab_medium',
       'fraktal_ab_live','fraktal_ab_host_events','fraktal_ab_config_provider',
       'fraktal_ab_config_provider_wire','fraktal_ab_config_provider_client')
sources={};constants={}
for name in names:
    path=T/(name+'.py');data=path.read_bytes();tree=ast.parse(data)
    imports=sorted({node.module for node in ast.walk(tree)
                    if isinstance(node,ast.ImportFrom) and node.module}
                   |{alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names})
    sources[name]=dict(sha256=hashlib.sha256(data).hexdigest().upper(),imports=imports,
        functions=[node.name for node in tree.body if isinstance(node,ast.FunctionDef)],
        classes=[node.name for node in tree.body if isinstance(node,ast.ClassDef)])
    literals={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try:literals[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    constants[name]=literals
assert constants['fraktal_ab_sets']['MAX_SETS']==wire.MAX_SETS
native_bytes=sum(count or 1 for name,count in wire.layout())*4
result=dict(schema='fraktal.ab.s6-host-service-inventory',schemaVersion=1,
    controllerAccess=False,codeGeneration=False,sources=sources,
    configSets={name:constants['fraktal_ab_sets'][name] for name in
                ('MAX_SETS','MAX_RECORDS','LINE_MAX','NAME_MAX','WINDOW_MS','AUDIT_CAPACITY',
                 'SET_KINDS','HEADER_FIELDS','RECORD_FIELDS')},
    providerV1=dict(version=wire.VERSION,textFields=wire.TEXTS,textByteValues=wire.BYTE_CAPACITY,
        textLengthFields=len(wire.TEXTS),layout=wire.layout(),nativeDintBytes=native_bytes),
    liveIndex={name:constants['fraktal_ab_live'][name] for name in
               ('LIVE_NAME','INDEX_NAME','INDEX_SCHEMA','INDEX_VERSION')},
    runtimeImportGraphClean=not (set(sys.modules)&{'fraktal_ab_declaration','fraktal_ab_station',
        'fraktal_ab_generate','fraktal_ab_projection','fraktal_ab_gateway'}))
assert result['runtimeImportGraphClean']
assert result['providerV1']['textByteValues']==1616 and native_bytes==6664
with (W/'host_service_inventory_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(sourceOwners=len(sources),textFields=len(wire.TEXTS),
    textByteValues=wire.BYTE_CAPACITY,nativeDintBytes=native_bytes,controllerAccess=False)))

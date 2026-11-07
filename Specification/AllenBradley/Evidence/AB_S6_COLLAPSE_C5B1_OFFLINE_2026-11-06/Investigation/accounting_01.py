from pathlib import Path
import ast,hashlib,json,subprocess,sys
R=Path('C:/Users/SoftIndVM/Fraktal');T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_fixture_observation as fixture
import fraktal_ab_press_s6_collapse_echo38 as profile
W=Path(__file__).parent;app=profile.application()
new={'Cfg0':{'SchemaVersion':'px.fingerprint/cfg_schema','BaselineWorkMs':'phase6.configuration/run/restore'},
     'ConfigAudit':{n:'phase6.run/capture accepted-write observation and refusal/no-change checks' for n in ('Head','Sequence','Kind','Value','SourceKey','Revision')},
     'Profiler':{'LastWork':'phase6.run/work sampled before CAPTURE_CONFIG'},
     'AirPressureMonitor':{'OutImm_PressureOk':'phase6.run/air-loss wait predicate'}}
old=json.loads((W/'reference_overlay.json').read_bytes())['commit']
provenance=[]
for surface,m,name,source in fixture.facts(app):
 if surface not in new:continue
 provenance.append(dict(surface=surface,member=m.name,nativeKind=m.kind,elements=m.dimension or 1,source=source+'.'+m.name,
     observed=name,consumer=new[surface][m.name],nativeReplay='old 86 accepted press captures' if surface!='ConfigAudit' else 'not available in old captures; S6-Q remains open',
     offlineProof='emitted writer/ST model, exact literal token append, template/default/read-back audits'))
assert len(provenance)==10
before=subprocess.check_output(['git','show',old+':FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase6_execute.py'],cwd=R).decode()
after=(T/'fraktal_ab_phase6_execute.py').read_text(encoding='utf-8')
def predicates(source):
 run=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='run')
 return [dict(test=ast.unparse(n.args[0]),assertion=ast.unparse(n.args[-1])) for n in ast.walk(run)
         if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='row']
result=dict(schema='fraktal.ab.c5b1-fact-and-case-accounting',schemaVersion=1,scope='Phase 6 capture and read-only viewer only; not all HX clients',parentCommit=old,fixtureFacts=len(fixture.facts(app)),addedFacts=provenance,
 protocols=[dict(case='read_only_viewer_queries_configuration',before='legacy Python gateway special-cases QUERY_CONFIG and acknowledges a mailbox write',after='packaged Dart readConfigurationPage; the sequence must not change',authority='approved S4b/D9 read-only configuration view'),
            dict(case='foreign_capture_scope',before='legacy CONFIG_KEY_UNKNOWN_KEY',after='Core TARGET_KEY',authority='approved S3k typed Core binding')],
 beforeRunPredicates=predicates(before),afterRunPredicates=predicates(after),
 preserved=['exact stored raw BaselineWorkMs equals sampled WORK, not candidate 999999','native audit value/kind/sequence/source key','rejected capture leaves configuration and accepted-write audit unchanged','setup and air release gates','baseline/mode/style restoration and final input disarm'],
 pending=['set workflows/Dart host process lifecycle','other HX consumers','Frame/staged endpoint removal/V6.12','native capture/audit, scan and integrated S6-Q after C7'],
 sources=[dict(path=p.relative_to(R).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper()) for p in (T/'fraktal_ab_phase6_execute.py',T/'fraktal_ab_phase5_execute.py',T/'fraktal_ab_press_execute.py',T/'fraktal_ab_fixture_reads.py')],controllerAccess=False)
with (W/'accounting_01.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(addedFacts=len(provenance),runPredicateSites=len(result['afterRunPredicates']),controllerAccess=False)))

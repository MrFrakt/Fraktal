from pathlib import Path
import json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools';sys.path.insert(0,str(T))
import fraktal_ab_schema_identity as si
before=si.read(T/'fixtures/schema_identity/fraktal_ab_press_canonical_echo38.json.gz')
after=si.surface(W/'press_01.L5X');declared=[si.Declared(**d) for d in json.loads((T/'fixtures/schema_identity/fraktal_ab_press_s6_collapse_echo38.declared.json').read_bytes())]
result=si.compare(before,after,declared)
with (W/'schema_press_02.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(passed=result['passed'],uncovered=len(result['uncovered']),covered=len(result['covered']),unused=len(result.get('unusedDeclarations',[])))))
raise SystemExit(0 if result['passed'] else 1)

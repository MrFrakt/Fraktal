from pathlib import Path
import ast,json
W=Path(__file__).parent
files=[]
for path in sorted(W.glob("*.py")):
 ast.parse(path.read_text(encoding="utf-8"),filename=str(path));files.append(path.name)
with (W/"control_syntax_01.json").open("x",encoding="utf-8") as out:json.dump(dict(passed=True,files=files,executed=False,controllerAccess=False),out,indent=2)
print(json.dumps(dict(passed=True,controlScripts=len(files))))

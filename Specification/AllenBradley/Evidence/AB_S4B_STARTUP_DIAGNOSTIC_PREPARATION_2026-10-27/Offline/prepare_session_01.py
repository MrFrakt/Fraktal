from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-status-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
before="OLD=Path('C:/work/fraktal-ab-s4b-cold-20261026/session_01')"
assert source.count(before)==1
source=source.replace(before,"OLD=Path('C:/work/fraktal-ab-s4b-status-20261027/session_01')")
before="G=OLD.parent/'offline_01'"
assert source.count(before)==1
source=source.replace(before,"G=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01')")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
import json,shutil
S=W.parent/'session_01'
shutil.copyfile(W/'desktop_diagnostic_qualification_test.dart',S/'desktop_diagnostic_qualification_test.dart')
path=S/'desktop_readonly.py'
text=path.read_text(encoding='utf-8')
before="env.pop('FRAKTAL_AB_DESKTOP_FORCE_STALE_FIXTURE',None)"
assert text.count(before)==1
text=text.replace(before,before+"\nenv.pop('FRAKTAL_AB_DESKTOP_FORCE_STARTUP_FAILURE_FIXTURE',None)")
path.write_text(text,encoding='utf-8',newline='')
path=S/'authorization.template.json'
approval=json.loads(path.read_bytes())
approval['Scope']+=' Diagnostic-only repository log adds source/RPC/server/transit/local age components on a rejected complete sample. The desktop helper retains the primary startup exception and stack. No freshness, retry, row proof or acceptance rule changes; this session may reproduce the refusal.'
path.write_text(json.dumps(approval,indent=2)+'\n',encoding='utf-8',newline='')
print('Prepared unapproved same-image startup diagnostic session; no controller access.')

import difflib,importlib.util,re
from pathlib import Path
w=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('canonical',r'C:\Projects\Fraktal\FraktalCore\PLC\Siemens\Spikes\S12_TypeMap\verify_roundtrip.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=(w/'press_04/23_00_FB_PressDemoLoadPosition.scl').read_text('ascii')
a=re.search(r'^FUNCTION_BLOCK\b.*?^END_FUNCTION_BLOCK\b[^\n]*',a,re.M|re.S)[0]
b=(w/'press_export_final/scl/FB_PressDemoLoadPosition.scl').read_text('utf-8-sig')
print('\n'.join(difflib.unified_diff(a.splitlines(),b.splitlines(),n=2))[:10000])
aa=m.canonical(a);bb=m.canonical(b)
print(type(aa),len(aa),len(bb))
for i,(x,y) in enumerate(zip(aa,bb)):
    if x!=y:
        print('canonical first difference',i,repr(aa[max(0,i-100):i+300]),repr(bb[max(0,i-100):i+300]));break

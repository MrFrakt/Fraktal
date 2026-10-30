from pathlib import Path
import gzip,json
R=Path('C:/Users/SoftIndVM/Fraktal');E=R/'Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Runtime'
q=json.loads(gzip.decompress((E/'generic_snapshot.json.gz').read_bytes()))
values=q['values']
for path,value in values.items():
    if '/Access/' in path and any(name in path for name in ('Level','ClassId','Policy')):
        print(path,'=',value)

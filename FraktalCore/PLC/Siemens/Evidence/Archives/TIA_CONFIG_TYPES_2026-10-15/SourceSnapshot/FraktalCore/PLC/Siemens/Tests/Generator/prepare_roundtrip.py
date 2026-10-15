"""Order native block sources by the validated package's dependency order."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def prepare(original,exported,out):
    ordered=[]
    for source in sorted(original.iterdir()):
        if source.suffix not in ('.scl','.udt','.db'):continue
        text=source.read_text(encoding='ascii')
        for block in re.finditer(r'^(TYPE|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\s+"([^"]+)"',text,re.M):
            path=exported/'scl'/(block[2]+source.suffix)
            if not path.exists():raise ValueError('native source missing: '+str(path))
            ordered.append(path)
    out.mkdir(parents=True,exist_ok=False)
    inventory={}
    for index,path in enumerate(ordered):
        name='%03d_%s' % (index,path.name)
        data=path.read_bytes();(out/name).write_bytes(data)
        inventory[name]=hashlib.sha256(data).hexdigest()
    (out/'inventory.json').write_bytes((json.dumps(inventory,indent=2)+'\n').encode('ascii'))
    print(json.dumps({'ordered_sources':len(ordered)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('original','exported','out'):p.add_argument(name,type=Path)
    args=p.parse_args();prepare(args.original,args.exported,args.out)

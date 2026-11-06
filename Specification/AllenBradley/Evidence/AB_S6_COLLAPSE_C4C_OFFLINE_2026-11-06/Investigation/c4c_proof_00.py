"""Token proof of C4c against C4b. Only AOI type names, V5 key renumbering,
derived counts/revisions and equivalent text-pool offsets may differ.
Usage: output.json before.L5X after.L5X [before.L5X after.L5X ...].
"""
from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET
T=Path('C:/work/fraktal-ab-c4-20261106/FraktalCore/PLC/Allen-Bradley/tools')
sys.path.insert(0,str(T))
import fraktal_ab_st_model as st
import fraktal_ab_schema_identity as si


def bodies(root):
    result={}
    for kind,nodes in (('program',root.iter('Program')),('aoi',root.iter('AddOnInstructionDefinition'))):
        for node in nodes:
            for routine in node.iter('Routine'):
                key=(kind,node.get('Name').replace('R8C4','R8'),routine.get('Name'))
                text='\n'.join(n.text or '' for n in routine.iter() if n.tag in ('Line','Text'))
                text=re.sub(r'\b(FRK_\w*?)R8C4(Rev)?\b',r'\1R8\2',text)
                result[key]=[(t.kind,t.text) for t in st.tokenize(text) if t.kind!='eof']
    return result


def compare(before,after):
    surfaces=[si.surface(p) for p in (before,after)]
    rootname=next(t[:-len('_MfHeader')] for t in surfaces[0]['tags'] if t.endswith('_MfHeader'))
    tables=[]
    for surface in surfaces:
        tags=surface['tags'];h=tags[rootname+'_MfHeader']['Data']
        keys={r['PortableKey']['DATA'].strip().strip("'"):int(r['NumericKey'])
              for r in tags[rootname+'_MfLocalization']['Data'] if int(r['PortableKey']['LEN'])}
        tables.append((keys,int(h['LocalizationCount']),int(h['ConfigRevision'])))
    (a,ac,ar),(b,bc,br)=tables
    mapping={a[k]:b[k] for k in a if k in b and a[k]!=b[k]}
    for x,y in ((ac,bc),(ac+1,bc+1),(ar,br)):
        if x!=y:mapping[x]=y
    roots=[ET.parse(p).getroot() for p in (before,after)]
    code=[bodies(r) for r in roots]
    def pool(root):
        tag=next(t for t in root.find('./Controller/Tags') if t.get('Name')==rootname+'_CanonicalTextPool')
        return [int(n.get('Value')) for n in tag.iter('Element')]
    pools=[pool(r) for r in roots]
    diffs=[];renumbered=offsets=0
    for key in sorted(set(code[0])|set(code[1])):
        a,b=code[0].get(key,[]),code[1].get(key,[])
        if len(a)!=len(b):
            diffs.append(dict(routine=key,reason='token count',counts=[len(a),len(b)]));continue
        for i,(x,y) in enumerate(zip(a,b)):
            if x==y:continue
            if x[0]==y[0]=='number':
                old,new=int(x[1]),int(y[1])
                if mapping.get(old)==new:renumbered+=1;continue
                context=[v for _,v in a[max(0,i-4):i]]
                if len(context)==4 and context[0].endswith('_CanonicalTextWork') and context[1:]==['.','Offset',':=']:
                    def string(data,pos):
                        end=data.index(0,pos) if 0 in data[pos:] else len(data)
                        return data[pos:end]
                    if string(pools[0],old)==string(pools[1],new):offsets+=1;continue
            diffs.append(dict(routine=key,index=i,before=x,after=y,context=a[max(0,i-6):i]))
    # Local relocation changes metadata only, never any executed AOI/routine token.
    return dict(passed=not diffs,routines=len(code[0]),renumberedLiterals=renumbered,
                movedPoolOffsets=offsets,poolBytes=list(map(len,pools)),differences=diffs,
                inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper()) for p in (before,after)])


output,*args=sys.argv[1:]
results=[compare(Path(args[i]),Path(args[i+1])) for i in range(0,len(args),2)]
result=dict(passed=all(r['passed'] for r in results),results=results,controllerAccess=False)
with Path(output).open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

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


def bodies(root, names=None):
    names=names or {}
    result={}
    for kind,nodes in (('program',root.iter('Program')),('aoi',root.iter('AddOnInstructionDefinition'))):
        for node in nodes:
            for routine in node.iter('Routine'):
                key=(kind,names.get(node.get('Name'),node.get('Name')),routine.get('Name'))
                text='\n'.join(n.text or '' for n in routine.iter() if n.tag in ('Line','Text'))
                for new,old in names.items():
                    text=re.sub(r'\b'+re.escape(new)+r'\b',old,text)
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
    oldnames={n.get('Name') for n in roots[0].iter('AddOnInstructionDefinition')}
    names={}
    for node in roots[1].iter('AddOnInstructionDefinition'):
        name=node.get('Name')
        if name in oldnames:continue
        base=re.sub(r'R8C4[0-9A-F]{8}(Rev)?$',r'R8\1',name)
        if base==name:base=re.sub(r'R8C4$', 'R8', name)
        if base not in oldnames and name.startswith('FRK_U_'):
            prefix=re.sub(r'R8C4$', 'R8', re.sub(r'_C4[0-9A-F]{8}$','',name))
            candidates=[old for old in oldnames if old.startswith(prefix)]
            assert len(candidates)==1, (name,candidates)
            base=candidates[0]
        assert base in oldnames, (name,base)
        names[name]=base
    code=[bodies(roots[0]),bodies(roots[1],names)]
    def pool(root):
        tag=next(t for t in root.find('./Controller/Tags') if t.get('Name')==rootname+'_CanonicalText')
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
                    following=a[i+1:i+7]
                    if len(following)==6 and [v for _,v in following[2:5]]==['.','Length',':='] and following[5][0]=='number':
                        length=int(following[5][1])
                        if 0 < length and pools[0][old:old+length]==pools[1][new:new+length] and len(pools[0][old:old+length])==length:
                            offsets+=1;continue
            diffs.append(dict(routine=key,index=i,before=x,after=y,context=a[max(0,i-6):i]))
    # Local relocation changes metadata only, never any executed AOI/routine token.
    return dict(passed=not diffs,routines=len(code[0]),renamedAoIs=names,renumberedLiterals=renumbered,
                movedPoolOffsets=offsets,poolBytes=list(map(len,pools)),differences=diffs,
                inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper()) for p in (before,after)])


output,*args=sys.argv[1:]
results=[compare(Path(args[i]),Path(args[i+1])) for i in range(0,len(args),2)]
result=dict(passed=all(r['passed'] for r in results),results=results,controllerAccess=False)
with Path(output).open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
print(json.dumps(result,indent=1))
raise SystemExit(0 if result['passed'] else 1)

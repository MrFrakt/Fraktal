"""Compare frame interfaces/access flags and every authored block's native source."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1] / 'tools'))
import tia_lint
spec=importlib.util.spec_from_file_location('canonical',HERE.parents[1] / 'Spikes/S12_TypeMap/verify_roundtrip.py')
CANON=importlib.util.module_from_spec(spec);spec.loader.exec_module(CANON)
SECTIONS={'VAR_INPUT':'Input','VAR_OUTPUT':'Output','VAR_IN_OUT':'InOut','VAR':'Static','VAR_TEMP':'Temp','VAR CONSTANT':'Constant'}


def verify(source,exported):
    result={'interfaces':{},'sources':{}}
    for path in sorted(source.iterdir()):
        if path.suffix not in ('.scl','.udt','.db'):continue
        text=path.read_text(encoding='ascii')
        # One input may contain several FCs; each is exported as its own source.
        matches=list(re.finditer(r'^(TYPE|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\b.*?^END_\1\b[^\n]*',text,re.M|re.S))
        if not matches:raise ValueError('no source blocks: '+path.name)
        for match in matches:
            body=match[0]
            name=re.match(r'\w+\s+"([^"]+)"',body)[1]
            target=exported/'scl'/(name+path.suffix)
            if CANON.canonical(body)!=CANON.canonical(target.read_text(encoding='utf-8-sig')):
                raise ValueError('canonical source differs: '+name)
            result['sources'][name]=True
        for block in tia_lint.parse_blocks(text):
            if block.kind not in ('FUNCTION_BLOCK','TYPE'):continue
            xml=exported/'xml'/(block.name+('.type.xml' if block.kind=='TYPE' else '.xml'))
            sections=ET.parse(xml).findall('.//Interface/{*}Sections/{*}Section')
            actual={(s.attrib['Name'],m.attrib['Name']):m for s in sections for m in s.findall('./{*}Member')}
            wanted={(("None" if d.section=='STRUCT' else SECTIONS[d.section]),d.name):d for d in block.decls+block.constants}
            if set(actual)!=set(wanted):raise ValueError('compiled interface inventory differs: '+block.name)
            for key,decl in wanted.items():
                member=actual[key]
                normalize=lambda t:re.sub(r'\s+|"','',t.split(':=')[0]).casefold()
                if normalize(member.attrib['Datatype'])!=normalize(decl.type_text):raise ValueError('compiled type differs: '+block.name+'.'+decl.name)
                flags={a.attrib['Name']:a.text.lower()=='true' for a in member.findall('./{*}AttributeList/{*}BooleanAttribute')}
                for attribute in ('ExternalAccessible','ExternalVisible','ExternalWritable'):
                    flag=re.search(attribute+r"\s*:=\s*'(True|False)'",decl.attrs,re.I)
                    if flag and flags.get(attribute,True)!=(flag[1].lower()=='true'):
                        raise ValueError('compiled access differs: '+block.name+'.'+decl.name+'.'+attribute)
            result['interfaces'][block.name]=len(actual)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('exported',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();result=verify(args.source,args.exported)
    with args.out.open('x',encoding='ascii',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({name:len(values) for name,values in result.items()}))

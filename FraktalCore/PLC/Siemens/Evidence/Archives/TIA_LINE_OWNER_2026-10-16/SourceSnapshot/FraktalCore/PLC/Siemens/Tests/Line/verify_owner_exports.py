"""Canonical code/types plus every authored global DB interface/access flag.

TIA moves DB initializers from declarations into BEGIN assignments. Compare DB
interfaces separately; the runtime checks qualify their actual restored values.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_verifier',HERE.parent/'Generator/verify_exports.py')
VERIFY=importlib.util.module_from_spec(spec);spec.loader.exec_module(VERIFY)


def verify(source,native):
    with tempfile.TemporaryDirectory() as folder:
        selected=Path(folder)
        for p in source.iterdir():
            if p.suffix in ('.scl','.udt'):shutil.copy2(p,selected/p.name)
        result=VERIFY.verify(selected,native)
    result['data_interfaces']={}
    for path in source.glob('*.db'):
        for block in VERIFY.tia_lint.parse_blocks(path.read_text('ascii')):
            if block.kind!='DATA_BLOCK' or not block.decls:continue
            members=ET.parse(native/'xml'/(block.name+'.xml')).findall('.//Interface/{*}Sections/{*}Section/{*}Member')
            actual={m.attrib['Name']:m for m in members}
            wanted={d.name:d for d in block.decls}
            if set(actual)!=set(wanted):raise ValueError('DB member inventory differs: '+block.name)
            for name,decl in wanted.items():
                member=actual[name]
                normalize=lambda t:re.sub(r'\s+|"','',t.split(':=')[0]).casefold()
                if normalize(member.attrib['Datatype'])!=normalize(decl.type_text):raise ValueError('DB member type differs: '+block.name+'.'+name)
                flags={a.attrib['Name']:a.text.lower()=='true' for a in member.findall('./{*}AttributeList/{*}BooleanAttribute')}
                for attribute in ('ExternalAccessible','ExternalVisible','ExternalWritable'):
                    match=re.search(attribute+r"\s*:=\s*'(True|False)'",decl.attrs,re.I)
                    if match and flags.get(attribute,True)!=(match[1].lower()=='true'):
                        raise ValueError('DB access differs: '+block.name+'.'+name+'.'+attribute)
            result['data_interfaces'][block.name]=len(actual)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('native',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();result=verify(args.source,args.native)
    with args.out.open('x',encoding='ascii',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({name:len(value) for name,value in result.items()}))

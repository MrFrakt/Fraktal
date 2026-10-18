"""Resolve the Core rationalization registry and registered module reason bands."""
import hashlib
import json
import re
from fraktal_tia_binding import REPO,CORE

REGISTRY=REPO/'Specification/reason_rationalization.json'
MODULES=REPO/'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Modules/Params/PL_ModuleReasons.TcGVL'
TCP=CORE/'Params/PL_TcpDevReasons.TcGVL'


def rules(catalog):
    numbers=dict(catalog.enums['E_Reason'])
    for path in (MODULES,TCP):
        numbers.update({name:int(value) for name,value in re.findall(r'\b(\w+)\s*:\s*DINT\s*:=\s*(\d+)\s*;',path.read_text('utf-8-sig'))})
    result=[]
    for name,rule in json.loads(REGISTRY.read_bytes())['reasons'].items():
        if name not in numbers:raise ValueError('Unbound registered reason '+name)
        result.append((numbers[name],rule))
    if len({n for n,r in result})!=len(result):raise ValueError('Registered reason numbers collide')
    return result


def inputs():return {p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (REGISTRY,MODULES,TCP)}

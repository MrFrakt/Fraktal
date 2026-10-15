"""Local authentication primitives; constants and work factor derive from Core."""
import hashlib
import re
import xml.etree.ElementTree as ET

from fraktal_tia_binding import CORE, REPO, PRIVATE
from fraktal_tia_generate import db

TEMPLATE = REPO / 'FraktalCore/PLC/Siemens/Framework/Core/access_services.scl.in'
SHA_AUTHORITY = CORE / 'Platform/F_Sha256.TcPOU'
PARAM_AUTHORITY = CORE / 'Params/PL_Fraktal.TcGVL'


def rounds():
    declaration = ET.fromstring(PARAM_AUTHORITY.read_bytes()).findtext('.//Declaration')
    return int(re.search(r'PIN_HASH_ROUNDS\s*:\s*\w+\s*:=\s*(\d+)', declaration)[1])


def inputs():
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (TEMPLATE, SHA_AUTHORITY, PARAM_AUTHORITY)}


def build(catalog):
    source = ET.fromstring(SHA_AUTHORITY.read_bytes())
    constants = re.findall(r'16#([0-9A-F]{8})', source.findtext('.//Declaration'))
    assert len(constants) == 64
    initial = re.findall(r'h\[\d\] := 16#([0-9A-F]{8})', source.findtext('.//ST'))
    assert len(initial) == 8
    text = TEMPLATE.read_text(encoding='ascii')
    text = text.replace('@SHA_K@', '\n'.join('    #K[%d] := DWORD#16#%s;' % (i,v) for i,v in enumerate(constants)))
    text = text.replace('@SHA_INIT@', '\n'.join('    #Hash[%d] := DWORD#16#%s;' % (i,v) for i,v in enumerate(initial)))
    text = text.replace('@PIN_HASH_ROUNDS@', str(rounds()))
    for enum, members in catalog.enums.items():
        for member, value in members.items():
            text = text.replace('@'+enum+'.'+member+'@', str(value))
    for name, value in catalog.capacities.items():
        text = text.replace('@'+name+'@', str(value))
    if '@' in text:
        raise ValueError('unresolved access template token')
    return {'05_FRK_LocalUsers.db': db('FRK_LocalUsers', [
        'Count'+PRIVATE+' : DInt;',
        'Rows'+PRIVATE+' : Array[1..%d] of "ST_UserRecord";' % catalog.capacities['MAX_USERS']]),
        '12a_AccessServices.scl': text}

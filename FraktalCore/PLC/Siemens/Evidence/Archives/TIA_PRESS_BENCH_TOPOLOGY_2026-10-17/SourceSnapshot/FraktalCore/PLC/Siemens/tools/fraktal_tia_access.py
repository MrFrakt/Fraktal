"""Local authentication primitives; constants and work factor derive from Core."""
import hashlib
import re
import xml.etree.ElementTree as ET

from fraktal_tia_binding import CORE, REPO, PRIVATE, type_source
from fraktal_tia_generate import db

TEMPLATE = REPO / 'FraktalCore/PLC/Siemens/Framework/Core/access_services.scl.in'
SHA_AUTHORITY = CORE / 'Platform/F_Sha256.TcPOU'
PARAM_AUTHORITY = CORE / 'Params/PL_Fraktal.TcGVL'
CRC_AUTHORITY = CORE / 'Platform/F_Crc32.TcPOU'
PROVIDER_AUTHORITY = CORE / 'Connectivity/FB_LocalAccessProvider.TcPOU'
PERSISTENCE = TEMPLATE.with_name('access_persistence.scl.in')
CHECKSUM = TEMPLATE.with_name('checksum_services.scl.in')


def rounds():
    declaration = ET.fromstring(PARAM_AUTHORITY.read_bytes()).findtext('.//Declaration')
    return int(re.search(r'PIN_HASH_ROUNDS\s*:\s*\w+\s*:=\s*(\d+)', declaration)[1])


def inputs():
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (TEMPLATE, PERSISTENCE, CHECKSUM, SHA_AUTHORITY, PARAM_AUTHORITY, CRC_AUTHORITY, PROVIDER_AUTHORITY)}


def build(catalog):
    source = ET.fromstring(SHA_AUTHORITY.read_bytes())
    constants = re.findall(r'16#([0-9A-F]{8})', source.findtext('.//Declaration'))
    assert len(constants) == 64
    initial = re.findall(r'h\[\d\] := 16#([0-9A-F]{8})', source.findtext('.//ST'))
    assert len(initial) == 8
    text = TEMPLATE.read_text(encoding='ascii')+'\n'+CHECKSUM.read_text(encoding='ascii')+'\n'+PERSISTENCE.read_text(encoding='ascii')
    crc = ET.fromstring(CRC_AUTHORITY.read_bytes()).findtext('.//ST')
    polynomial = re.search(r'SHR\(value, 1\) XOR DWORD#16#([A-F0-9]+)', crc)[1]
    text = text.replace('@CRC_POLYNOMIAL@', polynomial)
    text = text.replace('@SHA_K@', '\n'.join('    #K[%d] := DWORD#16#%s;' % (i,v) for i,v in enumerate(constants)))
    text = text.replace('@SHA_INIT@', '\n'.join('    #Hash[%d] := DWORD#16#%s;' % (i,v) for i,v in enumerate(initial)))
    text = text.replace('@PIN_HASH_ROUNDS@', str(rounds()))
    for enum, members in catalog.enums.items():
        for member, value in members.items():
            text = text.replace('@'+enum+'.'+member+'@', str(value))
    for name, value in catalog.capacities.items():
        text = text.replace('@'+name+'@', str(value))
    if re.search(r'@(?!ROOT_COUNT@|NAME_WIDTH@)[A-Z_\.]+@', text):
        raise ValueError('unresolved access template token')
    policy = type_source('FRK_AccessPolicyImage', [
        {'member':n, 'native_type':t, 'accessible':False, 'initial':''} for n,t in (
            ('SchemaVersion','UInt'), ('Initialized','Bool'), ('Scope','String[@NAME_WIDTH@]'), ('Generation','UDInt'),
            ('Policy','"ST_AccessPolicy"'), ('Checksum','DWord'))])
    users = db('FRK_LocalUsers', [
        'SchemaVersion'+PRIVATE+' : UInt;', 'Generation'+PRIVATE+' : UDInt;',
        'Count'+PRIVATE+' : DInt;',
        'Rows'+PRIVATE+' : Array[1..%d] of "ST_UserRecord";' % catalog.capacities['MAX_USERS'],
        'Checksum'+PRIVATE+' : DWord;']).replace('VAR\n', 'VAR RETAIN\n', 1)
    policies = db('FRK_AccessPolicies', [
        'Rows'+PRIVATE+' : Array[1..@ROOT_COUNT@] of "FRK_AccessPolicyImage";'
    ]).replace('VAR\n', 'VAR RETAIN\n', 1)
    runtime = db('FRK_AccessStorage', [
        'UsersReady'+PRIVATE+' : Bool;', 'UsersLost'+PRIVATE+' : Bool;',
        'EmptyPolicy'+PRIVATE+' : "ST_AccessPolicy";']).replace('END_VAR\nBEGIN', 'END_VAR\nVAR RETAIN\n    UsersCommissioned'+PRIVATE+' : Bool;\nEND_VAR\nBEGIN')
    return {'02_FRK_AccessPolicyImage.udt': policy, '05_FRK_LocalUsers.db': users,
            '05_FRK_AccessPolicies.db': policies, '05_FRK_AccessStorage.db': runtime,
            '12a_AccessServices.scl': text}

"""Bounded native assertions shared by Core and press integration suites."""
import json
import hashlib
import re
from pathlib import Path
from fraktal_tia_binding import type_source
from fraktal_tia_config import function

POLICY=Path(__file__).resolve().parents[1]/'Framework/Core/test_profile.json'


def build():
    count=json.loads(POLICY.read_bytes())['maximum_checks']
    fields={'Checks':'Int','Failures':'Int','FirstFailure':'Int',
            'Failed':'Array[1..%d] of Bool'%count,'ProtocolError':'Bool'}
    result={'02_FRK_TestResult.udt':type_source('FRK_TestResult',[
        dict(member=n,native_type=t,accessible=True,initial='') for n,t in fields.items()])}
    result['02_FRK_TestStatus.udt']=type_source('FRK_TestStatus',[
        dict(member=n,native_type=t,accessible=True,initial='')
        for n,t in [('Done','Bool'),('Checks','Int'),('Failures','Int'),('FirstFailure','Int'),('ImageHash','Array[0..7] of DWord')]])
    result['19a_TestRuntime.scl']=function('FRK_TestAssert',['Condition : Bool;','Code : Int;'],
        ['Result : "FRK_TestResult";'],[],[
            '    IF #Result.Checks >= %d OR #Code <> #Result.Checks + 1 THEN'%count,
            '        #Result.ProtocolError := TRUE; RETURN;', '    END_IF;',
            '    #Result.Checks := #Result.Checks + 1;',
            '    #Result.Failed[#Result.Checks] := NOT #Condition;',
            '    IF NOT #Condition THEN',
            '        #Result.Failures := #Result.Failures + 1;',
            '        IF #Result.FirstFailure = 0 THEN #Result.FirstFailure := #Code; END_IF;',
            '    END_IF;'])
    result['19a_TestRuntime.scl']+=function('FRK_TestPublish',['Complete : Bool;',*['Image%d : DWord;'%i for i in range(8)]],
        ['Result : "FRK_TestResult";','Status : "FRK_TestStatus";'],[],[
            '    #Status.Done := #Complete AND NOT #Result.ProtocolError;',
            '    #Status.Checks := #Result.Checks; #Status.Failures := #Result.Failures;',
            '    #Status.FirstFailure := #Result.FirstFailure;',
            *['    #Status.ImageHash[%d] := #Image%d;'%(i,i) for i in range(8)]])
    return result


def signature(sources,labels):
    """The one self-reference is normalized; all authored code and labels bind."""
    normalize=lambda text:re.sub(r'(\bImage[0-7]\s*:=\s*DWORD#)(?:\d+|@IMAGE_HASH_[0-7]@)',r'\g<1>0',text)
    payload={name:hashlib.sha256(normalize(text).encode('ascii')).hexdigest()
             for name,text in sorted(sources.items()) if Path(name).suffix in ('.scl','.udt','.db','.xml')}
    raw=json.dumps(dict(sources=payload,assertions=labels),sort_keys=True,separators=(',',':')).encode('ascii')
    return hashlib.sha256(raw).hexdigest()


def seal_signature(sources,labels):
    digest=signature(sources,labels)
    for i in range(8):sources={name:text.replace('@IMAGE_HASH_%d@'%i,str(int(digest[i*8:i*8+8],16))) for name,text in sources.items()}
    return sources


def verify_signature(directory):
    expected=json.loads((directory/'image_hash.json').read_bytes())['sha256']
    sources={p.name:p.read_text('ascii') for p in directory.iterdir() if p.suffix in ('.scl','.udt','.db','.xml')}
    labels=list(json.loads((directory/'assertions.json').read_bytes()).values())
    if signature(sources,labels)!=expected:raise ValueError('native fixture code/assertion fingerprint differs')
    return expected

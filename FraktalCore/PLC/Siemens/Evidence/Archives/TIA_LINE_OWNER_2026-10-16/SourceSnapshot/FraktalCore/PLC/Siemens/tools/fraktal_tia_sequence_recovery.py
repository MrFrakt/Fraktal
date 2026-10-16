"""Private consumed-size sequence lifecycle, driven by the generated Unit frame."""
import hashlib
from pathlib import Path

from fraktal_tia_binding import PRIVATE, REPO, type_source
from fraktal_tia_config import function

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/sequence_recovery.scl.in'


def frame_call(final=False):
    restart = 'FALSE' if final else '#Startup OR #Core.EvModeChanged OR #Core.EvAbortInError'
    return '    "FRK_SeqLifecycleUpdate"(Owner := #Core.RegIndex, Exec := #Core.Exec, Restart := '+restart+');'


def build(model, catalog):
    from fraktal_tia_generate import db
    fields = [('Valid', 'Bool'), ('Faulted', 'Bool'), ('ExecPrevious', 'DInt'),
              ('RestartEpoch', 'UDInt'), ('ResumeEpoch', 'UDInt')]
    sources = {'06_FRK_SequenceLifecycle.udt': type_source('FRK_SequenceLifecycle', [
        {'member': n, 'native_type': ty, 'accessible': False, 'initial': ''} for n, ty in fields])}
    selected = {t.name for t in model.types if t.sequence_view}
    owners = [i for i in model.instances if i.type_name in selected]
    sources['08_FRK_SequenceOwners.db'] = db('FRK_SequenceOwners',
        ['Empty'+PRIVATE+' : "FRK_SequenceLifecycle";']+
        ['O%03d'%i.index+PRIVATE+' : "FRK_SequenceLifecycle";' for i in owners])
    source = TEMPLATE.read_text('ascii')
    for enum, members in catalog.enums.items():
        for member, value in members.items():
            source = source.replace('@'+enum+'.'+member+'@', str(value))
    update = ['    CASE #Owner OF']
    read = ['    #Life := "FRK_SequenceOwners".Empty;', '    CASE #Owner OF']
    for i in owners:
        life = '"FRK_SequenceOwners".O%03d'%i.index
        update += ['        %d:'%i.index,
                   '            IF '+life+'.Faulted AND #Exec <> '+str(catalog.enums['E_ExecState']['ERROR'])+' THEN',
                   '                "FRK_SeqViewClearErrors"(Owner := #Owner);', '            END_IF;',
                   '            "FRK_SequenceOwnerUpdate"(Exec := #Exec, Restart := #Restart, Life := '+life+');']
        read.append('        %d: #Life := %s;'%(i.index, life))
    update += ['        ELSE RETURN;', '    END_CASE;']
    read += ['        ELSE RETURN;', '    END_CASE;']
    source += function('FRK_SeqLifecycleUpdate', ['Owner : DInt;', 'Exec : DInt;', 'Restart : Bool;'], [], [], update)
    source += function('FRK_SeqLifecycleRead', ['Owner : DInt;'], ['Life : "FRK_SequenceLifecycle";'], [], read)
    sources['17_SequenceRecovery.scl'] = source
    return sources, {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (TEMPLATE, Path(__file__))}

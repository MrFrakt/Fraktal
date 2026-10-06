"""Core 7.7 controller authority; TC3's local PIN provider is the oracle.

Only salted hashes are deployment data. The gateway derives the penultimate
digest; the PLC hashes it once and compares its own private registration.
Native PIN clients retain the complete 257-hash path. Each block is spread
over ten scans, at most eight rounds per scan. Rotates and sums use masked DINT
arithmetic, without native bit-distribution calls or signed overflow. Sampled
credentials are wiped before hashing; transient block state is cleared as it
is consumed and on completion/cancellation.
The mailbox acknowledges consumption immediately and remains available.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb

MAX_USERS, PIN_HASH_ROUNDS, WIDTH = 4, 256, 32
HASH_CHUNK = 8
HASH_BLOCK_SCANS = 2 + 64 // HASH_CHUNK
STATE_SCHEMA = 3
LOGIN_PIN, LOGIN_PREHASH = 0, 1
AUDIT_CAPACITY = gen.ALARM_RING
ACTOR_WORDS = WIDTH // 4
AUDIT_SCHEMA = 3
GATE_COUNT, ADMIN, ENGINEER, TIMEOUT_MAX = 12, 4, 3, 604800000
DENIED = 'std.error.accessDenied'
INVALID = 'std.error.accessPolicyInvalid'
BUSY = 'std.error.accessLoginBusy'
KEYS = (DENIED, INVALID, BUSY, 'std.audit.login', 'std.audit.loginFailed',
        'std.audit.logout', 'std.audit.autoLogout', 'std.audit.accessDenied',
        'std.audit.operatorAction', 'std.audit.dataAccessDenied')
# TC3 E_GatedAction; queries remain pure, logout/login never require a level.
GATES = {mb.SET_MODE: 4, mb.SET_MODEL: 3, mb.START: 5, mb.STOP: 5,
         mb.CONTROL_ON: 10, mb.CONTROL_OFF: 10, mb.OPERATOR_RESET: 7,
         mb.DECISION_ANSWER: 5, mb.MANUAL_COMMAND: 2, mb.MANUAL_HELD: 2,
         mb.SET_RUN_STYLE: 4, mb.STEP_REQUEST: 5, mb.SET_HOLD_RUN: 5,
         mb.RESET_OEE: 1, mb.WRITE_CONFIG: 1, mb.CAPTURE_CONFIG: 1,
         mb.SHELVE_ALARM: 9, mb.UNSHELVE_ALARM: 9, mb.FORCE_CHANNEL: 2,
         mb.QUERY_CONFIG: 0, mb.SET_ACCESS_LEVEL: 8, mb.SET_SESSION_TIMEOUT: 8,
         mb.LAMP_TEST: 10, mb.SET_CLASS_LEVEL: 8,
         **dict.fromkeys((mb.SAVE_CONFIG_SET, mb.LOAD_CONFIG_SET, mb.LIST_CONFIG_SETS,
                         mb.EXPORT_CONFIG_SET, mb.IMPORT_CONFIG_SET, mb.DELETE_CONFIG_SET, mb.CREATE_MODEL, mb.EXPORT_CURRENT_CONFIG), 11)}
PURE_KINDS = (mb.RELEASE_START, mb.RELEASE_MANUAL, mb.RELEASE_ACTION,
              mb.QUERY_CONFIG, mb.LIST_CONFIG_SETS, mb.EXPORT_CONFIG_SET, mb.EXPORT_CURRENT_CONFIG)


@dataclass(frozen=True)
class User:
    name: str
    level: int
    salt: str  # 16 bytes, hexadecimal
    pin_hash: str  # 32 bytes; never a plaintext PIN


def pin_hash(salt, pin):
    """Offline provisioning/oracle only. The runtime never calls Python crypto."""
    value = hashlib.sha256(salt + pin).digest()
    for _ in range(PIN_HASH_ROUNDS):
        value = hashlib.sha256(value + salt).digest()
    return value


def pin_prehash(salt, pin):
    """Password-equivalent preimage of the stored hash; never log or retain it."""
    value = hashlib.sha256(salt + pin).digest()
    for _ in range(PIN_HASH_ROUNDS - 1):
        value = hashlib.sha256(value + salt).digest()
    return value


def prepare_login(app, writes):
    """Transport acceleration only; the gateway makes no authentication decision.

    The final registration hash is never sent as a credential. Native clients
    can also supply a preimage, but only the PLC's final hash comparison grants
    a session. Preserve the complete batch and Sequence-last commit ordering.
    """
    values = {p.rsplit('/', 1)[-1]: v for p, _, v in writes}
    if app.access_users is None or values.get('Kind') != mb.LOGIN:
        return writes
    if values.get('IntValue', LOGIN_PIN) != LOGIN_PIN:
        raise ValueError('Web LOGIN requires a PIN, not a derived credential')
    user, secret = values.get('User', ''), values.get('Secret', '')
    if not isinstance(secret, str) or not secret.isascii() or not 1 <= len(secret) <= WIDTH:
        raise ValueError('LOGIN requires 1..32 ASCII PIN characters')
    # Native request rules and the transport use the same ASCII/width limits.
    mb.member_writes(app, 'User', user)
    mb.member_writes(app, 'Secret', secret)
    salt = next((bytes.fromhex(u.salt) for u in app.access_users if u.name == user), bytes(16))
    proof = pin_prehash(salt, secret.encode('ascii')).hex()
    replacements = {'IntValue': LOGIN_PREHASH, 'TextValue': proof, 'Secret': ''}
    root = next(p.rsplit('/', 1)[0] for p, _, _ in writes)
    out = [(p, typ, replacements.pop(p.rsplit('/', 1)[-1], v)) for p, typ, v in writes[:-1]]
    out += [(root + '/' + n, 'string' if n != 'IntValue' else 'int32', v)
            for n, v in replacements.items()]
    return out + [writes[-1]]


def validate_users(users):
    errors, names, salts = [], set(), set()
    if len(users) > MAX_USERS:
        errors.append('access provider exceeds MAX_USERS')
    for u in users:
        if not isinstance(u, User):
            errors.append('access registration must be a User hash record')
            continue
        if not u.name or len(u.name) > WIDTH or any(not 32 <= ord(c) <= 126 for c in u.name):
            errors.append('access user must be 1..32 printable ASCII characters')
        if u.name in names:
            errors.append('duplicate access user')
        names.add(u.name)
        if type(u.level) is not int or not 1 <= u.level <= ADMIN:
            errors.append('access user level must be OPERATOR..ADMIN')
        for field, width in ((u.salt, 32), (u.pin_hash, 64)):
            try:
                if len(field) != width or len(bytes.fromhex(field)) != width // 2:
                    raise ValueError()
            except (ValueError, TypeError):
                errors.append('access registration requires a 16-byte salt and 32-byte hash')
        if u.salt in salts:
            errors.append('access registrations require distinct salts')
        salts.add(u.salt)
    return errors


def tag(app, name):
    return f'FRK_{app.name}_Access{name}'


def login_timeout_ms(app):
    return (PIN_HASH_ROUNDS + 1) * HASH_BLOCK_SCANS * app.task_period_ms + 10000


def state_members(app):
    return (decl.scalar('SchemaVersion', initial=STATE_SCHEMA),
            *(decl.scalar(n) for n in ('CurrentLevel', 'UserLength', 'LoginFailed', 'LoginBusy', 'SessionTimeout')),
            decl.scalar('Required', dimension=GATE_COUNT), decl.scalar('UserBytes', dimension=WIDTH),
            decl.scalar('LoginTimeoutMs', initial=login_timeout_ms(app)),
            decl.scalar('LoginPrehashRounds', initial=PIN_HASH_ROUNDS),
            decl.scalar('LoginResultSequence'))


def audit_members():
    return (decl.scalar('SchemaVersion', initial=AUDIT_SCHEMA), decl.scalar('Head'), decl.scalar('Count'),
            *(decl.scalar(n, dimension=AUDIT_CAPACITY) for n in
              ('Sequence', 'Kind', 'Gate', 'Key', 'Accepted', 'UserLength')),
            decl.scalar('UserWords', dimension=AUDIT_CAPACITY * ACTOR_WORDS),
            *(decl.scalar(n, dimension=AUDIT_CAPACITY) for n in ('DataCapability', 'DataRequiredLevel')))


def user_capacity(users):
    # Private storage follows the deployed registrations, with one inert row
    # for an empty provider. MAX_USERS is a declaration ceiling, not a reserve.
    return max(1, len(users))


def users_members(users):
    capacity = user_capacity(users)
    return (decl.scalar('Count'),
            *(decl.scalar(n, dimension=capacity) for n in ('UserLength', 'Level')),
            decl.scalar('UserBytes', dimension=capacity * WIDTH),
            decl.scalar('Salt', dimension=capacity * 16),
            decl.scalar('Hash', dimension=capacity * WIDTH))


def work_members():
    return (*(decl.scalar(n) for n in ('Sequence', 'Hit', 'Valid', 'LoginValid', 'Rearmed', 'Remaining', 'IdleMs', 'Index',
              'Prior', 'ByteIndex', 'WordIndex', 'Round', 'Difference', 'Length', 'Low', 'High', 'Gate',
              'Permitted', 'Minimum', 'ActorLength', 'HashRan', 'Profile',
              'HashPhase', 'HashCursor', 'HashEnd', 'HashDone',
              'AuditKey', 'AuditKind', 'AuditSequence', 'AuditAccepted', 'AuditLength',
              'AuditSource', 'AuditByte', 'AuditWord', 'AuditEventSource', 'AuditGate')),
            *(decl.scalar(n, dimension=d) for n, d in
              (('User', WIDTH), ('Salt', 16), ('Buffer', 64), ('Words', 64),
               ('Digest', WIDTH), ('H', 8), ('V', 8), ('Temp', 5))))


def record_layouts(app):
    return (('State', STATE_SCHEMA, state_members(app)), ('Audit', AUDIT_SCHEMA, audit_members()),
            ('Users', 2, users_members(app.access_users)), ('Work', 6, work_members()))


def records(app):
    return [decl.Record('FRK_T_Access' + name + 'V' + str(version), members)
            for name, version, members in record_layouts(app)]


def user_data(users):
    held = {m.name: [0] * m.dimension if m.dimension else 0 for m in users_members(users)}
    held['Count'] = len(users)
    for i, u in enumerate(users):
        held['Level'][i], held['UserLength'][i] = u.level, len(u.name)
        for name, stride, data in (('UserBytes', WIDTH, u.name.encode('ascii')),
                                   ('Salt', 16, bytes.fromhex(u.salt)), ('Hash', WIDTH, bytes.fromhex(u.pin_hash))):
            held[name][i * stride:i * stride + len(data)] = data
    return held


def tags(app):
    import fraktal_ab_generate as gen
    import xml.etree.ElementTree as ET
    blocks = [gen._structure_tag(tag(app, n), 'FRK_T_Access' + n + 'V' + str(version), ms,
                external_access='Read Only' if n in ('State', 'Audit') else 'None')
              for n, version, ms in record_layouts(app)]
    root = ET.fromstring(blocks[2])
    data = user_data(app.access_users)
    for member in root.find('Data/Structure'):
        value = data[member.get('Name')]
        if isinstance(value, list):
            for el, v in zip(member, value):
                el.set('Value', str(v))
        else:
            member.set('Value', str(value))
    blocks[2] = ET.tostring(root, encoding='unicode')
    # A login remains active across scans. Sample its whole request atomically
    # before wiping the published secret; use the frozen mailbox layout.
    blocks.append(mb._structure_tag(app, tag(app, 'LoginRequest'), mb.request_type_name(app), mb.REQUEST_MEMBERS, 'None'))
    # Table lookup replaces 64 compiled CASE branches. Never externally writable.
    root = ET.fromstring(gen._dint_scratch_tag(tag(app, 'RoundConstants'), len(K)))
    root.set('Constant', 'true')
    for element, value in zip(root.find('Data/Array'), K):
        element.set('Value', str(_signed(value)))
    blocks.append(ET.tostring(root, encoding='unicode'))
    return blocks


def _signed(n):
    return n if n < 0x80000000 else n - 0x100000000


# FIPS 180-4; the 64 SHA-256 constants, in round order.
K = tuple(int(s, 16) for s in '''428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5
d807aa98 12835b01 243185be 550c7dc3 72be5d74 80deb1fe 9bdc06a7 c19bf174
e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da
983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967
27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85
a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070
19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3
748f82ee 78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2'''.split())
H = (0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
     0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)


def _rotate(app, dest, source, amount, logical=False):
    """ROTR/SHR with exact division and bounded DINT intermediates.

    Clearing discarded bits before division avoids Logix integer rounding.
    The two sign contributions are ORed separately. Call sites use distinct
    source/destination storage.
    """
    if not 1 <= amount <= 31 or dest == source:
        raise ValueError('rotate requires 1..31 bits and distinct storage')
    mask = 0x7fffffff & ~((1 << amount) - 1)
    shifted = f'(({source} AND {mask}) / {1 << amount})' if mask else '0'
    wrap_mask = (1 << (amount - 1)) - 1
    if not logical and wrap_mask:
        shifted += f' OR (({source} AND {wrap_mask}) * {1 << (32 - amount)})'
    lines = [f'{dest} := {shifted};',
             f'IF {source} < 0 THEN {dest} := {dest} OR {1 << (31 - amount)}; END_IF;']
    if not logical:
        lines += [f'IF ({source} AND {1 << (amount - 1)}) <> 0 THEN {dest} := {dest} OR -2147483648; END_IF;']
    return lines


def _add(app, dest, terms):
    """Modulo 2^32 through bounded sums of signed 16-bit high limbs.

    Masking low bits makes division exact on Logix. At most five terms keep
    both sums within DINT; ORing the sign bit avoids overflow on assembly.
    """
    if not 1 <= len(terms) <= 5:
        raise ValueError('modular sum requires one to five DINT terms')
    w = tag(app, 'Work')
    low, high = w + '.Low', w + '.High'
    return [f'{low} := ' + ' + '.join(f'({v} AND 65535)' for v in terms) + ';',
            f'{high} := ' + ' + '.join(f'(({v} AND -65536) / 65536)' for v in terms) + ';',
            f'{high} := ({high} + (({low} AND -65536) / 65536)) AND 65535;',
            f'{dest} := (({high} AND 32767) * 65536) OR ({low} AND 65535);',
            f'IF {high} >= 32768 THEN {dest} := {dest} OR -2147483648; END_IF;']


def sha_logic(app):
    """Advance one bounded phase, without falling through to another phase."""
    w = tag(app, 'Work')
    i, r, j = w + '.WordIndex', w + '.Round', w + '.ByteIndex'
    t = [w + f'.Temp[{k}]' for k in range(5)]
    v = [w + f'.V[{k}]' for k in range(8)]
    lines = ['(* FIPS 180-4 SHA-256; at most eight rounds per invocation. *)',
             f'CASE {w}.HashPhase OF', '0:', f'{w}.HashDone := 0;']
    lines += [f'{w}.H[{k}] := {_signed(n)};' for k, n in enumerate(H)]
    lines += [f'FOR {i} := 0 TO 15 DO', f'{j} := {i} * 4;',
              f'{w}.Words[{i}] := ({w}.Buffer[{j}] AND 127) * 16777216 + {w}.Buffer[{j} + 1] * 65536 + {w}.Buffer[{j} + 2] * 256 + {w}.Buffer[{j} + 3];',
              f'IF {w}.Buffer[{j}] >= 128 THEN {w}.Words[{i}] := {w}.Words[{i}] OR -2147483648; END_IF;', 'END_FOR;',
              f'FOR {i} := 0 TO 63 DO {w}.Buffer[{i}] := 0; END_FOR;']
    lines += [f'{v[k]} := {w}.H[{k}];' for k in range(8)]
    lines += [f'{w}.HashCursor := 0;', f'{w}.HashPhase := 1;', '1:',
              f'IF ({w}.HashCursor >= 0) AND ({w}.HashCursor <= {64 - HASH_CHUNK}) AND (({w}.HashCursor MOD {HASH_CHUNK}) = 0) THEN',
              f'{w}.HashEnd := {w}.HashCursor + {HASH_CHUNK - 1};',
              f'FOR {r} := {w}.HashCursor TO {w}.HashEnd DO', f'IF {r} >= 16 THEN',
              *_rotate(app, t[0], f'{w}.Words[{r} - 15]', 7),
              *_rotate(app, t[1], f'{w}.Words[{r} - 15]', 18),
              *_rotate(app, t[2], f'{w}.Words[{r} - 15]', 3, True),
              f'{t[0]} := {t[0]} XOR {t[1]} XOR {t[2]};',
              *_rotate(app, t[1], f'{w}.Words[{r} - 2]', 17),
              *_rotate(app, t[2], f'{w}.Words[{r} - 2]', 19),
              *_rotate(app, t[3], f'{w}.Words[{r} - 2]', 10, True),
              f'{t[1]} := {t[1]} XOR {t[2]} XOR {t[3]};',
              *_add(app, f'{w}.Words[{r}]', (f'{w}.Words[{r} - 16]', t[0], f'{w}.Words[{r} - 7]', t[1])), 'END_IF;',
              *_rotate(app, t[0], v[4], 6),
              *_rotate(app, t[1], v[4], 11), *_rotate(app, t[2], v[4], 25),
              f'{t[0]} := {t[0]} XOR {t[1]} XOR {t[2]};',
              f'{t[1]} := ({v[4]} AND {v[5]}) XOR ((NOT {v[4]}) AND {v[6]});',
              f'{t[2]} := {tag(app, "RoundConstants")}[{r}];',
              *_add(app, t[3], (v[7], t[0], t[1], t[2], f'{w}.Words[{r}]')),
              *_rotate(app, t[0], v[0], 2), *_rotate(app, t[1], v[0], 13), *_rotate(app, t[2], v[0], 22),
              f'{t[0]} := {t[0]} XOR {t[1]} XOR {t[2]};',
              f'{t[1]} := ({v[0]} AND {v[1]}) XOR ({v[0]} AND {v[2]}) XOR ({v[1]} AND {v[2]});',
              *_add(app, t[4], (t[0], t[1])),
              f'{v[7]} := {v[6]};', f'{v[6]} := {v[5]};', f'{v[5]} := {v[4]};',
              *_add(app, v[4], (v[3], t[3])),
              f'{v[3]} := {v[2]};', f'{v[2]} := {v[1]};', f'{v[1]} := {v[0]};',
              *_add(app, v[0], (t[3], t[4])), 'END_FOR;',
              f'{w}.HashCursor := {w}.HashEnd + 1;',
              f'IF {w}.HashCursor = 64 THEN {w}.HashPhase := 2; END_IF;', 'ELSE',
              f'{w}.LoginValid := 0;', f'{w}.Remaining := 0;', f'{w}.HashDone := 1;', 'END_IF;', '2:',
              f'FOR {i} := 0 TO 7 DO',
              *_add(app, f'{w}.H[{i}]', (f'{w}.H[{i}]', f'{w}.V[{i}]')),
              f'{w}.Digest[{i} * 4] := ({w}.H[{i}] AND 2130706432) / 16777216;',
              f'IF {w}.H[{i}] < 0 THEN {w}.Digest[{i} * 4] := {w}.Digest[{i} * 4] OR 128; END_IF;',
              f'{w}.Digest[{i} * 4 + 1] := ({w}.H[{i}] AND 16711680) / 65536;',
              f'{w}.Digest[{i} * 4 + 2] := ({w}.H[{i}] AND 65280) / 256;',
              f'{w}.Digest[{i} * 4 + 3] := {w}.H[{i}] AND 255;', 'END_FOR;']
    lines += [f'FOR {i} := 0 TO 63 DO', f'{w}.Words[{i}] := 0;', f'{w}.Buffer[{i}] := 0;', 'END_FOR;',
              f'{w}.HashPhase := 0;', f'{w}.HashDone := 1;', 'ELSE',
              f'{w}.LoginValid := 0;', f'{w}.Remaining := 0;', f'{w}.HashDone := 1;', 'END_CASE;']
    return lines


def wipe_secret(app, request=None):
    import fraktal_ab_mailbox as mb
    q, i = request or mb.request_tag_name(app), f'FRK_{app.name}_HmiWipe'
    return [f'{q}.Secret.LEN := 0;', f'FOR {i} := 0 TO {WIDTH - 1} DO', f'{q}.Secret.DATA[{i}] := 0;', 'END_FOR;']


def wipe_login(app, request=None):
    """PIN and preimage are credentials, including bytes beyond STRING LEN."""
    q, i = request or mb.request_tag_name(app), f'FRK_{app.name}_HmiWipe'
    return [*wipe_secret(app, q), f'{q}.TextValue.LEN := 0;',
            f'FOR {i} := 0 TO {mb.TEXT_VALUE_LENGTH - 1} DO',
            f'{q}.TextValue.DATA[{i}] := 0;', 'END_FOR;']


def _audit_sources(app):
    return (tag(app, 'Work') + '.User', tag(app, 'State') + '.UserBytes',
            mb.request_tag_name(app) + '.User.DATA')


def _audit(app, key, kind, sequence, accepted, actor_length, actor, *, event_source='1', gate=None):
    import fraktal_ab_manifest as mf
    w = tag(app, 'Work')
    return [f'{w}.AuditKey := {mf.numeric_key(app, key)};', f'{w}.AuditKind := {kind};',
            f'{w}.AuditSequence := {sequence};', f'{w}.AuditAccepted := {accepted};',
            f'{w}.AuditLength := {actor_length};', f'{w}.AuditSource := {_audit_sources(app).index(actor)};',
            f'{w}.AuditEventSource := {event_source};', f'{w}.AuditGate := {w + ".Gate" if gate is None else gate};',
            f'JSR({tag(app, "RecordAudit")},0);']


def audit_logic(app):
    """One event-ring writer; four actor bytes per DINT, little-endian."""
    w, a = tag(app, 'Work'), tag(app, 'Audit')
    active, ring = gen.alarm_active_tag(app), gen.alarm_ring_tag(app)
    i, j = w + '.Index', w + '.ByteIndex'
    slot = a + '.Head - 1'
    lines = [f'IF ({w}.AuditLength < 0) OR ({w}.AuditLength > {WIDTH}) THEN {w}.AuditLength := 0; END_IF;',
             f'{active}.RingHead := ({active}.RingHead MOD {AUDIT_CAPACITY}) + 1;',
             f'{a}.Head := {active}.RingHead;',
             f'IF {a}.Count < {AUDIT_CAPACITY} THEN {a}.Count := {a}.Count + 1; END_IF;']
    for name, value in (('Key', w + '.AuditKey'), ('Kind', w + '.AuditKind'), ('Sequence', w + '.AuditSequence'),
                        ('Accepted', w + '.AuditAccepted'), ('Gate', w + '.AuditGate'), ('UserLength', w + '.AuditLength')):
        lines += [f'{a}.{name}[{slot}] := {value};']
    import fraktal_ab_data_access as data
    import fraktal_ab_manifest as mf
    d = data.tag(app, 'Levels')
    lines += [f'{a}.DataCapability[{slot}] := 0;', f'{a}.DataRequiredLevel[{slot}] := 0;',
              f'IF {w}.AuditKey = {mf.numeric_key(app, data.DENIED)} THEN',
              f'{a}.DataCapability[{slot}] := {d}.RejectCapability;',
              f'{a}.DataRequiredLevel[{slot}] := {d}.RejectRequiredLevel;', 'END_IF;']
    # One authoritative event ring and one timestamp. The private provider
    # adds typed actor/action metadata at that ring's slot; ordinary alarms
    # continue through their existing capture path and may overwrite it.
    values = {'State': gen.ALARM_CLOSED, 'ReasonCode': 0, 'Severity': 0, 'ResetClass': 0,
              'SourceModuleId': w + '.AuditEventSource', 'ComeDate': f'FRK_{app.name}_NowDate',
              'ComeTime': f'FRK_{app.name}_NowTime', 'GoneDate': f'FRK_{app.name}_NowDate',
              'GoneTime': f'FRK_{app.name}_NowTime', 'ComeScan': f'FRK_{app.name}_ScanCount',
              'DurationMs': 0, 'IoRoles': 0, 'Shelved': 0}
    lines += [f'{ring}.Ring{name}[{slot}] := {value};' for name, value in values.items()]
    # Pack without signed overflow, including arbitrary native STRING bytes.
    # Low holds the byte position's power of 256 (at most 2^24).
    lines += [f'FOR {i} := 0 TO {ACTOR_WORDS - 1} DO', f'{w}.AuditWord := 0;', f'{w}.Low := 1;',
              f'FOR {j} := 0 TO 3 DO', f'{w}.AuditByte := 0;',
              f'IF {i} * 4 + {j} < {w}.AuditLength THEN', f'CASE {w}.AuditSource OF',
              *(f'{n}: {w}.AuditByte := {s}[{i} * 4 + {j}] AND 255;' for n, s in enumerate(_audit_sources(app))),
              'ELSE', f'{w}.AuditByte := 0;', 'END_CASE;', 'END_IF;',
              f'IF {j} = 3 THEN', f'{w}.AuditWord := {w}.AuditWord + ({w}.AuditByte AND 127) * {w}.Low;',
              f'IF {w}.AuditByte >= 128 THEN {w}.AuditWord := {w}.AuditWord OR -2147483648; END_IF;',
              'ELSE', f'{w}.AuditWord := {w}.AuditWord + {w}.AuditByte * {w}.Low;',
              f'{w}.Low := {w}.Low * 256;', 'END_IF;', 'END_FOR;',
              f'{a}.UserWords[({slot}) * {ACTOR_WORDS} + {i}] := {w}.AuditWord;', 'END_FOR;']
    return lines


def routines(app):
    return ((tag(app, 'Sha256'), sha_logic(app)),
            (tag(app, 'RecordAudit'), audit_logic(app)))


def _clear_session(app):
    s, w = tag(app, 'State'), tag(app, 'Work')
    i = w + '.Index'
    return [f'{s}.CurrentLevel := 0;', f'{s}.UserLength := 0;', f'{w}.IdleMs := 0;',
            f'FOR {i} := 0 TO {WIDTH - 1} DO', f'{s}.UserBytes[{i}] := 0;', 'END_FOR;']


def cancel_login(app):
    s, w, i = tag(app, 'State'), tag(app, 'Work'), tag(app, 'Work') + '.Index'
    return [f'{s}.LoginBusy := 0;', f'{w}.Remaining := 0;', f'{w}.LoginValid := 0;',
            f'{w}.HashPhase := 0;', f'{w}.HashDone := 0;', f'{w}.HashCursor := 0;',
            f'FOR {i} := 0 TO 63 DO {w}.Buffer[{i}] := 0; {w}.Words[{i}] := 0; END_FOR;',
            f'FOR {i} := 0 TO {WIDTH - 1} DO {w}.Digest[{i}] := 0; {w}.User[{i}] := 0; END_FOR;',
            f'FOR {i} := 0 TO 15 DO {w}.Salt[{i}] := 0; END_FOR;',
            f'FOR {i} := 0 TO 7 DO {w}.H[{i}] := 0; {w}.V[{i}] := 0; END_FOR;',
            f'FOR {i} := 0 TO 4 DO {w}.Temp[{i}] := 0; END_FOR;',
            *wipe_login(app, tag(app, 'LoginRequest'))]


def startup(app):
    """Volatile sessions never survive re-entering Run; policy/users do."""
    return ['IF S:FS THEN', *cancel_login(app), *_clear_session(app),
            f'{tag(app, "State")}.LoginFailed := 0;',
            f'{tag(app, "State")}.LoginResultSequence := 0;', *wipe_login(app), 'END_IF;']


def _pad(app, length):
    w = tag(app, 'Work')
    return [f'{w}.Buffer[{length}] := 128;',
            # Length*8 / 256 must be truncated explicitly (Logix rounds DINT divides).
            f'{w}.Buffer[62] := (({length} * 8) AND -256) / 256;',
            f'{w}.Buffer[63] := ({length} * 8) AND 255;']


def login(app):
    import fraktal_ab_mailbox as mb
    s, w, users, q = tag(app, 'State'), tag(app, 'Work'), tag(app, 'Users'), tag(app, 'LoginRequest')
    i, j = w + '.Index', w + '.ByteIndex'
    lines = [f'CPS({mb.request_tag_name(app)},{q},1);', *wipe_login(app),
             f'{w}.Sequence := FRK_{app.name}_HmiLastSequence;', f'{w}.Hit := -1;', f'{w}.LoginValid := 1;',
             f'{w}.Profile := {q}.IntValue;',
             f'IF {q}.Sequence <> {w}.Sequence THEN {w}.LoginValid := 0; END_IF;',
             f'{w}.ActorLength := {q}.User.LEN;',
             f'IF ({q}.User.LEN < 1) OR ({q}.User.LEN > {WIDTH}) THEN {w}.LoginValid := 0; {w}.ActorLength := 0; END_IF;',
             f'CASE {w}.Profile OF', f'{LOGIN_PIN}:',
             f'IF ({q}.Secret.LEN < 1) OR ({q}.Secret.LEN > {WIDTH}) THEN {w}.LoginValid := 0; END_IF;',
             f'{LOGIN_PREHASH}:',
             f'IF ({q}.TextValue.LEN <> 64) OR ({q}.Secret.LEN <> 0) THEN {w}.LoginValid := 0; END_IF;',
             'ELSE', f'{w}.LoginValid := 0;', 'END_CASE;',
             f'IF ({users}.Count < 0) OR ({users}.Count > {user_capacity(app.access_users)}) THEN {w}.LoginValid := 0; END_IF;',
             f'FOR {i} := 0 TO {WIDTH - 1} DO', f'{w}.User[{i}] := 0;',
             f'IF {i} < {w}.ActorLength THEN {w}.User[{i}] := {q}.User.DATA[{i}]; END_IF;', 'END_FOR;',
             f'FOR {i} := 0 TO {user_capacity(app.access_users) - 1} DO', f'{w}.Difference := 0;',
             f'IF {w}.ActorLength <> {users}.UserLength[{i}] THEN {w}.Difference := 1; END_IF;',
             f'FOR {j} := 0 TO {WIDTH - 1} DO',
             f'{w}.Difference := {w}.Difference OR ({w}.User[{j}] XOR {users}.UserBytes[{i} * {WIDTH} + {j}]);', 'END_FOR;',
             f'IF ({i} < {users}.Count) AND ({w}.Difference = 0) THEN {w}.Hit := {i}; END_IF;', 'END_FOR;',
             f'FOR {i} := 0 TO 63 DO {w}.Buffer[{i}] := 0; END_FOR;',
             f'FOR {i} := 0 TO 15 DO', f'{w}.Salt[{i}] := 0;',
             f'IF ({w}.Hit >= 0) AND ({w}.LoginValid <> 0) THEN {w}.Salt[{i}] := {users}.Salt[{w}.Hit * 16 + {i}]; END_IF;',
             'END_FOR;', f'{w}.Length := 16;', f'{w}.Remaining := {PIN_HASH_ROUNDS + 1};',
             f'IF {w}.Profile = {LOGIN_PREHASH} THEN',
             f'{w}.Length := 48;', f'{w}.Remaining := 1;',
             f'FOR {i} := 0 TO {WIDTH - 1} DO', f'{w}.Low := 0;',
             f'FOR {j} := 0 TO 1 DO', f'{w}.High := {q}.TextValue.DATA[{i} * 2 + {j}];',
             f'IF ({w}.High >= 48) AND ({w}.High <= 57) THEN {w}.High := {w}.High - 48;',
             f'ELSIF ({w}.High >= 97) AND ({w}.High <= 102) THEN {w}.High := {w}.High - 87;',
             f'ELSE {w}.LoginValid := 0; {w}.High := 0; END_IF;',
             f'{w}.Low := {w}.Low * 16 + {w}.High;', 'END_FOR;',
             f'{w}.Buffer[{i}] := {w}.Low;', 'END_FOR;',
             f'FOR {i} := 0 TO 15 DO {w}.Buffer[{i} + 32] := {w}.Salt[{i}]; END_FOR;',
             'ELSE',
             f'FOR {i} := 0 TO 15 DO {w}.Buffer[{i}] := {w}.Salt[{i}]; END_FOR;',
             f'IF {w}.LoginValid <> 0 THEN', f'{w}.Length := {q}.Secret.LEN + 16;',
             f'FOR {i} := 0 TO {WIDTH - 1} DO', f'IF {i} < {q}.Secret.LEN THEN',
             f'{w}.Buffer[{i} + 16] := {q}.Secret.DATA[{i}] AND 255;', 'END_IF;', 'END_FOR;', 'END_IF;',
             'END_IF;', *wipe_login(app, q), *_pad(app, w + '.Length'),
             f'{w}.HashPhase := 0;', f'{w}.HashDone := 0;',
             f'{w}.HashRan := 1;', f'JSR({tag(app, "Sha256")},0);',
             f'{s}.LoginBusy := 1;']
    return lines


def cyclic(app):
    import fraktal_ab_mailbox as mb
    s, w, users = tag(app, 'State'), tag(app, 'Work'), tag(app, 'Users')
    i = w + '.Index'
    lines = [f'{w}.HashRan := 0;', f'{w}.Rearmed := 0;', f'{w}.Gate := -1;', f'IF {s}.LoginBusy <> 0 THEN',
             f'IF ({w}.Remaining > 0) AND ({w}.Remaining <= {PIN_HASH_ROUNDS + 1}) THEN',
             f'{w}.HashRan := 1;', f'JSR({tag(app, "Sha256")},0);',
             f'IF {w}.HashDone <> 0 THEN',
             f'IF {w}.Remaining > 0 THEN {w}.Remaining := {w}.Remaining - 1; END_IF;',
             f'IF {w}.Remaining > 0 THEN',
             f'FOR {i} := 0 TO {WIDTH - 1} DO {w}.Buffer[{i}] := {w}.Digest[{i}]; END_FOR;',
             f'FOR {i} := 0 TO 15 DO {w}.Buffer[{i} + 32] := {w}.Salt[{i}]; END_FOR;',
             *_pad(app, '48'), f'{w}.HashDone := 0;', 'END_IF;', 'END_IF;',
             'ELSE', f'{w}.LoginValid := 0;', f'{w}.Remaining := 0;', 'END_IF;',
             f'IF {w}.Remaining = 0 THEN', f'{w}.Difference := 1;',
             f'IF ({w}.Hit >= 0) AND ({w}.LoginValid <> 0) THEN', f'{w}.Difference := 0;',
             f'FOR {i} := 0 TO {WIDTH - 1} DO',
             f'{w}.Difference := {w}.Difference OR ({w}.Digest[{i}] XOR {users}.Hash[{w}.Hit * {WIDTH} + {i}]);', 'END_FOR;',
             f'IF ({users}.Level[{w}.Hit] < 1) OR ({users}.Level[{w}.Hit] > {ADMIN}) THEN {w}.Difference := 1; END_IF;', 'END_IF;',
             f'{w}.Gate := -1;', f'IF {w}.Difference = 0 THEN',
             f'{s}.CurrentLevel := {users}.Level[{w}.Hit];', f'{s}.UserLength := {w}.ActorLength;',
             f'FOR {i} := 0 TO {WIDTH - 1} DO {s}.UserBytes[{i}] := {w}.User[{i}]; END_FOR;',
             f'{s}.LoginFailed := 0;', f'{w}.IdleMs := 0;', f'{w}.Rearmed := 1;',
             *_audit(app, 'std.audit.login', '1', w + '.Sequence', '1', w + '.ActorLength', w + '.User'),
             'ELSE', f'{s}.LoginFailed := 1;',
             *_audit(app, 'std.audit.loginFailed', '1', w + '.Sequence', '0', w + '.ActorLength', w + '.User'), 'END_IF;',
             f'{s}.LoginResultSequence := {w}.Sequence;', *cancel_login(app), 'END_IF;', 'END_IF;',
             f'IF ({s}.CurrentLevel > 0) AND ({s}.SessionTimeout > 0) AND ({w}.Rearmed = 0) THEN',
             f'IF {w}.IdleMs < {TIMEOUT_MAX} THEN {w}.IdleMs := {w}.IdleMs + {app.task_period_ms}; END_IF;',
             f'IF {w}.IdleMs >= {s}.SessionTimeout THEN',
             *_audit(app, 'std.audit.autoLogout', '2', '0', '1', s + '.UserLength', s + '.UserBytes'),
             *_clear_session(app), 'END_IF;', 'END_IF;']
    return lines


def dispatch(app):
    import fraktal_ab_mailbox as mb
    s, w, q = tag(app, 'State'), tag(app, 'Work'), mb.request_tag_name(app)
    i = w + '.Index'
    # Cyclic may finish the prior login before dispatch samples a new request.
    # Preserve that scan's spent block budget even after LoginBusy is cleared.
    return [f'{mb.LOGIN}: (* LOGIN *)', f'IF ({s}.LoginBusy <> 0) OR ({w}.HashRan <> 0) THEN', *wipe_login(app), *mb._refuse(app, BUSY),
            f'{w}.Prior := {q}.User.LEN;',
            f'IF ({w}.Prior < 0) OR ({w}.Prior > {WIDTH}) THEN {w}.Prior := 0; END_IF;',
            *_audit(app, 'std.audit.loginFailed', '1', f'FRK_{app.name}_HmiLastSequence', '0', w + '.Prior', q + '.User.DATA'),
            'ELSE', *login(app), *mb._accept(app), 'END_IF;',
            f'{mb.LOGOUT}: (* LOGOUT *)',
            f'IF {s}.LoginBusy <> 0 THEN',
            *_audit(app, 'std.audit.loginFailed', '1', w + '.Sequence', '0', w + '.ActorLength', w + '.User'),
            'END_IF;',
            f'IF {s}.CurrentLevel > 0 THEN',
            *_audit(app, 'std.audit.logout', '2', f'FRK_{app.name}_HmiLastSequence', '1', s + '.UserLength', s + '.UserBytes'),
            'END_IF;', *cancel_login(app), *_clear_session(app), *mb._accept(app),
            f'{mb.SET_ACCESS_LEVEL}: (* SET_ACCESS_LEVEL *)',
            # TextValue is a StringFamily, even for a native CIP client. Never
            # trust a gateway's numeric translation to stand in for validation.
            f'{w}.Valid := 0;', f'IF {q}.TextValue.LEN = 1 THEN',
            f'{i} := {q}.TextValue.DATA[0] - 48;',
            f'IF ({i} >= 0) AND ({i} <= {ADMIN}) THEN {w}.Valid := 1; END_IF;', 'END_IF;',
            f'IF ({q}.IntValue < 0) OR ({q}.IntValue >= {GATE_COUNT}) THEN {w}.Valid := 0; END_IF;',
            f'IF ({q}.IntValue = 8) AND ({i} > {s}.CurrentLevel) THEN {w}.Valid := 0; END_IF;',
            f'IF {w}.Valid <> 0 THEN', f'{s}.Required[{q}.IntValue] := {i};', *mb._accept(app),
            'ELSE', *mb._refuse(app, INVALID), 'END_IF;',
            f'{mb.SET_SESSION_TIMEOUT}: (* SET_SESSION_TIMEOUT *)',
            f'IF ({q}.DurationMs >= 0) AND ({q}.DurationMs <= {TIMEOUT_MAX}) THEN',
            f'{s}.SessionTimeout := {q}.DurationMs;', *mb._accept(app),
            'ELSE', *mb._refuse(app, INVALID), 'END_IF;']


def permits(app, gate):
    s = tag(app, 'State')
    return f'({s}.CurrentLevel >= 0) AND ({s}.CurrentLevel <= {ADMIN}) AND ({s}.Required[{gate}] >= 0) AND ({s}.Required[{gate}] <= {ADMIN}) AND ({s}.CurrentLevel >= {s}.Required[{gate}])'


def check(app):
    import fraktal_ab_mailbox as mb
    s, w, q = tag(app, 'State'), tag(app, 'Work'), mb.request_tag_name(app)
    lines = [f'{w}.Gate := -1;', f'{w}.Minimum := 0;', f'{w}.Permitted := 1;', f'CASE {q}.Kind OF']
    lines += [f'{kind}: {w}.Gate := {gate};' for kind, gate in sorted(GATES.items())]
    lines += ['ELSE', '(* LOGIN, LOGOUT and release queries are ungated. *)', 'END_CASE;',
              # Release of a held command always withdraws its output (TC3).
              f'IF {w}.Gate >= 0 THEN',
              # QUERY_CONFIG always returns metadata; value visibility and
              # writes/captures are determined by each effective class level.
              f'IF ({q}.Kind <> {mb.QUERY_CONFIG}) AND ({q}.Kind <> {mb.WRITE_CONFIG}) AND ({q}.Kind <> {mb.CAPTURE_CONFIG}) THEN',
              f'IF NOT ({permits(app, w + ".Gate")}) THEN {w}.Permitted := 0; END_IF;', 'END_IF;',
              f'IF {s}.CurrentLevel < {w}.Minimum THEN {w}.Permitted := 0; END_IF;', 'END_IF;',
              # TC3 checks ENGINEER directly, independently of open/tighter
              # DATA_WRITE or CONFIG_SET thresholds. -2 identifies that gate.
              f'IF {q}.Kind = {mb.ACK_CONFIG_RESTORE} THEN', f'{w}.Gate := -2;', f'{w}.Permitted := 0;',
              f'IF ({s}.CurrentLevel >= {ENGINEER}) AND ({s}.CurrentLevel <= {ADMIN}) THEN {w}.Permitted := 1; END_IF;', 'END_IF;',
              f'IF ({q}.Kind = {mb.SET_HOLD_RUN}) AND ({q}.BoolValue = 0) THEN {w}.Permitted := 1; END_IF;',
              f'IF ({q}.Kind = {mb.MANUAL_HELD}) AND ({q}.BoolValue = 0) THEN {w}.Permitted := 1; END_IF;']
    return lines


def report(app, report_tag, gate):
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    # Range check precedes subscript: corrupt/native release-action ordinal
    # is a refusal, never an array fault. Each IF owns its only subscript.
    w = tag(app, 'Work')
    lines = [f'{w}.Permitted := 0;', f'IF ({gate} >= 0) AND ({gate} < {GATE_COUNT}) THEN',
             f'IF {permits(app, gate)} THEN {w}.Permitted := 1; END_IF;', 'END_IF;',
             f'IF {w}.Permitted = 0 THEN',
             *gen.report_add(report_tag, mf.numeric_key(app, DENIED), 0, 0, 'ACCESS', DENIED), 'END_IF;']
    return lines


def after(app):
    import fraktal_ab_mailbox as mb
    s, w, q, a = tag(app, 'State'), tag(app, 'Work'), mb.request_tag_name(app), mb.response_tag_name(app)
    import fraktal_ab_data_access as data
    lines = [f'IF {w}.Gate <> -1 THEN', f'IF {w}.Permitted = 0 THEN',
             f'IF {data.tag(app, "Levels")}.RejectCapability <> 0 THEN',
             *_audit(app, data.DENIED, q + '.Kind', f'FRK_{app.name}_HmiLastSequence', '0', s + '.UserLength', s + '.UserBytes'),
             'ELSE',
             *_audit(app, 'std.audit.accessDenied', q + '.Kind', f'FRK_{app.name}_HmiLastSequence', '0', s + '.UserLength', s + '.UserBytes'),
             'END_IF;',
             f'ELSIF ({q}.Kind <> {mb.LOGIN}) AND ({q}.Kind <> {mb.LOGOUT}) THEN',
             f'CASE {q}.Kind OF', ','.join(map(str, PURE_KINDS)) + ':',
             '(* Pure queries do not record operator activity. *)', 'ELSE',
             f'IF ({a}.Accepted <> 0) AND ({s}.CurrentLevel > 0) THEN', f'{w}.IdleMs := 0;',
             *_audit(app, 'std.audit.operatorAction', q + '.Kind', f'FRK_{app.name}_HmiLastSequence', '1', s + '.UserLength', s + '.UserBytes'),
             'END_IF;', 'END_CASE;', 'END_IF;', 'END_IF;']
    return lines


def status(app, held):
    # A missing session/policy fails closed in the existing generic mapper.
    if held is None:
        return {}
    out = {'Access/CurrentLevel': held['CurrentLevel'],
           'Access/CurrentUser': bytes(held['UserBytes'][:max(0, min(WIDTH, held['UserLength']))]).decode('ascii', errors='replace'),
           'Access/LoginFailed': bool(held['LoginFailed']), 'Access/LoginBusy': bool(held['LoginBusy']),
           'Access/LoginTimeoutMs': held['LoginTimeoutMs'],
           'Access/LoginPrehashRounds': held['LoginPrehashRounds'],
           'Access/LoginResultSequence': held['LoginResultSequence'] & 0xffffffff,
           'Access/Policy/SessionTimeout': held['SessionTimeout']}
    out.update({f'Access/Policy/Required[{i + 1}]': n for i, n in enumerate(held['Required'])})
    return out


def audit_status(app, rows, held, ring):
    """Enrich MESSAGE slots of the existing 64-entry controller alarm ring."""
    import fraktal_ab_generate as gen
    if held is None or ring is None or held.get('SchemaVersion') != AUDIT_SCHEMA:
        return {}
    keys = {r['NumericKey']: r['PortableKey'] for r in rows.get('Localization', [])}
    out = {}
    for slot in range(AUDIT_CAPACITY):
        occupied = bool(held['Key'][slot]) and ring['RingState'][slot] == gen.ALARM_CLOSED and ring['RingReasonCode'][slot] == 0
        if not occupied:
            continue
        n = max(0, min(WIDTH, held['UserLength'][slot]))
        words = held['UserWords'][slot * ACTOR_WORDS:(slot + 1) * ACTOR_WORDS]
        actor = b''.join((v & 0xffffffff).to_bytes(4, 'little') for v in words)[:n].decode('ascii', errors='replace')
        event = dict(Description=keys.get(held['Key'][slot], '') + ': ' + actor +
                     ' [kind=' + str(held['Kind'][slot]) + ', gate=' + str(held['Gate'][slot]) + ']',
                     SourcePath=app.name + '.Access')
        if keys.get(held['Key'][slot]) in ('std.audit.alarmShelved', 'std.audit.alarmUnshelved'):
            import fraktal_ab_projection as projection
            event['SourcePath'] = projection._module_path(app, ring['RingSourceModuleId'][slot])
            if held['Sequence'][slot] == 0:
                event['Description'] += ' [automatic]'
        capability = held['DataCapability'][slot]
        if capability:
            cap = next((row for row in rows.get('WriteCapabilities', []) if row['CapabilityIndex'] == capability), None)
            write_key = keys.get(cap['WriteKeyKey'], '') if cap else ''
            event['Description'] += ' [value=' + write_key + ', required=' + str(held['DataRequiredLevel'][slot]) + ']'
        out.update({f'AlarmLog/Ring[{slot + 1}]/{k}': v for k, v in event.items()})
    return out

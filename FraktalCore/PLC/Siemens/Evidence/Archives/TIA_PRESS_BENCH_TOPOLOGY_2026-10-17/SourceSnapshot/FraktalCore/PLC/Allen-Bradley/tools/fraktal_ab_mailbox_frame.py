"""S9's bounded native request; the public HMI request remains unchanged.

One DINT-array write stages the complete operation and its bounded arguments.
Sequence is a separate, final commit. The PLC snapshots the frame with CPS,
checks its version and matching sequence, then decodes into its private request.
Large ConfigSet records remain a separately staged configuration transaction.
"""

import struct

CONNECTION_SIZE = 500
# The pinned pylogix _convert_write_data reserves this overhead before choosing
# an unfragmented chunk. Derive the capacity against that conservative rule.
PYLOGIX_PACKET_OVERHEAD = 110
SCHEMA = 1
HEADER_WORDS = 10  # version, kind, three scalar arguments, five string lengths
STRINGS = ('TargetPath', 'NameValue', 'TextValue', 'User', 'Secret')
SCALARS = ('Kind', 'IntValue', 'BoolValue', 'DurationMs')


def native_path(app):
    return f'FRK_{app.name}_HmiRequest.Frame.Words'


def word_count(app):
    path_bytes = len(native_path(app))
    result = (CONNECTION_SIZE - PYLOGIX_PACKET_OVERHEAD - path_bytes - path_bytes % 2) // 4
    if result <= HEADER_WORDS + 1:
        raise ValueError('native mailbox path leaves no bounded argument space')
    return result


def argument_bytes(app):
    return (word_count(app) - HEADER_WORDS - 1) * 4


def profile(app):
    return dict(schema=SCHEMA, connectionBytes=CONNECTION_SIZE,
                words=word_count(app), stringArgumentBytes=argument_bytes(app))


def signed(value):
    if isinstance(value, bool) or not isinstance(value, int) or not -0x80000000 <= value <= 0xffffffff:
        raise ValueError('mailbox word is outside 32 bits')
    return value if value < 0x80000000 else value - 0x100000000


def encode(app, values):
    import fraktal_ab_mailbox as mb
    unknown = set(values) - {n for n, *_ in mb.REQUEST_MEMBERS}
    if unknown:
        raise ValueError(f'not mailbox members: {sorted(unknown)}')
    chunks = []
    for name in STRINGS:
        text = values.get(name, '')
        if not isinstance(text, str) or not text.isascii():
            raise ValueError(f'{name} requires ASCII text')
        mb.member_writes(app, name, text)  # same per-field bounds as native clients
        chunks.append(text.encode('ascii'))
    payload = b''.join(chunks)
    if len(payload) > argument_bytes(app):
        raise ValueError(f'command string arguments exceed {argument_bytes(app)} bytes; use staged configuration')
    words = [SCHEMA, *(signed(int(values.get(n, 0))) for n in SCALARS),
             *(len(c) for c in chunks)]
    payload = payload.ljust(argument_bytes(app), b'\0')
    words.extend(struct.unpack('<' + 'i' * (len(payload) // 4), payload))
    words.append(signed(values['Sequence']))
    return words


def decode(app, words):
    """Test/apparatus decoder; the generated PLC decoder owns runtime behavior."""
    import fraktal_ab_mailbox as mb
    if len(words) != word_count(app) or words[0] != SCHEMA:
        raise ValueError('native frame schema/length does not match')
    lengths = words[5:10]
    widths = {n: w for n, _, w, _ in mb.REQUEST_MEMBERS}
    if any(n < 0 or n > widths[k] for k, n in zip(STRINGS, lengths)) or sum(lengths) > argument_bytes(app):
        raise ValueError('native frame string lengths are invalid')
    raw = struct.pack('<' + 'i' * (len(words) - HEADER_WORDS - 1), *words[10:-1])
    out = dict(zip(SCALARS, words[1:5]), Sequence=words[-1] & 0xffffffff)
    cursor = 0
    for name, length in zip(STRINGS, lengths):
        out[name] = raw[cursor:cursor + length].decode('ascii')
        cursor += length
    return out


def type_name(app):
    return f'FRK_T_{app.name}HmiFrameV1'


def sample_tag(app):
    return f'FRK_{app.name}_HmiFrameSample'


def routine_name(app):
    return f'FRK_{app.name}HmiFrame'


def members(app):
    import fraktal_ab_declaration as decl
    return (decl.scalar('Words', dimension=word_count(app)),)


def data_types(app):
    import fraktal_ab_generate as gen
    body = '\n'.join(gen._member_xml(m) for m in members(app))
    return [f'<DataType Name="{type_name(app)}" Family="NoFamily" Class="User"><Members>{body}</Members></DataType>']


def tags(app):
    import fraktal_ab_generate as gen
    return [gen._structure_tag(sample_tag(app), type_name(app), members(app), 'None'),
            *(f'<Tag Name="FRK_{app.name}_HmiFrame{n}" TagType="Base" DataType="DINT" Radix="Decimal" Constant="false" ExternalAccess="None"/>'
              for n in ('Cursor', 'Word', 'Byte', 'Valid', 'Field'))]


def logic(app):
    import fraktal_ab_mailbox as mb
    q, sample = mb.request_tag_name(app), sample_tag(app)
    words, i = sample + '.Words', f'FRK_{app.name}_HmiWipe'
    cursor, word, byte, valid = (f'FRK_{app.name}_HmiFrame{n}' for n in ('Cursor', 'Word', 'Byte', 'Valid'))
    field = f'FRK_{app.name}_HmiFrameField'
    count = word_count(app)
    lines = [f'IF {q}.Sequence <> FRK_{app.name}_HmiLastSequence THEN',
             f'CPS({q}.Frame,{sample},1);', f'{valid} := 1;',
             f'IF ({words}[0] <> {SCHEMA}) OR ({words}[{count - 1}] <> {q}.Sequence) THEN {valid} := 0; END_IF;']
    widths = {n: w for n, _, w, _ in mb.REQUEST_MEMBERS}
    for index, name in enumerate(STRINGS, 5):
        lines += [f'IF ({words}[{index}] < 0) OR ({words}[{index}] > {widths[name]}) THEN {valid} := 0; END_IF;',
                  f'{q}.{name}.LEN := 0;']
    total = ' + '.join(f'{words}[{n}]' for n in range(5, 10))
    # Individual checks precede the sum, preventing a corrupt DINT overflow.
    lines += [f'IF {valid} <> 0 THEN', f'IF ({total}) > {argument_bytes(app)} THEN {valid} := 0; END_IF;',
              'END_IF;', f'{q}.Kind := -1;', f'IF {valid} <> 0 THEN', f'{cursor} := 0;']
    lines += [f'FOR {field} := 5 TO 9 DO', f'CASE {field} OF']
    lines += [f'{index}: {q}.{name}.LEN := {words}[{field}];' for index, name in enumerate(STRINGS, 5)]
    lines += ['END_CASE;', f'FOR {i} := 0 TO {words}[{field}] - 1 DO',
                  f'{word} := {HEADER_WORDS} + ({cursor} - ({cursor} MOD 4)) / 4;',
                  f'CASE ({cursor} MOD 4) OF',
                  f'0: {byte} := {words}[{word}] AND 255;',
                  f'1: {byte} := ({words}[{word}] AND 65280) / 256;',
                  f'2: {byte} := ({words}[{word}] AND 16711680) / 65536;',
                  f'3: {byte} := ({words}[{word}] AND 2130706432) / 16777216;',
                  f'IF {words}[{word}] < 0 THEN {byte} := {byte} OR 128; END_IF;',
                  'END_CASE;', f'IF {byte} > 127 THEN {valid} := 0; END_IF;', f'CASE {field} OF']
    lines += [f'{index}: {q}.{name}.DATA[{i}] := {byte};' for index, name in enumerate(STRINGS, 5)]
    lines += ['END_CASE;', f'{cursor} := {cursor} + 1;', 'END_FOR;', 'END_FOR;']
    lines += [f'IF {valid} <> 0 THEN']
    lines += [f'{q}.{name} := {words}[{index}];' for index, name in enumerate(SCALARS, 1)]
    # Private string storage is sampled only by the existing command handler.
    # Clear both frame copies before AckSequence can be published, including
    # credential bytes beyond LEN. A malformed frame is refused, never retried.
    lines += ['END_IF;', 'END_IF;', f'FOR {i} := 0 TO {count - 1} DO',
              f'{q}.Frame.Words[{i}] := 0;', f'{words}[{i}] := 0;', 'END_FOR;',
              f'{cursor} := 0;', f'{word} := 0;', f'{byte} := 0;', 'END_IF;']
    return tuple(lines)

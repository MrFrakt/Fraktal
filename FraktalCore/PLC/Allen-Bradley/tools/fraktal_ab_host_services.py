"""V6.11 shared host ingress: PLC-owned job identity and its commit state table.

Engineering only. The host adapter consumes the manifest row and Templates
through fraktal_ab_host_service_binding; it never resolves a key or decides a
verdict. This module owns the per-root generic part every host service shares:
the commit/acknowledge state table (uint32 serial order, payload/commit
agreement, no replay), job identity and chunk order, the job window, and the
CPS-published reply. Service routines run between `ingress` and `finish` on an
accepted chunk; they validate its body, stage it and advance or complete the
job, and react to its Outcome after `finish` in the same scan.
"""
import hashlib

import fraktal_ab_canonical_publication as pub
import fraktal_ab_host_service_binding as binding

MINOR = binding.MINOR
HEADER_FIELDS = binding.HEADER_FIELDS
P = 'FRK_T_'
REQUEST = P + 'HostRequestV611'
CHUNK = P + 'HostChunkV611'
REPLY = P + 'HostReplyV611'
SNAPSHOT = P + 'HostSnapshotV611'
WORK = P + 'HostWorkV611'
ROW = P + 'HostServiceBindingV611'
CHUNK_MEMBER = 'Body'


def string_type(width):
    # The host writes the request whole. A published canonical string's LEN and
    # DATA are Read Only, which refuses that write with CIP 0x0F (privilege
    # violation, first native session 2026-11-04), so the request's texts use
    # this Read/Write family, as the typed command ingress uses its own.
    return pub.PREFIX + f'String{width}HostV611'


def string_data_types():
    import xml.etree.ElementTree as ET
    out = []
    for width in sorted({*binding.TEXTS.values(), binding.KEY_WIDTH}):
        node = ET.Element('DataType', Name=string_type(width), Family='StringFamily', Class='User')
        fields = ET.SubElement(node, 'Members')
        for name, kind, count, radix in (('LEN', 'DINT', 0, 'Decimal'), ('DATA', 'SINT', width, 'ASCII')):
            ET.SubElement(fields, 'Member', Name=name, DataType=kind, Dimension=str(count), Radix=radix,
                          Hidden='false', ExternalAccess='Read/Write')
        out.append(ET.tostring(node, encoding='unicode'))
    return out
RECORDS_PER_CHUNK = 8
CONNECTION_BYTES = 4000
# An operator waits for FETCH and PRESENT: the HMI's acknowledgement budget is 2 s.
ANSWER_MS = 1500
# Work.Outcome, consumed by the owning service in the scan it is set.
COMPLETED, ABANDONED, TIMED_OUT = 1, 2, 3
WORK_MEMBERS = ('Armed', 'Serial', 'Seen', 'LastSeen', 'New', 'Error', 'Upper', 'Lower',
                'PriorUpper', 'Claimed', 'Accept', 'JobCounter', 'ElapsedMs', 'WindowMs',
                'Outcome', 'Dirty', 'Index', 'Bad')


def enabled(app):
    return app.canonical_host_services


def validate(app):
    if type(app.canonical_host_services) is not bool:
        return ['canonical_host_services must be a BOOL opt-in']
    if not enabled(app):
        return []
    import fraktal_ab_declaration as decl
    errors = []
    if not app.canonical_owner_revisions or app.canonical_publication_stage != 13:
        errors.append('host services require the complete V6.10 owner-revision profile')
    if not services(app):
        errors.append('host services require a configuration-set store or a host-event ring')
    if app.config_sets and app.access_users is None:
        errors.append('host configuration sets require the access gate their jobs are opened under')
    if decl.live_documents(app) and not app.config_sets:
        errors.append('host live documents are restored through the configuration-set transaction')
    return errors


def mutating(app):
    return any(s in binding.MUTATING for s in services(app))


def ring_revision_tag(app):
    return _name(app, 'HostRingRevision')


def _name(app, suffix):
    value = f'FRK_{app.name}_{suffix}'
    return value if len(value) <= 40 else value[:23] + '_' + hashlib.sha256(value.encode()).hexdigest()[:16]


def request_tag(app): return _name(app, 'HostRequest')
def sample_tag(app): return _name(app, 'HostSample')
def commit_tag(app): return _name(app, 'HostCommit')
def reply_tag(app): return _name(app, 'HostReply')
def work_tag(app): return _name(app, 'HostWork')


def services(app):
    """The services this root actually serves; an unused one is not advertised."""
    import fraktal_ab_declaration as decl
    out = []
    if app.config_sets:
        out += [binding.SERVICES['ConfigSets'], binding.SERVICES['ConfigProvider']]
    if decl.live_documents(app):
        out.append(binding.SERVICES['LiveDocuments'])
    if app.host_event_capacity:
        out.append(binding.SERVICES['HostEvents'])
    return out


def maximum_chunk_bytes():
    """The request record's native size bound, published so a client can refuse early."""
    return CONNECTION_BYTES - 256


def rows(app):
    import fraktal_ab_access as access
    import fraktal_ab_mailbox as mb
    out = []
    for service in services(app):
        row = dict(RootSymbol=app.name, Service=service, Version=binding.VERSION,
                   RequestSymbol='', ChunkMember='', MaximumChunkBytes=0, ConnectionBytes=0,
                   CommitSymbol='', ReplySymbol='', CanonicalRoot='', AccessGate=-1)
        if service == binding.SERVICES['HostEvents']:
            row['CanonicalRoot'] = app.name + '/HostEvents'
        else:
            row.update(RequestSymbol=request_tag(app), ChunkMember=CHUNK_MEMBER,
                       MaximumChunkBytes=maximum_chunk_bytes(), ConnectionBytes=CONNECTION_BYTES,
                       CommitSymbol=commit_tag(app), ReplySymbol=reply_tag(app))
            # A host opens LiveDocuments jobs itself, under the operator's set gate.
            if service == binding.SERVICES['LiveDocuments']:
                row['AccessGate'] = access.GATES[mb.LOAD_CONFIG_SET]
        out.append(row)
    return binding.bindings(out) if out else out


def augment(app, definitions, snapshot_count):
    M, S = pub.Member, pub.string_type
    definitions[CHUNK] = (*(M(n, 'DINT', access='Read/Write') for n in binding.SCALARS),
                          *(M(n, string_type(w), access='Read/Write') for n, w in binding.TEXTS.items()),
                          M('Keys', string_type(binding.KEY_WIDTH), count=RECORDS_PER_CHUNK, access='Read/Write'),
                          *(M(n, 'DINT', count=RECORDS_PER_CHUNK, access='Read/Write') for n in binding.COLUMNS))
    definitions[REQUEST] = (*(M(n, 'DINT', access='Read/Write') for n in (*binding.HEADER, *binding.ENVELOPE)),
                            M(CHUNK_MEMBER, CHUNK, access='Read/Write'))
    definitions[SNAPSHOT] = (*(M(n, 'DINT') for n in binding.SNAPSHOT),
                             M('Values', 'DINT', count=max(1, snapshot_count)))
    definitions[REPLY] = (*(M(n, 'DINT') for n in binding.REPLY),
                          *(M(n, S(w)) for n, w in binding.REPLY_TEXTS.items()), M('Snapshot', SNAPSHOT))
    definitions[WORK] = (*(M(n, 'DINT') for n in WORK_MEMBERS), M('Reply', REPLY))
    definitions[ROW] = tuple(M(k, S(255 if k == 'CanonicalRoot' else 40) if k in binding.TEXT_FIELDS else 'DINT')
                             for k in sorted(binding.FIELD))


def manifest_members(app):
    M = pub.Member
    return (M('HostServiceBindingsCount', 'DINT'), M('HostServiceBindingsCapacity', 'DINT'),
            M('HostServiceBindings', ROW, count=len(rows(app))))


def augment_schema(app, definitions):
    """The V6.11 manifest table, and the ingress types only where a row names them."""
    if not enabled(app):
        return
    import fraktal_ab_generate as gen
    import fraktal_ab_host_sets as host_sets
    augment(app, definitions, len(gen.editable_values(app)))
    if not mutating(app):
        for kind in (REQUEST, CHUNK, REPLY, SNAPSHOT, WORK):
            del definitions[kind]
    definitions[pub.header_type(app)] += manifest_members(app)
    if host_sets.enabled(app):
        host_sets.augment(app, definitions)


def tags(app, serialize):
    import fraktal_ab_host_sets as host_sets
    if not enabled(app):
        return []
    ring = ([f'<Tag Name="{ring_revision_tag(app)}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read Only"/>']
            if binding.SERVICES['HostEvents'] in services(app) else [])
    if not mutating(app):
        return ring
    return [serialize(request_tag(app), REQUEST, dict(SchemaVersion=binding.VERSION), access='Read/Write'),
            serialize(sample_tag(app), REQUEST, {}, access='None'),
            serialize(work_tag(app), WORK, {}, access='None'),
            serialize(reply_tag(app), REPLY, dict(SchemaVersion=binding.VERSION)),
            f'<Tag Name="{commit_tag(app)}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read/Write"/>',
            *ring, *(host_sets.tags(app, serialize) if host_sets.enabled(app) else [])]


def before_command_ingress(app):
    """Host ingress, its services and the reply, ahead of the typed command ingress."""
    import fraktal_ab_host_sets as host_sets
    if not enabled(app) or not mutating(app):
        return []
    return [*host_sets.prologue(app), *ingress(app), f'JSR({host_sets.service_routine(app)},0);',
            *finish(app), *host_sets.outcome(app)]


def after_command_ingress(app):
    import fraktal_ab_host_sets as host_sets
    return host_sets.resume(app) if host_sets.enabled(app) else []


def routines(app):
    import fraktal_ab_host_sets as host_sets
    return host_sets.routines(app) if enabled(app) else []


def _serial(w):
    """The typed ingress's unsigned serial subtraction, in 16-bit halves.

    Neither a wide literal nor a platform arithmetic-fault exception: a commit
    is accepted only when it lies strictly ahead of Serial within half the
    uint32 circle. Equal is a replay; behind or a half-circle away is stale.
    """
    return [f'{w}.Upper := ({w}.Seen AND 2147418112) / 65536;',
            f'IF {w}.Seen < 0 THEN {w}.Upper := {w}.Upper + 32768; END_IF;',
            f'{w}.PriorUpper := ({w}.Serial AND 2147418112) / 65536;',
            f'IF {w}.Serial < 0 THEN {w}.PriorUpper := {w}.PriorUpper + 32768; END_IF;',
            f'{w}.Lower := ({w}.Seen AND 65535) - ({w}.Serial AND 65535);',
            f'{w}.Upper := {w}.Upper - {w}.PriorUpper;',
            f'IF {w}.Lower < 0 THEN {w}.Upper := {w}.Upper - 1; END_IF;',
            f'IF {w}.Upper < 0 THEN {w}.Upper := {w}.Upper + 65536; END_IF;',
            f'IF ({w}.Upper >= 32768) OR (({w}.Upper = 0) AND ({w}.Lower = 0)) THEN {w}.Error := {binding.STALE_SERIAL};',
            f'ELSE {w}.Serial := {w}.Seen; END_IF;']


def _text_bounded(value, width):
    return f'({value}.LEN < 0) OR ({value}.LEN > {width})'


def ingress(app):
    """Consume at most one commit; decide only what every service shares."""
    w, s, r, c = work_tag(app), sample_tag(app), work_tag(app) + '.Reply', commit_tag(app)
    b = s + '.' + CHUNK_MEMBER
    bounded = [f'({s}.Final < 0) OR ({s}.Final > 1) OR ({s}.Status < 0) OR ({s}.Status > {binding.UNAVAILABLE})',
               f'({b}.Kind < {binding.NONE}) OR ({b}.Kind > {binding.TEXT})',
               f'({b}.Count < 0) OR ({b}.Count > 64) OR ({b}.Total < 0) OR ({b}.Total > 64)',
               *(_text_bounded(f'{b}.{n}', width) for n, width in binding.TEXTS.items())]
    lines = [f'{w}.New := 0;', f'{w}.Error := 0;', f'{w}.Claimed := 0;', f'{w}.Accept := 0;', f'{w}.Outcome := 0;',
             f'{w}.Seen := {c};',
             # Only a download (Armed = 0) seeds the serial. A later first scan
             # still consumes a changed commit, so a write made during program
             # mode is refused visibly instead of swallowed, and a writer that
             # advances from Serial never repeats the value the PLC last saw.
             f'IF {w}.Armed = 0 THEN', f'{w}.Serial := {w}.Seen;', f'{w}.LastSeen := {w}.Seen;',
             f'{w}.Armed := 1;', 'END_IF;',
             # A host stream cannot resume across a first scan; its owner refuses.
             f'IF S:FS AND ({r}.JobSequence <> 0) THEN', *abandon(app, ABANDONED), 'END_IF;',
             f'IF {w}.Seen <> {w}.LastSeen THEN', f'{w}.New := 1;', f'{w}.LastSeen := {w}.Seen;',
             *_serial(w), 'END_IF;',
             # A stale serial is refused as stale: its payload is never sampled.
             f'IF ({w}.New <> 0) AND ({w}.Error = 0) THEN', f'CPS({request_tag(app)},{s},1);',
             f'IF ({r}.JobSequence <> 0) AND ({s}.JobSequence = {r}.JobSequence) THEN {w}.Claimed := 1; END_IF;',
             # Every key extent is bounded before any service loop indexes DATA.
             f'{w}.Bad := 0;', f'FOR {w}.Index := 0 TO {RECORDS_PER_CHUNK - 1} DO',
             f'IF {_text_bounded(b + ".Keys[" + w + ".Index]", binding.KEY_WIDTH)} THEN {w}.Bad := 1; END_IF;',
             'END_FOR;',
             f'IF {s}.SchemaVersion <> {binding.VERSION} THEN {w}.Error := {binding.INVALID};',
             f'ELSIF ({s}.StagedSequence <> {w}.Seen) OR ({c} <> {w}.Seen) THEN {w}.Error := {binding.COLLIDED};',
             f'ELSIF {s}.ManifestRevision <> {pub.header_tag(app)}.ConfigRevision THEN {w}.Error := {binding.STALE_REVISION};',
             *(f'ELSIF {term} THEN {w}.Error := {binding.INVALID};' for term in bounded),
             f'ELSIF {w}.Bad <> 0 THEN {w}.Error := {binding.INVALID};',
             f'ELSIF {s}.JobSequence = 0 THEN',
             # A host may open a job only while none is active; the service decides the rest.
             f'IF {r}.JobSequence <> 0 THEN {w}.Error := {binding.BUSY}; ELSE {w}.Accept := 1; END_IF;',
             f'ELSIF {w}.Claimed = 0 THEN {w}.Error := {binding.NO_JOB};',
             f'ELSIF ({s}.Service <> {r}.JobService) OR ({s}.Operation <> {r}.JobOperation) OR ({s}.Chunk <> {r}.NextChunk) THEN',
             f'{w}.Error := {binding.ORDER};',
             'ELSE', f'{w}.Accept := 1;', 'END_IF;', 'END_IF;']
    return lines


def finish(app):
    """Abandon on any refused claim, run the job window, publish the reply."""
    w, r = work_tag(app), work_tag(app) + '.Reply'
    return [f'IF {w}.New <> 0 THEN',
            # A refused chunk that claimed the job breaks its stream: never a partial apply.
            f'IF ({w}.Claimed <> 0) AND ({w}.Error <> 0) AND ({r}.JobSequence = {sample_tag(app)}.JobSequence) THEN',
            *abandon(app, ABANDONED), 'END_IF;',
            f'{r}.Serial := {w}.Serial;', f'{r}.AckSequence := {w}.Seen;', f'{r}.ErrorCode := {w}.Error;',
            f'IF {w}.Error = 0 THEN {r}.Accepted := 1; ELSE {r}.Accepted := 0; END_IF;', f'{w}.Dirty := 1;',
            'END_IF;',
            f'IF {r}.JobSequence <> 0 THEN',
            f'{w}.ElapsedMs := {w}.ElapsedMs + {app.task_period_ms};',
            f'IF {w}.ElapsedMs >= {w}.WindowMs THEN', *abandon(app, TIMED_OUT), 'END_IF;', 'END_IF;',
            # One CPS per changed scan: a reader sees the whole old or new reply.
            f'IF {w}.Dirty <> 0 THEN', f'CPS({r},{reply_tag(app)},1);', f'{w}.Dirty := 0;', 'END_IF;']


def open_job(app, service, operation, phase, window_ms=ANSWER_MS):
    """Begin a job; the next chunk the host must send is chunk 0."""
    w, r = work_tag(app), work_tag(app) + '.Reply'
    return [f'IF ({w}.JobCounter < 1) OR ({w}.JobCounter >= 2147483646) THEN {w}.JobCounter := 1;',
            f'ELSE {w}.JobCounter := {w}.JobCounter + 1; END_IF;',
            f'{r}.JobSequence := {w}.JobCounter;', f'{r}.JobService := {service};',
            f'{r}.JobOperation := {operation};', f'{r}.JobPhase := {phase};', f'{r}.NextChunk := 0;',
            f'{w}.ElapsedMs := 0;', f'{w}.WindowMs := {window_ms};', f'{w}.Dirty := 1;']


def next_phase(app, service, phase, window_ms=ANSWER_MS):
    """Continue the same job under its next phase; chunk numbering restarts."""
    w, r = work_tag(app), work_tag(app) + '.Reply'
    return [f'{r}.JobService := {service};', f'{r}.JobPhase := {phase};', f'{r}.NextChunk := 0;',
            f'{w}.ElapsedMs := 0;', f'{w}.WindowMs := {window_ms};', f'{w}.Dirty := 1;']


def advance(app):
    r = work_tag(app) + '.Reply'
    return [f'{r}.NextChunk := {r}.NextChunk + 1;', f'{work_tag(app)}.Dirty := 1;']


def _close(app):
    w, r = work_tag(app), work_tag(app) + '.Reply'
    lines = [f'{r}.{n} := 0;' for n in ('JobSequence', 'JobService', 'JobOperation', 'JobPhase',
                                         'NextChunk', 'JobInt', 'JobBool')]
    # Job text is a transported document piece; it never outlives its job.
    for name, width in binding.REPLY_TEXTS.items():
        lines += [f'{r}.{name}.LEN := 0;', f'FOR {w}.Index := 0 TO {width - 1} DO',
                  f'{r}.{name}.DATA[{w}.Index] := 0;', 'END_FOR;']
    return lines + [f'{w}.ElapsedMs := 0;', f'{w}.WindowMs := 0;', f'{w}.Dirty := 1;']


def complete(app):
    return [*_close(app), f'{work_tag(app)}.Outcome := {COMPLETED};']


def abandon(app, outcome):
    return [*_close(app), f'{work_tag(app)}.Outcome := {outcome};']

"""V6.11 configuration-set service on the shared host ingress.

Engineering only. The operator's set command reaches the controller first,
through the typed command ingress, and the mailbox owner gates it as before.
When the command needs host data, the owner *parks* it: no acknowledgement is
written, the previous answer stays published, and a job asks the host for
exactly the input it needs:
- FETCH (ConfigSets), before the transaction: a stored document in chunks
  addressed by write key, a store's status, or an import piece's verdict;
- PRESENT (ConfigProvider), before the acknowledgement: the catalog, or the
  header line a current export renders from the transaction's snapshot.

This routine resolves each key through the typed ingress's own route table
into a private staging record. Once the job completes, the parked command
resumes in a scan of its own and runs the unchanged set transaction
(`sets.dispatch_logic`). Its rejection text, export line and catalog are
published before the acknowledgement. An accepted save, delete or import
commit then opens a STORE job, whose receipt ConfigPersist consumes as before.

The host never maps a key to an ordinal and never decides a verdict. A parked
command either runs within PARK_MS of arriving or is refused, so it never runs
after the operator's client has given up on it.
"""
import fraktal_ab_canonical_publication as pub
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_mailbox as mb
import fraktal_ab_sets as sets

WORK = pub.PREFIX + 'HostSetWorkV611'
# The FETCH job window is 1.5 s and the HMI's acknowledgement budget is 2 s.
PARK_MS = 1800
UNAVAILABLE_KEY = 'project.mailbox.refused.host_service_unavailable'
BUSY_KEY = 'project.mailbox.refused.host_service_busy'
KEYS = (UNAVAILABLE_KEY, BUSY_KEY)
# The typed ingress's refusal code for a parked command that could not run.
HOST_UNAVAILABLE = 6
DOCUMENT_KINDS = (mb.LOAD_CONFIG_SET, mb.EXPORT_CONFIG_SET, mb.CREATE_MODEL)
STATUS_KINDS = (mb.SAVE_CONFIG_SET, mb.DELETE_CONFIG_SET)
# Neither names a set: a catalog has none, an import piece learns it from the host.
NAMELESS = (mb.LIST_CONFIG_SETS, mb.IMPORT_CONFIG_SET)
SERVED = sets.SET_KINDS
INTS = ('Parked', 'Hold', 'Ready', 'Resumed', 'Ran', 'Failed', 'Sequence', 'Kind', 'IntValue',
        'BoolValue', 'DurationMs', 'ParkedMs', 'Header', 'Scoped', 'Records', 'Total', 'HasLine',
        'LineIndex', 'Catalog', 'Prior', 'Unresolved', 'Index', 'Record', 'Bad', 'StoreAck', 'StoreResult',
        'Host', 'SavedOwner', 'Verdict', 'VerdictKey', 'KeepFailed', 'Restoring', 'Permits')
TEXTS = dict(User=mb.USER_LENGTH, Name=sets.NAME_MAX, HeaderScope=binding.TEXTS['Scope'],
             HeaderModel=binding.TEXTS['Model'], RejectScope=binding.TEXTS['Scope'],
             RejectKey=binding.KEY_WIDTH, Line=sets.LINE_MAX)


def enabled(app):
    return bool(app.config_sets) and host.enabled(app)


def live(app):
    """LiveDocuments: a host keeps the root's documents and restores them after a download."""
    import fraktal_ab_declaration as decl
    return enabled(app) and decl.live_documents(app)


def work_tag(app): return host._name(app, 'HostSetWork')
def staged_tag(app): return host._name(app, 'HostSetStaged')
def catalog_tag(app): return host._name(app, 'HostSetCatalog')
def empty_tag(app): return host._name(app, 'HostSetEmptyEntry')
def entry_routine(app): return host._name(app, 'HostSetEntry')
def service_routine(app): return host._name(app, 'HostSetService')
def present_routine(app): return host._name(app, 'HostSetPresent')


def augment(app, definitions):
    M, S = pub.Member, pub.string_type
    definitions[WORK] = (*(M(n, 'DINT') for n in INTS), M('Epoch', 'LINT'),
                         *(M(n, S(w)) for n, w in TEXTS.items()))


def tags(app, serialize):
    import fraktal_ab_canonical_config as config
    import fraktal_ab_generate as gen
    return [serialize(work_tag(app), WORK, {}, access='None'),
            gen._structure_tag(staged_tag(app), sets.request_name(), sets.request_members(), 'None'),
            # The catalog arrives one entry per chunk and is published whole.
            serialize(catalog_tag(app), config.SET, [{} for _ in range(sets.MAX_SETS)], array=True, access='None'),
            serialize(empty_tag(app), config.SET, {}, access='None')]


def _kinds(name, kinds):
    return '(' + ' OR '.join(f'({name} = {k})' for k in kinds) + ')'


def _copy(target, source, index):
    """target := source; the caller has bounded source.LEN to target's width."""
    return [f'{target}.LEN := {source}.LEN;', f'FOR {index} := 0 TO {source}.LEN - 1 DO',
            f'{target}.DATA[{index}] := {source}.DATA[{index}];', 'END_FOR;']


def _ascii(source, index, bad):
    """bad := 1 when any byte of source is outside 1..127, the frozen set text."""
    return [f'FOR {index} := 0 TO {source}.LEN - 1 DO',
            f'IF {source}.DATA[{index}] < 1 THEN {bad} := 1; END_IF;', 'END_FOR;']


def _seek(app, source, purpose):
    """Resolve source through the typed ingress's route table (its Find routine)."""
    import fraktal_ab_canonical_commands as commands
    c = commands.work_tag(app)
    return [*commands.copy_string(app, c + '.Seek', source), f'{c}.Purpose := {purpose};',
            f'JSR({commands.routine(app, "Find")},0);']


def prologue(app):
    h = work_tag(app)
    lines = [f'{h}.Hold := 0;', f'{h}.Resumed := 0;', f'{h}.Ran := 0;']
    if not live(app):
        return lines
    import fraktal_ab_access as access
    import fraktal_ab_generate as gen
    w, r = host.work_tag(app), host.work_tag(app) + '.Reply'
    # What a host may open now: restore jobs only while restoring, under the
    # same set-gate predicate the owner applies to the logged-in session.
    return lines + [f'IF {gen.config_restoring(app)} THEN {h}.Restoring := 1; ELSE {h}.Restoring := 0; END_IF;',
                    f'IF {access.permits(app, access.GATES[mb.LOAD_CONFIG_SET])} THEN {h}.Permits := 1; ELSE {h}.Permits := 0; END_IF;',
                    f'IF ({r}.Restoring <> {h}.Restoring) OR ({r}.SessionPermits <> {h}.Permits) THEN',
                    f'{r}.Restoring := {h}.Restoring;', f'{r}.SessionPermits := {h}.Permits;', f'{w}.Dirty := 1;', 'END_IF;']


def _literal(target, text):
    """A short ASCII literal, byte by byte: no text-pool entry for a protocol constant."""
    return [f'{target}.LEN := {len(text)};', *(f'{target}.DATA[{i}] := {ord(ch)};' for i, ch in enumerate(text))]


def _name_bytes(app):
    """Stage Name: a name outside ASCII stages as no name at all, as the broker staged it."""
    q, h = staged_tag(app), work_tag(app)
    i = h + '.Index'
    return [f'{h}.Bad := 0;', *_ascii(h + '.Name', i, h + '.Bad'),
            f'IF {h}.Bad <> 0 THEN {h}.Name.LEN := 0; END_IF;', f'{q}.NameLength := {h}.Name.LEN;',
            f'FOR {i} := 0 TO {sets.NAME_MAX - 1} DO',
            f'IF {i} < {h}.Name.LEN THEN {q}.NameBytes[{i}] := {h}.Name.DATA[{i}]; ELSE {q}.NameBytes[{i}] := 0; END_IF;',
            'END_FOR;']


def _stage_defaults(app):
    """The controller's own staging for a fresh command, as the broker staged it."""
    import fraktal_ab_manifest as mf
    q, h, req = staged_tag(app), work_tag(app), mb.request_tag_name(app)
    i = h + '.Index'
    name = f'{req}.TextValue'
    lines = [f'{q}.SchemaVersion := 1;', f'{q}.Sequence := FRK_{app.name}_HmiLastSequence;',
             f'{q}.Operation := {req}.Kind;', f'{q}.Commit := 0;', f'{q}.Valid := 1;', f'{q}.RootId := 1;',
             f'{q}.SetSchema := 1;', f'{q}.ConfigRev := {mf.config_revision(app)};', f'{q}.Kind := 1;',
             f'{q}.Count := 0;', f'{q}.StoreAck := 0;', f'{q}.StoreResult := 0;',
             f'IF ({req}.Kind = {mb.SAVE_CONFIG_SET}) OR ({req}.Kind = {mb.EXPORT_CURRENT_CONFIG}) THEN {q}.Kind := {req}.IntValue; END_IF;',
             f'IF {req}.Kind = {mb.IMPORT_CONFIG_SET} THEN {q}.Commit := {req}.BoolValue; END_IF;',
             f'{h}.Name.LEN := 0;', f'{h}.Header := 0;', f'{h}.HasLine := 0;',
             # A creation is named by its new model code; a catalog or an import
             # piece by nothing the operator gives; every other set by its name.
             f'IF {req}.Kind = {mb.CREATE_MODEL} THEN', f'{q}.Kind := 0;',
             f'IF ({req}.NameValue.LEN >= 1) AND ({req}.NameValue.LEN <= {sets.NAME_MAX}) THEN',
             *_copy(h + '.Name', req + '.NameValue', i), 'END_IF;',
             f'ELSIF NOT {_kinds(req + ".Kind", NAMELESS)} THEN',
             f'IF ({name}.LEN >= 1) AND ({name}.LEN <= {sets.NAME_MAX}) THEN', *_copy(h + '.Name', name, i), 'END_IF;',
             'END_IF;', *_name_bytes(app),
             f'IF ({h}.Name.LEN = 0) AND NOT {_kinds(req + ".Kind", NAMELESS)} THEN {q}.Valid := 0; END_IF;',
             # A creation that copies a set needs that set's name, too.
             f'IF ({req}.Kind = {mb.CREATE_MODEL}) AND ({req}.BoolValue <> 0) AND '
             f'(({name}.LEN < 1) OR ({name}.LEN > {sets.NAME_MAX})) THEN {q}.Valid := 0; END_IF;']
    return lines


def _snapshot(app):
    """The transaction's snapshot, published with the job a host renders it for."""
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    h, q, s = work_tag(app), staged_tag(app), sets.state_tag(app)
    snapshot = host.work_tag(app) + '.Reply.Snapshot'
    return [f'{snapshot}.Kind := {q}.Kind;', f'{snapshot}.Count := {s}.Count;',
            f'{snapshot}.ModelOrdinal := {s}.ModelOrdinal;', f'{snapshot}.Date := {s}.Date;',
            f'{snapshot}.Clock := {s}.Clock;', f'{snapshot}.Synchronized := {s}.TimeSynchronized;',
            f'{snapshot}.Revision := {mf.config_revision(app)};',
            f'FOR {h}.Index := 0 TO {max(1, len(gen.editable_values(app))) - 1} DO',
            f'{snapshot}.Values[{h}.Index] := {s}.Snapshot[{h}.Index];', 'END_FOR;']


def _park(app, service, phase, job_name=None, job_text=False):
    """Hold the command without an answer and ask the host for its input."""
    h, req, r = work_tag(app), mb.request_tag_name(app), host.work_tag(app) + '.Reply'
    import fraktal_ab_canonical_commands as commands
    lines = [f'{h}.Parked := 1;', f'{h}.Hold := 1;', f'{h}.Ready := 0;', f'{h}.Failed := 0;',
             f'{h}.ParkedMs := 0;', f'{h}.Sequence := {commands.work_tag(app)}.OwnerSequence;',
             *(f'{h}.{n} := {req}.{n};' for n in ('Kind', 'IntValue', 'BoolValue', 'DurationMs')),
             *_copy(h + '.User', req + '.User', h + '.Index'),
             *(f'{h}.{n} := 0;' for n in ('Header', 'Scoped', 'Records', 'Total', 'HasLine', 'LineIndex',
                                          'Catalog', 'Unresolved')),
             *(f'{h}.{n}.LEN := 0;' for n in ('HeaderScope', 'HeaderModel', 'RejectScope', 'RejectKey', 'Line')),
             *host.open_job(app, binding.SERVICES[service], req + '.Kind', phase),
             f'{r}.JobInt := {req}.IntValue;', f'{r}.JobBool := {req}.BoolValue;']
    if job_name:
        lines += _copy(r + '.JobName', job_name, h + '.Index')
    if job_text:
        # An import piece is a transported document fragment; it is wiped with its job.
        lines += _copy(r + '.JobText', req + '.TextValue', h + '.Index')
    return lines


def _store_job(app):
    """After an accepted save, delete or import commit: the host writes, then answers with a receipt."""
    h, r = work_tag(app), host.work_tag(app) + '.Reply'
    stored = (f'(({h}.Kind = {mb.SAVE_CONFIG_SET}) OR ({h}.Kind = {mb.DELETE_CONFIG_SET}) OR '
              f'(({h}.Kind = {mb.IMPORT_CONFIG_SET}) AND ({h}.BoolValue <> 0)))')
    return [f'IF ({mb.response_tag_name(app)}.Accepted <> 0) AND {stored} THEN',
            *host.open_job(app, binding.SERVICES['ConfigSets'], h + '.Kind', binding.STORE, sets.WINDOW_MS),
            *_copy(r + '.JobName', h + '.Name', h + '.Index'),
            f'IF {h}.Kind = {mb.SAVE_CONFIG_SET} THEN', *_snapshot(app), 'END_IF;', 'END_IF;']


def entry(app):
    """The owner's branch for every set kind."""
    h, req, r = work_tag(app), mb.request_tag_name(app), host.work_tag(app) + '.Reply'
    q = staged_tag(app)
    run = [f'{h}.Ran := 1;', f'JSR({sets.routine_name(app)},0);']
    user = f'({req}.User.LEN >= 0) AND ({req}.User.LEN <= {mb.USER_LENGTH})'
    # Only a well-formed command that needs host data parks. Anything else runs
    # now, so the transaction refuses and audits it exactly as before.
    parks = (f'{user} AND (({q}.Valid <> 0) OR {_kinds(req + ".Kind", NAMELESS)}) AND '
             f'(({req}.Kind <> {mb.CREATE_MODEL}) OR ({req}.BoolValue = 1))')
    preempt = []
    if live(app):
        # A keep job yields to an operator's set command; the host keeps it later.
        preempt = [f'IF ({h}.Resumed = 0) AND ({h}.Parked = 0) AND ({r}.JobSequence <> 0) AND '
                   f'({r}.JobService = {binding.SERVICES["LiveDocuments"]}) AND ({r}.JobPhase = {binding.SNAPSHOT_PHASE}) THEN',
                   *host.abandon(app, host.ABANDONED), 'END_IF;']
    return [*preempt, f'IF {h}.Resumed <> 0 THEN',
            # A current export's transaction ran when the command arrived; only
            # the host's rendering was awaited.
            f'IF {h}.Kind = {mb.EXPORT_CURRENT_CONFIG} THEN', *mb._accept(app),
            'ELSE', *run, *_store_job(app), 'END_IF;',
            # One job at a time: a second set command is refused, never queued.
            f'ELSIF ({h}.Parked <> 0) OR ({r}.JobSequence <> 0) THEN', *mb._refuse(app, BUSY_KEY),
            'ELSE', *_stage_defaults(app),
            f'IF {req}.Kind = {mb.EXPORT_CURRENT_CONFIG} THEN', *run,
            f'IF {mb.response_tag_name(app)}.Accepted <> 0 THEN',
            *_park(app, 'ConfigProvider', binding.PRESENT, job_name=h + '.Name'), *_snapshot(app), 'END_IF;',
            f'ELSIF {parks} THEN',
            f'IF {req}.Kind = {mb.LIST_CONFIG_SETS} THEN', *_park(app, 'ConfigProvider', binding.PRESENT),
            f'FOR {h}.Index := 0 TO {sets.MAX_SETS - 1} DO', f'CPS({empty_tag(app)},{catalog_tag(app)}[{h}.Index],1);',
            'END_FOR;',
            f'ELSIF {req}.Kind = {mb.IMPORT_CONFIG_SET} THEN', *_park(app, 'ConfigSets', binding.FETCH, job_text=True),
            # The document the host reads: a creation copies the named source set.
            'ELSE', *_park(app, 'ConfigSets', binding.FETCH, job_name=req + '.TextValue'), 'END_IF;',
            'ELSE', *run, 'END_IF;', 'END_IF;']


def _import_name(app):
    """An import's set name, as the host's parse of its pieces knows it."""
    q, h, b = staged_tag(app), work_tag(app), host.sample_tag(app) + '.' + host.CHUNK_MEMBER
    return [f'IF ({b}.Name.LEN >= 1) AND ({b}.Name.LEN <= {sets.NAME_MAX}) THEN',
            *_copy(h + '.Name', b + '.Name', h + '.Index'), 'END_IF;', *_name_bytes(app),
            f'IF {h}.Name.LEN = 0 THEN {q}.Valid := 0; END_IF;']


def _fetch(app):
    w, s = host.work_tag(app), host.sample_tag(app)
    b, h, q = s + '.' + host.CHUNK_MEMBER, work_tag(app), staged_tag(app)
    invalid = f'{w}.Error := {binding.INVALID};'
    importing = f'({h}.Kind = {mb.IMPORT_CONFIG_SET})'
    return [f'IF {s}.Status <> {binding.OK} THEN',
            # A host that cannot serve answers once, with nothing else; an
            # import names its set. The transaction then refuses and audits
            # the command as invalid.
            f'IF ({s}.Final <> 1) OR (({b}.Kind <> {binding.NONE}) AND NOT ({importing} AND '
            f'({b}.Kind = {binding.HEADER_CHUNK}))) THEN {invalid}', 'ELSE',
            f'IF {b}.Kind = {binding.HEADER_CHUNK} THEN', *_import_name(app), 'END_IF;',
            f'{q}.Valid := 0;', f'{h}.Ready := 1;', *host.complete(app), 'END_IF;',
            'ELSE', *_fetch_chunk(app, [f'{h}.Ready := 1;', *host.complete(app)]), 'END_IF;']


def _fetch_chunk(app, done):
    """One OK document chunk; `done` runs when the document is complete."""
    import fraktal_ab_canonical_commands as commands
    w, s, r = host.work_tag(app), host.sample_tag(app), host.work_tag(app) + '.Reply'
    b, h, q, c = s + '.' + host.CHUNK_MEMBER, work_tag(app), staged_tag(app), commands.work_tag(app)
    i = h + '.Index'
    invalid = f'{w}.Error := {binding.INVALID};'
    document = _kinds(h + '.Kind', DOCUMENT_KINDS)
    importing = f'({h}.Kind = {mb.IMPORT_CONFIG_SET})'
    incomplete = (f'(({importing} OR {document}) AND ({h}.Header = 0)) OR ({document} AND '
                f'(({h}.Records <> {h}.Total) OR (({h}.Kind = {mb.EXPORT_CONFIG_SET}) AND ({h}.HasLine = 0))))')
    lines = [f'CASE {b}.Kind OF',
             f'{binding.HEADER_CHUNK}:',
             f'IF ({r}.NextChunk <> 0) OR NOT ({document} OR {importing}) THEN {invalid}',
             # An import piece: the host's parse names the set and, on commit, counts its records.
             f'ELSIF {importing} THEN', f'{h}.Header := 1;', f'{q}.Count := {b}.Total;', *_import_name(app),
             'ELSE',
             f'{h}.Header := 1;', f'{h}.Total := {b}.Total;', f'{q}.Count := {b}.Total;',
             *(f'{q}.{t} := {b}.{f};' for t, f in (('SetSchema', 'SetSchema'), ('ConfigRev', 'ConfigRev'),
                                                    ('Kind', 'RecordKind'))),
             *_copy(h + '.HeaderScope', b + '.Scope', i), *_copy(h + '.HeaderModel', b + '.Model', i),
             # The stored set answers the one named; its root must be this one.
             f'IF {b}.Name.LEN <> {r}.JobName.LEN THEN {q}.Valid := 0;', 'ELSE',
             f'FOR {i} := 0 TO {b}.Name.LEN - 1 DO',
             f'IF {b}.Name.DATA[{i}] <> {r}.JobName.DATA[{i}] THEN {q}.Valid := 0; END_IF;', 'END_FOR;', 'END_IF;',
             f'IF ({h}.Kind = {mb.CREATE_MODEL}) AND ({b}.RecordKind <> 0) THEN {q}.Valid := 0; END_IF;',
             *_seek(app, b + '.Scope', 4), f'IF {c}.Matches = 1 THEN {q}.RootId := 1; ELSE {q}.RootId := 0; END_IF;',
             'END_IF;',
             f'{binding.RECORDS}:',
             f'IF NOT {document} OR ({h}.Header = 0) OR ({b}.Total <> {h}.Total) OR ({b}.Count < 1) OR '
             f'({b}.Count > {host.RECORDS_PER_CHUNK}) OR ({h}.Records + {b}.Count > {h}.Total) THEN {invalid}',
             'ELSE', *_seek(app, b + '.Scope', 4), f'{h}.Scoped := {c}.Matches;',
             f'FOR {i} := 0 TO {b}.Count - 1 DO', f'{h}.Record := {h}.Records + {i};', f'{c}.Found := 0;',
             # A record outside this root resolves to no ordinal; the transaction refuses it.
             f'IF {h}.Scoped = 1 THEN', *_seek(app, f'{b}.Keys[{i}]', 2), 'END_IF;',
             f'{q}.Ordinal[{h}.Record] := {c}.Found;',
             *(f'{q}.{t}[{h}.Record] := {b}.{f}[{i}];' for t, f in
               (('Revision', 'Revisions'), ('RecordKind', 'RecordKinds'), ('ValueType', 'ValueTypes'),
                ('Value', 'Values'))),
             # The first unresolved record's text is the rejection a reader can show.
             f'IF ({c}.Found = 0) AND ({h}.Unresolved = 0) THEN', f'{h}.Unresolved := {h}.Record + 1;',
             # Inside the record loop: copy with the typed ingress's own index.
             *_copy(h + '.RejectScope', b + '.Scope', c + '.Index'),
             *_copy(h + '.RejectKey', f'{b}.Keys[{i}]', c + '.Index'),
             'END_IF;', 'END_FOR;',
             f'{h}.Records := {h}.Records + {b}.Count;', 'END_IF;',
             f'{binding.TEXT}:',
             f'IF ({h}.Kind <> {mb.EXPORT_CONFIG_SET}) OR ({h}.Header = 0) OR ({h}.Records <> {h}.Total) OR '
             f'({h}.HasLine <> 0) OR ({b}.Count <> {h}.IntValue) OR ({b}.Count > {h}.Total) OR '
             f'({b}.Total <> {h}.Total) THEN {invalid}',
             'ELSE', *_copy(h + '.Line', b + '.Line', i), f'{h}.LineIndex := {b}.Count;', f'{h}.HasLine := 1;',
             'END_IF;',
             f'{binding.NONE}:', f'IF {document} OR {importing} THEN {invalid} END_IF;',
             'ELSE', invalid, 'END_CASE;',
             f'IF {w}.Error = 0 THEN',
             f'IF {s}.Final = 0 THEN', *host.advance(app),
             f'ELSIF {incomplete} THEN', invalid,
             'ELSE', *done, 'END_IF;', 'END_IF;']
    return lines


def _present(app):
    """PRESENT: the catalog for a list, or a current export's rendered header line."""
    w, s, r = host.work_tag(app), host.sample_tag(app), host.work_tag(app) + '.Reply'
    b, h, q = s + '.' + host.CHUNK_MEMBER, work_tag(app), staged_tag(app)
    entry = f'{catalog_tag(app)}[{r}.NextChunk]'
    i, j, bad = h + '.Index', h + '.Prior', h + '.Bad'
    invalid = f'{w}.Error := {binding.INVALID};'
    listing = f'({h}.Kind = {mb.LIST_CONFIG_SETS})'
    # Every bound a reader of the published catalog relies on, before any copy.
    malformed = (f'({b}.Total < 1) OR ({b}.Total > {sets.MAX_SETS}) OR ({r}.NextChunk >= {b}.Total) OR '
                 f'(({r}.NextChunk > 0) AND ({b}.Total <> {h}.Total)) OR '
                 f'({b}.SetSchema < 1) OR ({b}.SetSchema > 65535) OR ({b}.RecordKind < 0) OR ({b}.RecordKind > 2) OR '
                 f'({b}.Synchronized < 0) OR ({b}.Synchronized > 1) OR ({b}.Name.LEN < 1) OR ({b}.Scope.LEN < 1) OR '
                 f'({bad} <> 0)')
    lines = [f'IF {s}.Status <> {binding.OK} THEN',
             f'IF ({s}.Final <> 1) OR ({b}.Kind <> {binding.NONE}) THEN {invalid}', 'ELSE',
             # An unreadable store refuses the list in its transaction; a
             # current export already accepted, so its rendering is unavailable.
             f'IF {listing} THEN {q}.Valid := 0; ELSE {h}.Failed := 1; END_IF;',
             f'{h}.Ready := 1;', *host.complete(app), 'END_IF;',
             f'ELSIF {listing} THEN', f'CASE {b}.Kind OF',
             f'{binding.NONE}:', f'IF ({r}.NextChunk <> 0) OR ({s}.Final <> 1) THEN {invalid} END_IF;',
             f'{binding.CATALOG}:', f'{bad} := 0;',
             *_ascii(b + '.Name', i, bad), *_ascii(b + '.Scope', i, bad), *_ascii(b + '.Model', i, bad),
             # A set name appears once in a catalog.
             f'IF {r}.NextChunk <= {sets.MAX_SETS} THEN', f'FOR {j} := 0 TO {r}.NextChunk - 1 DO',
             f'IF {catalog_tag(app)}[{j}].SetName.LEN = {b}.Name.LEN THEN', f'{h}.Record := 1;',
             f'FOR {i} := 0 TO {b}.Name.LEN - 1 DO',
             f'IF {catalog_tag(app)}[{j}].SetName.DATA[{i}] <> {b}.Name.DATA[{i}] THEN {h}.Record := 0; END_IF;',
             'END_FOR;', f'IF {h}.Record <> 0 THEN {bad} := 1; END_IF;', 'END_IF;', 'END_FOR;', 'END_IF;',
             f'IF {malformed} THEN {invalid}', 'ELSE',
             f'{entry}.Used := 1;', *_copy(entry + '.SetName', b + '.Name', i),
             *_copy(entry + '.RootIdentity', b + '.Scope', i), *_copy(entry + '.ModelCode', b + '.Model', i),
             *(f'{entry}.{t} := {b}.{f};' for t, f in (('SetSchema', 'SetSchema'), ('ConfigRev', 'ConfigRev'),
                                                        ('Kind', 'RecordKind'), ('RecordCount', 'Count'))),
             f'{entry}.TimeSynchronized := {b}.Synchronized <> 0;',
             # Unsigned seconds, widened before the scale, as the provider does.
             f'{h}.Epoch := {b}.CreatedSeconds;', f'IF {h}.Epoch < 0 THEN',
             f'{h}.Epoch := {h}.Epoch + 2147483647;', f'{h}.Epoch := {h}.Epoch + 2147483647 + 2;', 'END_IF;',
             f'{h}.Epoch := {h}.Epoch * 1000000000;', f'{entry}.CreatedAt := {h}.Epoch;',
             f'{h}.Total := {b}.Total;', f'{h}.Catalog := {r}.NextChunk + 1;', 'END_IF;',
             'ELSE', invalid, 'END_CASE;',
             f'IF {w}.Error = 0 THEN',
             f'IF {s}.Final = 0 THEN', *host.advance(app),
             f'ELSIF ({b}.Kind = {binding.NONE}) OR ({h}.Catalog = {h}.Total) THEN', f'{h}.Ready := 1;',
             *host.complete(app), 'ELSE', invalid, 'END_IF;', 'END_IF;',
             # A current export: one header line, rendered from the published snapshot.
             f'ELSIF ({b}.Kind <> {binding.TEXT}) OR ({s}.Final <> 1) OR ({b}.Count <> 0) OR '
             f'({b}.Total <> {sets.state_tag(app)}.Count) THEN {invalid}',
             'ELSE', *_copy(h + '.Line', b + '.Line', i), f'{h}.LineIndex := 0;', f'{h}.Total := {b}.Total;',
             f'{h}.HasLine := 1;', f'{h}.Ready := 1;', *host.complete(app), 'END_IF;']
    return lines


def _reset(app):
    h = work_tag(app)
    return [*(f'{h}.{n} := 0;' for n in ('Header', 'Scoped', 'Records', 'Total', 'HasLine', 'LineIndex',
                                         'Catalog', 'Unresolved')),
            *(f'{h}.{n}.LEN := 0;' for n in ('HeaderScope', 'HeaderModel', 'RejectScope', 'RejectKey', 'Line'))]


def _keep_open(app):
    """A host asks for one document's current values: station, line or model n."""
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as mf
    import fraktal_ab_models as models
    w, s, r = host.work_tag(app), host.sample_tag(app), host.work_tag(app) + '.Reply'
    b, snapshot = s + '.' + host.CHUNK_MEMBER, r + '.Snapshot'
    groups = {kind: [(o, rec, m) for o, rec, m in gen.editable_values(app) if sets.config_kind(rec) == kind]
              for kind in (0, 1, 2)}
    which = [f'(({b}.RecordKind = 0) AND {models.ordinal_guard(app, b + ".Count")})' if kind == 0 else
             f'({b}.RecordKind = {kind})' for kind, values in groups.items() if values]
    # Documents are never captured while restoring: a fresh image holds defaults.
    lines = [f'IF {gen.config_restoring(app)} THEN {w}.Error := {binding.BUSY};',
             f'ELSIF ({s}.Chunk <> 0) OR ({s}.Final <> 0) OR ({b}.Kind <> {binding.NONE}) OR NOT ({" OR ".join(which)}) THEN',
             f'{w}.Error := {binding.INVALID};', 'ELSE',
             *host.open_job(app, binding.SERVICES['LiveDocuments'], s + '.Operation', binding.SNAPSHOT_PHASE, sets.WINDOW_MS),
             *host.advance(app),
             f'{snapshot}.Kind := {b}.RecordKind;', f'{snapshot}.ModelOrdinal := 0;',
             f'{snapshot}.Date := FRK_{app.name}_NowDate;', f'{snapshot}.Clock := FRK_{app.name}_NowTime;',
             f'{snapshot}.Synchronized := {gen.health_probe_tag(app)}.TimeIsSynchronized;',
             f'{snapshot}.Revision := {mf.config_revision(app)};', f'CASE {b}.RecordKind OF']
    for kind, values in groups.items():
        if not values:
            continue
        lines += [f'{kind}:', f'{snapshot}.Count := {len(values)};']
        if kind == 0:
            lines += [f'{snapshot}.ModelOrdinal := {b}.Count;']
            lines += [f'{snapshot}.Values[{o - 1}] := {gen.model_cfg_tag(app)}[{b}.Count - 1].{m.name};'
                      for o, _rec, m in values]
        else:
            if kind == 1:
                lines += [f'{snapshot}.ModelOrdinal := FRK_{app.name}_Unit.ModelOrdinal;']
            lines += [f'{snapshot}.Values[{o - 1}] := {rec.name}Tag.{m.name};' for o, rec, m in values]
    return lines + ['ELSE', '(* Unreachable: the document was validated above. *)', 'END_CASE;', 'END_IF;']


def _restore_open(app):
    """A host opens one restore document while the controller restores, under the set gate."""
    import fraktal_ab_access as access
    import fraktal_ab_generate as gen
    import fraktal_ab_live as live_documents
    import fraktal_ab_manifest as mf
    w, s, r = host.work_tag(app), host.sample_tag(app), host.work_tag(app) + '.Reply'
    b, h, q = s + '.' + host.CHUNK_MEMBER, work_tag(app), staged_tag(app)
    creating = f'({s}.Operation = {mb.CREATE_MODEL})'
    return [f'IF NOT {gen.config_restoring(app)} THEN {w}.Error := {binding.NOT_RESTORING};',
            f'ELSIF NOT ({access.permits(app, access.GATES[mb.LOAD_CONFIG_SET])}) THEN {w}.Error := {binding.ACCESS};',
            f'ELSIF ({s}.Chunk <> 0) OR ({b}.Kind <> {binding.HEADER_CHUNK}) OR '
            f'(({s}.Status <> {binding.OK}) AND ({s}.Status <> {binding.LOST})) THEN {w}.Error := {binding.INVALID};',
            'ELSE',
            # Parked like an operator command, but no operator waits on it: it
            # resumes as a silent owner pass whose verdict returns on the job.
            f'{h}.Host := 1;', f'{h}.Parked := 1;', f'{h}.Ready := 0;', f'{h}.Failed := 0;', f'{h}.ParkedMs := 0;',
            f'{h}.Sequence := 0;', f'{h}.Kind := {s}.Operation;', f'{h}.IntValue := 0;', f'{h}.BoolValue := 0;',
            f'IF {creating} THEN {h}.BoolValue := 1; END_IF;', f'{h}.DurationMs := {s}.Argument;', f'{h}.User.LEN := 0;',
            *_reset(app),
            *host.open_job(app, binding.SERVICES['LiveDocuments'], s + '.Operation', binding.RESTORE),
            f'{r}.JobInt := {s}.Argument;', *_literal(r + '.JobName', live_documents.LIVE_NAME),
            f'{q}.SchemaVersion := 1;', f'{q}.Sequence := 0;', f'{q}.Operation := {s}.Operation;', f'{q}.Commit := 0;',
            f'{q}.Valid := 1;', f'{q}.RootId := 1;', f'{q}.SetSchema := 1;', f'{q}.ConfigRev := {mf.config_revision(app)};',
            f'{q}.Kind := 1;', f'{q}.Count := 0;', f'{q}.StoreAck := 0;',
            # The station document answers the restore: LOST says a document was lost.
            f'IF {s}.Status = {binding.LOST} THEN {q}.StoreResult := 2; ELSE {q}.StoreResult := 1; END_IF;',
            # A model the catalog no longer has is created under its own code.
            f'IF {creating} THEN', f'{q}.Kind := 0;', f'{h}.Name.LEN := 0;',
            f'IF ({b}.Model.LEN >= 1) AND ({b}.Model.LEN <= {sets.NAME_MAX}) THEN',
            *_copy(h + '.Name', b + '.Model', h + '.Index'),
            'END_IF;', 'ELSE', *_literal(h + '.Name', live_documents.LIVE_NAME), 'END_IF;', *_name_bytes(app),
            f'IF {h}.Name.LEN = 0 THEN {q}.Valid := 0; END_IF;',
            *_fetch_chunk(app, _restored(app)), 'END_IF;']


def _restored(app):
    """A complete restore document: resume; the job stays open for its verdict."""
    return [f'{work_tag(app)}.Ready := 1;', f'{host.work_tag(app)}.Dirty := 1;']


def service(app):
    """One accepted chunk; runs between host.ingress and host.finish."""
    w, s, r = host.work_tag(app), host.sample_tag(app), host.work_tag(app) + '.Reply'
    b, h = s + '.' + host.CHUNK_MEMBER, work_tag(app)
    sets_service, provider = binding.SERVICES['ConfigSets'], binding.SERVICES['ConfigProvider']
    documents = binding.SERVICES['LiveDocuments']
    if live(app):
        # Only an operator command opens a set job; a host opens only its own
        # live-document jobs, and never while another command waits.
        opened = [f'IF {s}.JobSequence = 0 THEN',
                  f'IF {h}.Parked <> 0 THEN {w}.Error := {binding.BUSY};',
                  f'ELSIF {s}.Service <> {documents} THEN {w}.Error := {binding.NO_JOB};',
                  f'ELSIF {s}.Operation = {mb.EXPORT_CURRENT_CONFIG} THEN', *_keep_open(app),
                  f'ELSIF ({s}.Operation = {mb.LOAD_CONFIG_SET}) OR ({s}.Operation = {mb.CREATE_MODEL}) THEN',
                  *_restore_open(app), f'ELSE {w}.Error := {binding.INVALID};', 'END_IF;',
                  f'ELSIF ({r}.JobService = {documents}) AND ({r}.JobPhase = {binding.RESTORE}) AND ({h}.Ready = 0) THEN',
                  f'IF {s}.Status <> {binding.OK} THEN {w}.Error := {binding.INVALID};', 'ELSE',
                  *_fetch_chunk(app, _restored(app)), 'END_IF;',
                  # The host has read the transaction's verdict, or written its keep.
                  f'ELSIF ({r}.JobService = {documents}) AND (({r}.JobPhase = {binding.STORE}) OR '
                  f'({r}.JobPhase = {binding.SNAPSHOT_PHASE})) THEN',
                  f'IF ({s}.Final <> 1) OR ({b}.Kind <> {binding.NONE}) THEN {w}.Error := {binding.INVALID};', 'ELSE',
                  f'IF {r}.JobPhase = {binding.SNAPSHOT_PHASE} THEN',
                  f'IF {s}.Status = {binding.OK} THEN {h}.KeepFailed := 0; ELSE {h}.KeepFailed := 1; END_IF;', 'END_IF;',
                  *host.complete(app), 'END_IF;']
    else:
        # Only an operator command opens a set job; a host cannot.
        opened = [f'IF {s}.JobSequence = 0 THEN {w}.Error := {binding.NO_JOB};']
    return [f'IF {w}.Accept <> 0 THEN', *opened,
            f'ELSIF ({r}.JobService = {sets_service}) AND ({r}.JobPhase = {binding.FETCH}) THEN', *_fetch(app),
            f'ELSIF ({r}.JobService = {provider}) AND ({r}.JobPhase = {binding.PRESENT}) THEN', *_present(app),
            f'ELSIF ({r}.JobService = {sets_service}) AND ({r}.JobPhase = {binding.STORE}) THEN',
            f'IF ({s}.Final <> 1) OR ({b}.Kind <> {binding.NONE}) THEN {w}.Error := {binding.INVALID};', 'ELSE',
            f'IF {s}.Status = {binding.OK} THEN {h}.StoreResult := 1; ELSE {h}.StoreResult := 2; END_IF;',
            f'{h}.StoreAck := {sets.state_tag(app)}.PendingSequence;', *host.complete(app), 'END_IF;',
            f'ELSE {w}.Error := {binding.ORDER};', 'END_IF;', 'END_IF;']


def outcome(app):
    """After host.finish: a parked command whose host failed or ran late resumes as a refusal."""
    w, r, h = host.work_tag(app), host.work_tag(app) + '.Reply', work_tag(app)
    return [f'IF {h}.Parked <> 0 THEN', f'{h}.ParkedMs := {h}.ParkedMs + {app.task_period_ms};',
            f'IF {h}.Ready = 0 THEN',
            f'IF ({w}.Outcome = {host.ABANDONED}) OR ({w}.Outcome = {host.TIMED_OUT}) THEN {h}.Ready := 1; {h}.Failed := 1; END_IF;',
            f'IF ({h}.Ready = 0) AND ({h}.ParkedMs >= {PARK_MS}) THEN',
            f'IF {r}.JobSequence <> 0 THEN', *host.abandon(app, host.ABANDONED), 'END_IF;',
            f'{h}.Ready := 1;', f'{h}.Failed := 1;', 'END_IF;', 'END_IF;', 'END_IF;']


def resume(app):
    """After the typed ingress: re-enter the owner in a scan with no new command."""
    import fraktal_ab_canonical_commands as commands
    h, c, req = work_tag(app), commands.work_tag(app), mb.request_tag_name(app)
    late = f'({h}.Failed <> 0) OR ({h}.ParkedMs >= {PARK_MS})'
    arguments = [f'{c}.LegacyAck := {mb.response_tag_name(app)}.AckSequence;',
                 *(f'{req}.{n} := {h}.{n};' for n in ('Kind', 'IntValue', 'BoolValue', 'DurationMs')),
                 *_copy(req + '.User', h + '.User', h + '.Index')]
    operator = [f'{h}.Resumed := 1;', f'{c}.Pending := 1;', f'{c}.NewCore := 1;', f'{c}.Error := 0;',
                f'{c}.OwnerSequence := {h}.Sequence;', f'{c}.CoreSeen := {h}.Sequence;', *arguments,
                f'IF {late} THEN {c}.Error := {HOST_UNAVAILABLE}; END_IF;']
    if not live(app):
        return [f'IF ({h}.Ready <> 0) AND ({c}.Pending = 0) THEN', f'{h}.Ready := 0;', f'{h}.Parked := 0;',
                *operator, 'END_IF;']
    # A host's restore document runs as a silent owner pass: no operator
    # sequence, acknowledgement or answer moves, and its verdict returns on
    # the job. A failed one runs nothing; its host saw its job end.
    return [f'IF ({h}.Ready <> 0) AND ({c}.Pending = 0) THEN', f'{h}.Ready := 0;', f'{h}.Parked := 0;',
            f'IF {h}.Host = 0 THEN', *operator,
            f'ELSIF {late} THEN {h}.Host := 0;',
            'ELSE', f'{h}.Resumed := 1;', f'{h}.Hold := 1;', f'{h}.SavedOwner := {c}.OwnerSequence;',
            f'{c}.Pending := 1;', f'{c}.NewCore := 0;', f'{c}.Error := 0;', f'{c}.OwnerSequence := 0;',
            *arguments, 'END_IF;', 'END_IF;']


def present(app):
    """Rejection text, export line and catalog, published before the acknowledgement."""
    import fraktal_ab_canonical_commands as commands
    import fraktal_ab_canonical_text as text
    h, q, s, req = work_tag(app), staged_tag(app), sets.state_tag(app), mb.request_tag_name(app)
    p, root, c = app.name + '.ConfigPersist', app.name, commands.work_tag(app)
    accepted = f'{mb.response_tag_name(app)}.Accepted'
    scope, key, t = p + '.LastRejectScope', p + '.LastRejectKey', commands.route_tag(app)
    i = h + '.Index'
    lines = [f'{scope}.LEN := 0;', f'{key}.LEN := 0;',
             f'IF {_kinds(req + ".Kind", (mb.EXPORT_CONFIG_SET, mb.EXPORT_CURRENT_CONFIG))} THEN',
             f'{root}.ConfigSetDocument.LEN := 0;', f'{root}.ConfigSetDocumentLine := -1;',
             f'{root}.ConfigSetDocumentLines := 0;',
             f'IF ({accepted} <> 0) AND ({h}.HasLine <> 0) AND (({h}.Ran <> 0) OR ({h}.Resumed <> 0)) THEN',
             *_copy(root + '.ConfigSetDocument', h + '.Line', i),
             f'{root}.ConfigSetDocumentLine := {h}.LineIndex;', f'{root}.ConfigSetDocumentLines := {h}.Total;',
             'END_IF;', 'END_IF;',
             # An accepted list replaces the whole catalog in this scan, never a part of it.
             f'IF ({req}.Kind = {mb.LIST_CONFIG_SETS}) AND ({accepted} <> 0) AND ({h}.Ran <> 0) THEN',
             f'{root}.ConfigSetCount := {h}.Catalog;', f'FOR {i} := 0 TO {sets.MAX_SETS - 1} DO',
             f'CPS({catalog_tag(app)}[{i}],{root}.ConfigSets[{i}],1);', 'END_FOR;', 'END_IF;',
             f'IF {accepted} = 0 THEN',
             f'IF ({h}.Ran <> 0) AND ({h}.Header <> 0) AND {_kinds(req + ".Kind", (mb.LOAD_CONFIG_SET, mb.EXPORT_CONFIG_SET))} THEN',
             f'{h}.Record := {s}.RejectIndex;',
             f'IF ({h}.Record >= 1) AND ({h}.Record <= {q}.Count) THEN',
             f'IF {q}.Ordinal[{h}.Record - 1] <> 0 THEN', *text.put_text(app, scope, app.name, 80),
             f'FOR {c}.Cursor := 0 TO {len(commands.rows(app)) - 1} DO',
             f'IF ({t}[{c}.Cursor].Purpose = 2) AND ({t}[{c}.Cursor].Value = {q}.Ordinal[{h}.Record - 1]) AND '
             f'({t}[{c}.Cursor].Length <= {binding.KEY_WIDTH}) THEN',
             *text.put(app, key, f'{t}[{c}.Cursor].Offset', f'{t}[{c}.Cursor].Length'), 'END_IF;', 'END_FOR;',
             'ELSE', *_copy(scope, h + '.RejectScope', i), *_copy(key, h + '.RejectKey', i), 'END_IF;',
             f'ELSIF {q}.RootId = 0 THEN', *_copy(scope, h + '.HeaderScope', i),
             f'ELSIF {q}.Kind = 0 THEN', *_copy(scope, h + '.HeaderModel', i),
             'ELSE', *_copy(key, h + '.Name', i), 'END_IF;',
             # The staged name: empty when it was not a valid set name, as before.
             f'ELSIF ({h}.Ran <> 0) OR ({h}.Resumed <> 0) THEN', *_copy(key, h + '.Name', i),
             # Refused before any staging (access, busy): the name the operator
             # gave. An import piece names no set.
             f'ELSIF {req}.Kind = {mb.CREATE_MODEL} THEN',
             f'IF ({req}.NameValue.LEN >= 1) AND ({req}.NameValue.LEN <= {sets.NAME_MAX}) THEN',
             *_copy(key, req + '.NameValue', i), 'END_IF;',
             f'ELSIF ({req}.Kind <> {mb.IMPORT_CONFIG_SET}) AND ({req}.TextValue.LEN >= 1) AND '
             f'({req}.TextValue.LEN <= {sets.NAME_MAX}) THEN',
             *_copy(key, req + '.TextValue', i), 'END_IF;', 'END_IF;']
    return lines


def after_owner(app):
    """Presentation for every acknowledged set command; a parked one has none yet."""
    if not enabled(app):
        return []
    req = mb.request_tag_name(app)
    import fraktal_ab_canonical_commands as commands
    lines = [f'IF ({commands.work_tag(app)}.Pending <> 0) AND ({work_tag(app)}.Hold = 0) AND '
             f'{_kinds(req + ".Kind", sets.SET_KINDS)} THEN', f'JSR({present_routine(app)},0);', 'END_IF;']
    if not live(app):
        return lines
    h, c, r = work_tag(app), commands.work_tag(app), host.work_tag(app) + '.Reply'
    # After a silent pass: the operator's sequence returns, and the verdict
    # goes to the host, whose receipt then closes the job.
    return lines + [f'IF ({h}.Host <> 0) AND ({h}.Resumed <> 0) THEN',
                    f'{c}.OwnerSequence := {h}.SavedOwner;', f'FRK_{app.name}_HmiLastSequence := {h}.SavedOwner;',
                    f'IF ({r}.JobSequence <> 0) AND ({r}.JobService = {binding.SERVICES["LiveDocuments"]}) THEN',
                    f'{r}.JobBool := {h}.Verdict;', f'{r}.JobInt := {h}.VerdictKey;',
                    *host.next_phase(app, binding.SERVICES['LiveDocuments'], binding.STORE), 'END_IF;',
                    f'{h}.Host := 0;', 'END_IF;']


def routines(app):
    if not enabled(app):
        return []
    return [(entry_routine(app), entry(app)), (service_routine(app), service(app)),
            (present_routine(app), present(app))]

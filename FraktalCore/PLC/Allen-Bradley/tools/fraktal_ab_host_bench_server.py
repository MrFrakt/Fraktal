"""Test apparatus: the emitted V6.11 controller on the bench, served over stdio.

`python fraktal_ab_host_bench_server.py sets|live` builds the bench for the
press (live documents off, or as declared), prints `{"ready": true}` and then
answers one JSON request per line. The Dart host adapter's tests drive it as
their controller: the published reply in, request and commit out, operator
commands, scans and read-back for assertions. It also renders the engineering
documents a test compares the adapter's output with.

For the real CIP port it also acts as the wire. `capture` returns the
namespace the port discovers: synthetic Templates, which are not a measured
Logix layout, and the emitted manifest, normalized. `read_tag` answers a
symbolic path with the type header and the value's bytes. `write_tag`
decodes the request into its tag, or stores the commit and scans.

Offline only: it opens no connection, and it is never part of a deployed
station.
"""
import dataclasses
import json
import struct
import sys

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_reader as reader
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s4b_owner_demo as demo
import fraktal_ab_host_service_binding as binding
import fraktal_ab_host_services as host
import fraktal_ab_live as live
import fraktal_ab_mailbox as mb
import fraktal_ab_models as models
import fraktal_ab_sets as sets
import test_fraktal_ab_host_sets as bench_sets
from test_fraktal_ab_host_sets import Context, Station


def _signed(value):
    return value - 0x100000000 if value > 0x7fffffff else value


# Synthetic types for the tables the port reads; the root's carries only the
# members the port reads.
CAPABILITY, KEY, ROOT = 'FRK_T_BenchCapability', 'FRK_T_BenchKey', 'FRK_T_BenchRoot'


def encode_record(objects, sizes, handle, value):
    """Pack plain values (text as str) into a synthetic Template's bytes."""
    raw = bytearray(sizes[handle])

    def put(base, rows, value):
        for row in rows:
            if row['name'] not in value:
                continue
            items = value[row['name']] if row['array'] else [value[row['name']]]
            for k, item in enumerate(items):
                if row['struct']:
                    child = reader.member_table(objects[row['handle']])
                    at = base + row['offset'] + k * sizes[row['handle']]
                    if reader.is_string(child) is not None:
                        length, data = child
                        encoded = item.encode('latin-1')
                        struct.pack_into('<i', raw, at + length['offset'], len(encoded))
                        raw[at + data['offset']:at + data['offset'] + len(encoded)] = encoded
                    else:
                        put(at, child, item)
                else:
                    struct.pack_into('<i', raw, base + row['offset'] + 4 * k, item)
    put(0, reader.member_table(objects[handle]), value)
    return bytes(raw)


class Server:
    def __init__(self, variant):
        app = (bench_sets.application() if variant == 'sets'
               else dataclasses.replace(demo.application(), canonical_host_services=True))
        self.ctx = Context(app)
        self.app = app
        self.s = Station(self.ctx)
        self._layout = None

    def text_only(self, value):
        """Bench values with text as str and every other leaf (BOOL included) as stored."""
        if isinstance(value, dict) and set(value) == {'LEN', 'DATA'}:
            return self.s.bench.text(value)
        if isinstance(value, dict):
            return {k: self.text_only(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.text_only(v) for v in value]
        return value

    def plain(self, value):
        if isinstance(value, dict) and set(value) == {'LEN', 'DATA'}:
            return self.s.bench.text(value)
        if isinstance(value, dict):
            return {k: self.plain(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.plain(v) for v in value]
        return int(value) if isinstance(value, bool) else value

    # -- the port -------------------------------------------------------------
    def reply(self):
        return self.plain(self.s.host_reply)

    def submit(self, envelope, body):
        sequence = binding.next_sequence(self.reply())
        request = self.s.t[host.request_tag(self.app)]
        request.update(SchemaVersion=1, StagedSequence=_signed(sequence),
                       ManifestRevision=self.s.t[pub.header_tag(self.app)]['ConfigRevision'], **envelope)
        complete = binding.complete(body, host.RECORDS_PER_CHUNK)
        target = request['Body']
        for name, value in complete.items():
            if name == 'Keys':
                for i, key in enumerate(value):
                    self.s.bench.put(target['Keys'][i], key)
            elif isinstance(value, str):
                self.s.bench.put(target[name], value)
            elif isinstance(value, list):
                target[name][:] = value
            else:
                target[name] = value
        self.s.t[host.commit_tag(self.app)] = _signed(sequence)
        self.s.scan()
        answer = self.reply()
        return answer if answer['AckSequence'] & 0xffffffff == sequence else None

    def facts(self):
        t, root = self.s.t, self.s.t[self.app.name]
        keys = {r['NumericKey']: self.s.bench.text(r['PortableKey']) for r in t[f'FRK_{self.app.name}_MfLocalization']}
        return dict(root=self.app.name,
                    revision=int(self.s.bench.text(t[pub.header_tag(self.app)]['LegacyContentHash'])[:6], 16),
                    capabilities=[[r['CapabilityIndex'], keys[r['WriteKeyKey']], r['ConfigKind'], r['ValueType']]
                                  for r in t[f'FRK_{self.app.name}_MfWriteCapabilities'] if r['CapabilityIndex']],
                    codes=[self.s.bench.text(m['ModelCode']) for m in root['AvailableModels'][:root['AvailableModelCount']]],
                    capacity=root['ModelCapacity'])

    def key(self, numeric):
        return next((self.s.bench.text(r['PortableKey']) for r in self.s.t[f'FRK_{self.app.name}_MfLocalization']
                     if r['NumericKey'] == numeric), '')

    # -- the CIP wire: the port's own transport, over synthetic Templates ------------
    def layout(self):
        """What the port discovers: Templates, symbols and the emitted manifest, normalized."""
        if self._layout is None:
            from test_fraktal_ab_host_service_binding import pack, physical
            app, t, M = self.app, self.s.t, pub.Member
            definitions = pub.schema(app)
            host.augment_schema(app, definitions)
            manifest = wire.normalize(physical(definitions, pub.header_type(app),
                                               self.text_only(t[pub.header_tag(app)])))
            command = next(c for c in manifest['commandBindings'] if c['RootSymbol'] == app.name)
            for kind, symbol in ((CAPABILITY, command['CapabilitiesSymbol']), (KEY, command['KeysSymbol'])):
                definitions[kind] = tuple(M(n, pub.string_type(len(v['DATA'])) if isinstance(v, dict) else 'DINT')
                                          for n, v in t[symbol][0].items())
            model = next(k for k, members in definitions.items() if [m.name for m in members] == ['ModelCode'])
            definitions[ROOT] = (M('AvailableModelCount', 'DINT'),
                                 M('AvailableModels', model, count=len(t[app.name]['AvailableModels'])),
                                 M('ModelCapacity', 'DINT'))
            templates, handles = pack(definitions, (host.REQUEST, host.REPLY, CAPABILITY, KEY, ROOT))
            ingress = next(r for r in manifest['hostServiceBindings'] if r['RootSymbol'] == app.name)
            if ingress['CommitSymbol'] != host.commit_tag(app):
                raise ValueError('the bench commit tag differs from the manifest row')
            objects, sizes = reader.template_objects(templates)
            self._layout = dict(
                definitions=definitions, templates=templates, objects=objects, sizes=sizes, manifest=manifest,
                byName={entry['name']: entry for entry in templates},
                kinds={ingress['RequestSymbol']: host.REQUEST, ingress['ReplySymbol']: host.REPLY,
                       command['CapabilitiesSymbol']: CAPABILITY, command['KeysSymbol']: KEY, app.name: ROOT},
                request=ingress['RequestSymbol'], commit=ingress['CommitSymbol'],
                symbols=[dict(name=ingress['RequestSymbol'], handle=handles[host.REQUEST], arrayRank=0),
                         dict(name=ingress['ReplySymbol'], handle=handles[host.REPLY], arrayRank=0),
                         dict(name=ingress['CommitSymbol'], atomic=0xc4, arrayRank=0),
                         dict(name=command['CapabilitiesSymbol'], handle=handles[CAPABILITY], arrayRank=1),
                         dict(name=command['KeysSymbol'], handle=handles[KEY], arrayRank=1),
                         dict(name=app.name, handle=handles[ROOT], arrayRank=0)])
        return self._layout

    def read_tag(self, segments):
        """A Read Tag answer for a symbolic path: the type header, then the value's bytes."""
        layout = self.layout()
        (name, index), *rest = segments
        kind, value = layout['kinds'][name], self.s.t[name]
        if index is not None:
            value = value[index]
        for member, index in rest:
            row = next(m for m in layout['definitions'][kind] if m.name == member)
            kind, value = row.kind, value[member]
            if index is not None:
                value = value[index]
        if kind == 'DINT':
            return struct.pack('<Hi', 0xc4, int(value)).hex()
        entry = layout['byName'][kind]
        raw = encode_record(layout['objects'], layout['sizes'], entry['handle'], self.plain(value))
        return (struct.pack('<HH', 0x02a0, entry['structureHandle']) + raw).hex()

    def write_tag(self, symbol, data):
        """A Write Tag from the port: the request decoded into its tag, or the commit, then a scan.

        The data is the service's own: the type (and a structure's handle),
        one element, then the value. Any other header is refused.
        """
        layout, raw = self.layout(), bytes.fromhex(data)
        if symbol == layout['commit']:
            kind, count, value = struct.unpack('<HHi', raw)
            if (kind, count) != (0xc4, 1):
                raise ValueError('the commit is not one DINT')
            self.s.t[symbol] = value
            self.s.scan()
            return
        if symbol != layout['request']:
            raise ValueError('the port writes only its request and its commit: ' + symbol)
        entry = layout['byName'][host.REQUEST]
        if struct.unpack_from('<HHH', raw) != (0x02a0, entry['structureHandle'], 1):
            raise ValueError('the request header is not one element of its structure')
        self._assign(self.s.t[symbol], reader.decode_record(raw[6:], entry['handle'], layout['templates']),
                     host.REQUEST)

    def _assign(self, target, value, kind):
        for m in self.layout()['definitions'][kind]:
            items = value[m.name] if m.count else [value[m.name]]
            for i, item in enumerate(items):
                if m.kind.startswith(pub.PREFIX + 'String'):
                    text = item if isinstance(item, str) else bytes.fromhex(item['bytes'])[:item['LEN']].decode('latin-1')
                    self.s.bench.put(target[m.name][i] if m.count else target[m.name], text)
                elif m.kind == 'DINT':
                    if m.count:
                        target[m.name][i] = item
                    else:
                        target[m.name] = item
                else:
                    self._assign(target[m.name][i] if m.count else target[m.name], item, m.kind)

    # -- the operator and the assertions ------------------------------------------
    def read(self):
        t, root, persist = self.s.t, self.s.t[self.app.name], self.s.t[self.app.name]['ConfigPersist']
        station = gen.station_cfg_record(self.app)
        return dict(station=self.s.station(), persist=dict(self.s.persist()),
                    restoring=int(t[station.name + 'Tag']['SchemaVersion'] == 0),
                    stamped=t[station.name + 'Tag']['SchemaVersion'] == station.schema_version,
                    audits=t[sets.state_tag(self.app)]['AuditCount'],
                    catalog=[root['ConfigSetCount'], [self.s.bench.text(e['SetName']) for e in root['ConfigSets']]],
                    document=self.s.bench.text(root['ConfigSetDocument']),
                    lines=[root['ConfigSetDocumentLine'], root['ConfigSetDocumentLines']],
                    rejectKey=self.s.bench.text(persist['LastRejectKey']),
                    models=t[models.tag(self.app)]['Count'])

    def document(self, name, kind, source, model='', created=0, clock=0):
        """The engineering rendering: current values, declared initials or changed ones."""
        t = self.s.t
        def value(_o, record, member):
            if source == 'changed':
                if member.kind == 'boolean':
                    return 0 if member.initial else 1
                return member.maximum if member.initial != member.maximum else member.minimum
            if source == 'initial':
                return member.initial
            if sets.config_kind(record) == 0:
                return t[gen.model_cfg_tag(self.app)][0][member.name]
            return t[record.name + 'Tag'][member.name]
        return sets.values_document(self.app, name, kind, value, model, created, clock)

    def kept(self, created):
        """The engineering keeper's documents for the controller's current values."""
        t, codes = self.s.t, self.facts()['codes']
        held = live.Capture(restoring=False, records={r.name: dict(t[r.name + 'Tag']) for r in self.app.records},
                            banks=[dict(b) for b in t[gen.model_cfg_tag(self.app)][:len(codes)]], codes=codes,
                            model_ordinal=t[f'FRK_{self.app.name}_Unit']['ModelOrdinal'])
        return live.documents(self.app, held, created)

    def handle(self, request):
        op = request['op']
        if op == 'station':
            self.s = Station(self.ctx)
            return dict(ok=True, kinds=dict(save=mb.SAVE_CONFIG_SET, load=mb.LOAD_CONFIG_SET))
        if op == 'reply':
            return self.reply()
        if op == 'submit':
            return dict(reply=self.submit(request['envelope'], request['body']))
        if op == 'facts':
            return self.facts()
        if op == 'key':
            return dict(text=self.key(request['numeric']))
        if op == 'scan':
            self.s.scan(request.get('count', 1))
            return dict(ok=True)
        if op == 'command':
            return dict(sequence=self.s.command(request['kind'], **request.get('arguments', {})))
        if op == 'answered':
            return dict(answered=self.s.answered(request['sequence']), accepted=int(bool(self.s.reply['Accepted'])),
                        diagnostic=self.s.diagnostic())
        if op == 'read':
            return self.read()
        if op == 'set':
            record = next(r for r in self.app.records if r.station_cfg)
            member = next(m for _o, rec, m in gen.editable_values(self.app) if rec.station_cfg and m.write_key == request['key'])
            self.s.t[record.name + 'Tag'][member.name] = request['value']
            return dict(ok=True)
        if op == 'document':
            return dict(document=self.document(request['name'], request['kind'], request['source'],
                                               request.get('model', ''), request.get('created', 0),
                                               request.get('clock', 0)))
        if op == 'kept':
            return dict(documents=self.kept(request['created']))
        if op == 'python_store':
            # Python's own store and medium, for byte parity with the adapter's.
            import fraktal_ab_live_medium as medium
            import fraktal_ab_set_documents as documents
            from pathlib import Path
            folder = Path(request['directory'])
            if request.get('document') is not None:
                documents.FileStore(folder / 'sets').save(request['document'])
                medium.FileMedium(folder / 'live').write(request['key'], request['document'])
            files = {str(p.relative_to(folder)).replace('\\', '/'): p.read_bytes().decode('ascii')
                     for p in sorted(folder.rglob('*')) if p.is_file()}
            read = documents.FileStore(folder / 'sets').list() if (folder / 'sets').exists() else []
            return dict(files=files, listed=read)
        if op == 'encode':
            # The engineering encoder over the binding tests' synthetic Templates.
            from test_fraktal_ab_host_service_binding import pack
            definitions = {}
            host.augment(self.app, definitions, snapshot_count=5)
            templates, handles = pack(definitions, (host.REQUEST, host.REPLY))
            row = next(r for r in host.rows(self.app) if r['Service'] == request['service'])
            symbols = [dict(name=row['RequestSymbol'], handle=handles[host.REQUEST], arrayRank=0),
                       dict(name=row['ReplySymbol'], handle=handles[host.REPLY], arrayRank=0),
                       dict(name=row['CommitSymbol'], atomic=0xc4, arrayRank=0)]
            plan = binding.encode(row, symbols, templates, request['revision'], request['envelope'],
                                  binding.complete(request['body'], host.RECORDS_PER_CHUNK), request['sequence'],
                                  connection_bytes=4000)
            return dict(row=row, symbols=symbols, templates=templates,
                        payload=plan.payload_request.hex(), commit=plan.commit_request.hex())
        if op == 'capture':
            layout = self.layout()
            return dict(symbols=layout['symbols'], templates=layout['templates'], manifest=layout['manifest'])
        if op == 'read_tag':
            return dict(data=self.read_tag([tuple(segment) for segment in request['path']]))
        if op == 'write_tag':
            self.write_tag(request['symbol'], request['data'])
            return dict(ok=True)
        if op == 'members':
            return dict(members={m.write_key: [m.minimum, m.maximum, m.kind]
                                 for _o, _r, m in gen.editable_values(self.app)})
        raise ValueError('unknown bench request: ' + op)


def main():
    server = Server(sys.argv[1])
    print(json.dumps(dict(ready=True, root=server.app.name)), flush=True)
    for line in sys.stdin:
        try:
            answer = server.handle(json.loads(line))
        except Exception as error:  # reported to the test, which fails on it
            answer = dict(error=f'{type(error).__name__}: {error}')
        print(json.dumps(answer), flush=True)


if __name__ == '__main__':
    main()

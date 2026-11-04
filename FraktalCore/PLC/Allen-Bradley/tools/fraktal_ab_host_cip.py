"""The host adapter's controller port over pylogix: discovery, reply, request, facts.

Declaration-free. Discovery is the S1 read alone. A request is one 0x4D write
of the negotiated layout followed by its DINT commit, on a connection at least
the size the PLC publishes. Its acknowledgement is polled for a bounded time,
and a request left unacknowledged is never resent (the controller refuses a
replay as stale). Facts are read from the symbols the manifest names: the
typed command binding's capability and key tables, the root's model catalog.
"""
from __future__ import annotations

import time

import fraktal_ab_canonical_reader as reader
import fraktal_ab_host_service_binding as binding
from fraktal_ab_host_adapter import Capability, Facts, RootService, Unanswered, revision_of

ANSWER_S = 1.0


def plain(value):
    """S1-decoded values as Python values: a StringFamily becomes its text."""
    if isinstance(value, dict) and value.get('string') is True:
        return bytes.fromhex(value['bytes']).decode('utf-8')
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value


class CipPort:
    def __init__(self, comm, capture, rows, *, wait=0.02, answer_s=ANSWER_S, clock=time.monotonic, sleep=time.sleep):
        # One root's mutating rows: they share one ingress and differ by service.
        self.comm, self.capture = comm, capture
        self.rows = {r['Service']: r for r in rows}
        self.row = rows[0]
        self.root = self.row['RootSymbol']
        self.symbols = {s['name']: s for s in capture['symbols']}
        self.objects, sizes = reader.template_objects(capture['templates'])
        self.extent, unused = binding.schema(self.row, self.symbols, self.objects, sizes, reader.member_table,
                                             reader.is_string)
        self.wait_s, self.answer_s, self.clock, self.sleep = wait, answer_s, clock, sleep
        command = next(b for b in capture['manifest']['commandBindings'] if b['RootSymbol'] == self.root)
        self.command = command
        self._capabilities = None
        self._keys = None

    def _record(self, symbol, handle=None):
        sample = self.comm.Read(symbol)
        if sample.Status != 'Success' or not isinstance(sample.Value, (bytes, bytearray)):
            raise Unanswered(f'{symbol} did not read')
        handle = self.symbols[symbol.split('[')[0].split('.')[0]]['handle'] if handle is None else handle
        return plain(reader.decode_record(bytes(sample.Value), handle, self.capture['templates']))

    def _scalar(self, symbol):
        sample = self.comm.Read(symbol)
        if sample.Status != 'Success' or type(sample.Value) is not int:
            raise Unanswered(f'{symbol} did not read')
        return sample.Value

    def reply(self):
        return self._record(self.row['ReplySymbol'])

    def wait(self):
        self.sleep(self.wait_s)

    def submit(self, envelope, body):
        sequence = binding.next_sequence(self.reply())
        # The capture was validated once, at discovery (S1); a chunk only encodes.
        row = self.rows[envelope['Service']]
        plan = binding.encode(row, self.capture['symbols'], self.capture['templates'],
                              self.capture['manifest']['configRevision'], envelope,
                              binding.complete(body, self.extent), sequence, connection_bytes=row['ConnectionBytes'])
        self.comm.ConnectionSize = max(self.comm.ConnectionSize or 0, self.row['ConnectionBytes'])
        for request in (plan.payload_request, plan.commit_request):
            status, unused = self.comm.conn.send(request)
            if status != 0:
                raise Unanswered(f'host-service write refused (status {status})')
        deadline = self.clock() + self.answer_s
        while self.clock() < deadline:
            answer = self.reply()
            if answer['AckSequence'] & 0xffffffff == sequence:
                return answer
            self.sleep(self.wait_s)
        raise Unanswered(f'host-service request {sequence} was not acknowledged')

    def _element_handle(self, symbol):
        return self.symbols[symbol]['handle']

    def facts(self):
        if self._capabilities is None:
            symbol = self.command['CapabilitiesSymbol']
            rows = [self._record(f'{symbol}[{i}]', self._element_handle(symbol))
                    for i in range(self.command['CapabilitiesCount'])]
            self._capabilities = tuple(Capability(r['CapabilityIndex'], self.key_text(r['WriteKeyKey']),
                                                  r['ConfigKind'], r['ValueType']) for r in rows)
        count = self._scalar(f'{self.root}.AvailableModelCount') if self._has('AvailableModelCount') else 0
        codes = tuple(self._model(i) for i in range(count))
        capacity = self._scalar(f'{self.root}.ModelCapacity') if self._has('ModelCapacity') else 0
        return Facts(self.root, revision_of(self.capture['manifest']['legacyContentHash']), self._capabilities,
                     codes, capacity)

    def _has(self, member):
        return any(r['name'] == member for r in reader.member_table(self.objects[self.symbols[self.root]['handle']]))

    def _model(self, index):
        row = next(r for r in reader.member_table(self.objects[self.symbols[self.root]['handle']])
                   if r['name'] == 'AvailableModels')
        return self._record(f'{self.root}.AvailableModels[{index}]', row['handle'])['ModelCode']

    def key_text(self, numeric):
        if self._keys is None:
            symbol = self.command['KeysSymbol']
            self._keys = {}
            for i in range(self.command['KeysCount']):
                row = self._record(f'{symbol}[{i}]', self._element_handle(symbol))
                self._keys[row['NumericKey']] = row['PortableKey']
        return self._keys.get(numeric, '')


def open_services(comm, *, expect_serial, wait=0.02, environ=None):
    """One RootService per root with a mutating host-service row; [] when there is none."""
    import fraktal_ab_live_medium as medium
    import fraktal_ab_set_documents as documents
    unused, capture = reader.read_document(comm, expect_serial=expect_serial)
    manifest = capture['manifest']
    if manifest.get('schemaMinor', 0) < binding.MINOR:
        return []
    services, seen = [], set()
    for row in manifest['hostServiceBindings']:
        if row['Service'] not in binding.MUTATING or row['RootSymbol'] in seen:
            continue
        seen.add(row['RootSymbol'])
        rows = [r for r in manifest['hostServiceBindings'] if r['RootSymbol'] == row['RootSymbol']]
        folder = documents.directory_for(row['RootSymbol'], expect_serial, environ)
        live = medium.FileMedium(folder / 'live') if any(r['Service'] == binding.SERVICES['LiveDocuments']
                                                         for r in rows) else None
        mutating = [r for r in rows if r['Service'] in binding.MUTATING]
        services.append(RootService(CipPort(comm, capture, mutating, wait=wait), documents.FileStore(folder), live))
    return services

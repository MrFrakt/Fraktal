library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'cip_manifest.dart';
import 'cip_namespace.dart';
import 'cip_publication.dart';
import 'cip_template.dart';
import 'cip_transport.dart';

/// The V6.11 host-service vocabulary, as the controller publishes it
/// (Fraktal/AB `fraktal_ab_host_service_binding.py` is the engineering twin).
abstract final class CipHost {
  static const version = 1, minor = 11;
  static const configSets = 1, configProvider = 2, liveDocuments = 3, hostEvents = 4;
  static const mutating = {1, 2, 3};
  // Request.Status: the host's outcome for the job phase it answers.
  static const ok = 1, failed = 2, refused = 3, lost = 4, unavailable = 5;
  // Body.Kind.
  static const none = 0, header = 1, records = 2, catalog = 3, text = 4;
  // Reply.JobPhase.
  static const fetch = 1, store = 2, present = 3, snapshot = 4, restore = 5;
  // Reply.ErrorCode.
  static const invalid = 1,
      collided = 2,
      staleSerial = 3,
      staleRevision = 4,
      noJob = 5,
      order = 6,
      access = 7,
      busy = 8,
      notRestoring = 9;
  static const headerFields = [
    'SchemaVersion',
    'ManifestRevision',
    'StagedSequence'
  ];
  static const envelope = [
    'Service',
    'JobSequence',
    'Operation',
    'Argument',
    'Chunk',
    'Final',
    'Status'
  ];
  static const scalars = [
    'Kind',
    'Count',
    'Total',
    'SetSchema',
    'ConfigRev',
    'RecordKind',
    'CreatedSeconds',
    'Synchronized'
  ];
  static const texts = {'Scope': 80, 'Name': 80, 'Model': 64, 'Line': 480};
  static const columns = ['Revisions', 'RecordKinds', 'ValueTypes', 'Values'];
  static const keyWidth = 160;
}

/// A request the controller did not acknowledge: it concluded nothing, and it
/// is never resent (the controller refuses a replay as stale).
final class CipHostUnanswered implements Exception {
  final String message;
  const CipHostUnanswered(this.message);
  @override
  String toString() => 'CipHostUnanswered: $message';
}

/// A sparse chunk with every field it does not name at its empty value.
Map<String, Object?> cipHostComplete(Map<String, Object?> body, int extent) {
  final out = <String, Object?>{
    for (final n in CipHost.scalars) n: 0,
    for (final n in CipHost.texts.keys) n: '',
    'Keys': List<Object?>.filled(extent, ''),
    for (final n in CipHost.columns) n: List<Object?>.filled(extent, 0),
  };
  for (final entry in body.entries) {
    final current = out[entry.key];
    if (!out.containsKey(entry.key))
      throw FormatException('Unknown host chunk field: ${entry.key}.');
    if (current is List) {
      final value = entry.value;
      if (value is! List || value.length > extent)
        throw const FormatException(
            'Host chunk column exceeds the negotiated extent.');
      out[entry.key] = [...value, ...current.skip(value.length)];
    } else {
      out[entry.key] = entry.value;
    }
  }
  return out;
}

/// The negotiated shared ingress: request, chunk and reply Templates.
final class CipHostLayout {
  final Map<String, Object?> row;
  final int extent, structureHandle, replyHandle;
  final CipTemplate request, chunk;
  final CipTemplateDecoder decoder;

  CipHostLayout._(this.row, this.extent, this.structureHandle, this.replyHandle,
      this.request, this.chunk, this.decoder);

  /// The client's half of the V6.11 schema check: every layout fact it encodes
  /// against is the Template's, and any deviation refuses.
  factory CipHostLayout.negotiate(
      CipNamespace namespace, Map<String, Object?> row) {
    if (!CipHost.mutating.contains(row['Service']))
      throw const FormatException('Host events have no ingress.');
    CipSymbol structured(String name) {
      final s = namespace.symbols[name];
      if (s == null ||
          !s.structured ||
          s.rank != 0 ||
          !namespace.templates.containsKey(s.handle))
        throw FormatException('Host-service Symbol unavailable: $name.');
      return s;
    }

    final request = structured(row['RequestSymbol'] as String),
        reply = structured(row['ReplySymbol'] as String);
    final commit = namespace.symbols[row['CommitSymbol'] as String];
    if (commit == null || commit.structured || commit.rank != 0 || commit.atomic != 0xc4)
      throw const FormatException('Host commit must be a DINT scalar Symbol.');
    final decoder = namespace.decoderFor([request.handle, reply.handle]);
    final outer = decoder.templates[request.handle]!;
    final members = {for (final m in outer.members) m.name: m};
    bool dint(CipTemplateMember? m, [int count = 0]) =>
        m != null &&
        !m.isStructure &&
        m.atomic == 0xc4 &&
        m.isArray == (count != 0) &&
        (count == 0 || m.info == count);
    if (members.keys.toSet().difference({
          ...CipHost.headerFields,
          ...CipHost.envelope,
          row['ChunkMember']
        }).isNotEmpty ||
        members.length != CipHost.headerFields.length + CipHost.envelope.length + 1 ||
        outer.byteSize > (row['MaximumChunkBytes'] as int) ||
        [...CipHost.headerFields, ...CipHost.envelope]
            .any((n) => !dint(members[n])))
      throw const FormatException(
          'Host request envelope layout or size bound differs.');
    final body = members[row['ChunkMember']]!;
    if (!body.isStructure || body.isArray)
      throw const FormatException('Host chunk must be a structured scalar.');
    final chunk = decoder.templates[body.handle]!;
    final fields = {for (final m in chunk.members) m.name: m};
    final keys = fields['Keys'];
    final extent = keys != null && keys.isArray ? keys.info : 0;
    bool string(CipTemplateMember? m, int width, [int count = 0]) =>
        m != null &&
        m.isStructure &&
        m.isArray == (count != 0) &&
        (count == 0 || m.info == count) &&
        decoder.templates[m.handle]?.stringByteCapacity == width;
    if (fields.length !=
            CipHost.scalars.length +
                CipHost.texts.length +
                1 +
                CipHost.columns.length ||
        extent < 1 ||
        extent > 64 ||
        CipHost.scalars.any((n) => !dint(fields[n])) ||
        CipHost.texts.entries.any((e) => !string(fields[e.key], e.value)) ||
        !string(keys, CipHost.keyWidth, extent) ||
        CipHost.columns.any((n) => !dint(fields[n], extent)))
      throw const FormatException('Host chunk layout differs from V6.11.');
    final handle = namespace.templates[request.handle]!.structureHandle;
    if (handle < 0 || handle > 0xffff)
      throw const FormatException(
          'Template attribute 1 structure handle unavailable.');
    return CipHostLayout._(Map.unmodifiable(row), extent, handle, reply.handle,
        outer, chunk, decoder);
  }

  /// One Write Tag payload for the request and its separate DINT commit; the
  /// same bytes `fraktal_ab_host_service_binding.encode` produces.
  (Uint8List, Uint8List) encode(
      {required int manifestRevision,
      required Map<String, Object?> envelope,
      required Map<String, Object?> body,
      required int sequence,
      required int connectionBytes}) {
    if (connectionBytes < (row['ConnectionBytes'] as int))
      throw const FormatException(
          'Host connection is below the PLC-published minimum.');
    if (envelope.keys.toSet().length != CipHost.envelope.length ||
        !CipHost.envelope.every(envelope.containsKey) ||
        envelope['Service'] != row['Service'])
      throw const FormatException(
          'Complete host envelope for this service required.');
    if (sequence < 0 || sequence > 0xffffffff)
      throw const FormatException('Sequence is not UInt32.');
    final complete = cipHostComplete(body, extent);
    final raw = Uint8List(request.byteSize), bytes = ByteData.sublistView(raw);
    void integer(int at, Object? value,
        [int lower = -0x80000000, int upper = 0x7fffffff]) {
      if (value is! int || value < lower || value > upper)
        throw const FormatException('Host scalar is outside its DINT range.');
      bytes.setUint32(at, value & 0xffffffff, Endian.little);
    }

    void text(int at, CipTemplate type, Object? value, int width) {
      if (value is! String)
        throw const FormatException('Host text requires a string.');
      final encoded = _utf8(value);
      if (encoded.length > width || encoded.contains(0))
        throw const FormatException(
            'Host text exceeds native width or contains NUL.');
      bytes.setInt32(at + type.members[0].offset, encoded.length, Endian.little);
      raw.setRange(at + type.members[1].offset,
          at + type.members[1].offset + encoded.length, encoded);
    }

    final outer = {for (final m in request.members) m.name: m};
    integer(outer['SchemaVersion']!.offset, CipHost.version, 0, 0xffffffff);
    integer(outer['ManifestRevision']!.offset, manifestRevision & 0xffffffff, 0,
        0xffffffff);
    integer(outer['StagedSequence']!.offset, sequence, 0, 0xffffffff);
    for (final name in CipHost.envelope) {
      integer(outer[name]!.offset, envelope[name]);
    }
    final base = outer[row['ChunkMember']]!.offset;
    final fields = {for (final m in chunk.members) m.name: m};
    for (final name in CipHost.scalars) {
      integer(base + fields[name]!.offset, complete[name]);
    }
    for (final entry in CipHost.texts.entries) {
      final m = fields[entry.key]!;
      text(base + m.offset, decoder.templates[m.handle]!, complete[entry.key],
          entry.value);
    }
    final keys = fields['Keys']!, type = decoder.templates[keys.handle]!;
    final values = complete['Keys'] as List;
    for (var i = 0; i < extent; i++) {
      text(base + keys.offset + i * type.byteSize, type, values[i],
          CipHost.keyWidth);
    }
    for (final name in CipHost.columns) {
      final column = complete[name] as List;
      for (var i = 0; i < extent; i++) {
        integer(base + fields[name]!.offset + 4 * i, column[i]);
      }
    }
    final payload = Uint8List.fromList(
        [...cipWords([0x02a0, structureHandle, 1]), ...raw]);
    final commit = Uint8List.fromList([
      ...cipWords([0xc4, 1]),
      ...(ByteData(4)..setUint32(0, sequence, Endian.little))
          .buffer
          .asUint8List()
    ]);
    // The same conservative connected-message allowance as the command writer.
    if (payload.length +
                cipSymbolPath(row['RequestSymbol'] as String).length +
                112 >
            connectionBytes ||
        commit.length + cipSymbolPath(row['CommitSymbol'] as String).length + 112 >
            connectionBytes)
      throw const FormatException(
          'Host chunk does not fit one connected Write Tag request.');
    return (payload, commit);
  }

  Map<String, Object?> decodeReply(Uint8List raw) =>
      Map<String, Object?>.from(decoder.decode(replyHandle, raw) as Map);
}

Uint8List _utf8(String value) {
  // Unpaired surrogates would be replaced lossily by the encoder: refuse them.
  final units = value.codeUnits;
  for (var i = 0; i < units.length; i++) {
    final u = units[i];
    if (u >= 0xd800 && u <= 0xdbff) {
      if (i + 1 >= units.length || units[i + 1] < 0xdc00 || units[i + 1] > 0xdfff)
        throw const FormatException('Host text is not valid Unicode.');
      i++;
    } else if (u >= 0xdc00 && u <= 0xdfff) {
      throw const FormatException('Host text is not valid Unicode.');
    }
  }
  return Uint8List.fromList(const Utf8Encoder().convert(value));
}

/// One write-key capability the controller publishes.
final class CipHostCapability {
  final int ordinal, kind, valueType;
  final String key;
  const CipHostCapability(this.ordinal, this.key, this.kind, this.valueType);
}

/// What the controller publishes about one root: enough to render its documents.
final class CipHostFacts {
  final String root;
  final int revision, capacity;
  final List<CipHostCapability> capabilities;
  final List<String> codes;
  const CipHostFacts(
      this.root, this.revision, this.capabilities, this.codes, this.capacity);
  bool get line => capabilities.any((c) => c.kind == 2);
  bool get models => capabilities.any((c) => c.kind == 0);
}

/// The configuration revision documents carry: the legacy content hash's first 24 bits.
int cipHostRevision(Object? legacyHash) {
  if (legacyHash is! String ||
      !RegExp(r'^[0-9A-Fa-f]{6,}$').hasMatch(legacyHash))
    throw const FormatException('Legacy content hash unavailable.');
  return int.parse(legacyHash.substring(0, 6), radix: 16);
}

/// The adapter's view of one root's ingress; a test may implement it over a bench.
abstract interface class CipHostPort {
  String get root;
  Future<Map<String, Object?>> reply();
  Future<Map<String, Object?>> submit(
      Map<String, Object?> envelope, Map<String, Object?> body);
  Future<CipHostFacts> facts();
  Future<String> keyText(int numeric);
  Future<void> wait();
}

/// One root's ingress over a read connection and a command connection.
final class CipHostIngress implements CipHostPort {
  final CipReadTransport wire;
  final Future<CipCommandTransport> Function() open;
  final CipNamespace namespace;
  final CipManifest manifest;
  final Map<int, Map<String, Object?>> rows;
  final Map<int, CipHostLayout> layouts;
  final Map<String, Object?> command;
  final Duration answer, poll;
  CipCommandTransport? _command;
  List<CipHostCapability>? _capabilities;
  Map<int, String>? _keys;
  late final CipTemplateDecoder _facts;

  CipHostIngress(this.wire, this.open, this.namespace, this.manifest,
      List<Map<String, Object?>> rootRows,
      {this.answer = const Duration(seconds: 1),
      this.poll = const Duration(milliseconds: 20)})
      : rows = {for (final r in rootRows) r['Service'] as int: r},
        layouts = {
          for (final r in rootRows)
            r['Service'] as int: CipHostLayout.negotiate(namespace, r)
        },
        command = manifest
            .rows('commandBindings')
            .singleWhere((b) => b['RootSymbol'] == rootRows.first['RootSymbol']) {
    final handles = <int>[];
    for (final name in [
      command['CapabilitiesSymbol'],
      command['KeysSymbol'],
      root
    ]) {
      final symbol = namespace.symbols[name];
      if (symbol != null && symbol.structured) handles.add(symbol.handle);
    }
    _facts = namespace.decoderFor(handles);
  }

  @override
  String get root => rows.values.first['RootSymbol'] as String;

  Future<Map<String, Object?>> _record(String path, int handle) async =>
      Map<String, Object?>.from(_facts.templates.containsKey(handle)
          ? _facts.decode(handle, await namespace.readStruct(wire, path, handle)) as Map
          : layouts.values.first.decoder
              .decode(handle, await namespace.readStruct(wire, path, handle)) as Map);

  @override
  Future<Map<String, Object?>> reply() async {
    final layout = layouts.values.first;
    final row = layout.row;
    return layout.decodeReply(await namespace.readStruct(
        wire, row['ReplySymbol'] as String, layout.replyHandle));
  }

  @override
  Future<void> wait() => Future<void>.delayed(poll);

  @override
  Future<Map<String, Object?>> submit(
      Map<String, Object?> envelope, Map<String, Object?> body) async {
    final service = envelope['Service'] as int, row = rows[service];
    if (row == null) throw const FormatException('Unbound host service.');
    final before = await reply();
    final sequence = ((before['Serial'] as int) + 1) & 0xffffffff;
    final (payload, commit) = layouts[service]!.encode(
        manifestRevision: manifest.revision,
        envelope: envelope,
        body: body,
        sequence: sequence,
        connectionBytes: row['ConnectionBytes'] as int);
    try {
      final wire = _command ??= await open();
      for (final (symbol, data) in [
        (row['RequestSymbol'] as String, payload),
        (row['CommitSymbol'] as String, commit)
      ]) {
        final written = await wire.writeTag(symbol, data);
        if (written.status != 0)
          throw CipHostUnanswered('host-service write refused (${written.status})');
      }
    } on Object {
      _command?.abort();
      _command = null;
      rethrow;
    } finally {
      payload.fillRange(0, payload.length, 0);
    }
    final deadline = DateTime.now().add(answer);
    while (DateTime.now().isBefore(deadline)) {
      final answer = await reply();
      if (((answer['AckSequence'] as int) & 0xffffffff) == sequence) return answer;
      await wait();
    }
    throw CipHostUnanswered('host-service request $sequence was not acknowledged');
  }

  @override
  Future<CipHostFacts> facts() async {
    _capabilities ??= await () async {
      final symbol = namespace.symbols[command['CapabilitiesSymbol']]!;
      return [
        for (var i = 0; i < (command['CapabilitiesCount'] as int); i++)
          await () async {
            final r = await _record(
                '${command['CapabilitiesSymbol']}[$i]', symbol.handle);
            return CipHostCapability(
                r['CapabilityIndex'] as int,
                await keyText(r['WriteKeyKey'] as int),
                r['ConfigKind'] as int,
                r['ValueType'] as int);
          }()
      ];
    }();
    final members = {
      for (final m in _facts.templates[namespace.symbols[root]!.handle]!.members)
        m.name: m
    };
    final count = members.containsKey('AvailableModelCount')
        ? await CipNamespace.readDint(wire, '$root.AvailableModelCount')
        : 0;
    final codes = <String>[
      for (var i = 0; i < count; i++)
        (await _record('$root.AvailableModels[$i]',
            members['AvailableModels']!.handle))['ModelCode'] as String
    ];
    final capacity = members.containsKey('ModelCapacity')
        ? await CipNamespace.readDint(wire, '$root.ModelCapacity')
        : 0;
    return CipHostFacts(root, cipHostRevision(manifest.document['legacyContentHash']),
        List.unmodifiable(_capabilities!), List.unmodifiable(codes), capacity);
  }

  @override
  Future<String> keyText(int numeric) async {
    if (_keys == null) {
      final symbol = namespace.symbols[command['KeysSymbol']]!;
      _keys = {};
      for (var i = 0; i < (command['KeysCount'] as int); i++) {
        final r = await _record('${command['KeysSymbol']}[$i]', symbol.handle);
        _keys![r['NumericKey'] as int] = r['PortableKey'] as String;
      }
    }
    return _keys![numeric] ?? '';
  }

  Future<void> close() async {
    _command?.abort();
    await wire.close();
  }
}

/// One root's canonical host-event ring, read-only and declaration-free.
///
/// The ring is one member of the root structure. It is read whole, as one
/// structure, between two reads of its own owner revision, which the PLC holds
/// odd while it changes the ring. Then it is projected exactly as the gateway
/// projects any canonical subtree. A host never writes the ring, acknowledging
/// nothing to the PLC: its cursor is its own.
final class CipHostEventsReader {
  final CipReadTransport wire;
  final CipNamespace namespace;
  final String root, revisionSymbol;
  final CipTemplateMember member;
  final CipTemplateDecoder _decoder;
  final CipPublication _publication;
  final String legacyContentHash;

  CipHostEventsReader._(this.wire, this.namespace, this.root, this.revisionSymbol, this.member,
      this._decoder, this._publication, this.legacyContentHash);

  factory CipHostEventsReader(CipReadTransport wire, CipNamespace namespace,
      CipManifest manifest, Map<String, Object?> row) {
    final root = row['RootSymbol'] as String;
    if (row['Service'] != CipHost.hostEvents || row['CanonicalRoot'] != '$root/HostEvents')
      throw const FormatException('Not a HostEvents binding row.');
    final owners = [
      for (final o in manifest.rows('ownerReadBindings'))
        if (o['CanonicalPrefix'] == '$root/HostEvents') o
    ];
    if (owners.length != 1)
      throw const FormatException('The host-event ring needs exactly one owner-read row.');
    final revision = namespace.symbols[owners.single['RevisionSymbol'] as String];
    if (revision == null || revision.structured || revision.rank != 0 || revision.atomic != 0xc4)
      throw const FormatException('The ring revision must be a DINT scalar Symbol.');
    final symbol = namespace.symbols[root];
    if (symbol == null || !symbol.structured || symbol.rank != 0)
      throw FormatException('Host-event root unavailable: $root.');
    final decoder = namespace.decoderFor([symbol.handle]);
    final members = decoder.templates[symbol.handle]!.members.where((m) => m.name == 'HostEvents');
    if (members.length != 1 || !members.single.isStructure || members.single.isArray)
      throw const FormatException('The root publishes no HostEvents structure.');
    final hash = manifest.document['legacyContentHash'];
    if (hash is! String || hash.isEmpty) throw const FormatException('Legacy content hash unavailable.');
    return CipHostEventsReader._(wire, namespace, root, revision.name, members.single, decoder,
        CipPublication(namespace, manifest), hash);
  }

  /// The ring's owner revision: it changes whenever the ring does.
  Future<int> revision() => CipNamespace.readDint(wire, revisionSymbol);

  /// The ring's canonical values keyed `HostEvents/...`, or null when the
  /// revision was odd or moved during the read (read again later).
  Future<Map<String, Object?>?> read() async {
    final before = await revision();
    if (before.isOdd) return null;
    final raw = await namespace.readStruct(wire, '$root.HostEvents', member.handle);
    if (await revision() != before) return null;
    return project(raw);
  }

  /// The canonical values of one ring structure's bytes.
  Map<String, Object?> project(Uint8List raw) {
    final value = Map<String, Object?>.from(_decoder.decode(member.handle, raw) as Map);
    final count = value['Count'];
    if (count is! int) throw const FormatException('Host-event ring count unavailable.');
    final projected = _publication.projectSubtree(
        '$root/HostEvents', member, value, {'$root/HostEvents/Count': count})['values'] as Map;
    return {
      for (final e in projected.entries) (e.key as String).substring(root.length + 1): e.value
    };
  }
}

/// Every HostEvents ring a V6.11 manifest binds; empty below V6.11.
List<CipHostEventsReader> cipHostEventsReaders(
        CipReadTransport wire, CipNamespace namespace, CipManifest manifest) =>
    manifest.minor < CipHost.minor
        ? []
        : [
            for (final row in manifest.rows('hostServiceBindings'))
              if (row['Service'] == CipHost.hostEvents)
                CipHostEventsReader(wire, namespace, manifest, row)
          ];

/// What one controller asks of a host: its ingresses and its event rings.
final class CipHostDiscovery {
  final CipReadTransport wire;
  final List<CipHostIngress> ingresses;
  final List<CipHostEventsReader> events;
  const CipHostDiscovery(this.wire, this.ingresses, this.events);
  bool get isEmpty => ingresses.isEmpty && events.isEmpty;

  Future<void> close() async {
    for (final port in ingresses) {
      await port.close();
    }
    await wire.close();
  }
}

/// Discover every root's host services and event rings on one controller.
Future<CipHostDiscovery> cipHostDiscover(
    {required String host,
    int port = 44818,
    int slot = 0,
    required String expectSerial}) async {
  final wire = await CipSocketTransport.connect(
      host: host, port: port, slot: slot, expectSerial: expectSerial);
  try {
    final namespace = await CipNamespace.discover(wire);
    final candidates = namespace.symbols.values
        .where((s) =>
            s.structured &&
            s.rank == 0 &&
            CipManifest.looksLike(namespace.templates[s.handle]!.members
                .map((m) => m['name'] as String)
                .toSet()))
        .toList();
    if (candidates.length != 1)
      throw const FormatException(
          'Exactly one canonical publication manifest is required.');
    final symbol = candidates.single;
    final first = await namespace.readStruct(wire, symbol.name, symbol.handle);
    final second = await namespace.readStruct(wire, symbol.name, symbol.handle);
    if (first.length != second.length ||
        [for (var i = 0; i < first.length; i++) first[i] != second[i]].any((v) => v))
      throw const FormatException('Manifest changed during discovery.');
    final manifest = CipManifest.fromPhysical(Map<String, Object?>.from(
        namespace.decoderFor([symbol.handle]).decode(symbol.handle, first) as Map));
    final ports = cipHostIngresses(
        wire,
        namespace,
        manifest,
        (connectionBytes) => CipCommandSocketTransport.connect(
            host: host,
            port: port,
            slot: slot,
            expectSerial: expectSerial,
            connectionBytes: connectionBytes));
    final discovery = CipHostDiscovery(wire, ports, cipHostEventsReaders(wire, namespace, manifest));
    // A controller serving nothing keeps no connection open between looks.
    if (discovery.isEmpty) await wire.close();
    return discovery;
  } on Object {
    wire.abort();
    rethrow;
  }
}

/// One ingress per root with a mutating host-service row, all sharing [wire].
/// [open] opens a command connection of the row's negotiated size. Empty
/// below V6.11 or when no root binds a mutating service.
List<CipHostIngress> cipHostIngresses(
    CipReadTransport wire,
    CipNamespace namespace,
    CipManifest manifest,
    Future<CipCommandTransport> Function(int connectionBytes) open) {
  if (manifest.minor < CipHost.minor) return [];
  final byRoot = <String, List<Map<String, Object?>>>{};
  for (final row in manifest.rows('hostServiceBindings')) {
    if (CipHost.mutating.contains(row['Service']))
      (byRoot[row['RootSymbol'] as String] ??= []).add(row);
  }
  return [
    for (final rows in byRoot.values)
      CipHostIngress(wire, () => open(rows.first['ConnectionBytes'] as int),
          namespace, manifest, rows)
  ];
}

library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'cip_publication.dart';
import 'cip_transport.dart';
import 'opcua_session_client.dart';

/// Transient bytes only. Never include these records in diagnostics or captures.
final class CipCommandWritePlan {
  final String payloadSymbol, commitSymbol;
  final Uint8List payload, commit;
  CipCommandWritePlan(
      this.payloadSymbol, this.commitSymbol, this.payload, this.commit);

  void clear() {
    payload.fillRange(0, payload.length, 0);
    commit.fillRange(0, commit.length, 0);
  }
}

/// Encode the discovered Core ABI without sampling command input records.
/// Validation completes before either write, including all UTF-8 byte lengths.
CipCommandWritePlan cipCommandWritePlan(
    CipPublication publication, List<OpcUaWrite> writes, int connectionBytes) {
  if (writes.isEmpty || writes.length > 10)
    throw const FormatException('Invalid command batch size.');
  final last = writes.last;
  const suffix = '/HmiRequest/Sequence';
  if (!last.path.endsWith(suffix) ||
      last.type != OpcUaWriteType.uint32 ||
      last.value is! int ||
      (last.value as int) < 0 ||
      (last.value as int) > 0xffffffff)
    throw const FormatException('Command requires a final UInt32 Sequence.');
  final root = last.path.substring(0, last.path.length - suffix.length);
  final rows = publication.manifest
      .rows('commandBindings')
      .where((r) => r['RootSymbol'] == root)
      .toList();
  if (rows.length != 1)
    throw const FormatException('Command root is not discovered.');
  final row = rows.single;
  if (connectionBytes < (row['ConnectionBytes'] as int) ||
      connectionBytes > 4000)
    throw const FormatException('Command connection bound differs.');
  final prefix = '$root/HmiRequest/';
  final fields = <String, OpcUaWrite>{};
  for (final write in writes.take(writes.length - 1)) {
    if (!write.path.startsWith(prefix) ||
        !publication.commandArguments.containsKey(write.path) ||
        fields.containsKey(write.path.substring(prefix.length)))
      throw const FormatException('Unknown, duplicate or mixed command field.');
    fields[write.path.substring(prefix.length)] = write;
  }
  final symbol = publication.namespace.symbols[row['PayloadSymbol']]!;
  final template = publication.decoder.templates[symbol.handle]!;
  final structure =
      publication.namespace.templates[symbol.handle]!.structureHandle;
  if (structure < 0 ||
      structure > 65535 ||
      template.byteSize > (row['MaximumPayloadBytes'] as int))
    throw const FormatException('Invalid command Template extent or handle.');
  final raw = Uint8List(template.byteSize), bytes = ByteData.sublistView(raw);
  try {
    final envelope = {for (final m in template.members) m.name: m};
    for (final entry in {
      'SchemaVersion': row['Version'] as int,
      'ManifestRevision': publication.manifest.revision,
      'StagedSequence': last.value as int,
    }.entries) {
      bytes.setUint32(envelope[entry.key]!.offset, entry.value, Endian.little);
    }
    final args = envelope[row['ArgumentsMember']]!;
    for (final member in publication.decoder.templates[args.handle]!.members) {
      final write = fields[member.name], at = args.offset + member.offset;
      final string = member.isStructure
          ? publication.decoder.templates[member.handle]
          : null;
      if (string != null) {
        if (write != null &&
            (write.type != OpcUaWriteType.string || write.value is! String))
          throw const FormatException('Command text type differs.');
        final value = write?.value as String? ?? '';
        // Dart's UTF-8 replacement of an unpaired surrogate is lossy. Reject it.
        final encoded = utf8.encode(value);
        if (utf8.decode(encoded) != value ||
            encoded.contains(0) ||
            encoded.length > string.stringByteCapacity!)
          throw const FormatException(
              'Command text exceeds its Template or is invalid.');
        final len = string.members.singleWhere((m) => m.name == 'LEN');
        final data = string.members.singleWhere((m) => m.name == 'DATA');
        if (len.offset < 0 ||
            data.offset < len.offset + 4 ||
            data.offset + string.stringByteCapacity! > string.byteSize)
          throw const FormatException('Invalid command StringFamily layout.');
        bytes.setInt32(at + len.offset, encoded.length, Endian.little);
        raw.setRange(
            at + data.offset, at + data.offset + encoded.length, encoded);
      } else if (member.atomic == 0xc1) {
        if (write != null &&
            (write.type != OpcUaWriteType.boolean || write.value is! bool))
          throw const FormatException('Command Boolean type differs.');
        if (write?.value == true)
          raw[at + member.info ~/ 8] |= 1 << (member.info % 8);
      } else {
        final unsigned = member.name == 'DurationMs';
        final value = write?.value ?? 0;
        if (value is! int ||
            write != null &&
                write.type !=
                    (unsigned ? OpcUaWriteType.uint32 : OpcUaWriteType.int32) ||
            value < (unsigned ? 0 : -0x80000000) ||
            value > (unsigned ? 0xffffffff : 0x7fffffff))
          throw const FormatException('Command integer type or range differs.');
        bytes.setUint32(at, value & 0xffffffff, Endian.little);
      }
    }
    final payloadSymbol = row['PayloadSymbol'] as String,
        commitSymbol = row['CommitSymbol'] as String;
    final payload = Uint8List.fromList([
      ...cipWords([0x02a0, structure, 1]),
      ...raw
    ]);
    final commit = Uint8List.fromList([
      ...cipWords([0xc4, 1]),
      ...(ByteData(4)..setUint32(0, last.value as int, Endian.little))
          .buffer
          .asUint8List()
    ]);
    if (payload.length + cipSymbolPath(payloadSymbol).length + 112 >
            connectionBytes ||
        commit.length + cipSymbolPath(commitSymbol).length + 112 >
            connectionBytes)
      throw const FormatException('Command does not fit one Write Tag.');
    return CipCommandWritePlan(payloadSymbol, commitSymbol, payload, commit);
  } finally {
    raw.fillRange(0, raw.length, 0);
  }
}

/// One dedicated connection, serialized payload/commit pairs, no retries.
/// A transport ambiguity poisons this writer; only rediscovery can replace it.
final class CipCommandWriter {
  final CipPublication publication;
  final CipCommandTransport wire;
  final Future<void> Function()? verifyPublication;
  Future<void> _tail = Future<void>.value();
  bool _closed = false;
  bool get requiresRediscovery => _closed;
  CipCommandWriter(this.publication, this.wire, {this.verifyPublication});

  Future<bool> writeBatch(List<OpcUaWrite> writes) {
    if (_closed)
      return Future.error(
          const OpcUaTransportException('CIP command discovery required.'));
    final plan = cipCommandWritePlan(publication, writes, wire.connectionBytes);
    final result = _tail.then((_) async {
      try {
        if (_closed)
          throw const OpcUaTransportException(
              'CIP command discovery required.');
        await verifyPublication?.call();
        final staged = await wire.writeTag(plan.payloadSymbol, plan.payload);
        if (staged.data.isNotEmpty)
          throw const FormatException('Invalid Write Tag reply.');
        if (staged.status != 0) return false;
        final committed = await wire.writeTag(plan.commitSymbol, plan.commit);
        if (committed.data.isNotEmpty)
          throw const FormatException('Invalid Write Tag reply.');
        return committed.status == 0;
      } on Object {
        _closed = true;
        wire.abort();
        rethrow;
      } finally {
        plan.clear();
      }
    });
    _tail = result.then<void>((_) {}, onError: (Object _) {});
    return result;
  }

  Future<void> close() async {
    _closed = true;
    wire.abort();
    await _tail;
  }
}

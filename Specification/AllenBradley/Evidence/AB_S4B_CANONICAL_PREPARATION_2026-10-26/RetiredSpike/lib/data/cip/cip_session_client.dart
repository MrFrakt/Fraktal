library;

/// A gateway-less Fraktal/AB transport: the HMI speaks EtherNet/IP to the
/// controller directly through libplctag, derives the module tree from the
/// §3.10.2 manifest and serves the repository's flat snapshot from live
/// controller tags.
///
/// **Spike scope.** The supported production transport for Fraktal/AB remains
/// the CIP gateway (`fraktal_ab_gateway.py`), which serves the complete
/// projection (4000+ leaves: config pages, alarm log, shift/OEE, access,
/// release reports, per-module live status). This client serves the core
/// operator surface — the manifest-derived module tree, unit mode/step/counts,
/// mailbox ack, decision — with the member bindings listed in `_unitMembers`
/// and the chart/response offsets below. Surfaces it does not serve are
/// absent keys, which the mapper renders as absent views, never as wrong
/// values.
///
/// **Write surface.** Only the command mailbox is writable (Core §14: the one
/// surface the generated project exposes), written as a read-modify-write of
/// the whole `FRK_Press_HmiRequest` structure with the commit word last — the
/// same ordering contract the gateway's writer enforces. The PLC re-checks
/// every command through its own release gates.

import 'dart:typed_data';

import 'package:fraktal_opcua_client/opcua_session_client.dart';

import 'eip_cip_client.dart';
import 'fraktal_manifest.dart';

class CipSessionClient implements OpcUaBulkReadClient, OpcUaPathDiscoveryClient {
  final String host;
  final int port;
  final String appName;
  final EipCipClient client;
  FraktalManifest? _manifest;

  CipSessionClient._(
      {required this.host, required this.port, required this.appName})
      : client = EipCipClient(host: host, port: port);

  static Future<CipSessionClient> connect(
      {required String host, int port = 44818, String appName = 'Press'}) async {
    final session = CipSessionClient._(host: host, port: port, appName: appName);
    await session.client.connect();
    return session;
  }

  @override
  Future<void> close() => client.close();

  /// Reads a UDT tag (or struct array) via connected reads, chunked for
  /// large element counts. The client strips the CIP type word and the UDT
  /// instance header, so each chunk is exactly `count` rows of raw members
  /// and the concatenation is the whole table.
  Future<Uint8List> _readStruct(String tagName, [int elementCount = 1]) async {
    if (elementCount == 1) {
      return client.connectedRead(tagName);
    }
    const chunkSize = 8;
    final chunks = <Uint8List>[];
    for (var start = 0; start < elementCount; start += chunkSize) {
      final count = (start + chunkSize > elementCount)
          ? elementCount - start
          : chunkSize;
      final tag = start == 0 ? tagName : '$tagName[$start]';
      chunks.add(await client.connectedRead(tag, elementCount: count));
    }
    final total = chunks.fold<int>(0, (n, c) => n + c.length);
    final out = Uint8List(total);
    var offset = 0;
    for (final chunk in chunks) {
      out.setRange(offset, offset + chunk.length, chunk);
      offset += chunk.length;
    }
    return out;
  }

  Future<FraktalManifest> _ensureManifest() async {
    final existing = _manifest;
    if (existing != null) {
      return existing;
    }
    _manifest = await FraktalManifest.read(
        (tag, count) async => _readStruct(tag, count), appName);
    return _manifest!;
  }

  // ---- member offsets (byte offsets into the generated UDTs; every member
  // before the ones used here is a plain DINT, so offset = 4 * position) ----

  static const _unitMembers = [
    'SchemaVersion', 'Par_TaskPeriodMs', 'Mode', 'ModeRequest', 'ModelRequest',
    'CommitModel', 'ModelOrdinal', 'ModeSwitches', 'Step', 'PrevStep',
    'Running', 'Complete', 'Aborted', 'Error', 'ErrorID', 'ErrorSource',
    'ReportedReason', 'ReportedCount', 'ReportedSource', 'DecisionId',
    'DecisionAnswer', 'DecisionCount', 'CycleCount', 'GoodCount',
    'ScrapCount', 'ReworkCount', 'OrderFail', 'StepScan', 'RunRequest',
    'AbortRequest', 'ResetRequest', 'DiagReason', 'StallTimeMs',
    'StepExpectedMs', 'StallMs', 'StallStep', 'StepTimedOut', 'DiagIoRoles',
    'DiagStamped', 'DiagSinceDate', 'DiagSinceTime',
  ];
  static int _unitOffset(String member) => 4 * _unitMembers.indexOf(member);

  // FRK_T_PressChart leads with the scalars before its arrays:
  // StepCursor(0), ActiveStepNumber(4), StallReason(8), ActiveChain(12),
  // CurrentStepMs(16).
  static const _chartStallReason = 8;
  static const _chartActiveChain = 12;
  static const _chartCurrentStepMs = 16;

  // FRK_T_PressHmiResponse: AckSequence(0), Accepted(4), DiagnosticKey(8).
  static const _responseAck = 0;
  static const _responseAccepted = 4;
  static const _responseDiagnosticKey = 8;

  // The request mailbox is accessed member-wise only: five key strings
  // (LEN + DATA[56]) and the scalar words. The struct itself rejects
  // whole-tag access with a privilege violation — the generated project's
  // own guard for the one writable surface.
  static const _requestStringMembers = [
    'TargetPath', 'NameValue', 'TextValue', 'User', 'Secret',
  ];

  @override
  Future<Map<String, Object?>> snapshot() async {
    final manifest = await _ensureManifest();
    final keys = manifest.keys;
    final values = <String, Object?>{};

    final unit = await _readStruct('FRK_${appName}_Unit');
    int unitMember(String name) {
      final offset = _unitOffset(name);
      if (offset < 0 || offset + 4 > unit.length) {
        return 0;
      }
      return ByteData.sublistView(unit).getInt32(offset, Endian.little);
    }

    Uint8List? chart;
    int chartInt(int offset) {
      if (chart == null || offset + 4 > chart.length) {
        return 0;
      }
      return ByteData.sublistView(chart).getInt32(offset, Endian.little);
    }

    final error = unitMember('Error');
    final running = unitMember('Running');
    final complete = unitMember('Complete');
    values
      ..['Press/Status/Name'] = appName
      ..['Press/Status/ModuleType'] = 1
      ..['Press/Status/State'] = error != 0
          ? 4
          : running != 0
              ? 2
              : complete != 0
                  ? 3
                  : 1 // E_ExecState ERROR/BUSY/DONE/READY
      ..['Press/Status/FaultActive'] = error != 0
      ..['Press/ModeActivePublished'] = unitMember('Mode')
      ..['Press/GoodCount'] = unitMember('GoodCount')
      ..['Press/NokCount'] = unitMember('ScrapCount')
      ..['Press/ReworkCount'] = unitMember('ReworkCount')
      ..['Press/CurrentStep/StepNo'] = unitMember('Step')
      ..['Press/RunStyle'] = 0
      ..['Press/Decision/Default'] = unitMember('DecisionAnswer');

    final reason = unitMember('DiagReason');
    final stamped = unitMember('DiagStamped') == reason;
    values
      ..['Press/Status/Diagnostic/ReasonCode'] = reason
      ..['Press/Status/Diagnostic/Description'] = ''
      ..['Press/Status/Diagnostic/IoTag'] = ''
      ..['Press/Status/Diagnostic/IoAddress'] = ''
      ..['Press/Status/Diagnostic/Since'] =
          (stamped && reason != 0) ? unitMember('DiagSinceDate') : 0
      ..['Press/Status/Diagnostic/TimeSynchronized'] = false;

    try {
      chart = await _readStruct('FRK_${appName}_Chart');
      values
        ..['Press/CurrentStepElapsed'] = chartInt(_chartCurrentStepMs)
        ..['Press/StallReason'] = chartInt(_chartStallReason)
        ..['Press/ActiveChain'] = chartInt(_chartActiveChain)
        ..['Press/CurrentStepTimedOut'] = unitMember('StepTimedOut') != 0;
    } on Object {
      // Chart members stay absent when the chart read fails; the unit values
      // above are already live.
    }

    // Mode/run-style policy, as the projection publishes it.
    for (var mode = 1; mode <= 4; mode++) {
      values['Press/SupportedModesPublished[$mode]'] = true;
      values['Press/ModePolicy[$mode]/Shield'] = 0; // INTERRUPTIBLE
      values['Press/ModePolicy[$mode]/Style'] = 1; // IMMEDIATE
    }
    values
      ..['Press/SupportedRunStylesPublished[1]'] = true
      ..['Press/SupportedRunStylesPublished[2]'] = true
      ..['Press/SupportedRunStylesPublished[3]'] = true;

    // Module tree from the manifest: name, type and display key are
    // manifest-driven; live Status on non-root modules is a per-type binding
    // and stays absent in this spike.
    //
    // Type keys are NOT in the manifest (the controller carries no copy —
    // the gateway takes them from the declaration), so this client carries
    // the press declaration's pairs verbatim: project.moduleType.
    // pneumaticallyPress root, then fraktal_ab_press_echo38's modules.
    const typeKeys = {
      'Press': 'project.moduleType.pneumaticPress',
      'Press.PressRam': 'std.moduleType.cylinder',
      'Press.Door': 'std.moduleType.cylinder',
      'Press.PartSlide': 'std.moduleType.cylinder',
      'Press.PartPresentSensor': 'std.moduleType.digitalInput',
      'Press.TwoHand': 'std.moduleType.twoHand',
      'Press.AirPressureMonitor': 'std.moduleType.airPressure',
    };
    for (final row in manifest.rows['Modules'] ?? const []) {
      final identity = keys[row['CanonicalPathKey']] ?? '';
      if (identity.isEmpty) {
        continue;
      }
      final base = identity.replaceAll('.', '/');
      final tier = row['Tier'] as int;
      values
        ..['$base/Status/Name'] = identity
        ..['$base/Status/ModuleType'] = tier == 0 ? 1 : 3 // TIER_ROOT = 0
        ..['$base/Status/DisplayNameKey'] = keys[row['LocalNameKey']] ?? ''
        ..['$base/Status/TypeKey'] = typeKeys[identity] ?? '';
    }

    // Command mailbox ack surface, as the repository polls it.
    final response = await _readStruct('FRK_${appName}_HmiResponse');
    int responseInt(int offset) =>
        ByteData.sublistView(response).getInt32(offset, Endian.little);
    values
      ..['Press/HmiResponse/AckSequence'] = responseInt(_responseAck)
      ..['Press/HmiResponse/Accepted'] = responseInt(_responseAccepted) != 0;
    final diagKey = responseInt(_responseDiagnosticKey);
    values['Press/HmiResponse/Diagnostic'] = keys[diagKey] ?? '';
    // The request mailbox STRUCT rejects whole-tag access (Privilege
    // violation, by contract); its members are individually readable.
    values['Press/HmiRequest/Sequence'] =
        await _readDint('FRK_${appName}_HmiRequest.Sequence');

    // Published access session (FRK_T_AccessStateV3, Read-Only tag). The
    // repository's login flow polls these paths and reads the declared
    // LoginTimeoutMs as its result budget — the login hash runs 257
    // prehash rounds asynchronously, so the budget must be the provider's
    // own, not the repository's six-second default. Raw member reads carry
    // [addSize(2)][type(2)][instance(2)] before the struct.
    try {
      final state = await client.connectedReadRaw('FRK_${appName}_AccessState');
      const o = 6;
      int dint(int offset) =>
          ByteData.sublistView(state).getInt32(offset, Endian.little);
      final userLength = dint(o + 8).clamp(0, 32);
      final userBytes = [
        for (var i = 0; i < 32; i++) dint(o + 24 + 4 * 12 + 4 * i),
      ];
      values
        ..['Press/Access/CurrentUser'] = String.fromCharCodes(
            userBytes.take(userLength).where((b) => b != 0 && b < 128))
        ..['Press/Access/CurrentLevel'] = dint(o + 4)
        ..['Press/Access/LoginFailed'] = dint(o + 12) != 0
        ..['Press/Access/LoginBusy'] = dint(o + 16) != 0
        ..['Press/Access/LoginTimeoutMs'] = dint(o + 24 + 4 * 12 + 4 * 32)
        ..['Press/Access/LoginResultSequence'] =
            dint(o + 24 + 4 * 12 + 4 * 32 + 12) & 0xFFFFFFFF;
    } on Object {
      // A station without the access provider publishes no session keys;
      // the repository keeps its default login budget.
    }

    // The repository consumes the gateway envelope: values plus the stable
    // discovered path set.
    return {
      'values': values,
      'paths': values.keys.toList()..sort(),
    };
  }

  /// Raw connected read passthrough for diagnostics.
  Future<Uint8List> readRawConnected(String tagName) =>
      client.connectedReadRaw(tagName);

  Future<int> _readDint(String tagName) async {
    final raw = await client.connectedRead(tagName);
    if (raw.length < 4) {
      return 0;
    }
    return ByteData.sublistView(raw).getInt32(0, Endian.little);
  }


  // The V3 mailbox decodes a committed request from the native Frame words,
  // not from the legacy members: on the Sequence commit it samples
  // Frame.Words, checks Words[0] == schema and Words[last] == Sequence, then
  // rewrites Kind and the string members from the frame. Member writes
  // therefore buffer here and stage as one frame array write followed by the
  // Sequence commit — arguments first, commit word last, two round trips.
  final Map<String, Object> _staged = {};

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    final parts = path.split('/');
    if (parts.length != 3 || parts[0] != appName || parts[1] != 'HmiRequest') {
      return false;
    }
    final member = parts[2];
    if (member == 'Sequence') {
      if (type == OpcUaWriteType.string) {
        return false;
      }
      final sequence = (value as num).toInt() & 0xFFFFFFFF;
      await client.connectedWriteDints(
          'FRK_${appName}_HmiRequest.Frame.Words',
          _encodeFrame(_staged, sequence));
      _staged.clear();
      await _rawCipWriteDint('Sequence', sequence);
      return true;
    }
    final keyWidth = (await _ensureManifest()).keyWidth;
    if (_requestStringMembers.contains(member)) {
      if (type != OpcUaWriteType.string) {
        return false;
      }
      final text = value.toString();
      _staged[member] = text.length.clamp(0, keyWidth) <= text.length
          ? text
          : text.substring(0, keyWidth);
      return true;
    }
    if (type == OpcUaWriteType.string) {
      return false;
    }
    _staged[member] = type == OpcUaWriteType.boolean
        ? ((value == true) ? 1 : 0)
        : (value as num).toInt();
    return true;
  }

  /// The S9 bounded native frame (fraktal_ab_mailbox_frame.encode): schema,
  /// Kind/IntValue/BoolValue/DurationMs, the five string lengths, the packed
  /// ASCII payload padded to the argument space, and the Sequence echo —
  /// sized to the same 500-byte pylogix connection budget the generator
  /// derives word_count from, so the PLC's own length check matches.
  List<int> _encodeFrame(Map<String, Object> values, int sequence) {
    const schema = 1;
    const headerWords = 10;
    const strings = ['TargetPath', 'NameValue', 'TextValue', 'User', 'Secret'];
    const scalars = ['Kind', 'IntValue', 'BoolValue', 'DurationMs'];
    const connectionSize = 500;
    const packetOverhead = 110;
    final path = 'FRK_${appName}_HmiRequest.Frame.Words';
    final wordCount =
        (connectionSize - packetOverhead - path.length - path.length % 2) ~/ 4;
    final argumentBytes = (wordCount - headerWords - 1) * 4;

    int signed(int v) => v < 0x80000000 ? v : v - 0x100000000;
    final chunks = [
      for (final name in strings) (values[name] as String? ?? '').codeUnits,
    ];
    final payloadLength = chunks.fold<int>(0, (n, c) => n + c.length);
    if (payloadLength > argumentBytes) {
      throw CipException('string arguments exceed $argumentBytes bytes',
          payloadLength);
    }
    final words = <int>[
      schema,
      for (final name in scalars)
        signed((values[name] as int? ?? 0) & 0xFFFFFFFF),
      for (final chunk in chunks) chunk.length,
    ];
    final payload = BytesBuilder();
    for (final chunk in chunks) {
      payload.add(chunk);
    }
    final padded = Uint8List(argumentBytes)..setAll(0, payload.toBytes());
    final view = ByteData.sublistView(padded);
    for (var i = 0; i < argumentBytes ~/ 4; i++) {
      words.add(view.getInt32(i * 4, Endian.little));
    }
    words.add(signed(sequence));
    return words;
  }

  /// Write-only mailbox members (ExternalAccess=None) cannot be sized by a
  /// read, so their Write Tag services are issued with fully known types —
  /// the connected transport needs no prior read for that.
  Future<void> _rawCipWriteDint(String memberName, int value) =>
      client.connectedWriteDint('FRK_${appName}_HmiRequest.$memberName', value);

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    // snapshot() returns the repository envelope; the paths live in `values`.
    final snapshotValues =
        (await snapshot())['values'] as Map<String, Object?>? ?? const {};
    return {
      for (final path in browsePaths)
        if (snapshotValues.containsKey(path)) path: snapshotValues[path]!,
    };
  }

  @override
  Future<List<String>> discoverPaths() async {
    final values = await snapshot();
    return values.keys.toList()..sort();
  }
}

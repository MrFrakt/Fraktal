library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'opcua_session_client.dart';

/// Siemens S7 **Web API** (JSON-RPC 2.0 over HTTPS) implementation of the
/// transport-neutral session contract — the licence-free Fraktal/TIA path
/// (Part IV §1 transport decision, §11.1a). Like [AdsSessionClient] it emits the
/// SAME `fraktal.opcua.snapshot.v1` browse-path document, so the repository,
/// the snapshot mapper and every view are unchanged.
///
/// Facts this client is built on, all measured on a CPU 1214C V4.7.3
/// (Specification/Siemens/Evidence/TIA_S1W_WEBAPI_2026-10-08.md):
/// * reads are **leaf-only** — a structure or `DTL` read whole is `204`, so
///   discovery expands every structure and array to its scalar leaves;
/// * cost is ≈ 57 ms per request + ≈ 15 ms per leaf, and the CPU serves one
///   request at a time across sessions — batches stay small so a mailbox
///   acknowledgement never queues behind a large snapshot;
/// * an idle keep-alive connection is closed after 1–2 s, while the login token
///   outlives it — connections are disposable, the session is not;
/// * a second `Api.Login` on a live token answers `101`; an expired token (2.5 min
///   idle) answers `2 Permission denied` — the client logs in again once.
class WebApiSessionClient
    implements
        OpcUaBulkReadClient,
        OpcUaTieredReadClient,
        OpcUaBatchSessionClient,
        OpcUaPathDiscoveryClient {
  /// Synthetic prefix, as the ADS client uses `PLC1/MAIN`: server-specific
  /// prefixes never enter Fraktal identity (OPCUA_TRANSPORT "Snapshot").
  static const String pathPrefix = 'PLC1';

  final WebApiTransport _transport;
  final String _user;
  final String _password;
  final List<String> _roots;
  final int _batchSize;
  final int _maxLeaves;
  final Duration _slowPeriod;
  final DateTime Function() _now;

  String? _token;
  bool _closed = false;
  List<WebApiLeaf> _leaves = const [];
  Map<String, WebApiLeaf> _leafByPath = const {};
  bool _truncated = false;
  Set<String> _slow = const {};
  Set<String> _excluded = const {};
  final Map<String, Map<String, Object?>> _slowCache = {};
  DateTime? _slowReadAt;
  bool _slowForced = true;

  WebApiSessionClient._(
    this._transport, {
    required String user,
    required String password,
    required List<String> roots,
    required int batchSize,
    required int maxLeaves,
    required Duration slowPeriod,
    required DateTime Function() now,
  })  : _user = user,
        _password = password,
        _roots = List.unmodifiable(roots),
        _batchSize = batchSize,
        _maxLeaves = maxLeaves,
        _slowPeriod = slowPeriod,
        _now = now;

  /// Logs in and discovers the published tree. [roots] names the deployed root
  /// DBs (TIA §3.10.1); empty means every DB whose top level has a `Status`
  /// structure. Discovery runs here so a missing right or an unreachable CPU
  /// fails the connect, not the first operator view.
  static Future<WebApiSessionClient> connect({
    required WebApiTransport transport,
    required String user,
    required String password,
    List<String> roots = const [],
    int batchSize = 20,
    int maxLeaves = 20000,
    Duration slowPeriod = const Duration(seconds: 10),
    DateTime Function()? now,
  }) async {
    if (batchSize < 1 || batchSize > 200) {
      throw ArgumentError.value(batchSize, 'batchSize', 'must be 1..200');
    }
    final client = WebApiSessionClient._(
      transport,
      user: user,
      password: password,
      roots: roots,
      batchSize: batchSize,
      maxLeaves: maxLeaves,
      slowPeriod: slowPeriod,
      now: now ?? DateTime.now,
    );
    try {
      await client._login();
      await client._discover();
      return client;
    } on Object {
      await transport.close();
      rethrow;
    }
  }

  // ---------------------------------------------------------------- session

  Future<void> _login() async {
    // Never send the old token with Api.Login: that answers 101.
    _token = null;
    final result = await _call('Api.Login', {'user': _user, 'password': _password},
        relogin: false);
    final token = result is Map ? result['token'] : null;
    if (token is! String || token.isEmpty) {
      throw const OpcUaTransportException('Web API login returned no token.');
    }
    _token = token;
  }

  /// One JSON-RPC call. A remote error is an [OpcUaRemoteException]; transport
  /// failures stay [OpcUaTransportException]. An expired token is renewed once.
  Future<Object?> _call(String method, Object? params, {bool relogin = true}) async {
    final replies = await _batch([_Request(method, params)], relogin: relogin);
    final reply = replies.single;
    if (reply.error != null) throw OpcUaRemoteException(reply.describe(method));
    return reply.result;
  }

  int _nextId = 1;

  Future<List<_Reply>> _batch(List<_Request> requests, {bool relogin = true}) async {
    if (_closed) throw const OpcUaTransportException('Web API client closed.');
    if (requests.isEmpty) return const [];
    final ids = [for (var i = 0; i < requests.length; i++) _nextId++];
    final payload = [
      for (var i = 0; i < requests.length; i++)
        {
          'jsonrpc': '2.0',
          'id': ids[i],
          'method': requests[i].method,
          if (requests[i].params != null) 'params': requests[i].params,
        },
    ];
    final decoded = await _transport.post(payload, token: _token);
    final byId = <int, _Reply>{};
    for (final item in decoded is List ? decoded : [decoded]) {
      if (item is! Map) continue;
      final id = item['id'];
      if (id is int) byId[id] = _Reply(item['result'], item['error']);
    }
    final replies = [
      for (final id in ids)
        byId[id] ?? const _Reply(null, {'code': -1, 'message': 'no reply'}),
    ];
    // Code 2 on a session that holds a token: it expired (2.5 min idle). Log in
    // again and send ONCE more. Nothing was applied by a refused call, so the
    // resend is not a replay; a genuine missing right fails again and stands.
    if (relogin && _token != null && replies.any((r) => r.code == 2)) {
      await _login();
      return _batch(requests, relogin: false);
    }
    return replies;
  }

  // -------------------------------------------------------------- discovery

  Future<void> _discover() async {
    final roots = _roots.isNotEmpty ? _roots : await _findRoots();
    final leaves = <WebApiLeaf>[];
    var truncated = false;
    // Breadth-first, one browse request per batch of open nodes: shallow
    // contract members are found before implementation detail (OPCUA_TRANSPORT).
    var level = [for (final root in roots) _Node([root])];
    while (level.isNotEmpty && !truncated) {
      final next = <_Node>[];
      for (var i = 0; i < level.length && !truncated; i += _batchSize) {
        final chunk = level.sublist(i, i + _batchSize > level.length ? level.length : i + _batchSize);
        final replies = await _batch([
          for (final node in chunk)
            _Request('PlcProgram.Browse', {'var': node.webVar, 'mode': 'children'}),
        ]);
        for (var k = 0; k < chunk.length; k++) {
          final reply = replies[k];
          if (reply.error != null) {
            throw OpcUaRemoteException(reply.describe('PlcProgram.Browse ${chunk[k].webVar}'));
          }
          for (final child in reply.result is List ? reply.result as List : const []) {
            if (child is! Map) continue;
            final name = child['name'];
            if (name is! String || name.isEmpty) continue;
            final datatype = '${child['datatype'] ?? ''}';
            final structured = child['has_children'] == true;
            for (final segment in _segmentsFor(name, child['array_dimensions'])) {
              final node = chunk[k].child(segment);
              if (structured) {
                next.add(node);
              } else if (datatype != 'unsupported') {
                if (leaves.length >= _maxLeaves) {
                  truncated = true;
                  break;
                }
                leaves.add(WebApiLeaf(node.snapshotPath, node.webVar, datatype));
              }
            }
          }
        }
      }
      level = next;
    }
    _leaves = List.unmodifiable(leaves);
    _leafByPath = {for (final leaf in leaves) leaf.path: leaf};
    _truncated = truncated;
    _slowCache.clear();
    _slowForced = true;
  }

  /// Every DB whose top level carries a `Status` structure is a module root.
  Future<List<String>> _findRoots() async {
    final top = await _call('PlcProgram.Browse', {'mode': 'children'});
    final dbs = [
      for (final entry in top is List ? top : const [])
        if (entry is Map && entry['datatype'] == 'datablock' && entry['name'] is String)
          entry['name'] as String,
    ];
    final roots = <String>[];
    for (var i = 0; i < dbs.length; i += _batchSize) {
      final chunk = dbs.sublist(i, i + _batchSize > dbs.length ? dbs.length : i + _batchSize);
      final replies = await _batch([
        for (final db in chunk)
          _Request('PlcProgram.Browse', {'var': _Node([db]).webVar, 'mode': 'children'}),
      ]);
      for (var k = 0; k < chunk.length; k++) {
        final children = replies[k].result;
        if (children is! List) continue; // an inaccessible DB is not a root
        if (children.any((c) => c is Map && c['name'] == 'Status' && c['has_children'] == true)) {
          roots.add(chunk[k]);
        }
      }
    }
    if (roots.isEmpty) {
      throw const OpcUaTransportException(
          'Web API discovery found no DB with a Status structure: no deployed '
          'root is accessible to this user, or none is published.');
    }
    return roots;
  }

  /// `Rows` with dimensions [{start_index: 0, count: 2}] → `Rows[0]`, `Rows[1]`;
  /// a multi-dimensional array uses TIA's `Name[i,j]` form.
  static Iterable<String> _segmentsFor(String name, Object? dimensions) sync* {
    if (dimensions is! List || dimensions.isEmpty) {
      yield name;
      return;
    }
    final ranges = <List<int>>[];
    for (final d in dimensions) {
      if (d is! Map) return;
      final start = (d['start_index'] as num?)?.toInt() ?? 0;
      final count = (d['count'] as num?)?.toInt() ?? 0;
      ranges.add([for (var i = 0; i < count; i++) start + i]);
    }
    Iterable<List<int>> product(int depth) sync* {
      if (depth == ranges.length) {
        yield const [];
        return;
      }
      for (final head in ranges[depth]) {
        for (final tail in product(depth + 1)) {
          yield [head, ...tail];
        }
      }
    }

    for (final index in product(0)) {
      yield '$name[${index.join(',')}]';
    }
  }

  // --------------------------------------------------------------- snapshot

  @override
  Future<Map<String, Object?>> snapshot() async {
    final now = _now();
    final slowDue = _slowForced ||
        _slowReadAt == null ||
        now.difference(_slowReadAt!) >= _slowPeriod;
    final toRead = [
      for (final leaf in _leaves)
        if (!_excluded.contains(leaf.path) && (slowDue || !_slow.contains(leaf.path))) leaf,
    ];
    final read = await _readLeaves(toRead);
    if (slowDue) {
      _slowReadAt = now;
      _slowForced = false;
      _slowCache
        ..clear()
        ..addAll({
          for (final leaf in toRead)
            if (_slow.contains(leaf.path)) leaf.path: read[leaf.path]!,
        });
    }
    final values = <String, Object?>{};
    final dataValues = <String, Object?>{};
    for (final leaf in _leaves) {
      if (_excluded.contains(leaf.path)) continue;
      final dataValue = read[leaf.path] ?? _slowCache[leaf.path];
      if (dataValue == null) continue;
      dataValues[leaf.path] = dataValue;
      if (dataValue['status'] == 0) values[leaf.path] = dataValue['value'];
    }
    return {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'nodeCount': _leaves.length,
      'truncated': _truncated,
      'namespaces': const <String>[],
      'values': values,
      'dataValues': dataValues,
    };
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    final leaves = [
      for (final path in browsePaths)
        if (_leafByPath[path] case final leaf?) leaf,
    ];
    final read = await _readLeaves(leaves);
    return {
      for (final entry in read.entries)
        if (entry.value['status'] == 0) entry.key: entry.value['value'],
    };
  }

  @override
  Future<List<String>> discoverPaths() async => [for (final leaf in _leaves) leaf.path];

  /// Reads leaves in small batches. A per-leaf error is that leaf's Bad
  /// quality, never a stale Good value (OPCUA_TRANSPORT "Snapshot").
  Future<Map<String, Map<String, Object?>>> _readLeaves(List<WebApiLeaf> leaves) async {
    final out = <String, Map<String, Object?>>{};
    for (var i = 0; i < leaves.length; i += _batchSize) {
      final chunk = leaves.sublist(i, i + _batchSize > leaves.length ? leaves.length : i + _batchSize);
      final replies = await _batch([
        for (final leaf in chunk) _Request('PlcProgram.Read', {'var': leaf.webVar}),
      ]);
      for (var k = 0; k < chunk.length; k++) {
        final leaf = chunk[k];
        final reply = replies[k];
        out[leaf.path] = reply.error == null
            ? {'status': 0, 'type': leaf.opcUaType, 'value': reply.result}
            : {'status': _badStatus, 'type': leaf.opcUaType, 'error': reply.describe('PlcProgram.Read')};
      }
    }
    return out;
  }

  static const int _badStatus = 0x80000000;

  // ------------------------------------------------------------------ writes

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    final leaf = _leafByPath[path];
    if (leaf == null) return false;
    final replies = await _batch([_writeRequest(leaf, type, value)]);
    return replies.single.error == null;
  }

  /// One commit-last mailbox transaction (Core §3.10(a″)): every argument in
  /// one request, then the commit marker ALONE, only after every argument was
  /// accepted. Neither request relies on server-side atomicity.
  @override
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    if (writes.isEmpty) return true;
    final leaves = [for (final w in writes) _leafByPath[w.path]];
    if (leaves.any((leaf) => leaf == null)) return false;
    final arguments = [
      for (var i = 0; i < writes.length - 1; i++)
        _writeRequest(leaves[i]!, writes[i].type, writes[i].value),
    ];
    if (arguments.isNotEmpty) {
      final replies = await _batch(arguments);
      if (replies.any((r) => r.error != null)) return false;
    }
    final commit = writes.last;
    final replies = await _batch([_writeRequest(leaves.last!, commit.type, commit.value)]);
    return replies.single.error == null;
  }

  _Request _writeRequest(WebApiLeaf leaf, OpcUaWriteType type, Object value) {
    final Object json = switch (type) {
      OpcUaWriteType.boolean => value == true,
      OpcUaWriteType.int32 || OpcUaWriteType.uint32 || OpcUaWriteType.int64 => (value as num).toInt(),
      OpcUaWriteType.doubleValue => (value as num).toDouble(),
      OpcUaWriteType.string => '$value',
    };
    return _Request('PlcProgram.Write', {'var': leaf.webVar, 'value': json});
  }

  // ------------------------------------------------------------------- tiers

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    _slow = browsePaths.toSet();
  }

  @override
  Future<void> refreshSlowPaths() async {
    _slowForced = true;
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    _excluded = browsePaths.toSet();
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    try {
      if (_token != null) await _call('Api.Logout', null, relogin: false);
    } on Object {
      // logout is best effort; the token expires on its own
    }
    _closed = true;
    await _transport.close();
  }
}

/// One discovered scalar leaf: its snapshot browse path, its Web API name and
/// its Web API datatype.
final class WebApiLeaf {
  final String path;
  final String webVar;
  final String datatype;

  const WebApiLeaf(this.path, this.webVar, this.datatype);

  /// OPC UA built-in type name, as the OPC UA bridge reports it in dataValues.
  String get opcUaType => switch (datatype) {
        'bool' => 'Boolean',
        'byte' || 'usint' => 'Byte',
        'sint' => 'SByte',
        'int' => 'Int16',
        'word' || 'uint' => 'UInt16',
        'dint' => 'Int32',
        'dword' || 'udint' => 'UInt32',
        'lint' => 'Int64',
        'lword' || 'ulint' => 'UInt64',
        'real' => 'Float',
        'lreal' => 'Double',
        'string' || 'wstring' || 'char' || 'wchar' => 'String',
        _ => datatype,
      };
}

final class _Node {
  final List<String> segments;

  const _Node(this.segments);

  _Node child(String segment) => _Node([...segments, segment]);

  /// `PLC1/SpikeUnit/Rows[3]/Parent` — the ADS bridge's spelling.
  String get snapshotPath => [WebApiSessionClient.pathPrefix, ...segments].join('/');

  /// `"SpikeUnit"."Rows"[3]."Parent"` — every name quoted (measured: accepted,
  /// and it makes reserved-looking member names such as `Name` unambiguous).
  String get webVar => segments.map((segment) {
        final bracket = segment.indexOf('[');
        return bracket < 0
            ? '"$segment"'
            : '"${segment.substring(0, bracket)}"${segment.substring(bracket)}';
      }).join('.');
}

final class _Request {
  final String method;
  final Object? params;

  const _Request(this.method, this.params);
}

final class _Reply {
  final Object? result;
  final Object? error;

  const _Reply(this.result, this.error);

  int? get code {
    final e = error;
    return e is Map && e['code'] is num ? (e['code'] as num).toInt() : null;
  }

  String describe(String method) {
    final e = error;
    final message = e is Map ? e['message'] : null;
    return '$method -> ${code ?? '?'} ${message ?? ''}'.trim();
  }
}

/// The wire: POSTs one JSON-RPC payload and returns the decoded reply. Kept
/// separate so the protocol logic above is tested without a controller.
abstract interface class WebApiTransport {
  Future<Object?> post(Object payload, {String? token});
  Future<void> close();
}

/// HTTPS to `https://<host>:<port>/api/jsonrpc` over ONE persistent TLS
/// connection, trusting EXACTLY one pinned server certificate — never the
/// system roots, never "accept any". Every new connection is checked against
/// the pin.
///
/// Why not `dart:io` HttpClient: the 1214C needs ~2.75 s for every TLS
/// handshake, and HttpClient opened a new connection for every request to it
/// (a new local port each time, measured) although the CPU keeps the
/// connection open for a second request on the same socket (measured, ~60 ms).
/// A request then cost ~2.8 s instead of ~60 ms. This minimal HTTP/1.1 client
/// keeps one connection, serializes requests on it (the CPU serves one request
/// at a time anyway) and keeps it warm with `Api.Ping` before the CPU's 1–2 s
/// idle close.
final class HttpsWebApiTransport implements WebApiTransport {
  final String _host;
  final int _port;
  final List<int> _pinnedDer;
  final Duration _timeout;
  final Duration? _keepAlive;

  SecureSocket? _socket;
  StreamIterator<List<int>>? _incoming;
  List<int> _buffer = const [];
  int _offset = 0;
  Future<void> _tail = Future.value();
  Timer? _keepAliveTimer;
  bool _closed = false;
  String? _pinFailure;

  /// [pinnedCertificate] is the CPU's web server certificate as PEM or DER
  /// (captured once at commissioning, e.g. by `tia_webapi.py --trust-first`).
  /// [keepAlive] null disables the idle ping.
  HttpsWebApiTransport({
    required String host,
    int port = 443,
    required List<int> pinnedCertificate,
    Duration timeout = const Duration(seconds: 10),
    Duration? keepAlive = const Duration(milliseconds: 700),
  })  : _host = host,
        _port = port,
        _pinnedDer = certificateDer(pinnedCertificate),
        _timeout = timeout,
        _keepAlive = keepAlive;

  @override
  Future<Object?> post(Object payload, {String? token}) =>
      _serialized(() => _postWithRetry(utf8.encode(jsonEncode(payload)), token));

  /// One request at a time on the one connection.
  Future<T> _serialized<T>(Future<T> Function() action) {
    final result = _tail.then((_) => action());
    _tail = result.then<void>((_) {}, onError: (Object _, StackTrace __) {});
    return result;
  }

  Future<Object?> _postWithRetry(List<int> body, String? token) async {
    if (_closed) throw const OpcUaTransportException('Web API transport closed.');
    _keepAliveTimer?.cancel();
    final reused = _socket != null;
    try {
      return await _exchange(body, token);
    } on _ConnectionLost {
      _drop();
      // A connection the CPU closed while idle. Only a REUSED connection is
      // retried, once, on a fresh one (pin checked again). Safe: reads are
      // idempotent and the mailbox commit is inert when resent (the PLC acts
      // only on a CHANGED Sequence).
      if (!reused) throw const OpcUaTransportException('Web API connection lost.');
      try {
        return await _exchange(body, token);
      } on _ConnectionLost {
        _drop();
        throw const OpcUaTransportException('Web API connection lost.');
      }
    } finally {
      _armKeepAlive();
    }
  }

  void _armKeepAlive() {
    final period = _keepAlive;
    if (period == null || _closed || _socket == null) return;
    _keepAliveTimer = Timer(period, () {
      // Through the same queue: never interleaves with a real request.
      unawaited(_serialized<Object?>(() async {
        if (_closed || _socket == null) return null;
        try {
          return await _postWithRetry(
              utf8.encode('{"jsonrpc":"2.0","method":"Api.Ping","id":0}'), null);
        } on Object {
          return null; // the next real request reconnects
        }
      }));
    });
  }

  Future<Object?> _exchange(List<int> body, String? token) async {
    final socket = _socket ?? await _connect();
    final head = StringBuffer()
      ..write('POST /api/jsonrpc HTTP/1.1\r\n')
      ..write('Host: $_host\r\n')
      ..write('Content-Type: application/json\r\n')
      ..write('Content-Length: ${body.length}\r\n');
    if (token != null) head.write('X-Auth-Token: $token\r\n');
    head.write('\r\n');
    try {
      socket.add([...latin1.encode(head.toString()), ...body]);
      await socket.flush().timeout(_timeout);
    } on TimeoutException {
      _drop();
      throw const OpcUaTransportException('Web API request timed out (send).');
    } on IOException {
      throw const _ConnectionLost();
    }
    final List<int> responseBody;
    final int status;
    final bool closeAfter;
    try {
      final statusLine = latin1.decode(await _readLine());
      final parts = statusLine.split(' ');
      status = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
      final headers = <String, String>{};
      while (true) {
        final line = latin1.decode(await _readLine());
        if (line.isEmpty) break;
        final colon = line.indexOf(':');
        if (colon > 0) {
          headers[line.substring(0, colon).trim().toLowerCase()] = line.substring(colon + 1).trim();
        }
      }
      closeAfter = headers['connection']?.toLowerCase() == 'close';
      if (headers['transfer-encoding']?.toLowerCase().contains('chunked') == true) {
        final out = <int>[];
        while (true) {
          final sizeLine = latin1.decode(await _readLine());
          final size = int.parse(sizeLine.split(';').first.trim(), radix: 16);
          if (size == 0) {
            while ((await _readLine()).isNotEmpty) {} // trailers, then the blank line
            break;
          }
          out.addAll(await _readExactly(size));
          await _readLine();
        }
        responseBody = out;
      } else {
        final length = int.tryParse(headers['content-length'] ?? '');
        if (length == null) throw const _ConnectionLost(); // no framing: unusable
        responseBody = await _readExactly(length);
      }
    } on TimeoutException {
      _drop(); // the connection's state is unknown: never reuse it
      throw const OpcUaTransportException('Web API request timed out (reply).');
    } on FormatException catch (error) {
      _drop();
      throw OpcUaTransportException('Web API reply is not valid HTTP', error);
    }
    if (closeAfter) _drop();
    if (status != 200) throw OpcUaTransportException('Web API HTTP $status');
    try {
      return jsonDecode(utf8.decode(responseBody));
    } on FormatException catch (error) {
      throw OpcUaTransportException('Web API reply is not JSON', error);
    }
  }

  Future<SecureSocket> _connect() async {
    _pinFailure = null;
    try {
      // No trusted roots: every certificate reaches onBadCertificate, which
      // accepts exactly the pinned one. A CA-signed certificate cannot bypass it.
      final socket = await SecureSocket.connect(
        _host,
        _port,
        context: SecurityContext(withTrustedRoots: false),
        onBadCertificate: (certificate) {
          final ok = _sameBytes(certificate.der, _pinnedDer);
          if (!ok) _pinFailure = 'server certificate "${certificate.subject}" is not the pinned one';
          return ok;
        },
        timeout: _timeout,
      ).timeout(_timeout);
      socket.setOption(SocketOption.tcpNoDelay, true);
      _socket = socket;
      _incoming = StreamIterator(socket);
      _buffer = const [];
      _offset = 0;
      return socket;
    } on HandshakeException catch (error) {
      throw OpcUaTransportException(_pinFailure ?? 'TLS handshake failed', error);
    } on TimeoutException catch (error) {
      throw OpcUaTransportException('Web API connect timed out', error);
    } on SocketException catch (error) {
      throw OpcUaTransportException('Web API connect failed', error);
    }
  }

  Future<bool> _fill() async {
    final incoming = _incoming;
    if (incoming == null) return false;
    final more = await incoming.moveNext().timeout(_timeout);
    if (!more) return false;
    _buffer = [..._buffer.sublist(_offset), ...incoming.current];
    _offset = 0;
    return true;
  }

  Future<List<int>> _readLine() async {
    while (true) {
      for (var i = _offset; i + 1 < _buffer.length; i++) {
        if (_buffer[i] == 13 && _buffer[i + 1] == 10) {
          final line = _buffer.sublist(_offset, i);
          _offset = i + 2;
          return line;
        }
      }
      if (!await _fill()) throw const _ConnectionLost();
    }
  }

  Future<List<int>> _readExactly(int count) async {
    while (_buffer.length - _offset < count) {
      if (!await _fill()) throw const _ConnectionLost();
    }
    final out = _buffer.sublist(_offset, _offset + count);
    _offset += count;
    return out;
  }

  void _drop() {
    _socket?.destroy();
    _socket = null;
    _incoming = null;
    _buffer = const [];
    _offset = 0;
  }

  @override
  Future<void> close() async {
    _closed = true;
    _keepAliveTimer?.cancel();
    await _tail;
    _drop();
  }

  /// PEM (`-----BEGIN CERTIFICATE-----`) or DER bytes → DER.
  static List<int> certificateDer(List<int> bytes) {
    final text = latin1.decode(bytes, allowInvalid: true);
    const begin = '-----BEGIN CERTIFICATE-----';
    const end = '-----END CERTIFICATE-----';
    final start = text.indexOf(begin);
    if (start < 0) return List.unmodifiable(bytes);
    final stop = text.indexOf(end, start);
    if (stop < 0) throw const FormatException('PEM certificate has no END line.');
    final base64Body = text.substring(start + begin.length, stop).replaceAll(RegExp(r'\s'), '');
    return List.unmodifiable(base64.decode(base64Body));
  }

  static bool _sameBytes(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    var diff = 0;
    for (var i = 0; i < a.length; i++) {
      diff |= a[i] ^ b[i];
    }
    return diff == 0;
  }
}

/// The server closed the connection before a complete reply.
final class _ConnectionLost implements Exception {
  const _ConnectionLost();
}

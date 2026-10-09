// Dev probe: speak the fraktal.opcua.gateway.v1 WebSocket protocol to a running
// gateway exactly as the Web HMI does — discovery, snapshot, one mailbox
// transaction (SET_MODE to the mode already active: accepted, nothing moves),
// and one write outside the write root that the GATEWAY must refuse.
//
//   dart run tool/probe_gateway_ws.dart <ws://127.0.0.1:PORT/fraktal> <root browse path> [snapshot.json]
//   e.g. dart run tool/probe_gateway_ws.dart ws://127.0.0.1:8099/fraktal PLC1/SpikeUnit
import 'dart:async';
import 'dart:convert';
import 'dart:io';

Future<void> main(List<String> args) async {
  final url = Uri.parse(args[0]);
  final root = args[1];
  final socket = await WebSocket.connect(url.toString(),
      headers: {'Origin': 'http://127.0.0.1:${url.port}'});
  final replies = <int, Completer<Map<String, Object?>>>{};
  socket.listen((message) {
    final decoded = jsonDecode(message as String) as Map<String, Object?>;
    replies.remove(decoded['id'])?.complete(decoded);
  });
  var nextId = 1;
  Future<Map<String, Object?>> call(String method, [Map<String, Object?> params = const {}]) {
    final id = nextId++;
    final done = Completer<Map<String, Object?>>();
    replies[id] = done;
    socket.add(jsonEncode({'protocol': 'fraktal.opcua.gateway.v1', 'id': id, 'method': method, 'params': params}));
    return done.future.timeout(const Duration(seconds: 60));
  }

  try {
    var w = Stopwatch()..start();
    final discovered = await call('discoverPaths');
    final paths = ((discovered['result'] as Map)['paths'] as List).cast<String>();
    stdout.writeln('[ws] discoverPaths ok=${discovered['ok']} paths=${paths.length} in ${w.elapsedMilliseconds}ms');

    w = Stopwatch()..start();
    var snap = await call('snapshot');
    var values = ((snap['result'] as Map)['values'] as Map);
    stdout.writeln('[ws] snapshot ok=${snap['ok']} values=${values.length} in ${w.elapsedMilliseconds}ms '
        'protocol=${(snap['result'] as Map)['protocol']}');
    if (args.length > 2) {
      // Optional: keep the exact snapshot document as a mapper fixture.
      File(args[2]).writeAsStringSync(const JsonEncoder.withIndent(' ').convert(snap['result']));
      stdout.writeln('[ws] snapshot written to ${args[2]}');
    }
    stdout.writeln('[ws]   $root/Status/Name=${values['$root/Status/Name']} '
        'ModuleType=${values['$root/Status/ModuleType']} Mode=${values['$root/Mode']}');

    final mode = values['$root/Mode'] as int;
    final next = ((values['$root/HmiRequest/Sequence'] as int) + 1) & 0xFFFFFFFF;
    w = Stopwatch()..start();
    final batch = await call('writeBatch', {
      'writes': [
        {'path': '$root/HmiRequest/Kind', 'valueType': 'int32', 'value': 3},
        {'path': '$root/HmiRequest/IntValue', 'valueType': 'int32', 'value': mode},
        {'path': '$root/HmiRequest/Sequence', 'valueType': 'uint32', 'value': next},
      ]
    });
    final ackIndex = paths.indexOf('$root/HmiResponse/AckSequence');
    final acceptedIndex = paths.indexOf('$root/HmiResponse/Accepted');
    Map ack = const {};
    while (w.elapsed < const Duration(seconds: 5)) {
      final read = await call('readValues', {
        'revision': (discovered['result'] as Map)['revision'],
        'indices': [ackIndex, acceptedIndex],
      });
      ack = (read['result'] as Map?) ?? const {};
      final ackValues = ack['values'] is Map ? ack['values'] as Map : ack;
      if (ackValues['$root/HmiResponse/AckSequence'] == next) {
        ack = ackValues;
        break;
      }
    }
    stdout.writeln('[ws] writeBatch SET_MODE($mode) seq=$next ok=${batch['ok']} result=${batch['result']} '
        'ack=${ack['$root/HmiResponse/AckSequence'] == next} accepted=${ack['$root/HmiResponse/Accepted']} '
        'in ${w.elapsedMilliseconds}ms');

    final outside = await call('writeBatch', {
      'writes': [
        {'path': '$root/Status/State', 'valueType': 'int32', 'value': 3},
      ]
    });
    stdout.writeln('[ws] write outside HmiRequest: ok=${outside['ok']} error="${outside['error']}" (expect refused)');

    final replay = await call('writeBatch', {
      'writes': [
        {'path': '$root/HmiRequest/Kind', 'valueType': 'int32', 'value': 3},
        {'path': '$root/HmiRequest/IntValue', 'valueType': 'int32', 'value': mode},
        {'path': '$root/HmiRequest/Sequence', 'valueType': 'uint32', 'value': next},
      ]
    });
    stdout.writeln('[ws] same Sequence again: ok=${replay['ok']} result=${replay['result']} (expect false: no replay)');
  } finally {
    await socket.close();
  }
  exit(0);
}

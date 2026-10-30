from pathlib import Path
W=Path(__file__).parent
raw=(W/'packet_timing_01.dart').read_text()
start=raw.index('  final transport = TimedWire(')
end=raw.index('  final outcomes =',start)
raw=raw[:start]+'''  final transports = <TimedWire>[];
  for(var i=0;i<4;i++) {
    transports.add(TimedWire(await CipSocketTransport.connect(host:'127.0.0.1',slot:0,expectSerial:'601FC87B')));
  }
  final transport=transports.first;
  final pool=CipReadPool.fromConnected(transports);
'''+raw[end:]
needle='    transport.counters.addAll('
assert raw.count(needle)==1
raw=raw.replace(needle,'    for(final transport in transports) transport.counters.addAll(')
needle='      transport.phase = phase;';assert raw.count(needle)==1
raw=raw.replace(needle,'      for(final transport in transports) transport.phase = phase;')
raw=raw.replace("'connections': 1","'connections': 4")
raw=raw.replace("'events': transport.events,","'events': [for(var i=0;i<transports.length;i++) for(final e in transports[i].events) {'socket':i,...e}],")
raw=raw.replace("'events': transport.events.length,","'events': transports.fold<int>(0,(n,t)=>n+t.events.length),")
raw=raw.replace('not four-connection client acceptance','not UI/worker acceptance')
with (W/'packet_timing_02.dart').open('x') as f:f.write(raw)
print('Read-only four-socket comparison prepared; no values or writes logged')

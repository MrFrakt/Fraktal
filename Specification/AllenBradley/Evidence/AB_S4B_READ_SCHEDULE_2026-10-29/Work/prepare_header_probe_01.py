from pathlib import Path
W=Path(__file__).parent
OLD=Path('C:/work/fraktal-ab-s4b-observer-20261029/offline_01/qualify_observer_peer_01.py')
raw=OLD.read_text(encoding='utf-8')
raw=raw.replace("W/'observer_peer_wire_01.log'","W/'header_peer_wire_01.log'")
start=raw.index('        command=[')
end=raw.index('    finally:',start)
raw=raw[:start]+'''        command=[str(DART),'--packages='+str(H/'.dart_tool/package_config.json'),
            str(W/'header_probe_01.dart'),endpoint,str(W/'header_probe_01.json.gz')]
        with (W/'header_probe_01.log').open('x',encoding='utf-8') as output:
            completed=subprocess.run(command,cwd=H,stdout=output,stderr=subprocess.STDOUT,timeout=180,**flags)
'''+raw[end:]
raw=raw[:raw.index('report=json.loads')]+'''assert completed.returncode==0 and peer_code==0 and not forced
report=json.loads(gzip.decompress((W/'header_probe_01.json.gz').read_bytes()))
assert report['measurementComplete'] and report['controllerChanges']==0
last=lines[-1];assert last['controllerWrites']==last['refusedServices']==0
print(json.dumps(dict(measurementComplete=True,samples=len(report['outcomes']),
    firstRefused=not report['outcomes'][-1]['good'],controllerChanges=0)))
'''
with (W/'run_header_probe_01.py').open('x') as f:f.write(raw)

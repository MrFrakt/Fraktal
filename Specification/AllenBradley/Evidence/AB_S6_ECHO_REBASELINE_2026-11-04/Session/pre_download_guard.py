"""Read-only precondition: Echo 601FC87B is factory-empty, unfaulted and dump-free.

The owner factory-reset Echo on 2026-11-04 (its previous storage is archived
under Documents\\EchoFactoryResetBackup\\Root_20261104_133216). This session may
only re-establish the pinned genealogy baseline on that empty controller, so it
refuses unless the controller still publishes no controller-scope tag. The
first run records the state; --verify-only re-checks it without replacing it.
"""
from pathlib import Path
import datetime, json, subprocess, sys
from pylogix import PLC

D = Path(__file__).parent
DUMPS = Path('C:/ProgramData/Rockwell Software/FactoryTalk Logix Echo/Controllers/'
             '91dec7d6-8ac3-45c9-ab2e-0d039c7006fd/Root')
subprocess.run([sys.executable, str(D / 'scripts/guard_echo.py')], check=True)
dumps = sorted(p.relative_to(DUMPS).as_posix() for p in DUMPS.rglob('*.dmp')) if DUMPS.exists() else []
with PLC('127.0.0.1') as comm:
    comm.ProcessorSlot, comm.SocketTimeout = 0, 5
    tags = comm.GetTagList(allTags=False)
    programs = comm.GetProgramsList()
report = dict(readOnly=True, serial='601FC87B', dumpFiles=dumps, tagListStatus=tags.Status,
              controllerTags=len(tags.Value or []), programListStatus=programs.Status,
              programs=list(programs.Value or []),
              capturedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
report['factoryEmpty'] = (tags.Status == 'Success' and report['controllerTags'] == 0
                          and not report['programs'])
report['passed'] = report['factoryEmpty'] and not dumps
name = 'pre_download_guard_verify.json' if '--verify-only' in sys.argv else 'pre_download_guard.json'
with (D / name).open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)

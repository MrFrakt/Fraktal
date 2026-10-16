"""Own one disposable simulator host for a fixed Target and always release it."""
from contextlib import contextmanager
import json
import re
import subprocess
import time
from pathlib import Path


@contextmanager
def hosted(target,label):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,64}',label):raise ValueError('invalid evidence label')
    stop=target.work/(label+'.stop');log=target.work/(label+'.host.log');err=target.work/(label+'.host.stderr')
    if any(p.exists() for p in (stop,log,err)):raise ValueError('session evidence must be new')
    helper=Path(__file__).with_name('Invoke-TiaIsolatedBench.ps1')
    with log.open('xb') as stdout,err.open('xb') as stderr:
        process=subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(helper),
            '-Profile',str(target.profile_path),'-Action','host','-StopFile',str(stop)],
            stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+90
            while True:
                rows=[]
                for line in log.read_text('utf-8-sig').splitlines():
                    try:rows.append(json.loads(line))
                    except ValueError:pass
                if any(r.get('event')=='bench' for r in rows):break
                if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('isolated simulator host did not become ready: '+str(err))
                time.sleep(.25)
            yield
        finally:
            # A resource monitor or operator may already have requested stop.
            # Always wait for host cleanup, including that early-stop path.
            stop.touch(exist_ok=True)
            process.wait(timeout=60)
            if process.returncode:raise RuntimeError('simulator session failed; inspect '+str(err))

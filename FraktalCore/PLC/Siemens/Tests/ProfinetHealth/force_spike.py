"""Force-job detection spike (P8, owner decision 3B): what can see a TIA force job?

TIA force tables have no runtime API. This hosts the PROFINET fixture (its
central DQ_1 is a real, forceable output address) with its web server on, and
records, every two seconds while the owner starts and stops a force job in TIA
Portal: the LED instruction's STOP/RUN, ERROR and MAINT states as the program
sees them, the operating mode and the diagnostic buffer as a host sees them,
plus once the firmware's complete Web API method list. Nothing is asserted;
the observations decide what Fraktal can annunciate.

Run every stage through Tests/Access/with_credentials.ps1 (-Action probe
-ScriptFile this file -Output <stage>:<label>): prepare, then session (in the
background), then stop.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
HERE = Path(__file__).resolve().parent; TIA = HERE.parents[1]
sys.path.insert(0, str(TIA/'tools')); sys.path.insert(0, str(TIA/'Tests/Line'))
from fraktal_tia_gate import compile_fresh
from owner_target import Target
from tia_isolated_session import hosted
from tia_webapi import WebApi, WebApiError, leaf_var
# Loaded under its own name: `make_fixture` is the Line suite's, which run_bench imports.
_spec = importlib.util.spec_from_file_location('profinet_fixture', HERE/'make_fixture.py')
make_fixture = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(make_fixture)

LOCAL = Path(os.environ['LOCALAPPDATA'])/'Fraktal'
STATION = 'FrkPnForce'
PERIOD_S = 2.0
LEDS = ('stop_run', 'error', 'maint')


def paths(label):
    if not re.fullmatch(r'P8_ForceSpike_\d{8}_\d{2}', label): raise ValueError('new dated evidence label required')
    work = LOCAL/'TiaSpikes'/label
    return work, work/'revision', LOCAL/'TiaStations'/label, LOCAL/'TiaStations'/(label + '.webapi.pin')


def target(label):
    work, _, stations, _ = paths(label)
    return Target(HERE/'bench.json', work, stations/STATION/(STATION + '.ap20'))


def prepare(label):
    work, revision, stations, pin = paths(label)
    if pin.exists(): raise ValueError('a fresh project needs a fresh certificate pin')
    work.mkdir(parents=True, exist_ok=False)
    sources, labels = make_fixture.build(); (revision/'sources').mkdir(parents=True)
    for name, text in sources.items(): (revision/'sources'/name).write_bytes(text.encode('ascii'))
    compile_fresh(revision, stations, STATION, HERE/'bench.json', work/'compile.log', make_fixture.HARDWARE)
    target(label).configure_web(work/'web_user.log', enable=True)


def observe(api, emit):
    def attempt(method, params=None):
        try: return dict(ok=api.call(method, params))
        except WebApiError as error: return dict(error=str(error))
    leds = {}
    for index, name in enumerate(LEDS, 1):
        leds[name] = attempt('PlcProgram.Read', {'var': leaf_var(['GDB_ProfinetTest', 'LedReturn[%d]' % index])})
    emit(dict(event='observation', leds=leds, mode=attempt('Plc.ReadOperatingMode'),
              diagnostics=attempt('DiagnosticBuffer.Browse', {'language': 'en-US', 'count': 8})))


def session(label):
    work, revision, _, pin = paths(label)
    bench = target(label)
    if not (work/'web_user.log').is_file(): raise ValueError('prepare the fixture first')
    stop = work/'spike.stop'
    with hosted(bench, 'session'):
        bench.download(revision, attempt='download')
        api = WebApi(bench.profile['address'], pin, not pin.exists())
        with (work/'observations.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            def emit(row): stream.write(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **row)) + '\n'); stream.flush()
            try:
                api.login('fraktal')
                emit(dict(event='methods', methods=api.call('Api.Browse')))
                while not stop.exists():
                    observe(api, emit); time.sleep(PERIOD_S)
                observe(api, emit)
            finally:
                if api.conn: api.conn.close()


def stop(label):
    paths(label)[0].joinpath('spike.stop').touch(exist_ok=False)


if __name__ == '__main__':
    stage, label = sys.argv[1].split(':', 1)
    {'prepare': prepare, 'session': session, 'stop': stop}[stage](label)

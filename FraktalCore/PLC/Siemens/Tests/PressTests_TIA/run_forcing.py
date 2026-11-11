"""Engineering press image: fresh compile and read-back, one isolated download, live forcing probe.

Run through Tests/Access/with_credentials.ps1 (-Action probe -ScriptFile this file),
which supplies the existing DPAPI web credential. The label names new local
TiaSpikes/TiaStations directories and an unused certificate pin. `prepare`
and `web` need no test CPU; `live` hosts one, so it runs separately once the
host has the memory for a powered test CPU beside TIA Portal.
"""
import json
import os
from pathlib import Path
import re
import sys
HERE=Path(__file__).resolve().parent;TIA=HERE.parents[1]
sys.path.insert(0,str(TIA/'tools'));sys.path.insert(0,str(HERE.parent/'Line'))
import fraktal_tia_examples as examples
from fraktal_tia_gate import compile_fresh
from owner_target import Target
from tia_isolated_session import hosted
from probe_forcing import probe

LOCAL=Path(os.environ['LOCALAPPDATA'])/'Fraktal'
STATION='FrkPressForce'


def paths(label):
    if not re.fullmatch(r'P8_PressForceLive_\d{8}_\d{2}',label):raise ValueError('new dated evidence label required')
    work=LOCAL/'TiaSpikes'/label
    return work,work/'revision',LOCAL/'TiaStations'/label,LOCAL/'TiaStations'/(label+'.webapi.pin')


def prepare(label):
    work,revision,stations,pin=paths(label)
    if pin.exists():raise ValueError('a fresh project needs a fresh certificate pin')
    work.mkdir(parents=True,exist_ok=False)
    definition=json.loads((examples.EXAMPLE/'press.json').read_bytes())
    definition['integration']['output_forcing']=True
    examples.generate(revision/'sources',definition)
    compile_fresh(revision,stations,STATION,HERE/'bench.json',work/'compile.log')


def web(label):
    """A fresh gate project serves no web: switch it on, then add the user."""
    work,revision,stations,pin=paths(label)
    if not (revision/'owner_verified_private.json').is_file():raise ValueError('prepare the compiled image first')
    Target(HERE/'bench.json',work,stations/STATION/(STATION+'.ap20')).configure_web(work/'web_user.log',enable=True)


def live(label,attempt='1'):
    """Each attempt keeps its own session, download and probe evidence; none is overwritten."""
    work,revision,stations,pin=paths(label)
    if not attempt.isdigit():raise ValueError('attempt is a number')
    suffix='' if attempt=='1' else attempt
    target=Target(HERE/'bench.json',work,stations/STATION/(STATION+'.ap20'))
    if not (work/'web_user.log').is_file():raise ValueError('prepare the offline web user first')
    with hosted(target,'session'+suffix):
        target.download(revision,attempt='download'+suffix)
        probe(target,work/('probe'+suffix+'.jsonl'),pin)


if __name__=='__main__':
    stage,label,*attempt=sys.argv[1].split(':')
    {'prepare':prepare,'web':web,'live':live}[stage](label,*attempt)

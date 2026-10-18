"""Compile/read-back witnesses precede every isolated download; DPAPI wrapper owns credentials."""
from pathlib import Path
import sys
from target import TARGET,WORK
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from tia_isolated_session import hosted
from probe_live import probe

def run(revision,label,provision=True):
    revision=revision.resolve()
    if revision.parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    if provision:TARGET.configure_web(WORK/(label+'_web.log'))
    with hosted(TARGET,label):
        TARGET.download(revision,attempt=label)
        probe(WORK/(label+'.jsonl'))

if __name__=='__main__':
    revision=Path(sys.argv[1]);run(revision,revision.name+'_press_live')

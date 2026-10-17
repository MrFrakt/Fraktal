"""Compile separately, then download once and always release the test CPU."""
from pathlib import Path
import sys
from target import TARGET,WORK
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from tia_isolated_session import hosted
from probe_live import probe


def run(revision,label=None):
    revision=revision.resolve()
    if revision.parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    label=label or revision.name+'_models'
    with hosted(TARGET,label):
        TARGET.download(revision,attempt=label)
        probe(WORK/(label+'.jsonl'))


if __name__=='__main__':run(Path(sys.argv[1]))

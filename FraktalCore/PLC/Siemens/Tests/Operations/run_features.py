"""Re-run the live two-root feature fixture with guaranteed isolated cleanup."""
from pathlib import Path
import sys
from target import TARGET,WORK
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from tia_isolated_session import hosted
from probe_features import probe


def run(revision,label=None):
    revision=revision.resolve()
    if revision.parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    label=label or revision.name+'_features'
    with hosted(TARGET,label):
        TARGET.download(revision,attempt=label)
        probe(WORK/(label+'.jsonl'))


if __name__=='__main__':run(Path(sys.argv[1]))

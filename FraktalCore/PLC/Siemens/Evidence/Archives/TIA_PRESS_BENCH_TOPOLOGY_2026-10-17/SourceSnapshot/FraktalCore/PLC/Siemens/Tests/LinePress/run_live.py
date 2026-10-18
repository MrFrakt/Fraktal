"""Download only after offline compile/read-back; always close the test CPU."""
import importlib.util
from pathlib import Path
import sys
from target import TARGET,WORK
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from tia_isolated_session import hosted
from probe_live import probe


def run(revision,label=None):
    revision=revision.resolve()
    if revision.parent!=WORK.resolve():raise ValueError('fixed isolated workspace required')
    label=label or revision.name+'_line_press'
    with hosted(TARGET,label):
        TARGET.download(revision,attempt=label)
        probe(WORK/(label+'.jsonl'))
        # Reuse the shipped wired-GRAPH checks against the same deployed press.
        path=Path(__file__).resolve().parent.parent/'PressTests_TIA/probe_live.py'
        spec=importlib.util.spec_from_file_location('line_press_graph_regression',path)
        regression=importlib.util.module_from_spec(spec);spec.loader.exec_module(regression)
        regression.TARGET=TARGET;regression.WORK=WORK
        regression.probe(WORK/(label+'_graph.jsonl'))


if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else None)

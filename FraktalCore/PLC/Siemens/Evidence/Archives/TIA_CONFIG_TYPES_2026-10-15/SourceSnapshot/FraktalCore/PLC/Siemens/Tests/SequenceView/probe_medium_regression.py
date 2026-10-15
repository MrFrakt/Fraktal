"""Run the existing view outcomes on the combined medium fixture."""
import argparse
from pathlib import Path
from probe_web import probe

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path)
    print({'checks':probe(p.parse_args().out,expect_medium=True)})

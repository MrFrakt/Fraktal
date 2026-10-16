"""Explicit second virtual CPU for the source-bound mirror workbench."""
import os
from pathlib import Path
import sys

from owner_target import Target, original, TIA, HERE

WORK = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Line_Mirror_20261016'
PROFILE_PATH = HERE/'bench_mirror.json'
PROJECT = Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Line_Mirror_Runtime_20261016/FrkS12/FrkS12.ap20'
TARGET = Target(PROFILE_PATH, WORK, PROJECT)
PROFILE = TARGET.profile
action, guard = TARGET.action, TARGET.guard


if __name__ == '__main__':
    if sys.argv[1] == '--provision-web': TARGET.provision_web(Path(sys.argv[2]))
    else: TARGET.download(Path(sys.argv[1]))

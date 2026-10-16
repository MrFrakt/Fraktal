"""One fixed unmapped .55 accounting/test-runner bench."""
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Line'))
from owner_target import Target,original

WORK=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Operations_20261016'
PROJECT=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Operations_20261016/FrkS12/FrkS12.ap20'
TARGET=Target(HERE/'bench.json',WORK,PROJECT)

if __name__=='__main__':TARGET.download(Path(sys.argv[1]))

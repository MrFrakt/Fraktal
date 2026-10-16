"""Dedicated unmapped press feature bench; never the saved Fraktal instance."""
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Line'))
from owner_target import Target,original

WORK=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Operations_20261016'
PROJECT=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Press_Features_20261016/FrkS12/FrkS12.ap20'
TARGET=Target(HERE/'bench.json',WORK,PROJECT)

if __name__=='__main__':
    if sys.argv[1]=='--provision-web':TARGET.provision_web(Path(sys.argv[2]))
    else:TARGET.download(Path(sys.argv[1]))

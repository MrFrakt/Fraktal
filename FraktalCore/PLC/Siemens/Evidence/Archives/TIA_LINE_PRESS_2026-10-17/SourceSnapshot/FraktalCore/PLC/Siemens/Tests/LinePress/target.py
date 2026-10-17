"""One reserved unmapped press CPU, with the existing offline project/pin."""
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Line'))
from owner_target import Target,original
WORK=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Line_Press_20261017'
PROJECT=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Press_Features_20261016/FrkS12/FrkS12.ap20'
TARGET=Target(HERE.parent/'PressTests_TIA/bench.json',WORK,PROJECT)

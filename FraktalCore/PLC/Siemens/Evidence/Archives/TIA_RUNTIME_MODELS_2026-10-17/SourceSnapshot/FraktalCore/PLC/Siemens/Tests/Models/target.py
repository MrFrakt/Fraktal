"""Reuse one reserved CPU and saved offline project; preserve original Fraktal."""
import os
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'Line'))
from owner_target import Target,original
WORK=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaSpikes/Models_20261017'
PROJECT=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Operations_20261016/FrkS12/FrkS12.ap20'
TARGET=Target(HERE.parent/'Operations/bench.json',WORK,PROJECT)

"""Disposable local Echo tower fixture: semantic outputs, no electrical I/O."""
from dataclasses import replace
import fraktal_ab_part_demo as part
from fraktal_ab_signal_tower import SignalTower


def application():
    return replace(part.application(), signal_tower=SignalTower())

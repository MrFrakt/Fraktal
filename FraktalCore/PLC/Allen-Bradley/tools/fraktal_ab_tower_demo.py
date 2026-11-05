"""Disposable local Echo tower fixture: semantic outputs, no electrical I/O."""
from dataclasses import replace
import fraktal_ab_part_demo as part
from fraktal_ab_signal_tower import SignalTower
import fraktal_ab_document_revision as document_revision


def application():
    return replace(part.application(), signal_tower=SignalTower(), config_predecessors=document_revision.recorded('fraktal_ab_tower_demo', '6F3F8CDA9A8F6B59'))

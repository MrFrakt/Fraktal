"""Which station declaration the generic Fraktal/AB tools serve.

The generator, the projection, the gateway and the manifest reader are not the
press's: they serve whatever station is declared. One environment variable
names the declaration module - any importable module exposing `application()`
- and every one of them reads it here, so a new station is selected in one
place and never by editing a tool:

    set FRAKTAL_AB_DECLARATION=fraktal_ab_station_template

Unset, the station is the press demo, which is what this repository's
evidence and bench harnesses are written against. The press harnesses
(`fraktal_ab_press_execute.py`, the phase and parity harnesses) remain the
press's and refuse any other controller by their fingerprint.
"""

from __future__ import annotations

import importlib
import os

ENV = "FRAKTAL_AB_DECLARATION"
DEFAULT = "fraktal_ab_press_demo"


def module_name() -> str:
    return os.environ.get(ENV, "").strip() or DEFAULT


def application():
    """The selected station's declaration."""
    return importlib.import_module(module_name()).application()

#!/usr/bin/env python3
"""The press declaration on Echo carrying AUTO in all three renditions.

fraktal_ab_press_echo38 with one deployment choice changed: AUTO is emitted in
ST, SFC and LD. The L24ER carries the ladder alone to fit its memory (owner,
2026-10-07); the AUTO graph is the same single declaration, so that selection is
a subset of this one. This is the legacy oracle for the press S3 exit candidate.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_press_echo38 as echo


def application() -> decl.Application:
    base = echo.application()
    return replace(base, chains=tuple(replace(c, renditions=decl.RENDITIONS) if c.name == 'AUTO' else c
                                      for c in base.chains))


def generate(source: Path, output: Path) -> dict[str, object]:
    import fraktal_ab_generate
    return fraktal_ab_generate.generate(application(), source, output)

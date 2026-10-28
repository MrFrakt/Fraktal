#!/usr/bin/env python3
"""S3 exit candidate: the authoritative press declaration with the accepted S3k publication.

Equipment, recipes, chains and policy come from fraktal_ab_press_rendition_echo38:
the press declaration retargeted to Echo, carrying AUTO in all three renditions.
Only the canonical publication choices accepted on the genealogy bench are added.
Echo emulates no electrical I/O, so the press's reviewed I/O catalog is bound to a
sampled-word source, exactly as the S3j bench did; physical-module identity
remains a separate gate.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import fraktal_ab_declaration as decl
import fraktal_ab_press_demo as press
import fraktal_ab_press_rendition_echo38 as oracle


def application() -> decl.Application:
    return replace(oracle.application(), canonical_publication_stage=13, canonical_observation_period_ms=50,
                   canonical_table_driven=True, canonical_type_manifest=True, canonical_io_fixture=True,
                   io_modules=(replace(press._press_io(), sample_tag='FRK_Press_SimIo',
                                       type_id='Fixture: sampled controller words'),))


def generate(source: Path, output: Path) -> dict[str, object]:
    import fraktal_ab_generate
    return fraktal_ab_generate.generate(application(), source, output)

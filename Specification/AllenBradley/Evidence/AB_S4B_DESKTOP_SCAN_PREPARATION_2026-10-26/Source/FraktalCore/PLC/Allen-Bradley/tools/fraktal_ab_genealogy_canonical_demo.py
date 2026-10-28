"""Gated S2 migration image of the genealogy bench; no deployment action."""
from dataclasses import replace

import fraktal_ab_genealogy_demo as genealogy


def application():
    return replace(genealogy.application(), canonical_publication_stage=2)


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)

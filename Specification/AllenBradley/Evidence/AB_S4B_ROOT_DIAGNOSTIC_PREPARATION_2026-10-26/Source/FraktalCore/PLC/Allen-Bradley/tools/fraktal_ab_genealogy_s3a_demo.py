"""Gated S3a genealogy migration image; this declaration grants no deployment."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


def application():
    return replace(genealogy.application(), canonical_publication_stage=3)


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)

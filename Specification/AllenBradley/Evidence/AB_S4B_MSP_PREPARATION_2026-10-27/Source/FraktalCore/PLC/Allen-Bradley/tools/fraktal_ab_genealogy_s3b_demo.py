"""Offline S3b migration candidate; this declaration grants no deployment."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


def application():return replace(genealogy.application(),canonical_publication_stage=4)


def generate(source,output):
    import fraktal_ab_generate as gen
    return gen.generate(application(),source,output)

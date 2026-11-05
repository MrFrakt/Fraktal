"""Offline S3b migration candidate; this declaration grants no deployment."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_document_revision as document_revision


def application():return replace(genealogy.application(),canonical_publication_stage=4, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3b_demo', '6F3F8CDA9A8F6B59'))


def generate(source,output):
    import fraktal_ab_generate as gen
    return gen.generate(application(),source,output)

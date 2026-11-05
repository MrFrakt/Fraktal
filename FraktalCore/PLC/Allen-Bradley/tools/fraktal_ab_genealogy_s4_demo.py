"""S4 engineering profile: the accepted S3k values plus V6.7 guard bindings."""
from dataclasses import replace
import fraktal_ab_genealogy_s3k_demo as previous
import fraktal_ab_document_revision as document_revision


def application():
    return replace(previous.application(), canonical_read_coherence=True, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s4_demo', '6F3F8CDA9A8F6B59'))

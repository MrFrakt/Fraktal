"""Approved V6.10 owner-revision qualification profile; V6.8 stays frozen."""
from dataclasses import replace
import fraktal_ab_genealogy_s4b_demo as previous
import fraktal_ab_document_revision as document_revision


def application():
    return replace(previous.application(), canonical_owner_revisions=True, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s4b_owner_demo', '6F3F8CDA9A8F6B59'))

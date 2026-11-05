"""S4b engineering profile: approved V6.8 read-only configuration discovery."""
from dataclasses import replace
import fraktal_ab_genealogy_s4_demo as previous
import fraktal_ab_document_revision as document_revision


def application():return replace(previous.application(),canonical_config_read_view=True, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s4b_demo', '6F3F8CDA9A8F6B59'))

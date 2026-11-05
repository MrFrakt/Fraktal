"""S3g candidate. Selecting a declaration grants no controller authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_document_revision as document_revision


def application():return replace(genealogy.application(),canonical_publication_stage=9, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3g_demo', '6F3F8CDA9A8F6B59'))

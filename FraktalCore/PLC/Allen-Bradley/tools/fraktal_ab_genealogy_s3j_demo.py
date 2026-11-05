"""Disposable S3j sampled-word bench; no physical I/O module is configured.

The inherited genealogy device simulation remains unchanged. The electrical
catalog is the reviewed press catalog; its separate word source exercises the
PLC topology owner without pretending that Echo emulates electrical I/O.
"""
from dataclasses import replace
import fraktal_ab_genealogy_s3i_demo as prior
import fraktal_ab_press_demo as press
import fraktal_ab_document_revision as document_revision


def application():
    return replace(prior.application(),canonical_publication_stage=12,
        canonical_type_manifest=True,canonical_table_driven=True,canonical_io_fixture=True,
        io_modules=(replace(press._press_io(),sample_tag='FRK_Press_SimIo',type_id='Fixture: sampled controller words'),), config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s3j_demo', '6F3F8CDA9A8F6B59'))

"""Approved V6.10 owner-revision qualification profile; V6.8 stays frozen."""
from dataclasses import replace
import fraktal_ab_genealogy_s4b_demo as previous


def application():
    return replace(previous.application(), canonical_owner_revisions=True)

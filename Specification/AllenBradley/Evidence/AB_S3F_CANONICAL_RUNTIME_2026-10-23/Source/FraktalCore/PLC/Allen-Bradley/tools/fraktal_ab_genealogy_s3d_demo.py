"""Offline S3d candidate; selecting it grants no deployment authorization."""
from dataclasses import replace
import fraktal_ab_genealogy_demo as genealogy


def application():return replace(genealogy.application(),canonical_publication_stage=6)

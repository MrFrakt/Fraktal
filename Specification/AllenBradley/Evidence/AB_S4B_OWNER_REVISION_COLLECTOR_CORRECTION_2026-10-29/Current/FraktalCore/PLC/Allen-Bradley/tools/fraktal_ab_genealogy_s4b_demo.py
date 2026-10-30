"""S4b engineering profile: approved V6.8 read-only configuration discovery."""
from dataclasses import replace
import fraktal_ab_genealogy_s4_demo as previous


def application():return replace(previous.application(),canonical_config_read_view=True)

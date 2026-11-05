"""S6 V6.11 host-services qualification profile; the V6.10 owner profile stays frozen.

The approved owner-revision profile plus the `canonical_host_services` opt-in:
the HostServiceBindings table, the shared host ingress and the HostEvents ring
on its own owner revision. Pre-collapse, so the legacy event ring and staged
endpoints are still emitted beside it; that is what lets one native capture
compare the canonical ring with the legacy one (WP6.5) before WP6.6 removes them.
"""
from dataclasses import replace
import fraktal_ab_genealogy_s4b_owner_demo as previous
import fraktal_ab_document_revision as document_revision


def application():
    return replace(previous.application(), canonical_host_services=True, config_predecessors=document_revision.recorded('fraktal_ab_genealogy_s6_host_demo', '6F3F8CDA9A8F6B59'))

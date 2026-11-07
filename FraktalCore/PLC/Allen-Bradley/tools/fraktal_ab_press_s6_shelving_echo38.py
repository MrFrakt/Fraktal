"""Acceptance-only S6-Q shelving profile, never a production health default.

The Phase 6 shelving fixture requires a standing, registry-shelvable event.
This profile explicitly requires unavailable controller metrics, using the
existing Part III §8 health/alarm owner to supply reason 21. The normal S6-Q
press keeps those metrics excluded. All equipment, documents, renditions,
policy and observation facts are inherited unchanged.
"""
from dataclasses import replace

import fraktal_ab_press_s6_collapse_echo38 as press


def application():
    app = press.application()
    return replace(app, system_health=replace(app.system_health, require_controller_metrics=True))

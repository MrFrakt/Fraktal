#!/usr/bin/env python3
"""L81E/v38 Echo variant of the authoritative press declaration.

Equipment, recipes, chains and policy come from fraktal_ab_press_demo. Only
controller/deployment properties change here. No physical I/O is declared;
output updates stay disabled. The extra account and readable mailbox arguments
belong only to this simulation. Neither is inherited by the physical bench.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import fraktal_ab_access as access
import fraktal_ab_declaration as decl
import fraktal_ab_press_demo as press


def application() -> decl.Application:
    base = press.application()
    return replace(
        base,
        controller="1756-L81E",
        major_revision=38,
        controller_identity="1756-L81E/A 38.011",
        comment='Fraktal/AB press demo on the Logix Echo emulator: the runtime base application retargeted to a 1756-L81E v38 station. No control power or physical I/O.',
        io_modules=(),
        access_users=base.access_users + (
            access.User('echo_admin', 4, '7f2f87d638bcef72113fa1047a24aca3', '8a2856647691346ffbaf309c7b3194f413dc5429eb273270e06c104d14540c37'),
        ),
        simulation_mailbox_rw=True,
    )


def generate(source: Path, output: Path) -> dict[str, object]:
    """The ordinary regeneration gate entry point."""
    import fraktal_ab_generate
    return fraktal_ab_generate.generate(application(), source, output)

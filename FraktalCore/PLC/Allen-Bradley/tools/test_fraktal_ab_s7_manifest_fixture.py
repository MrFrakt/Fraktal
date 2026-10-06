import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from fraktal_ab_l5x_inventory import inventory
from fraktal_ab_s7_manifest_fixture import (
    HEADER_TYPE,
    MEMORY_BUDGET_BYTES,
    TABLES,
    default_capacities,
    estimated_bytes,
    generate,
)


SEED = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content TargetType="Controller" TargetName="FraktalPhase0">
<Controller Use="Target" Name="FraktalPhase0" ProcessorType="1769-L24ER-QB1B" MajorRev="33">
<DataTypes/>
<Modules><Module Name="Discrete_IO" Inhibited="false"/></Modules>
<Tags/>
<Programs/>
<Tasks/>
</Controller>
</RSLogix5000Content>
"""


def build(temporary: str, capacities=None):
    source = Path(temporary) / "seed.L5X"
    output = Path(temporary) / "manifest.L5X"
    source.write_text(SEED, encoding="utf-8")
    evidence = generate(source, output, capacities)
    return evidence, output.read_text(encoding="utf-8"), inventory(output)


class S7ManifestFixtureTests(unittest.TestCase):
    def test_output_is_well_formed(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, text, _ = build(temporary)
            ElementTree.fromstring(text)

    def test_every_frozen_table_is_materialised_at_its_capacity(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _, census = build(temporary)
            for table in TABLES:
                tag = census["ControllerTags"][table.tag]
                self.assertEqual(
                    tag["dimensions"],
                    str(evidence["Capacities"][table.symbol]),
                    table.name,
                )
                self.assertEqual(tag["dataType"], table.row_type)

    def test_header_carries_a_count_and_capacity_for_every_table(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary)
            members = {
                item["name"] for item in census["DataTypes"][HEADER_TYPE]["members"]
            }
            for table in TABLES:
                self.assertIn(f"{table.name}Count", members)
                self.assertIn(f"{table.name}Capacity", members)

    def test_capacities_are_parameters_not_constants(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, _, census = build(temporary, {"FRK_MAX_FIELDS": 64})
            self.assertEqual(
                census["ControllerTags"]["FRK_S7_Fields"]["dimensions"], "64"
            )

    def test_modules_and_nameplates_share_one_capacity_symbol(self):
        # a manifest that could hold more nameplates than modules would be
        # incoherent, so the symbol is shared deliberately
        symbols = {table.name: table.symbol for table in TABLES}
        self.assertEqual(symbols["Modules"], symbols["Nameplates"])

    def test_a_manifest_too_large_to_download_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            source.write_text(SEED, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exceeds the"):
                generate(
                    source,
                    Path(temporary) / "huge.L5X",
                    {"FRK_MAX_FIELDS": 4096, "FRK_MAX_LOCALIZATION_KEYS": 4096},
                )

    def test_capacity_bounds_are_enforced(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            source.write_text(SEED, encoding="utf-8")
            for value in (0, -1, 5000):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, "must be between"):
                        generate(
                            source,
                            Path(temporary) / f"bad{value}.L5X",
                            {"FRK_MAX_ROOTS": value},
                        )

    def test_estimate_tracks_capacity(self):
        small = estimated_bytes({**default_capacities(), "FRK_MAX_FIELDS": 64})
        large = estimated_bytes({**default_capacities(), "FRK_MAX_FIELDS": 512})
        self.assertLess(small["Total"], large["Total"])
        self.assertLess(large["Total"], MEMORY_BUDGET_BYTES)

    def test_only_the_revision_bump_is_writable(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, _, census = build(temporary)
            self.assertEqual(evidence["WritableInputs"], ["FRK_S7_BumpRevision"])
            writable = [
                name for name, tag in census["ControllerTags"].items()
                if tag["externalAccess"] == "Read/Write"
            ]
            self.assertEqual(writable, ["FRK_S7_BumpRevision"])

    def test_fixture_stays_memory_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, text, _ = build(temporary)
            self.assertNotRegex(text, r"\b(?:Local|Discrete_IO):[IOC]")
            self.assertIn('Module Name="Discrete_IO" Inhibited="true"', text)
            self.assertEqual(evidence["PhysicalIoReferences"], 0)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "seed.L5X"
            output = Path(temporary) / "manifest.L5X"
            source.write_text(SEED, encoding="utf-8")
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                generate(source, output)


if __name__ == "__main__":
    unittest.main()

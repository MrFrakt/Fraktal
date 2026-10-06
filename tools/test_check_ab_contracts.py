import copy
import json
import unittest
from pathlib import Path

from tools.check_ab_contracts import (
    CONTRACTS_PATH,
    PART_PATH,
    REQUIRED_CONTRACTS,
    audit,
)


class AbFrozenContractTests(unittest.TestCase):
    def setUp(self):
        self.contracts = json.loads(
            CONTRACTS_PATH.read_text(encoding="utf-8-sig")
        )
        self.part = PART_PATH.read_text(encoding="utf-8-sig")

    def test_repository_freeze_is_clean(self):
        self.assertEqual(audit(self.contracts, self.part), [])

    def test_every_required_contract_is_frozen(self):
        for name in REQUIRED_CONTRACTS:
            self.assertIn(name, self.contracts["contracts"])

    def test_the_gate_is_not_vacuous(self):
        # a freeze with no contracts at all must fail, otherwise a passing
        # result would say nothing
        empty = {"logicalTypes": {}, "capacities": [], "contracts": {}}
        self.assertNotEqual(audit(empty, self.part), [])

    def test_an_unavailable_type_in_a_contract_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        broken["contracts"]["valueEnvelope"]["fields"][0]["type"] = "float64"
        findings = audit(broken, self.part)
        self.assertTrue(
            any("silent narrowing" in item for item in findings), findings
        )

    def test_an_undeclared_type_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        broken["contracts"]["registry"]["header"][0]["type"] = "int128"
        findings = audit(broken, self.part)
        self.assertTrue(
            any("undeclared logical type" in item for item in findings), findings
        )

    def test_a_field_absent_from_part_three_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        broken["contracts"]["mailbox"]["request"][1]["name"] = "CommitSequenceNumber"
        findings = audit(broken, self.part)
        self.assertTrue(
            any("drifted" in item for item in findings), findings
        )

    def test_a_missing_marker_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        del broken["contracts"]["hostEvents"]["partIIIMarker"]
        findings = audit(broken, self.part)
        self.assertTrue(
            any("declares no Part III marker" in item for item in findings), findings
        )

    def test_a_marker_that_does_not_match_part_three_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        broken["contracts"]["registry"]["partIIIMarker"] = "Registry schema v1"
        findings = audit(broken, self.part)
        self.assertTrue(
            any("occurs 0 times" in item for item in findings), findings
        )

    def test_a_missing_version_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        del broken["contracts"]["manifest"]["version"]
        findings = audit(broken, self.part)
        self.assertTrue(
            any("declares no version" in item for item in findings), findings
        )

    def test_an_undeclared_capacity_reference_is_rejected(self):
        broken = copy.deepcopy(self.contracts)
        broken["contracts"]["manifest"]["tables"][0]["capacity"] = "FRK_MAX_INVENTED"
        findings = audit(broken, self.part)
        self.assertTrue(
            any("undeclared capacity" in item for item in findings), findings
        )

    def _first(self, resolved: bool) -> int:
        for index, entry in enumerate(self.contracts["capacities"]):
            if bool(entry["resolved"]) is resolved:
                return index
        self.fail(f"no capacity with resolved={resolved} to mutate")

    def test_an_unresolved_capacity_must_name_its_owner(self):
        broken = copy.deepcopy(self.contracts)
        broken["capacities"][self._first(False)].pop("owner")
        findings = audit(broken, self.part)
        self.assertTrue(
            any("names no owning spike" in item for item in findings), findings
        )

    def test_a_resolved_capacity_needs_a_value_and_evidence(self):
        broken = copy.deepcopy(self.contracts)
        entry = broken["capacities"][self._first(True)]
        entry.pop("value")
        entry.pop("evidence")
        findings = audit(broken, self.part)
        # a number without a measurement behind it is exactly what the spike
        # programme exists to prevent
        self.assertTrue(any("no value" in item for item in findings), findings)
        self.assertTrue(any("no evidence" in item for item in findings), findings)

    def test_a_newly_resolved_capacity_is_accepted_with_its_evidence(self):
        updated = copy.deepcopy(self.contracts)
        updated["capacities"][self._first(False)].update(
            {"resolved": True, "value": 8, "evidence": "AB_S9_EVIDENCE.md"}
        )
        self.assertEqual(audit(updated, self.part), [])

    def test_every_capacity_is_owned_and_resolved_only_with_evidence(self):
        for entry in self.contracts["capacities"]:
            self.assertIn(entry["owner"], {"S3", "S7", "S9", "S12"})
            if entry["resolved"]:
                self.assertIsInstance(entry["value"], int, entry["symbol"])
                self.assertGreater(entry["value"], 0, entry["symbol"])
                self.assertTrue(entry["evidence"].endswith(".md"), entry["symbol"])

    def test_s7_capacities_are_resolved_and_s9_is_not(self):
        by_symbol = {
            entry["symbol"]: entry for entry in self.contracts["capacities"]
        }
        for symbol, entry in by_symbol.items():
            with self.subTest(symbol=symbol):
                # S7 measured its eight at exactly the tested sizes; the mailbox
                # argument count belongs to S9 and is still open
                self.assertEqual(entry["resolved"], entry["owner"] == "S7")


if __name__ == "__main__":
    unittest.main()

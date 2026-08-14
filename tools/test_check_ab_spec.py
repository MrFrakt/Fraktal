import unittest
from pathlib import Path

from tools.check_ab_spec import (
    EIP_READ_PROBE_PATH,
    HMI_PATH,
    INTERFACE_CATALOG_PATH,
    OFFLINE_PROBE_PATH,
    PART_PATH,
    S2_EVIDENCE_PATH,
    STUDIO_VERIFY_PROBE_PATH,
    SYMBOLIC_READ_PROBE_PATH,
    audit_repo,
    audit_texts,
)


class AbSpecificationGateTests(unittest.TestCase):
    def setUp(self):
        self.part = PART_PATH.read_text(encoding="utf-8-sig")
        self.hmi = HMI_PATH.read_text(encoding="utf-8-sig")
        self.offline_probe = OFFLINE_PROBE_PATH.read_text(encoding="utf-8-sig")
        self.symbolic_read_probe = SYMBOLIC_READ_PROBE_PATH.read_text(
            encoding="utf-8-sig"
        )
        self.eip_read_probe = EIP_READ_PROBE_PATH.read_text(encoding="utf-8-sig")
        self.studio_verify_probe = STUDIO_VERIFY_PROBE_PATH.read_text(
            encoding="utf-8-sig"
        )

    def audit(self, part=None, hmi=None, offline_probe=None,
              symbolic_read_probe=None, eip_read_probe=None,
              studio_verify_probe=None):
        return audit_texts(
            part if part is not None else self.part,
            hmi if hmi is not None else self.hmi,
            offline_probe=(offline_probe if offline_probe is not None
                           else self.offline_probe),
            symbolic_read_probe=(
                symbolic_read_probe if symbolic_read_probe is not None
                else self.symbolic_read_probe
            ),
            eip_read_probe=(eip_read_probe if eip_read_probe is not None
                            else self.eip_read_probe),
            studio_verify_probe=(
                studio_verify_probe if studio_verify_probe is not None
                else self.studio_verify_probe
            ),
        )

    def test_repository_specification_is_consistent(self):
        self.assertEqual(audit_repo(Path(".")), [])

    def test_missing_provisional_marker_is_reported(self):
        broken = self.part.replace("**[PROVISIONAL S15]**", "**[PROVISIONAL]**", 1)
        findings = self.audit(part=broken)
        self.assertTrue(any("missing=[15]" in item for item in findings), findings)

    def test_readiness_promotion_requires_an_intentional_gate_change(self):
        broken = self.part.replace(
            "| R4 gates | **OPEN** |",
            "| R4 gates | **PASS** |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("readiness table" in item for item in findings), findings)

    def test_readiness_demotion_is_also_reported(self):
        broken = self.part.replace(
            "| R2 executable shape | **PASS** |",
            "| R2 executable shape | **OPEN** |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("readiness table" in item for item in findings), findings)

    def test_missing_s1_evidence_link_is_reported(self):
        broken = self.part.replace(
            "[`AB_S1_CIP_DATA_PATH_EVIDENCE.md`](AB_S1_CIP_DATA_PATH_EVIDENCE.md)",
            "S1 evidence pending",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("S1 evidence" in item for item in findings),
                        findings)

    def test_s1_cannot_be_returned_to_provisional_without_gate_change(self):
        broken = self.part.replace(
            "Timestamps for the §8 diagnostic model",
            "**[PROVISIONAL S1]** Timestamps for the §8 diagnostic model",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("extra=[1]" in item for item in findings), findings)

    def test_s2_cannot_be_returned_to_provisional_without_gate_change(self):
        broken = self.part.replace(
            "S2 fixes the pinned-v33 limits",
            "**[PROVISIONAL S2]** fixes the pinned-v33 limits",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("extra=[2]" in item for item in findings), findings)

    def test_s2_evidence_exists(self):
        self.assertTrue(S2_EVIDENCE_PATH.is_file())

    def test_s11_cannot_be_demoted_without_a_gate_change(self):
        broken = self.part.replace(
            "| AB §2.8, §3.5, §4.1 | S11 | **PASS** |",
            "| AB §2.8, §3.5, §4.1 | S11 | OPEN |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(
            any("must record S11 as PASS" in item for item in findings), findings
        )

    def test_s12_cannot_be_demoted_without_a_gate_change(self):
        broken = self.part.replace(
            "| AB §3.8 | S12 | **PASS** |",
            "| AB §3.8 | S12 | OPEN |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(
            any("must record S12 as PASS" in item for item in findings), findings
        )

    def test_s4_native_sfc_row_cannot_be_demoted(self):
        broken = self.part.replace(
            "| AB §3.5 native SFC | S4 | **PASS** |",
            "| AB §3.5 native SFC | S4 | OPEN |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(
            any("native-SFC row as PASS" in item for item in findings), findings
        )

    def test_general_s4_row_cannot_be_demoted(self):
        broken = self.part.replace(
            "| AB §2.5 | S4 | **PASS** |",
            "| AB §2.5 | S4 | OPEN |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(
            any("general S4 round-trip row as PASS" in item for item in findings),
            findings,
        )

    def test_s15_cannot_be_promoted_with_s4(self):
        broken = self.part.replace(
            "| AB §5.4 | S15 | OPEN |",
            "| AB §5.4 | S15 | **PASS** |",
            1,
        )
        findings = self.audit(part=broken)
        self.assertTrue(
            any("must keep S15 OPEN" in item for item in findings), findings
        )

    def test_engineering_interface_catalog_exists(self):
        self.assertTrue(INTERFACE_CATALOG_PATH.is_file())

    def test_missing_s4_s15_evidence_link_is_reported(self):
        broken = self.part.replace(
            "[`AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md`](AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md)",
            "S4/S15 evidence pending",
        )
        findings = self.audit(part=broken)
        self.assertTrue(any("partial S4/S15 evidence" in item for item in findings),
                        findings)

    def test_transport_specific_hmi_base_wording_is_reported(self):
        broken = self.hmi + "\ndesktop/mobile bind OPC UA directly\n"
        findings = self.audit(hmi=broken)
        self.assertTrue(any("transport-specific" in item for item in findings), findings)

    def test_missing_logical_contract_marker_is_reported(self):
        broken = self.part.replace("HostEvents logical schema, version 1", "HostEvents")
        findings = self.audit(part=broken)
        self.assertTrue(any("HostEvents logical schema" in item for item in findings),
                        findings)

    def test_controller_mutation_in_offline_probe_is_reported(self):
        broken = self.offline_probe + "\nawait project.DownloadAsync();\n"
        findings = self.audit(offline_probe=broken)
        self.assertTrue(any("forbidden API: DownloadAsync" in item
                            for item in findings), findings)

    def test_controller_write_in_symbolic_probe_is_reported(self):
        broken = self.symbolic_read_probe + "\ncontroller.Write('Tag', 1)\n"
        findings = self.audit(symbolic_read_probe=broken)
        self.assertTrue(any("forbidden API: controller.Write(" in item
                            for item in findings), findings)

    def test_mutating_service_in_eip_probe_is_reported(self):
        broken = self.eip_read_probe + "\nCIP_SET_ATTRIBUTE_SINGLE = 0x10\n"
        findings = self.audit(eip_read_probe=broken)
        self.assertTrue(any("forbidden API: CIP_SET_ATTRIBUTE" in item
                            for item in findings), findings)

    def test_controller_mutation_in_studio_verify_is_reported(self):
        broken = self.studio_verify_probe + "\nproject.DownloadAsync()\n"
        findings = self.audit(studio_verify_probe=broken)
        self.assertTrue(any("forbidden API: DownloadAsync" in item
                            for item in findings), findings)


if __name__ == "__main__":
    unittest.main()

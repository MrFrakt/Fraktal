"""Tests for V6.12 collapse manifest, reader, and retirement of Frame/staged services."""
import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fraktal_ab_canonical_manifest as manifest_wire
import fraktal_ab_canonical_publication as publication
import fraktal_ab_canonical_reader as reader
import fraktal_ab_config_provider as provider
import fraktal_ab_genealogy_s6_collapse_demo as genealogy_s6
import fraktal_ab_genealogy_s6_host_demo as genealogy_host
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_s6_collapse_echo38 as press_s6
import fraktal_ab_press_s6_shelving_echo38 as press_shelving
import test_fraktal_ab_host_service_binding as host_test


class V612ManifestTests(unittest.TestCase):
    def test_collapse_minor_constant(self):
        self.assertEqual(manifest_wire.COLLAPSE_MINOR, 12)
        self.assertEqual(manifest_wire.COLLAPSE_HEADER, manifest_wire.HOST_HEADER)

    def test_v612_manifest_values_for_collapsed_profiles(self):
        for decl, name in (
            (press_s6, "press_s6_collapse"),
            (press_shelving, "press_s6_shelving"),
            (genealogy_s6, "genealogy_s6_collapse"),
        ):
            with self.subTest(profile=name):
                app = decl.application()
                self.assertTrue(app.canonical_collapse)
                # services(app) must return empty list for collapsed profile
                self.assertEqual(provider.services(app), [])
                values = publication.manifest_values(app)
                self.assertEqual(values["SchemaMinor"], 12)
                self.assertEqual(values["ServicesCount"], 0)
                self.assertEqual(values["ServicesCapacity"], 0)
                self.assertNotIn("Services", values)
                self.assertGreater(values["HostServiceBindingsCount"], 0)

    def test_legacy_profiles_retain_staged_services(self):
        app = genealogy_host.application()
        self.assertFalse(app.canonical_collapse)
        services = provider.services(app)
        self.assertGreater(len(services), 0)
        values = publication.manifest_values(app)
        self.assertEqual(values["SchemaMinor"], 11)
        self.assertEqual(values["ServicesCount"], len(services))
        self.assertIn("Services", values)

    def test_v612_normalizes_empty_services_and_retains_host_services(self):
        app = press_s6.application()
        values = publication.manifest_values(app)
        defs = publication.schema(app)
        record = host_test.physical(defs, publication.header_type(app), values)
        normalized = manifest_wire.normalize(record)
        self.assertEqual(normalized["schemaMinor"], 12)
        self.assertEqual(normalized["services"], [])
        self.assertIn("hostServiceBindings", normalized)
        self.assertGreater(len(normalized["hostServiceBindings"]), 0)

    def test_v612_refuses_non_empty_services(self):
        app = press_s6.application()
        values = copy.deepcopy(publication.manifest_values(app))
        # Inject non-zero Services with row into a V6.12 record
        values["ServicesCount"] = 1
        values["ServicesCapacity"] = 1
        values["Services"] = [
            {
                "Kind": 1,
                "Version": 1,
                "BuildRevision": 1,
                "RequestSymbol": "Req",
                "RequestMember": "ConfigProvider",
                "ResponseSymbol": "Ack",
            }
        ]
        defs = publication.schema(app)
        # Add Services member to header type for physical serialization
        defs[publication.header_type(app)] += (
            publication.Member("Services", publication.PREFIX + "ServiceV63", count=1),
        )
        defs[publication.PREFIX + "ServiceV63"] = (
            publication.Member("Kind", "DINT"),
            publication.Member("Version", "DINT"),
            publication.Member("BuildRevision", "DINT"),
            publication.Member("RequestSymbol", publication.string_type(80)),
            publication.Member("RequestMember", publication.string_type(80)),
            publication.Member("ResponseSymbol", publication.string_type(80)),
        )
        record = host_test.physical(defs, publication.header_type(app), values)
        with self.assertRaisesRegex(ValueError, "V6.12 requires empty services"):
            manifest_wire.normalize(record)

    def test_reader_accepts_v612_and_refuses_non_empty_services(self):
        capture = {
            "schema": reader.SCHEMA,
            "schemaVersion": 1,
            "serial": "12345678",
            "readOnly": True,
            "templates": [],
            "symbols": [],
            "records": [],
            "coherenceBefore": ["HASH", 1, 0],
            "coherenceAfter": ["HASH", 1, 0],
            "manifest": {
                "schemaMajor": 6,
                "schemaMinor": 12,
                "publicationStage": 13,
                "valid": True,
                "truncated": False,
                "contentHash": "HASH",
                "configRevision": 1,
                "fragmentRevision": 0,
                "typeAnnotations": [
                    {
                        "TypeName": "T",
                        "MemberName": "M",
                        "LogicalType": "BOOL",
                        "LowerBound": 0,
                        "ElementCount": 0,
                        "CountMember": "",
                        "EffectiveAccess": "Read Only",
                    }
                ],
                "pathExceptions": [],
                "commandBindings": [
                    {
                        "Version": 1,
                        "RootSymbol": "Press",
                        "PayloadSymbol": "Payload",
                        "ArgumentsMember": "Args",
                        "CommitSymbol": "Commit",
                        "ResponseSymbol": "Reply",
                        "StatusSymbol": "Status",
                        "ConnectionBytes": 4000,
                        "MaximumPayloadBytes": 1024,
                        "ReadRole": "Operator",
                        "CapabilitiesSymbol": "",
                        "CapabilitiesCount": 0,
                        "KeysSymbol": "",
                        "KeysCount": 0,
                    }
                ],
                "commandOperations": [
                    {
                        "Kind": i,
                        "Supported": True,
                        "RequiresSetStage": False,
                        "RefusalKey": "",
                    }
                    for i in range(39)
                ],
                "readCoherenceBindings": [
                    {
                        "CanonicalPrefix": "Press",
                        "RevisionSymbol": "Rev",
                        "ProgressSymbol": "Prog",
                    }
                ],
                "readServices": [
                    {
                        "RootSymbol": "Press",
                        "CanonicalRoot": "Press",
                        "PageBytes": 1024,
                        "ItemCapacity": 100,
                    }
                ],
                "ownerReadBindings": [
                    {
                        "CanonicalPrefix": "Press",
                        "MembersJson": "[]",
                        "RevisionSymbol": "Rev",
                        "ProgressSymbol": "Prog",
                    }
                ],
                "hostServiceBindings": [
                    {
                        "Service": 1,
                        "RootSymbol": "Press",
                        "CanonicalRoot": "Press",
                        "CommitSymbol": "Commit",
                        "ReplySymbol": "Reply",
                        "AccessGate": 0,
                        "ConnectionBytes": 4000,
                        "MaximumChunkBytes": 1024,
                    }
                ],
                "services": [],
            },
        }
        # Valid V6.12 with services=[] passes reader manifest validation
        token = reader.coherence_token(capture["manifest"])
        self.assertEqual(token, ["HASH", 1, 0])

        # Non-empty services under V6.12 raises
        bad = copy.deepcopy(capture)
        bad["manifest"]["services"] = [{"Kind": 1}]
        with self.assertRaisesRegex(ValueError, "V6.12 requires empty services"):
            reader.snapshot(bad)


class MailboxRetirementTests(unittest.TestCase):
    def test_collapsed_hmi_request_has_none_external_access(self):
        for decl in (press_s6, press_shelving, genealogy_s6):
            app = decl.application()
            tags = mailbox.tags(app)
            # Find the FRK_{app.name}_HmiRequest tag
            req_tag_str = [t for t in tags if f'Name="{mailbox.request_tag_name(app)}"' in t]
            self.assertEqual(len(req_tag_str), 1)
            self.assertIn('ExternalAccess="None"', req_tag_str[0])
            self.assertNotIn('ExternalAccess="Read/Write"', req_tag_str[0])

            # Ensure Frame, ConfigSet, ConfigProvider are not nested inside request tag
            self.assertNotIn('StructureMember Name="Frame"', req_tag_str[0])
            self.assertNotIn('StructureMember Name="ConfigSet"', req_tag_str[0])
            self.assertNotIn('StructureMember Name="ConfigProvider"', req_tag_str[0])

    def test_legacy_hmi_request_has_read_write_external_access(self):
        app = genealogy_host.application()
        tags = mailbox.tags(app)
        req_tag_str = [t for t in tags if f'Name="{mailbox.request_tag_name(app)}"' in t]
        self.assertEqual(len(req_tag_str), 1)
        self.assertIn('ExternalAccess="Read/Write"', req_tag_str[0])
        self.assertIn('StructureMember Name="ConfigSet"', req_tag_str[0])


if __name__ == "__main__":
    unittest.main()

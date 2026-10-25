"""The S3h observation frame: emitted ST behaviour and its fail-closed reader."""
from dataclasses import replace
from types import SimpleNamespace
import struct
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_observation as observation
import fraktal_ab_canonical_publication as pub
import fraktal_ab_generate as gen
import fraktal_ab_genealogy_s3g_demo as s3g
import fraktal_ab_genealogy_s3h_demo as demo
import fraktal_ab_paired_observation as frame_reader
import fraktal_ab_st_model as st


class FrameGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.app = demo.application()

    def emitted(self, app):
        return "\n".join([*pub.data_types(app), *pub.tags(app), *pub.cyclic(app)])

    def test_disabled_declarations_emit_no_frame(self):
        for app in (s3g.application(), replace(self.app, canonical_observation_period_ms=0)):
            with self.subTest(stage=app.canonical_publication_stage):
                self.assertNotIn("Observation", self.emitted(app))
                self.assertEqual(observation.public_tags(app), ())

    def test_validation_refuses_unsupported_frames(self):
        self.assertEqual(pub.validate(self.app), [])
        for app in (replace(s3g.application(), canonical_observation_period_ms=50),
                    replace(self.app, canonical_observation_period_ms=55),
                    replace(self.app, canonical_observation_period_ms=10),
                    replace(self.app, canonical_observation_period_ms=1010),
                    replace(self.app, canonical_observation_period_ms=-50)):
            with self.subTest(period=app.canonical_observation_period_ms, stage=app.canonical_publication_stage):
                self.assertTrue(pub.validate(app))

    def test_frame_is_last_read_only_and_never_a_root_or_manifest_path(self):
        types = pub.data_types(self.app)
        node = ET.fromstring(types[-1])
        self.assertEqual(node.get("Name"), observation.type_name(self.app))
        members = node.findall("Members/Member")
        names = [m.get("Name") for m in members]
        self.assertEqual(names, [*observation.HEADER, *observation.sources(self.app)])
        self.assertNotIn("Status", names)
        self.assertEqual({m.get("ExternalAccess") for m in members}, {"Read Only"})
        declared = {t.get("Name"): t for t in ET.fromstring(gen.controller_tags(self.app)).findall("Tag")}
        for member in members[len(observation.HEADER):]:
            tag = declared[member.get("Name")]
            self.assertEqual((member.get("DataType"), member.get("Dimension")),
                             (tag.get("DataType"), tag.get("Dimensions") or "0"))
        for name in observation.public_tags(self.app):
            self.assertEqual(declared[name].get("ExternalAccess"), "Read Only")
        self.assertFalse([r for r in pub.field_rows(self.app) if "Observation" in r["CanonicalPath"]])
        self.assertEqual(observation.period_scans(self.app), 5)


class FrameScanTests(unittest.TestCase):
    """The emitted latch, run scan by scan in the ST model."""

    def setUp(self):
        self.app = app = demo.application()
        self.shapes = {name: count for name, (kind, count) in observation._declared(app).items()}
        self.tags ={f"FRK_{app.name}_ScanCount": 0, pub.generation_tag(app): 0,
                     pub.header_tag(app): dict(FragmentRevision=7), observation.generation_tag(app): 0}
        frame = dict(SourceGeneration=0, FragmentRevision=0)
        for name, count in self.shapes.items():
            self.tags[name] = [dict(V=0) for _ in range(count)] if count else dict(V=0)
            frame[name] = [dict(V=0) for _ in range(count)] if count else dict(V=0)
        self.tags[observation.frame_tag(app)] = frame
        self.controller = st.Controller(self.tags, {"CPS": st.cps_structure})
        self.program = st.parse("\n".join(observation.cyclic(app)))

    def scan(self, number):
        app, tags = self.app, self.tags
        tags[f"FRK_{app.name}_ScanCount"] = number
        tags[pub.generation_tag(app)] += 2
        for name, count in self.shapes.items():
            for item in (tags[name] if count else [tags[name]]):item["V"] = number
        self.controller.run(self.program)

    def values(self, record):
        return [item["V"] for item in record] if isinstance(record, list) else [record["V"]]

    def test_one_whole_scan_is_latched_every_period(self):
        app, tags = self.app, self.tags
        g, frame = observation.generation_tag(app), observation.frame_tag(app)
        history = []
        for number in range(1, 13):
            self.scan(number)
            history.append(tags[g])
            self.assertEqual(tags[g] % 2, 0)
            latched = number - number % 5
            for name in self.shapes:
                self.assertEqual(set(self.values(tags[frame][name])), {latched})
            if latched:
                self.assertEqual(tags[frame]["SourceGeneration"], 2 * latched)
                self.assertEqual(tags[frame]["FragmentRevision"], 7)
        self.assertEqual(history, [0] * 4 + [2] * 5 + [4] * 3)
        tags[app.name]["V"] = -1
        self.assertEqual(tags[frame][app.name]["V"], 10, "the frame is a copy, not an alias")

    def test_interrupted_negative_or_exhausted_generations_restart_cleanly(self):
        g = observation.generation_tag(self.app)
        for start, after in ((7, 8), (8, 10), (-3, 2), (2147483644, 2147483646),
                             (2147483645, 2), (2147483646, 2)):
            with self.subTest(start=start):
                self.tags[g] = start
                self.scan(5)
                self.assertEqual(self.tags[g], after)


def _row(name, offset, *, handle=None, atomic=None, array=0, info=0):
    return dict(name=name, info=info, code=0, offset=offset, atomic=atomic, struct=atomic is None,
                handle=handle if handle is not None else atomic, array=array, typeName=None)


class FrameReaderTests(unittest.TestCase):
    def setUp(self):
        self.header = observation.HEADER
        self.seed = dict(
            symbols=[dict(name="Frame", handle=100, arrayRank=0), dict(name="Root", handle=1, arrayRank=0),
                     dict(name="Ctx", handle=2, arrayRank=0), dict(name="Arr", handle=3, arrayRank=1)],
            templates=[dict(handle=1, byteSize=8, members=[]), dict(handle=2, byteSize=4, members=[]),
                       dict(handle=3, byteSize=4, members=[]),
                       dict(handle=100, byteSize=28, members=[
                           _row("SourceGeneration", 0, atomic=0xC4), _row("FragmentRevision", 4, atomic=0xC4),
                           _row("Root", 8, handle=1), _row("Ctx", 16, handle=2),
                           _row("Arr", 20, handle=3, array=1, info=2)])])
        self.tags = ["Root", "Defs", "Ctx", "Arr[0]", "Arr[1]"]
        self.sizes = {"Root": 8, "Defs": 3, "Ctx": 4, "Arr[0]": 4, "Arr[1]": 4}
        self.cached = {"Defs": SimpleNamespace(Status="Success", Value=b"def")}

    def live(self):
        return [t for t in self.tags if t not in self.cached]

    def test_layout_locates_every_read_from_the_frame_template(self):
        plan = frame_reader.layout(self.seed, "Frame", self.live(), self.sizes, self.header)
        self.assertEqual(plan["slices"], {"Root": (8, 16), "Ctx": (16, 20), "Arr[0]": (20, 24), "Arr[1]": (24, 28)})
        self.assertEqual(plan["header"], {"SourceGeneration": 0, "FragmentRevision": 4})

    def test_layout_refuses_any_difference_between_frame_and_reads(self):
        frame = self.seed["templates"][3]["members"]
        cases = {
            "unread member": dict(tags=["Root", "Arr[0]", "Arr[1]"]),
            "read outside frame": dict(tags=[*self.live(), "Other"]),
            "index past array": dict(tags=[*self.live(), "Arr[2]"], sizes={"Arr[2]": 4}),
            "array read whole": dict(tags=["Root", "Ctx", "Arr"], sizes={"Arr": 4}),
            "size differs": dict(sizes={"Ctx": 8}),
            "handle differs": dict(member=(3, dict(handle=1))),
            "header not DINT": dict(member=(1, dict(atomic=0xC3))),
            "ranges overlap": dict(member=(3, dict(offset=12))),
        }
        for label, change in cases.items():
            with self.subTest(label):
                seed = dict(symbols=self.seed["symbols"], templates=[dict(t) for t in self.seed["templates"]])
                members = [dict(r) for r in frame]
                if "member" in change:
                    index, update = change["member"]
                    members[index].update(update)
                seed["templates"][3] = dict(seed["templates"][3], members=members)
                with self.assertRaises(ValueError):
                    frame_reader.layout(seed, "Frame", change.get("tags", self.live()),
                                        {**self.sizes, **change.get("sizes", {})}, self.header)

    def run_read(self, *, source=10, revision=5, live=8, sizes=(4000, 4000)):
        events = []
        raw = struct.pack("<ii", source, revision) + bytes(range(8)) + b"ctx!" + b"a0a0" + b"a1a1"
        generations = iter((3, 10, 10))
        def frame_generation():
            events.append("frame generation");return next(generations)
        def live_generation():
            events.append("live generation");return live
        def partition(comm, tags, sizes, connections):
            self.assertEqual((tags, sizes, connections), (["Frame"], {"Frame": 28}, 2))
            return ([dict(kind="fragment", tags=["Frame"], request=b"r")], [])
        def acquire(channels, plans):
            events.append("wire");return [[(0, b"reply")], []]
        def decode(plan, replies, sizes):
            self.assertEqual(events[-1], "frame generation", "decode follows the closing sample")
            return {"Frame": SimpleNamespace(Status="Success", Value=raw)}
        with patch("fraktal_ab_paired_fragments.partition", side_effect=partition), \
                patch("fraktal_ab_paired_socket_reads.acquire", side_effect=acquire), \
                patch("fraktal_ab_paired_fragments.decode", side_effect=decode):
            pair = frame_reader.read([SimpleNamespace(ConnectionSize=s) for s in sizes], frame="Frame", tags=self.tags, sizes=self.sizes,
                                     seed=self.seed, cached=self.cached, live_generation=live_generation,
                                     frame_generation=frame_generation, fragment_revision=5, period_scans=5)
        return pair, events

    def test_read_requests_first_proves_the_frame_then_slices(self):
        pair, events = self.run_read()
        self.assertEqual(events, ["live generation", "frame generation", "frame generation", "wire", "frame generation"])
        self.assertTrue(pair["sameStateVerified"])
        self.assertEqual([r.Value for r in pair["rawResponses"]],
                         [bytes(range(8)), b"def", b"ctx!", b"a0a0", b"a1a1"])
        self.assertEqual(pair["stateEvidence"]["kind"], "PLC observation frame generation")
        self.assertEqual(pair["stateEvidence"]["generation"], 10)
        self.assertEqual(pair["stateEvidence"]["frame"], dict(tag="Frame", bytes=28, sourceGeneration=10,
                         notBefore=8, fragmentRevision=5, periodScans=5))
        self.assertEqual(pair["readPlan"], [dict(kind="fragment", tags=["Frame"])])

    def test_read_refuses_stale_incomplete_or_foreign_revision_frames(self):
        for label, change in (("predates request", dict(source=6)), ("odd source", dict(source=11)),
                              ("revision differs", dict(revision=6)), ("uninitialized", dict(live=0))):
            with self.subTest(label), self.assertRaises(ValueError):
                self.run_read(**change)

    def test_read_refuses_mailbox_sized_connections_before_any_controller_read(self):
        # A writer left at the 500-byte mailbox framing needs about 350
        # fragments, so no read can fit the frame period; refuse it outright.
        for sizes in ((500, 4000), (500, 500), (4000, 4002)):
            with self.subTest(sizes=sizes):
                with patch("fraktal_ab_paired_fragments.partition") as partition, \
                        self.assertRaisesRegex(ValueError, "4000-byte connections"):
                    frame_reader.read([SimpleNamespace(ConnectionSize=s) for s in sizes], frame="Frame",
                                      tags=self.tags, sizes=self.sizes, seed=self.seed, cached=self.cached,
                                      live_generation=lambda: self.fail("generation read"),
                                      frame_generation=lambda: self.fail("frame read"),
                                      fragment_revision=5, period_scans=5)
                partition.assert_not_called()


if __name__ == "__main__":
    unittest.main()

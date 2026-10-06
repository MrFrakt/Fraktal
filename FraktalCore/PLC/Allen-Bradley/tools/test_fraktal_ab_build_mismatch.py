"""A download the gateway did not restart for: said, not suffered.

The gateway loads its declaration once, at start, and §3.10 discovery is
fail-closed, so after a download it refuses a controller that is running
exactly what the repository declares. That is correct, and it had been met
four times as "commands do nothing". These tests hold the gateway to naming the
cause and its fix, and to telling that case apart from the ones a restart
would not help.
"""

import asyncio
import unittest

import fraktal_ab_gateway as gateway
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as projection
import test_fraktal_ab_projection as fixture

APP = projection.APP
DECLARED = manifest.content_hash(APP)


class TheRefusalCarriesBothHashes(unittest.TestCase):
    def test_a_hash_mismatch_is_a_build_mismatch(self):
        with self.assertRaises(projection.BuildMismatch) as raised:
            projection.validate(fixture.good_header(ContentHash="FFFF000011112222"))
        self.assertEqual(raised.exception.controller_hash, "FFFF000011112222")
        self.assertEqual(raised.exception.declared_hash, DECLARED)

    def test_it_is_still_a_refusal(self):
        """Every caller that refuses a projection keeps refusing this one."""
        self.assertTrue(issubclass(projection.BuildMismatch, projection.ProjectionRefused))

    def test_other_refusals_are_not_build_mismatches(self):
        with self.assertRaises(projection.ProjectionRefused) as raised:
            projection.validate(fixture.good_header(Valid=0))
        self.assertNotIsInstance(raised.exception, projection.BuildMismatch)


class TheFixIsNamed(unittest.TestCase):
    def test_a_download_after_start_asks_for_a_restart(self):
        text = gateway.explain_build_mismatch("NEW", "OLD", "NEW")
        self.assertIn("Restart the gateway", text)
        self.assertIn("after this gateway started", text)

    def test_a_controller_behind_the_repository_asks_for_a_download(self):
        text = gateway.explain_build_mismatch("OLD", "NEW", "NEW")
        self.assertIn("download", text)
        self.assertNotIn("Restart the gateway", text)

    def test_all_three_different_asks_for_both(self):
        text = gateway.explain_build_mismatch("A", "B", "C")
        self.assertIn("Regenerate, download, then restart", text)

    def test_an_unreadable_declaration_is_said_not_guessed(self):
        text = gateway.explain_build_mismatch("A", "B", None)
        self.assertIn("could not be read", text)
        self.assertNotIn("Restart", text)


class TheExplainer(unittest.TestCase):
    def refusal(self, controller):
        return projection.BuildMismatch("mismatch", controller, "OLD")

    def test_the_repository_is_probed_once_per_controller_build(self):
        calls, now = [], [0.0]
        explain = gateway.BuildMismatchExplainer(
            probe=lambda: calls.append(1) or "NEW", clock=lambda: now[0], ttl=60.0)
        with self.assertLogs(gateway.log, "ERROR") as logged:
            for _ in range(5):
                refusal = explain(self.refusal("NEW"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(logged.output), 1)
        self.assertIsInstance(refusal, projection.ProjectionRefused)
        self.assertIn("Restart the gateway", str(refusal))

    def test_a_new_controller_build_or_an_old_answer_is_probed_again(self):
        calls, now = [], [0.0]
        explain = gateway.BuildMismatchExplainer(
            probe=lambda: calls.append(1) or "NEW", clock=lambda: now[0], ttl=60.0)
        with self.assertLogs(gateway.log, "ERROR"):
            explain(self.refusal("NEW"))
            explain(self.refusal("OTHER"))
            now[0] = 61.0
            explain(self.refusal("OTHER"))
        self.assertEqual(len(calls), 3)


class TheStationSaysWhy(unittest.TestCase):
    def test_a_refusal_is_kept_for_healthz_and_cleared_by_a_good_read(self):
        outcomes = [projection.ProjectionRefused("Restart the gateway."),
                    {"values": {}, "discoveryRevision": 1}]

        def read():
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        station = gateway.Station(read, cache_ttl=0.0)
        with self.assertRaises(projection.ProjectionRefused):
            asyncio.run(station.document(force=True))
        self.assertEqual(station.last_refusal, "Restart the gateway.")
        asyncio.run(station.document(force=True))
        self.assertTrue(station.healthy)
        self.assertIsNone(station.last_refusal)

    def test_a_transport_failure_is_not_reported_as_a_refusal(self):
        def read():
            raise OSError("connection reset")

        station = gateway.Station(read, cache_ttl=0.0)
        with self.assertRaises(OSError):
            asyncio.run(station.document(force=True))
        self.assertIsNone(station.last_refusal)


class TheProbeReadsTheFilesNow(unittest.TestCase):
    def test_a_fresh_interpreter_computes_this_declarations_hash(self):
        self.assertEqual(gateway.declared_on_disk(), DECLARED)


if __name__ == "__main__":
    unittest.main()

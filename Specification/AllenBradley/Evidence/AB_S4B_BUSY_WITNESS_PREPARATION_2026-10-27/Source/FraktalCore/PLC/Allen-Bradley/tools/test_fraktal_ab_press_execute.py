"""The press harness's mailbox command: its acknowledgement, and its commit order.

The harness drives the bench through the mailbox rather than by writing the
request tags, because those became ``ExternalAccess None`` when AB 11.2.1 was
closed on 2026-09-23. What that conversion cost is the subject of this file: a
tag write is instantaneous and a mailbox command is not, so every call grew an
acknowledgement window - and a window of zero seconds fails every command by
construction while looking like a controller fault.
"""

import ast
import pathlib
import unittest

import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_execute as px
import fraktal_ab_press_parity as parity


class Reply:
    def __init__(self, status: str = "Success", value=None):
        self.Status = status
        self.Value = value


class FakeMailbox:
    """A controller that answers a committed request, one scan later.

    It models the acknowledgement contract and nothing else: ``AckSequence`` is
    set only when ``Sequence`` is written, which is what makes "the commit is
    last" observable rather than asserted.
    """

    def __init__(self, app, *, answer: bool = True, fail_tag: str | None = None):
        self.request = mailbox.request_tag_name(app)
        self.response = mailbox.response_tag_name(app)
        self.fail_tag = fail_tag
        self.answer = answer
        self.writes: list[tuple[str, object]] = []
        self.values: dict[str, object] = {
            f"{self.request}.Sequence": 0,
            f"{self.response}.AckSequence": 0,
            f"{self.response}.Accepted": 0,
            f"{self.response}.DiagnosticKey": 0,
        }

    def Write(self, tag, value):
        if tag == self.fail_tag:
            return Reply("Failed")
        self.writes.append((tag, value))
        if tag == f"{self.request}.Sequence":
            self.values[tag] = value
        if tag == f"{self.request}.Sequence" and self.answer:
            self.values[f"{self.response}.AckSequence"] = value
            self.values[f"{self.response}.Accepted"] = 1
        return Reply()

    def Read(self, tag):
        if tag not in self.values:
            return Reply("Failed")
        return Reply("Success", self.values[tag])


class CommandAcknowledgement(unittest.TestCase):
    def setUp(self):
        px._SEQUENCE["value"] = 0

    def test_a_command_returns_what_the_machine_answered(self):
        comm = FakeMailbox(px.APP)
        answer = px.command(comm, mailbox.START, settle=1.0)
        self.assertEqual(answer["sequence"], 1)
        self.assertTrue(answer["accepted"])

    def test_a_zero_window_can_never_observe_an_acknowledgement(self):
        """The defect this file exists for.

        ``settle`` is the deadline, not a linger. A caller passing 0.0 because
        it does not want to wait gets a loop whose condition is already false,
        so a perfectly healthy controller reports 'no acknowledgement'.
        """
        comm = FakeMailbox(px.APP)
        with self.assertRaises(AssertionError) as raised:
            px.command(comm, mailbox.START, settle=0.0)
        self.assertIn("no acknowledgement", str(raised.exception))
        # The command was fully issued: the controller answered, and only the
        # observer gave up - which is exactly why the symptom misleads.
        self.assertEqual(comm.values[f"{comm.response}.AckSequence"], 1)

    def test_an_unanswered_command_is_a_failure_not_a_silent_pass(self):
        comm = FakeMailbox(px.APP, answer=False)
        with self.assertRaises(AssertionError):
            px.command(comm, mailbox.START, settle=0.1)

    def test_a_failed_argument_never_reaches_the_commit(self):
        import fraktal_ab_mailbox_frame as frame
        comm = FakeMailbox(px.APP, fail_tag=frame.native_path(px.APP))
        with self.assertRaises(AssertionError):
            px.command(comm, mailbox.SET_MODE, settle=1.0, IntValue=px.MODE_AUTO)
        written = [tag for tag, _ in comm.writes]
        self.assertNotIn(f"{comm.request}.Sequence", written)

    def test_the_commit_marker_is_written_last(self):
        comm = FakeMailbox(px.APP)
        px.command(comm, mailbox.SET_MODE, settle=1.0, IntValue=px.MODE_AUTO)
        self.assertEqual(comm.writes[-1][0], f"{comm.request}.Sequence")


class ParityAckWindow(unittest.TestCase):
    def test_the_window_is_never_zero_for_any_settle_the_cli_accepts(self):
        for settle in (0.001, 0.5, 1.0, 4.0, 5.0):
            with self.subTest(settle=settle):
                self.assertGreater(parity.ack(settle), 0.0)
                self.assertLessEqual(parity.ack(settle), settle)

    def test_every_command_in_the_parity_walk_waits_through_ack(self):
        """Structural, so a literal cannot come back one call at a time.

        Six of these were written as ``settle=0.0`` when the walk was converted
        from tag writes, and the first one reached failed the whole run.
        """
        source = pathlib.Path(parity.__file__).read_text(encoding="utf-8")
        calls = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "command"
        ]
        self.assertTrue(calls)
        for call in calls:
            settle = next(
                (kw.value for kw in call.keywords if kw.arg == "settle"), None)
            self.assertIsNotNone(
                settle, f"px.command at line {call.lineno} takes the 2.0 default")
            self.assertTrue(
                isinstance(settle, ast.Call)
                and isinstance(settle.func, ast.Name)
                and settle.func.id == "ack",
                f"px.command at line {call.lineno} does not use ack(settle)")


class SequenceSeeding(unittest.TestCase):
    """The handler dispatches on Sequence CHANGING, not on it increasing.

    So a harness that restarts its counter at 1 is not refused as a replay -
    it is ignored, with no acknowledgement, for as long as it takes to walk
    past whatever the controller retained. Seeding is what makes the first
    command of a run reach the machine.
    """

    def setUp(self):
        px._SEQUENCE["value"] = 0

    def test_seeding_starts_above_what_the_controller_already_answered(self):
        comm = FakeMailbox(px.APP)
        comm.values[f"{comm.request}.Sequence"] = 17
        comm.values[f"{comm.response}.AckSequence"] = 17
        self.assertEqual(px.seed_sequence(comm), 17)
        answer = px.command(comm, mailbox.START, settle=1.0)
        self.assertEqual(answer["sequence"], 18)

    def test_seeding_reads_the_committed_request_even_if_unanswered(self):
        """A request committed but not yet answered still consumes its number."""
        comm = FakeMailbox(px.APP)
        comm.values[f"{comm.request}.Sequence"] = 9
        comm.values[f"{comm.response}.AckSequence"] = 4
        self.assertEqual(px.seed_sequence(comm), 9)

    def test_commands_follow_an_intervening_gateway_commit(self):
        comm = FakeMailbox(px.APP)
        self.assertEqual(px.command(comm, mailbox.START)['sequence'], 1)
        # A different helper commits and consumes sequence 2. The cached
        # harness counter still holds 1, so incrementing it would replay 2.
        comm.values[f"{comm.request}.Sequence"] = 2
        comm.values[f"{comm.response}.AckSequence"] = 2
        self.assertEqual(px.command(comm, mailbox.STOP)['sequence'], 3)
        self.assertEqual(comm.writes[-1], (f"{comm.request}.Sequence", 3))

    def test_unsigned_wrap_follows_the_controller_bit_pattern(self):
        comm = FakeMailbox(px.APP)
        comm.values[f"{comm.request}.Sequence"] = -1
        comm.values[f"{comm.response}.AckSequence"] = -1
        self.assertEqual(px.command(comm, mailbox.STOP)['sequence'], 0)

    def test_missing_cursor_or_ack_refuses_before_any_write(self):
        for tag_name in ('request', 'response'):
            with self.subTest(tag=tag_name):
                comm = FakeMailbox(px.APP)
                tag = (f"{comm.request}.Sequence" if tag_name == 'request'
                       else f"{comm.response}.AckSequence")
                del comm.values[tag]
                with self.assertRaises(AssertionError):
                    px.command(comm, mailbox.STOP)
                self.assertEqual(comm.writes, [])

    def test_an_outstanding_command_is_not_overwritten(self):
        comm = FakeMailbox(px.APP)
        comm.values[f"{comm.request}.Sequence"] = 9
        comm.values[f"{comm.response}.AckSequence"] = 8
        with self.assertRaisesRegex(AssertionError, 'settled acknowledgment'):
            px.command(comm, mailbox.STOP)
        self.assertEqual(comm.writes, [])

    def test_a_cursor_change_during_staging_never_commits(self):
        comm = FakeMailbox(px.APP)
        original = comm.Write

        def competing_write(tag, value):
            answer = original(tag, value)
            comm.values[f"{comm.request}.Sequence"] = 7
            comm.values[f"{comm.response}.AckSequence"] = 7
            return answer

        comm.Write = competing_write
        with self.assertRaisesRegex(AssertionError, 'changed during staging'):
            px.command(comm, mailbox.STOP)
        self.assertNotIn(f"{comm.request}.Sequence", [t for t, _ in comm.writes])

    def test_the_parity_walk_seeds_before_it_commands(self):
        """Ordered by line, not by ast.walk - which is breadth-first."""
        source = pathlib.Path(parity.__file__).read_text(encoding="utf-8")
        main = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "main")
        seeds = [node.lineno for node in ast.walk(main)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "seed_sequence"]
        walks = [node.lineno for node in ast.walk(main)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "run"]
        self.assertEqual(len(seeds), 1, "main() does not seed the sequence")
        self.assertEqual(len(walks), 1)
        self.assertLess(seeds[0], walks[0])


class ParityWriteSurface(unittest.TestCase):
    """Every direct write in the walk targets a tag the harness may write.

    This is the bug that bit twice in one sitting: RunRequest/ModeRequest/
    ResetRequest were converted to mailbox commands, AbortRequest was missed,
    and it surfaced only after two of the three walks had already run against
    the controller. px.write's guard catches it - at the point of the write,
    minutes in. Static is cheaper, and the module constants make it possible.
    """

    def test_no_direct_write_targets_a_command_tag(self):
        source = pathlib.Path(parity.__file__).read_text(encoding="utf-8")
        writes = [
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "write"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "px"
        ]
        self.assertTrue(writes)
        for call in writes:
            target = call.args[1]
            # px.FAULT[name] and friends are subscripts of a declared mapping;
            # resolve the mapping, not the key.
            if isinstance(target, ast.Subscript):
                target = target.value
            names = []
            if isinstance(target, ast.Attribute) and target.attr:
                names = [target.attr]
            elif isinstance(target, ast.Name):
                names = [target.id]
            self.assertTrue(names, f"unrecognised write target at line {call.lineno}")
            resolved = getattr(px, names[0], getattr(parity, names[0], None))
            self.assertIsNotNone(
                resolved, f"{names[0]} at line {call.lineno} is not a known tag")
            tags = (list(resolved.values()) if isinstance(resolved, dict)
                    else [resolved])
            for tag in tags:
                if tag == parity.RENDITION and not parity.AUTO.multi_rendition:
                    # select() returns before this write: one rendition, no selector.
                    continue
                self.assertIn(
                    tag, px.WRITABLE,
                    f"line {call.lineno} writes {tag}, outside the write surface")


if __name__ == "__main__":
    unittest.main()

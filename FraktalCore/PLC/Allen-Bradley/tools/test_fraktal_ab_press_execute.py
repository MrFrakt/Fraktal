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

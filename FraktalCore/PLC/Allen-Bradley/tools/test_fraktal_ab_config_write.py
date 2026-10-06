"""Core §3.10.2 on Allen-Bradley: editable configuration, and who decides.

The split under test is the one that makes this safe. The client sends a STRING
write key and a STRING value; the controller can read neither, so the gateway
resolves both into DINT slots - exactly as it already resolves a force
channel's path into a bit mask. What the gateway must NOT do is decide. Every
bound is re-tested on the controller, against the same declaration the L5X was
generated from, so a client that sends a number directly, or one built against
a different build, meets the same refusal.
"""

import dataclasses
import unittest

import fraktal_ab_declaration as decl
import fraktal_ab_config as config
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_demo as demo


APP = demo.application()
# The BROWSE path a client writes, which is what the resolver matches on -
# not the controller tag name. `Press/HmiRequest/NameValue`, never
# `FRK_Press_HmiRequest/NameValue`.
REQ = f"{APP.name}/HmiRequest"
# The same member as the controller's ST spells it.
ST_REQ = f"FRK_{APP.name}_HmiRequest"


def _writes(**members):
    """A mailbox batch in contract order, Sequence last."""
    out = [(f"{REQ}/Kind", "int32", members.pop("Kind", mailbox.WRITE_CONFIG))]
    for name, value in members.items():
        kind = "string" if isinstance(value, str) else "int32"
        out.append((f"{REQ}/{name}", kind, value))
    out.append((f"{REQ}/Sequence", "int32", 7))
    return out


def _value_of(writes, member):
    for path, _kind, value in writes:
        if path.endswith(f"/{member}"):
            return value
    return None


class Declaration(unittest.TestCase):
    def test_every_editable_value_declares_its_bounds(self):
        values = gen.editable_values(APP)
        self.assertTrue(values)
        for _ordinal, record, member in values:
            self.assertLessEqual(member.minimum, member.maximum,
                                 f"{record.name}.{member.name}")
            self.assertTrue(member.label_key, member.name)

    def test_a_default_outside_its_own_range_is_refused(self):
        """A §3.8a restore installs the default. A default the same contract
        would refuse to accept is a station that boots into a state no operator
        could have put it in."""
        bad = decl.Record(
            name="FRK_T_Bad", station_cfg=True,
            members=(decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=0),
                     decl.editable(decl.scalar("X", "", initial=9),
                                   "x", "k", minimum=0, maximum=5)))
        findings = decl._validate_record(bad)
        self.assertTrue(any("outside its own range" in f for f in findings),
                        findings)

    def test_ordinals_are_dense_and_follow_declaration_order(self):
        values = gen.editable_values(APP)
        self.assertEqual([o for o, _, _ in values],
                         list(range(1, len(values) + 1)))

    def test_an_unmarked_member_is_not_editable(self):
        """A value becomes editable because somebody declared it so, never
        because it happened to live in a configuration record."""
        schema = APP.records[0].members[0]
        self.assertEqual(schema.name, decl.SCHEMA_VERSION_MEMBER)
        self.assertFalse(schema.editable)
        self.assertNotIn(
            schema.name, [m.name for _o, _r, m in gen.editable_values(APP)])


class GatewayResolution(unittest.TestCase):
    def test_a_write_key_becomes_its_ordinal_and_the_text_its_value(self):
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="station.number", TextValue="42", IntValue=99))
        self.assertEqual(_value_of(writes, mailbox.CONFIG_ORDINAL_MEMBER),
                         mailbox.config_ordinal(APP, "station.number"))
        self.assertEqual(_value_of(writes, mailbox.CONFIG_VALUE_MEMBER), 42)

    def test_a_decimal_is_rounded_not_truncated(self):
        """A client rendering 2.5 s as '2500.0' means 2500."""
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="station.ramExtendLimitMs", TextValue="2500.0"))
        self.assertEqual(_value_of(writes, mailbox.CONFIG_VALUE_MEMBER), 2500)

    def test_an_undeclared_key_is_left_alone_for_the_controller_to_refuse(self):
        """Not guessed at, and not refused here. The controller's own CASE
        refuses it by name, which is where an operator should see it come
        from."""
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="press.doesNotExist", TextValue="1", IntValue=77))
        self.assertEqual(_value_of(writes, mailbox.CONFIG_ORDINAL_MEMBER), 77)

    def test_a_value_that_is_not_a_number_is_left_alone(self):
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="station.number", TextValue="tomorrow", BoolValue=0))
        self.assertEqual(_value_of(writes, mailbox.CONFIG_VALUE_MEMBER), 0)

    def test_it_does_not_fire_on_another_kind_carrying_a_name(self):
        writes = _writes(Kind=mailbox.SET_MODE, NameValue="station.number",
                         TextValue="42", IntValue=3)
        self.assertEqual(mailbox.resolve_config_batch(APP, writes), writes)

    def test_the_commit_marker_stays_last(self):
        """Injected members go before Sequence, never after: a half-written
        request must never be committable."""
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="station.number", TextValue="42"))
        self.assertTrue(writes[-1][0].endswith("/Sequence"))

    def test_a_member_the_client_omitted_still_arrives(self):
        """Otherwise the controller validates against the previous request's
        leftovers."""
        writes = mailbox.resolve_config_batch(APP, _writes(
            NameValue="station.number", TextValue="42"))
        self.assertIsNotNone(_value_of(writes, mailbox.CONFIG_VALUE_MEMBER))
        self.assertIsNotNone(_value_of(writes, mailbox.CONFIG_ORDINAL_MEMBER))

    def test_resolution_is_reached_through_the_one_entry_point(self):
        batch = _writes(NameValue="station.number", TextValue="42")
        self.assertEqual(mailbox.resolve_batch(APP, batch),
                         mailbox.resolve_config_batch(APP, batch))


class ControllerIsTheAuthority(unittest.TestCase):
    def setUp(self):
        self.text = "\n".join(mailbox._dispatch(APP))

    def test_every_editable_value_writes_only_its_own_record_member(self):
        from test_fraktal_ab_capture import controller, execute
        for ordinal, record, member in gen.editable_values(APP):
            with self.subTest(key=member.write_key):
                c = controller()
                expected = {r.name: dict(c.tags[r.name + 'Tag']) for r in APP.records}
                value = member.minimum if member.initial != member.minimum else member.maximum
                expected[record.name][member.name] = value
                answer = execute(c, Kind=mailbox.WRITE_CONFIG, DurationMs=0,
                                 IntValue=ordinal, BoolValue=value)
                self.assertEqual(answer['Accepted'], 1)
                self.assertEqual({r.name: c.tags[r.name + 'Tag'] for r in APP.records}, expected)

    def test_each_branch_tests_its_own_declared_bounds(self):
        value = config.candidate_tag(APP)
        low, high, _ = config.scratch_names(APP)
        self.assertIn(f'({value} < {low})', self.text)
        self.assertIn(f'({value} > {high})', self.text)
        for _ordinal, _record, member in gen.editable_values(APP):
            self.assertIn(f'{low} := {member.minimum};', self.text)
            self.assertIn(f'{high} := {member.maximum};', self.text)

    def test_an_out_of_range_value_is_refused_not_clamped(self):
        """Core §5.6: reject with a reason, never a silent default. A clamp
        would leave the operator believing the number they typed took."""
        self.assertIn("config_out_of_range", self.text)
        self.assertNotIn("MAX(", self.text)
        self.assertNotIn("LIM(", self.text)

    def test_an_undeclared_ordinal_is_refused_by_name(self):
        self.assertIn("config_key_unknown", self.text)

    def test_a_value_requiring_idle_re_tests_running_on_the_controller(self):
        """The client may have been shown READY a scan ago."""
        ready = [m for _o, _r, m in gen.editable_values(APP) if m.requires_ready]
        self.assertTrue(ready)
        self.assertIn(f"IF FRK_{APP.name}_Unit.Running <> 0 THEN", self.text)
        self.assertIn("config_requires_ready", self.text)

    def test_the_commit_is_the_only_thing_after_the_guards(self):
        """No branch writes the record before its checks have passed."""
        for _ordinal, record, member in gen.editable_values(APP):
            assign = f"{record.name}Tag.{member.name} :="
            guard = self.text.index(f"({member.minimum})") \
                if f"({member.minimum})" in self.text else 0
            self.assertIn(assign, self.text)
            self.assertGreater(self.text.index(assign), guard)

    def test_the_refusal_keys_are_published_for_translation(self):
        keys = mailbox.localization_keys()
        for key in (mailbox.CONFIG_KEY_UNKNOWN_KEY,
                    mailbox.CONFIG_OUT_OF_RANGE_KEY,
                    mailbox.CONFIG_NOT_READY_KEY):
            self.assertIn(key, keys)

    def test_a_value_editable_while_running_still_tests_its_bounds(self):
        """The press declares no such value, so this path would otherwise be
        emitted and never exercised. requires_ready controls WHEN a value may
        be written; it must not control WHETHER the range is checked."""
        record = decl.Record(
            name="FRK_T_Live", station_cfg=True,
            members=(decl.scalar(decl.SCHEMA_VERSION_MEMBER, "", initial=0),
                     decl.editable(decl.scalar("Trim", "", initial=5),
                                   "live.trim", "k", minimum=1, maximum=9,
                                   requires_ready=False)))
        app = dataclasses.replace(APP, records=(record,), line=None)
        text = chr(10).join(mailbox._dispatch(app))
        value = config.candidate_tag(APP)
        low, high, flags = config.scratch_names(app)
        self.assertIn(f"IF ({value} < {low}) OR ({value} > {high}) THEN", text)
        self.assertIn(f'{flags} := 0;', text)
        self.assertIn(f'{low} := 1;', text)
        self.assertIn(f'{high} := 9;', text)
        self.assertIn("config_out_of_range", text)
        # And no idle gate, because this value does not need one.
        self.assertIn(f'IF ({flags} MOD 2) <> 0 THEN', text)

    def test_a_station_with_nothing_editable_emits_no_branch(self):
        bare = dataclasses.replace(APP, records=tuple(
            dataclasses.replace(r, members=tuple(
                dataclasses.replace(m, write_key="") for m in r.members))
            for r in APP.records))
        text = "\n".join(mailbox._dispatch(bare))
        self.assertNotIn("config_out_of_range", text)
        self.assertIn("no_config_manifest", text)


if __name__ == "__main__":
    unittest.main()

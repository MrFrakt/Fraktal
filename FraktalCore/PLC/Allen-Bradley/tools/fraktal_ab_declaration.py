#!/usr/bin/env python3
"""The Fraktal/AB declaration: the committed source a Logix application emits from.

One declaration is the source of truth for an application. The generator turns it
into contract UDTs, module AOIs, a mode owner, routine bodies and an L5X.
Hand-authored L5X is forbidden; if something is not expressible here, the
declaration grows - the output never gets edited.

**The S16 findings are rules here, not conventions.** Each is enforced by
``validate`` and covered by a negative test, because a rule that cannot reject
anything is a comment:

1. **Ordering is self-checked.** Every emitted mode owner verifies that each
   child module AOI ran in this scan and counts a violation if not. S11 proved
   the ordering for sequences and S16 restated it for commands; a generator that
   emitted the call order correctly but could not detect its own violation would
   be relying on the author having got it right.
2. **Durations are milliseconds, converted from the declared task period**, and
   the emitted project asserts at build time that the task it is scheduled on
   still has that period. S16 found the task rate is part of the contract: a
   module moved to a task of another period silently changes its own timeouts.
3. **A held command's timeout does not accrue.** Held exists to distinguish "the
   operator let go" from "the machine is broken"; a hold that matures into a
   timeout destroys that distinction.
4. **The frozen v33 type map.** Booleans are 0/1 ``DINT``; durations are
   range-checked ``DINT`` milliseconds. ``TIME``/``TIME32``/``LREAL`` are absent
   and ``LINT`` is transport-only (S12). **No ``BOOL`` member may appear in a
   public contract UDT** - that layout is a recorded S12 hole, not a local call.
5. **Every ParCfg-shaped record starts with ``SchemaVersion : DINT``** (Core
   §3.8), so a reader can tell which contract it is holding before it reads it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence


# --- the frozen v33 type map (S12) -----------------------------------------

DINT = "DINT"
EXCLUDED_TYPES = ("TIME", "TIME32", "LREAL")
TRANSPORT_ONLY_TYPES = ("LINT",)
BOOLEAN_CARRIER = DINT       # 0/1, never BOOL - the S12 hole
DURATION_CARRIER = DINT      # milliseconds, range checked

DURATION_MIN_MS = 0
DURATION_MAX_MS = 3_600_000  # one hour; a range check that can actually reject

SCHEMA_VERSION_MEMBER = "SchemaVersion"


class DeclarationError(ValueError):
    """The declaration is not emittable. Raised instead of emitting bad Logix."""


# --- members and records ----------------------------------------------------

@dataclass(frozen=True)
class Member:
    """One contract UDT member. Everything is a DINT on this baseline."""

    name: str
    comment: str = ""
    kind: str = "scalar"          # scalar | boolean | duration_ms | reason
    dimension: int = 0
    initial: int = 0
    external_access: str = "Read/Write"

    # Core §3.10.2 write capability. A member with a `write_key` is EDITABLE:
    # a client may ask to change it, and the controller validates the ask
    # against `minimum`/`maximum` before committing. Empty means read-only,
    # which is the default - a value becomes editable because someone declared
    # it so, never because it happened to live in a configuration record.
    write_key: str = ""
    label_key: str = ""
    minimum: int = 0
    maximum: int = 0
    # Core §3.8a: most deployment values are only safe to change while the
    # owning root is idle. The controller re-tests this; the flag tells a
    # client so it can grey the field instead of offering a write that will be
    # refused.
    requires_ready: bool = True
    # Core 3.8c: a root-owned published scalar, relative to that root's
    # manifest (e.g. Profiler.LastWork). Empty offers no capture.
    capture_source: str = ""
    # Core 3.8d: independent of ConfigKind; '' uses DATA_READ/DATA_WRITE.
    class_id: str = ""
    min_read_level: int = 0
    min_write_level: int = 0

    @property
    def data_type(self) -> str:
        return DINT

    @property
    def editable(self) -> bool:
        return bool(self.write_key)


def editable(member: Member, write_key: str, label_key: str,
             minimum: int, maximum: int,
             requires_ready: bool = True) -> Member:
    """Mark a declared member editable, with the bounds the PLC will enforce.

    Bounds are mandatory rather than optional. An unbounded editable DINT on a
    machine is not a configuration value, it is a way to write 2147483647 into
    a dwell time; Core §5.6 says validate against the supported set and reject
    out of range with a reason, and a range nobody declared cannot be checked.
    """
    return replace(
        member, write_key=write_key, label_key=label_key,
        minimum=minimum, maximum=maximum, requires_ready=requires_ready)


def capture(member: Member, source: str) -> Member:
    """Offer a published machine value beside an already-editable field."""
    return replace(member, capture_source=source)


def config_access(member: Member, class_id: str = "", *,
                  min_read_level: int = 0, min_write_level: int = 0) -> Member:
    """Assign an editable value's class and immutable raise-only minima."""
    return replace(member, class_id=class_id, min_read_level=min_read_level,
                   min_write_level=min_write_level)


@dataclass(frozen=True)
class DataClass:
    """Root-owned deployment policy; these levels are retained defaults."""
    class_id: str
    label_key: str
    read_level: int = 0
    write_level: int = 0


def ideal_cycle_ms(initial: int, key: str,
                   comment: str = "the model's ideal cycle, for OEE Performance"
                   ) -> Member:
    """Core §8.5.1's per-model ideal cycle: the ParCfg member OEE Performance
    divides by, with TC3's label and range. The write key is the station's
    (TC3's press registers ``press.recipe.idealCycleMs``). Put it in the ParCfg
    record, name it in ``ideal_cycle_member``, and give every model a value -
    an ideal above the real cycle caps Performance at 100 %."""
    return editable(duration_ms("IdealCycleMs", comment, initial=initial),
                    key, "project.config.idealCycleMs", minimum=0, maximum=600000)


def baseline_work_ms(initial: int, key: str,
                     comment: str = "the model's WORK-time baseline, for the "
                                    "degradation watch") -> Member:
    """Core §8.11.4(d)'s per-model WORK-time baseline, with TC3's label and
    range; 0 turns the watch off. The write key is the station's (TC3's press:
    ``press.recipe.baselineWorkMs``). Name it in ``baseline_work_member``."""
    return editable(duration_ms("BaselineWorkMs", comment, initial=initial),
                    key, "project.config.baselineWorkMs", minimum=0, maximum=600000)


def boolean(name: str, comment: str = "", initial: int = 0,
            dimension: int = 0) -> Member:
    """A 0/1 DINT. Not a BOOL: the BOOL-member UDT layout is unmeasured (S12)."""
    return Member(name, comment, kind="boolean", initial=initial,
                  dimension=dimension)


def duration_ms(name: str, comment: str = "", initial: int = 0,
                dimension: int = 0) -> Member:
    return Member(name, comment, kind="duration_ms", initial=initial,
                  dimension=dimension)


def reason(name: str, comment: str = "", dimension: int = 0) -> Member:
    return Member(name, comment, kind="reason", dimension=dimension)


def scalar(name: str, comment: str = "", initial: int = 0, dimension: int = 0) -> Member:
    return Member(name, comment, kind="scalar", initial=initial, dimension=dimension)


@dataclass(frozen=True)
class Record:
    """A contract UDT.

    ``par_cfg`` marks the Core §3.8 configuration shape, which must lead with
    ``SchemaVersion``.

    ``station_cfg`` marks the Core §3.8a DEPLOYMENT shape. Both lead with
    ``SchemaVersion`` and the difference is what the first member STARTS at.
    A ParCfg ships with the program, so its version starts at the contract it
    is. A StationCfg is commissioned on the machine and has to survive, so its
    version starts at **zero** — Core §3.8a's "never written".

    That is not a convention borrowed from TwinCAT; it is the one marker Logix
    actually gives us. A Logix tag has no PERSISTENT class: values live in
    ESM-backed controller memory and a DOWNLOAD resets them to the values in
    the L5X. So a downloaded station reads its own initial value, sees zero,
    and initializes its declared defaults silently — which is exactly right,
    because a first boot has lost nothing. Any OTHER unrecognized version means
    a real commissioned image was rejected, and Core §3.8a says that shall be
    annunciated. The two cases are distinguishable only because zero is
    reserved, so it is reserved here by validation rather than by habit.
    """

    name: str
    members: tuple[Member, ...]
    comment: str = ""
    par_cfg: bool = False
    station_cfg: bool = False
    schema_version: int = 1
    line_cfg: bool = False


# --- modules ----------------------------------------------------------------

@dataclass(frozen=True)
class Command:
    """One command a module accepts, and where its simulated plant ends up."""

    name: str
    ordinal: int
    target_position: int
    comment: str = ""


@dataclass(frozen=True)
class ModuleType:
    """A reusable module type: ONE AOI definition, identical in every
    application that uses it - the Logix counterpart of a TC3 Fraktal_Modules
    function block.

    Logix links nothing at run time; every project must contain the AOIs it
    calls. So "a library" here means one canonical definition per type,
    generated from the type alone and embedded byte-for-byte, and the proof
    that it is a library is that two applications embed the same bytes.

    It therefore owns everything its logic depends on. Before this, the
    cylinder AOI was generated once per INSTANCE and read three things from
    the application that embedded it: the context UDT's name, the task period
    as a literal, and its own reason codes out of the application's reason
    table. A type that borrows its reason codes from whoever embeds it is not
    a type.

    ``reasons`` are the codes this type raises, by name. An application
    registers them for rationalization, and validation holds the two equal:
    the type is the source, the registration is checked against it.
    """

    type_key: str
    description: str
    reasons: dict[str, int] = field(default_factory=dict)
    # The I/O points a diagnostic of this type can implicate, as roles an
    # application binds to its electrical tags (`IoChannel.role`). Role i is
    # bit i of the context's `OutImm_IoRoles`: the AOI says WHICH point, as a
    # number, and the gateway turns it into the tag - TC3's CM names the tag
    # itself, which Logix v33 ST cannot do with a string (S12).
    io_roles: tuple[str, ...] = ()
    # A passive type is fed, never commanded: an instance declares an `input`
    # and no commands, and any command it receives is refused.
    passive: bool = False
    # The simulated plant's injections an instance of this type takes, each an
    # `<Name>Request` member fed from `FRK_<App>_<Name><Module>` every scan.
    # They are the evidence harness's surface, so a type declares its own.
    injections: tuple[str, ...] = ()


@dataclass(frozen=True)
class Module:
    """A module type: the Core §6.1 handshake over a simulated plant.

    ``adopts_faults`` records whether a parent awaiting this module adopts its
    first-out verbatim. It is a property of how the chain awaits the child, so
    the chain step carries the choice; this flag is the module's default.
    """

    name: str
    comment: str
    commands: tuple[Command, ...]
    speed_per_scan: int = 25
    timeout_ms: int = 500
    position_min: int = 0
    position_max: int = 100
    can_fault: bool = True
    # LOCALIZATION §7.1: what a faceplate is authored against. Every instance
    # of a type names the same key, and it is the same key the TwinCAT binding
    # publishes for that type, which is what lets one faceplate serve both. It
    # is presentation vocabulary: the gateway projects it from this
    # declaration, and it is not part of the controller manifest.
    type_key: str = ""
    # A passive input's source (TC3's HAL value): the tag the routine copies
    # into its RawValue every scan, before the module runs. Empty for a type
    # that is commanded instead.
    input: str = ""
    # TC3's SetAreaSafe: the application's interlock on this module, a step-
    # style condition (a tag or a ModuleState). Lost while commanded, the
    # module HOLDS on INTERLOCK_DROPPED and resumes by itself. None: always safe.
    area_safe: object = None
    # Configuration the application binds into this instance, each scan:
    # (context member, record name, record member). TC3's module registers its
    # own station value; here the application's StationCfg holds it, under the
    # type's own write key, and the routine carries it in.
    config: tuple = ()
    # The localization key the module reports when `area_safe` is what holds
    # it - TC3's SetAreaSafe DescriptionKey.
    area_safe_key: str = ""
    # TC3's SetDirectionalPermits: per command name, the Permits that command
    # needs, in first-out order. A command not listed is always permitted.
    # Lost while the command runs, the module HOLDS on INTERLOCK_DROPPED and
    # names the missing permit; in AUTO and MANUAL alike.
    permits: tuple = ()


@dataclass(frozen=True)
class ModuleState:
    """A step condition on a module's published state: it holds when every
    named member is non-zero. TC3's press waits at N100 on
    `PartPresentSensor.OutImm.Value AND .Quality`; this is that condition,
    declared rather than written."""

    module: str
    members: tuple[str, ...]
    # Members that must be ZERO for the condition to hold - TC3 writes
    # `PartSlide.OutImm.Extended AND NOT PartSlide.Busy AND NOT PartSlide.Error`
    # for a door's close permit, and the NOT half is a module state too.
    zero: tuple[str, ...] = ()


@dataclass(frozen=True)
class Permit:
    """One named condition a commanded direction needs (TC3's
    SetDirectionalPermits). Every condition in `conditions` must hold; `key` is
    the localization key the module reports when this permit is the one that
    is missing. A direction's permits are listed in first-out order, as TC3's
    press chooses the ram's: the first missing one is the one named."""

    conditions: tuple
    key: str
    # Empty applies in every mode; otherwise this is a mode-entry permit.
    modes: tuple[int, ...] = ()


@dataclass(frozen=True)
class StateFlag:
    """Core §3.12, TC3's _M_State: a named Boolean that is TRUE RIGHT NOW,
    derived from the modules every scan and never latched. `key` is what the
    operator reads; every condition in `conditions` must hold. TC3's press
    declares `pressAtLoadPosition` - its OutImm.Homed - this way, precisely
    because a latched "homed" keeps claiming it after a jog in MANUAL."""

    key: str
    conditions: tuple


@dataclass(frozen=True)
class SystemHealth:
    """Core §8.12 thresholds and requirements: TC3's ST_SystemHealthParCfg,
    reduced to what a Logix controller reports (AB spike S3). CPU load, free
    memory, IPC and distributed clock have no source here and are published
    unavailable, so they carry no threshold."""

    max_task_cycle_us: int
    max_task_jitter_us: int
    require_time_sync: bool = True
    require_fieldbus: bool = False
    require_dc_sync: bool = False

    @classmethod
    def for_task(cls, task_period_ms: int, *, require_time_sync: bool = False,
                 require_fieldbus: bool = False,
                 require_dc_sync: bool = False) -> "SystemHealth":
        """The default for a station on this baseline: an overrun is a real
        period over twice the declared one, high jitter is over a fifth of it
        (on 10 ms: 20 ms and 2 ms, ten times the worst S3 measured), and
        nothing this controller cannot have is required. Require time sync
        only where the station runs CIP Sync / PTP."""
        return cls(max_task_cycle_us=2 * task_period_ms * 1000,
                   max_task_jitter_us=task_period_ms * 1000 // 5,
                   require_time_sync=require_time_sync,
                   require_fieldbus=require_fieldbus,
                   require_dc_sync=require_dc_sync)


# TC3's PL_Fraktal.MAX_STATE_FLAGS: the published table's bound.
MAX_STATE_FLAGS = 12


@dataclass(frozen=True)
class UnitState:
    """A step condition on the owning Unit's own context - TC3's press waits
    at N100 on its own `_startLatched`."""

    members: tuple[str, ...]


@dataclass(frozen=True)
class RequiredBy:
    """A condition that counts only while a station policy asks for it.

    TC3's press writes `_twoHand.OutImm.SafeActive OR NOT
    _stationCfg.RequireTwoHandStart`: the two-hand is waited on only where the
    cell's risk assessment requires it, and the policy is deployment data, not
    a model's. `policy` names a boolean member of the station's StationCfg;
    with it set the condition is `condition`, with it clear it holds.
    """

    condition: object
    policy: str


def condition_base(condition) -> object:
    """The condition a policy gates, or the condition itself."""
    return condition.condition if isinstance(condition, RequiredBy) else condition


@dataclass(frozen=True)
class StartControl:
    """A physical start, as TC3's press has it (FB_PressDemoUnit.OnCyclic).

    A pulse of `pulse` in `mode` starts the chain from ready, through the same
    predicate an operator START uses, and latches `StartLatched` - but only
    when every `requires` condition already holds, so a press made before the
    part was loaded never starts the stroke when the part arrives. The latch
    is what the start step waits on; the chain clears it at cycle end, and an
    abort, a reset or a mode change clears it too.
    """

    pulse: ModuleState
    mode: int
    requires: tuple = ()


# --- chain steps ------------------------------------------------------------

ISSUE = "issue"                 # command a module, wait for Done
GUARDED = "guarded"             # command while conditions hold; losing one abandons it
DELAY = "delay"                 # wait a declared duration; paused while a condition fails
AWAIT = "await"                 # wait for named conditions
DECISION = "decision"           # wait for an operator answer, never faults
ADOPT = "adopt"                 # awaited child: adopt its first-out verbatim
REPORT = "report"               # child error reported, NOT adopted, then jump
MARK = "mark"                   # set a counter or flag
COMPLETE = "complete"           # terminal for a non-looping chain


# Core E_RunStyle, pinned to the TwinCAT DUT by test (§3.4.2).
RUN_CONTINUOUS, RUN_SINGLE_STEP, RUN_HOLD_TO_RUN = 0, 1, 2
RUN_STYLES = (RUN_CONTINUOUS, RUN_SINGLE_STEP, RUN_HOLD_TO_RUN)


@dataclass(frozen=True)
class Step:
    """One step of one chain."""

    number: int
    name: str
    action: str
    comment: str = ""
    module: str = ""
    command: str = ""
    duration_member: str = ""
    conditions: tuple[str, ...] = ()
    # The reason a waiting step publishes while a condition is missing.
    hold_reason: int = 0
    adopt_from: str = ""
    report_reason: int = 0
    decision_id: int = 0
    on_advance: int = -1
    on_jump: int = -1
    # A MARK step's work; on a commanding step, what completion does (TC3's
    # N190 drops the start latch when the slide is out).
    marks: tuple[str, ...] = ()
    time_class: str = "WORK"
    # Core §6.9(b): what the step is waiting for, by name. One label key per
    # entry of `conditions`, in order. The operator reads these, so a
    # condition without one is refused - a wait nobody can name is exactly
    # the stall §6.9 exists to explain.
    condition_labels: tuple[str, ...] = ()
    # TC3's M_TryIssue(Steppable := ...): a commanding step is a stop point
    # for SINGLE_STEP and HOLD_TO_RUN. False runs it straight through - a
    # step unsafe to pause before, or one grouped with the step before it.
    steppable: bool = True


# Core E_TimeClass, in ordinal order (§8.11.4(f)); pinned to the TwinCAT DUT by
# test_fraktal_ab_core_ordinals. WAIT_UPSTREAM and WAIT_DOWNSTREAM are what
# Starved and Blocked are derived from (§8.11.3).
TIME_CLASSES = ("WORK", "WAIT_UPSTREAM", "WAIT_DOWNSTREAM", "WAIT_OPERATOR",
                "WAIT_EXTERNAL")

# Core §6.9(b) condition records per step: TC3 PL_Fraktal.MAX_STEP_CONDS.
MAX_STEP_CONDS = 8


def declared_modes(app: "Application") -> tuple[int, ...]:
    """Every mode the application offers: each chain's, and the manual mode,
    which has none. One source for the mode select, the mode policy and the
    manifest."""
    modes = {c.mode_ordinal for c in app.chains}
    if app.manual_mode is not None:
        modes.add(app.manual_mode)
    return tuple(sorted(modes))


def module_permits(module: "Module", command: str) -> tuple:
    """The Permits a module's command needs, in first-out order."""
    for name, permits in module.permits:
        if name == command:
            return tuple(permits)
    return ()


def step_conditions(step: "Step") -> tuple[tuple[str, str], ...]:
    """(tag, label key) for each condition the step waits on, in record order.

    The one place both halves read: the generator writes `Chart.CondOk[i]` in
    this order, and the projection names slot i with this label. A guarded
    command's guard is its record 1, as TC3's AUTO N180 records it.
    """
    if step.action in (AWAIT, DELAY, GUARDED):
        return tuple(zip(step.conditions, step.condition_labels))
    return ()


def expected_member(step: "Step") -> str:
    """TC3's M_Step ExpectedTime, as the ParCfg duration member that holds it.

    A delay is expected to take its duration - TC3's N170 and N220 pass the
    same value to ExpectedTime and to M_Delay - so it is derived, never
    declared twice. Every other step expects nothing, as TC3's pass T#0S.
    """
    return step.duration_member if step.action == DELAY else ""


# The languages a chain's graph may be rendered in. The graph is declared once;
# a rendition is an emission of it, never a second maintained source. TC3 keeps
# the same rule for its press: one graph, several renditions, machine-checked
# for equality.
ST = "ST"
SFC = "SFC"
LD = "LD"
RENDITIONS = (ST, SFC, LD)


@dataclass(frozen=True)
class Chain:
    """One mode's step graph, and the languages it is rendered in."""

    name: str
    mode_ordinal: int
    steps: tuple[Step, ...]
    comment: str = ""
    loops: bool = False
    renditions: tuple[str, ...] = (ST,)

    @property
    def multi_rendition(self) -> bool:
        """True when this chain is carried in more than one language.

        A multi-rendition chain is hosted in program routines rather than inside
        the mode-owner AOI: an Add-On Instruction cannot contain an SFC routine,
        so the only way to render the same graph in all three languages is to
        put each rendition where all three can live.
        """
        return len(self.renditions) > 1


# --- the application --------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    """One operator decision a chain can wait on (Core §6.11).

    The controller publishes only the decision's ID - it cannot hold the
    prompt text, because v33 ST will not assign a string literal - so the
    question and its answers are declared here and the gateway resolves them
    against the live ID. Same seam as the step names and the model codes.

    Answer 1 advances the step and anything else takes its jump, which is the
    emitted DECISION logic, so the FIRST option is always the one that
    continues. Declaring them the other way round would put "scrap the part"
    under the button that means "carry on".
    """

    identifier: int
    prompt_key: str
    option_keys: tuple[str, ...]


# --- changeover ---------------------------------------------------------------


@dataclass(frozen=True)
class Model:
    """One changeover model: a named set of `ParCfg` values.

    Core §3.8 splits changeover into a FALLIBLE prepare and an INFALLIBLE
    bounded commit, and that split is why a model is declared as data rather
    than as logic. Everything that can be rejected - is this a model this
    station has? - is decided before the commit, so the commit is a bounded
    copy of known-good numbers into the configuration record and cannot fail
    halfway and leave the press configured as neither model.

    `values` names `ParCfg` members. A member this application does not
    declare is rejected here, not discovered when the copy writes nothing.
    """

    code: str
    description_key: str
    values: dict[str, int]


# --- physical I/O -----------------------------------------------------------

# E_ChannelDir / E_ChannelKind / E_NodeState, from the Core DUTs. Pinned by
# test_fraktal_ab_core_ordinals.py against the TwinCAT sources, like every
# other ordinal that crosses this boundary.
DIR_INPUT = 0
DIR_OUTPUT = 1
KIND_DIGITAL = 0
KIND_ANALOG = 1
NODE_OFFLINE = 0
NODE_OPERATIONAL = 4
NODE_FAULT = 5


@dataclass(frozen=True)
class IoChannel:
    """One physical channel, named by its electrical tag.

    ``name`` **is** the approved electrical tag, verbatim. `HMI_CONTRACT.md`
    requires it, because that is what lets an alarm cross-link to the fieldbus
    view; the operator-facing text lives in ``description_key`` and is the only
    part that may be localized.

    ``bit`` is the position in the owning module's data word, and it is kept
    equal to the TC3 channel number minus one so this declaration reads
    directly against `CX2030_PRESS_IO_MAPPING.md`. Channels TC3 leaves
    unmapped stay unmapped here rather than being closed up.
    """

    name: str
    description_key: str
    bit: int
    direction: int
    kind: int = KIND_DIGITAL
    unit: str = ""
    module_path: str = ""
    # Which of its module type's `io_roles` this channel is, so a diagnostic
    # that implicates the role names this electrical tag. Empty: none.
    role: str = ""


@dataclass(frozen=True)
class IoModule:
    """A physical I/O module in the controller's local chassis."""

    name: str
    type_id: str
    address: str
    description_key: str
    data_width: int
    channels: tuple[IoChannel, ...]

    @property
    def input_tag(self) -> str:
        return f"{self.address}:I.Data"

    @property
    def output_tag(self) -> str:
        return f"{self.address}:O.Data"

    @property
    def fault_tag(self) -> str:
        return f"{self.address}:I.Fault"


@dataclass(frozen=True)
class ReadBudget:
    """Deployment transport limits, not PLC data or a manifest identity."""

    poll_period_ms: int
    cache_ms: int
    fast_good_ms: int
    fast_expiry_ms: int
    slow_period_ms: int
    slow_good_ms: int
    slow_expiry_ms: int
    connection_bytes: int = 500

    def validate(self):
        fields = {k: v for k, v in vars(self).items() if k != 'connection_bytes'}
        if any(type(v) is not int or not 0 < v <= 60000 for v in fields.values()):
            return ['read budget requires positive integer milliseconds, at most 60000']
        if type(self.connection_bytes) is not int or not 500 <= self.connection_bytes <= 4000:
            return ['read connection requires 500..4000 bytes, proven on the deployment target']
        if not (self.cache_ms < self.poll_period_ms < self.fast_good_ms < self.fast_expiry_ms
                and self.slow_period_ms < self.slow_good_ms < self.slow_expiry_ms):
            return ['read budget requires cache < poll < Good < expiry and slow period < Good < expiry']
        return []

    def wire(self):
        return dict(schemaVersion=1, pollPeriodMs=self.poll_period_ms,
                    fastGoodMs=self.fast_good_ms, fastExpiryMs=self.fast_expiry_ms,
                    slowPeriodMs=self.slow_period_ms, slowGoodMs=self.slow_good_ms,
                    slowExpiryMs=self.slow_expiry_ms)


# Core E_ConfigStore, append-only and pinned to the TwinCAT DUT by test.
CONFIG_STORE_FILE_JSON = 1
CONFIG_STORE_EXTERNAL = 3
CONFIG_STORE_NAMES = {CONFIG_STORE_FILE_JSON: "FILE_JSON", CONFIG_STORE_EXTERNAL: "EXTERNAL"}


@dataclass(frozen=True)
class ConfigMedium:
    """Core 3.8b: where the gateway keeps this station's documents.

    The project picks the medium here, the way TC3's MAIN declares its
    I_PersistMedium and hands it to the root, the set store and the users.
    The directory is deployment data (one per controller serial), not part of
    the declaration. A database medium (EXTERNAL) is the same interface and is
    refused until an owner names its server, schema and credentials owner.

    `live_documents` keeps the root's station, line and model data as documents
    on the same medium and re-applies them through the controller's staged
    set path when the controller starts on an image it did not keep (after a
    download), instead of seeding each new image from a capture.
    """

    store: int = CONFIG_STORE_FILE_JSON
    live_documents: bool = False


def config_medium(app: "Application") -> "ConfigMedium | None":
    """The medium in force: a set store with no declared medium is the file
    medium, which is what every declaration before ConfigMedium had."""
    if app.config_medium is not None:
        return app.config_medium
    return ConfigMedium() if app.config_sets else None


def live_documents(app: "Application") -> bool:
    medium = config_medium(app)
    return medium is not None and medium.live_documents


@dataclass(frozen=True)
class Application:
    """One committed declaration: everything a Logix project is emitted from."""

    name: str
    controller: str
    major_revision: int
    task_name: str
    task_period_ms: int
    watchdog_ms: int
    comment: str
    records: tuple[Record, ...]
    modules: tuple[Module, ...]
    chains: tuple[Chain, ...]
    reasons: dict[str, int] = field(default_factory=dict)
    # Simulated operator and sensor inputs the harness writes. Every condition a
    # step waits on must name one of these: a condition referencing a tag that
    # does not exist is rejected here rather than discovered in Studio.
    sim_inputs: tuple[str, ...] = ()
    # Physical I/O, if the application has any. Empty means the plant is
    # arithmetic on controller tags and no fieldbus root is published.
    io_modules: tuple[IoModule, ...] = ()
    # Changeover models. Empty means the station has one configuration and
    # publishes no model, which is what SET_MODEL is refused against.
    models: tuple[Model, ...] = ()
    # The operator decisions this application's chains wait on.
    decisions: tuple[Decision, ...] = ()
    # The root Unit's type key (LOCALIZATION §7.1); empty = none published.
    type_key: str = ""
    # The model a freshly downloaded station is configured as. A station is
    # always running SOME set of numbers, so "no model" at boot is a station
    # that cannot tell you which product it is set up for.
    default_model: str = ""
    chart_steps: int = 32
    # Core §6.9: how long a step may run unheld before it is a stall. TC3's
    # FB_UnitBase.StallTime default, T#30S.
    stall_time_ms: int = 30000
    start_control: "StartControl | None" = None
    # TC3's MANUAL: a mode with no sequence. Its modules take the operator's
    # manual commands directly, through their interlocks, and Start is refused
    # there - there is nothing to start. None: every mode is a chain's.
    manual_mode: "int | None" = None
    # TC3's mode-entry release (FB_PressDemoRelease.ModeStart): conditions a
    # START needs on top of the Unit's own, each reported as
    # PERMISSIVE_NOT_MET under its key. Distinct from what a step waits on
    # later: those stay in the step's own condition record.
    start_permits: tuple = ()
    # Optional bounded PLC-owned catalog; zero retains the static catalog.
    model_capacity: int = 0
    # TC3's _M_SupportsRunStyle: the run styles the Unit's sequences may be
    # paced in (§3.4.2). CONTINUOUS always; SINGLE_STEP and HOLD_TO_RUN only
    # where every motion boundary is paced. NON-SAFETY: interlocks and the
    # certified safety layer are unaffected.
    run_styles: tuple = (RUN_CONTINUOUS,)
    # Core §8.5.1: the ParCfg member holding the model's ideal cycle time, in
    # ms - TC3's Oee.IdealCycleMs, set from ParCfg.IdealCycleMs per model.
    # Empty: Performance is never computed, and is published invalid rather
    # than 100 % (O7).
    ideal_cycle_member: str = ""
    # Core §8.11.4(d): the ParCfg member holding the model's WORK-time
    # baseline, in ms - TC3's Profiler.BaselineWorkMs. A cycle whose WORK time
    # passes it by more than the band raises one maintenance event per
    # excursion. Empty, or a baseline of 0: the watch is off.
    baseline_work_member: str = ""
    # Core §3.12: the Unit's derived state flags, published on TC3's generic
    # StateFlags table with the moment each last changed.
    state_flags: tuple = ()
    # Core §8.12: the station's health thresholds; None publishes no health.
    system_health: "SystemHealth | None" = None
    # Core 3.8b: opt-in gateway document store and controller set transaction.
    config_sets: bool = False
    # Core 3.8b: the medium those documents live on; None is the file medium.
    config_medium: ConfigMedium | None = None
    # Core 7.7: controller-owned policy/session and private provider records.
    # None keeps an older declaration's contract; () enables an empty provider.
    access_users: tuple | None = None
    data_classes: tuple[DataClass, ...] = ()
    program_name: str = ""
    routine_name: str = ""
    read_budget: ReadBudget | None = None
    # Optional composition-owned line, beside (never inside) the root forest.
    line: object | None = None

    @property
    def program(self) -> str:
        return self.program_name or f"FRK_{self.name}Program"

    @property
    def routine(self) -> str:
        return self.routine_name or f"FRK_{self.name}Main"


# --- validation -------------------------------------------------------------

def _validate_record(record: Record) -> list[str]:
    findings: list[str] = []
    if not record.members:
        findings.append(f"{record.name}: a contract record with no members")
    for member in record.members:
        if member.data_type != DINT:
            findings.append(
                f"{record.name}.{member.name}: {member.data_type} is not on the "
                f"frozen v33 map; every contract scalar is a DINT"
            )
        if member.kind == "duration_ms" and not (
            DURATION_MIN_MS <= member.initial <= DURATION_MAX_MS
        ):
            findings.append(
                f"{record.name}.{member.name}: duration {member.initial} ms is "
                f"outside the checked range {DURATION_MIN_MS}..{DURATION_MAX_MS}"
            )
        if member.kind == "boolean" and member.initial not in (0, 1):
            findings.append(
                f"{record.name}.{member.name}: a boolean carrier holds 0 or 1, "
                f"not {member.initial}"
            )
    for member in record.members:
        if not member.editable:
            continue
        if member.minimum > member.maximum:
            findings.append(
                f"{record.name}.{member.name}: minimum {member.minimum} is "
                f"above maximum {member.maximum}, so nothing can be written"
            )
        if not (member.minimum <= member.initial <= member.maximum):
            findings.append(
                f"{record.name}.{member.name}: the declared default "
                f"{member.initial} is outside its own range "
                f"[{member.minimum}, {member.maximum}] — a §3.8a restore would "
                f"install a value the same contract refuses to accept"
            )
        if member.kind == "boolean" and (member.minimum, member.maximum) != (0, 1):
            findings.append(
                f"{record.name}.{member.name}: a boolean carrier's range is "
                f"0..1, not [{member.minimum}, {member.maximum}]"
            )
        if not member.label_key:
            findings.append(
                f"{record.name}.{member.name}: an editable value needs a "
                f"label_key — an operator editing an unnamed number is the "
                f"failure this costs nothing to prevent"
            )
    if record.par_cfg or record.station_cfg or record.line_cfg:
        shape = "ParCfg" if record.par_cfg else "LineCfg" if record.line_cfg else "StationCfg"
        clause = "§3.8" if record.par_cfg else "§3.8e" if record.line_cfg else "§3.8a"
        if not record.members or record.members[0].name != SCHEMA_VERSION_MEMBER:
            findings.append(
                f"{record.name}: a {shape}-shaped record shall start with "
                f"{SCHEMA_VERSION_MEMBER} (Core {clause})"
            )
    if record.par_cfg and record.station_cfg:
        findings.append(
            f"{record.name}: a record is recipe data or deployment data, not "
            f"both — they differ in what survives a download (Core §3.8/§3.8a)"
        )
    if (record.station_cfg or record.line_cfg) and record.members \
            and record.members[0].name == SCHEMA_VERSION_MEMBER \
            and record.members[0].initial != 0:
        findings.append(
            f"{record.name}.{SCHEMA_VERSION_MEMBER}: retained configuration starts at 0, "
            f"not {record.members[0].initial}. Zero is Core §3.8a's 'never "
            f"written', and on Logix it is also what a download leaves behind — "
            f"a non-zero initial makes a fresh controller claim it holds a "
            f"commissioned image it has never been given"
        )
    if (record.station_cfg or record.line_cfg) and record.schema_version == 0:
        findings.append(
            f"{record.name}: schema_version 0 is reserved for 'never written' "
            f"and cannot be a real contract version (Core §3.8a)"
        )
    names = [m.name for m in record.members]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        findings.append(f"{record.name}: duplicate members {sorted(duplicates)}")
    return findings


def _module_state_findings(app: "Application", where: str,
                           condition: "ModuleState") -> list[str]:
    findings: list[str] = []
    if condition.module not in {m.name for m in app.modules}:
        findings.append(f"{where}: condition on unknown module {condition.module!r}")
    if not condition.members and not condition.zero:
        findings.append(f"{where}: a module condition names no member")
    return findings


def _permit_findings(app: "Application", where: str, permits) -> list[str]:
    """Each permit names what it is waiting for, from module states."""
    findings: list[str] = []
    for permit in permits:
        if not permit.key.startswith(("project.", "std.")):
            findings.append(f"{where}: permit key {permit.key!r} is not a "
                            f"localization key")
        if not permit.conditions:
            findings.append(f"{where}: permit {permit.key} has no condition")
        for condition in permit.conditions:
            if isinstance(condition, ModuleState):
                findings.extend(_module_state_findings(app, where, condition))
            elif isinstance(condition, (UnitState, RequiredBy)):
                findings.append(f"{where}: a permit reads module states only")
            elif condition not in app.sim_inputs:
                findings.append(f"{where}: condition {condition!r} is not a "
                                f"declared simulated input")
    return findings


def _validate_permits(app: "Application", module: "Module") -> list[str]:
    """TC3's directional permits: each names a command the module has, and
    each permit names what it is waiting for."""
    findings: list[str] = []
    commands = {c.name for c in module.commands}
    seen: set[str] = set()
    for name, permits in module.permits:
        where = f"{module.name}.{name}"
        if name not in commands:
            findings.append(f"{where}: a permit for a command {module.name} "
                            f"does not have")
        if name in seen:
            findings.append(f"{where}: permits declared twice")
        seen.add(name)
        findings.extend(_permit_findings(app, where, permits))
    if module.area_safe is not None and not module.area_safe_key:
        findings.append(f"{module.name}: an area interlock needs the key it "
                        f"reports when it holds the module")
    return findings


def _validate_chain(app: Application, chain: Chain) -> list[str]:
    findings: list[str] = []
    numbers = [s.number for s in chain.steps]
    duplicates = {n for n in numbers if numbers.count(n) > 1}
    if duplicates:
        findings.append(f"{chain.name}: duplicate step numbers {sorted(duplicates)}")
    known = set(numbers)
    module_names = {m.name for m in app.modules}
    duration_members = {
        m.name for r in app.records for m in r.members if m.kind == "duration_ms"
    }
    for step in chain.steps:
        where = f"{chain.name}.N{step.number}"
        for target, label in ((step.on_advance, "on_advance"), (step.on_jump, "on_jump")):
            if target != -1 and target not in known:
                findings.append(f"{where}: {label} targets missing step N{target}")
        if step.action in (ISSUE, GUARDED, ADOPT) and step.module not in module_names:
            findings.append(f"{where}: unknown module {step.module!r}")
        if step.action in (ISSUE, GUARDED):
            module = next(m for m in app.modules if m.name == step.module)
            if step.command not in {c.name for c in module.commands}:
                findings.append(
                    f"{where}: {step.module} has no command {step.command!r}"
                )
        if step.action == DELAY and step.duration_member not in duration_members:
            findings.append(
                f"{where}: delay references {step.duration_member!r}, which is not "
                f"a declared duration member"
            )
        if step.action == GUARDED:
            # TC3's N180: losing the guard abandons the command with a §6.9(e)
            # warning and takes the recovery jump. Each half has to be named.
            if not step.conditions:
                findings.append(f"{where}: a guarded command needs a guard condition")
            if step.on_jump == -1:
                findings.append(f"{where}: a guarded command needs the jump it "
                                f"takes when abandoned")
            if not step.report_reason:
                findings.append(f"{where}: a guarded command needs the warning "
                                f"reason it raises when abandoned")
        if step.marks and step.action not in (MARK, ISSUE, GUARDED):
            findings.append(f"{where}: only a mark or a commanding step carries marks")
        if step.action == REPORT and not step.report_reason:
            findings.append(f"{where}: a reported child condition needs a reason")
        if step.action == DECISION and not step.decision_id:
            findings.append(f"{where}: a decision step needs a decision id")
        if step.time_class not in TIME_CLASSES:
            findings.append(f"{where}: time class {step.time_class!r} is not a "
                            f"Core E_TimeClass member")
        # A delay's conditions pause it - TC3's N220 dwell, which does not
        # call M_Delay while the two-hand is released - so its time counts
        # only while they hold. A guarded command's are its guard.
        if step.conditions and step.action not in (AWAIT, DELAY, GUARDED):
            findings.append(f"{where}: only an await, a delay or a guarded "
                            f"command waits on conditions")
        if len(step.condition_labels) != len(step.conditions):
            findings.append(f"{where}: {len(step.conditions)} condition(s) but "
                            f"{len(step.condition_labels)} label(s); each needs one")
        for label in step.condition_labels:
            if not label.startswith(("project.", "std.")):
                findings.append(f"{where}: condition label {label!r} is not a "
                                f"localization key")
        if len(step_conditions(step)) > MAX_STEP_CONDS:
            findings.append(f"{where}: more than {MAX_STEP_CONDS} conditions; "
                            f"Core §6.9(b) records at most that many")
        station = next((r for r in app.records if r.station_cfg), None)
        for gated in step.conditions:
            if isinstance(gated, RequiredBy):
                policy = next((m for m in station.members if m.name == gated.policy),
                              None) if station else None
                if policy is None or policy.kind != "boolean":
                    findings.append(f"{where}: policy {gated.policy!r} is not a "
                                    f"boolean member of the StationCfg")
            condition = condition_base(gated)
            if isinstance(condition, RequiredBy):
                findings.append(f"{where}: a policy gates a condition, not a policy")
                continue
            if isinstance(condition, UnitState):
                if not condition.members:
                    findings.append(f"{where}: a Unit condition names no member")
                continue
            if isinstance(condition, ModuleState):
                findings.extend(_module_state_findings(app, where, condition))
                continue
            if condition not in app.sim_inputs:
                findings.append(
                    f"{where}: condition {condition!r} is not a declared "
                    f"simulated input; nothing would define that tag"
                )
    if chain.steps and not chain.loops:
        if not any(s.action == COMPLETE for s in chain.steps):
            findings.append(f"{chain.name}: a non-looping chain needs a COMPLETE step")

    if not chain.renditions:
        findings.append(f"{chain.name}: a chain must be rendered in at least one language")
    for rendition in chain.renditions:
        if rendition not in RENDITIONS:
            findings.append(f"{chain.name}: unknown rendition {rendition!r}")
    if len(set(chain.renditions)) != len(chain.renditions):
        findings.append(f"{chain.name}: duplicate renditions {list(chain.renditions)}")
    if chain.renditions and chain.renditions[0] != ST:
        # ST is the reference rendition every other one is compared against, so
        # it is the one that must always exist and be listed first.
        findings.append(f"{chain.name}: ST is the reference rendition and comes first")
    return findings


def _validate_io(app: Application) -> list[str]:
    """Every way an I/O declaration can be wrong before it reaches a chassis.

    An electrical tag is the one identifier that must survive verbatim from the
    I/O list to the HMI, so a duplicate or an empty one is rejected here. Two
    channels sharing a bit is the defect this catches that review does not:
    both read plausibly, and the second silently shadows the first.
    """
    findings: list[str] = []
    module_paths = {m.name for m in app.modules}
    addresses = [m.address for m in app.io_modules]
    repeated = {a for a in addresses if addresses.count(a) > 1}
    if repeated:
        findings.append(f"duplicate I/O module addresses {sorted(repeated)}")

    tags: list[str] = []
    for module in app.io_modules:
        if module.data_width <= 0:
            findings.append(f"{module.address}: data width must be positive")
        seen: dict[tuple[int, int], str] = {}
        for channel in module.channels:
            tags.append(channel.name)
            if not channel.name.strip():
                findings.append(f"{module.address}: a channel has no "
                                "electrical tag; the tag is the identity")
            if channel.direction not in (DIR_INPUT, DIR_OUTPUT):
                findings.append(f"{channel.name}: direction "
                                f"{channel.direction} is not an E_ChannelDir")
            if channel.kind not in (KIND_DIGITAL, KIND_ANALOG):
                findings.append(f"{channel.name}: kind {channel.kind} is not "
                                "an E_ChannelKind")
            if not 0 <= channel.bit < module.data_width:
                findings.append(
                    f"{channel.name}: bit {channel.bit} is outside "
                    f"{module.address}'s {module.data_width}-bit data word")
            slot = (channel.direction, channel.bit)
            if slot in seen:
                findings.append(
                    f"{channel.name} and {seen[slot]} both claim bit "
                    f"{channel.bit} on {module.address}")
            seen[slot] = channel.name
            if channel.module_path and channel.module_path not in module_paths:
                findings.append(
                    f"{channel.name}: module_path {channel.module_path!r} is "
                    "not a declared module")
    duplicates = {t for t in tags if tags.count(t) > 1}
    if duplicates:
        findings.append(f"duplicate electrical tags {sorted(duplicates)}")
    return findings


def _validate_models(app: Application) -> list[str]:
    """Every way a changeover declaration can be wrong before a commit runs.

    The commit is required to be infallible, so everything that could make it
    fail is checked here: a model naming a member the record does not have
    would copy nothing and leave the press silently on the previous model's
    value.
    """
    findings: list[str] = []
    if not app.models:
        return findings

    if app.model_capacity:
        if not app.config_sets or not len(app.models) <= app.model_capacity <= 8:
            findings.append("runtime catalog needs config_sets and capacity between seed count and 8")
        if any(not 1 <= len(m.code) <= 80 or any(not 33 <= ord(c) <= 126 for c in m.code) for m in app.models):
            findings.append("runtime model codes must be 1..80 ASCII characters")
    codes = [m.code for m in app.models]
    repeated = {c for c in codes if codes.count(c) > 1}
    if repeated:
        findings.append(f"duplicate model codes {sorted(repeated)}")

    par_cfg = next((r for r in app.records if getattr(r, "par_cfg", False)),
                   None)
    if par_cfg is None:
        findings.append("models are declared but there is no ParCfg record "
                        "for a changeover to commit into")
        return findings
    members = {m.name for m in par_cfg.members}
    if app.model_capacity:
        editable = {m.name for m in par_cfg.members if m.write_key}
        if any(set(model.values) - editable for model in app.models):
            findings.append("runtime catalog needs a typed write capability for every model value")

    for model in app.models:
        if not model.code.strip():
            findings.append("a model has no code; the code is its identity")
        if not model.values:
            findings.append(f"{model.code}: a model that changes nothing is "
                            "a label, not a changeover")
        for name, value in model.values.items():
            if name == SCHEMA_VERSION_MEMBER:
                findings.append(
                    f"{model.code}: a model may not rewrite "
                    f"{SCHEMA_VERSION_MEMBER}; the contract version is a "
                    "property of the record, not of the product")
            elif name not in members:
                findings.append(
                    f"{model.code}: {name!r} is not a member of "
                    f"{par_cfg.name}")
            if not -2147483648 <= value <= 2147483647:
                findings.append(f"{model.code}: {name} = {value} is outside "
                                "a DINT")

    if not app.default_model:
        findings.append("models are declared but none is the default; a "
                        "station boots running some set of numbers and has to "
                        "be able to say which model they belong to")
        return findings
    default = next((m for m in app.models if m.code == app.default_model), None)
    if default is None:
        findings.append(f"default model {app.default_model!r} is not declared")
        return findings
    # The initial values ARE the station's configuration until a changeover
    # runs. If they disagree with the default model, the station boots
    # publishing one model while running another's numbers - which is worse
    # than publishing nothing, because it is confidently wrong.
    initials = {m.name: m.initial for m in par_cfg.members}
    for name, value in default.values.items():
        if initials.get(name) != value:
            findings.append(
                f"{par_cfg.name}.{name} starts at {initials.get(name)} but the "
                f"default model {default.code} declares {value}; the station "
                "would boot claiming a model it is not configured as")
    return findings


def _validate_decisions(app: Application) -> list[str]:
    """A chain may not wait on a question nobody can read.

    A DECISION step whose ID is not declared publishes no prompt, and the HMI
    shows a decision card only when there IS a prompt - so the chain waits
    forever while the screen shows nothing. That is indistinguishable from a
    hang, and it is exactly how this one presented on the bench.
    """
    findings: list[str] = []
    declared = {d.identifier for d in app.decisions}
    identifiers = [d.identifier for d in app.decisions]
    repeated = {i for i in identifiers if identifiers.count(i) > 1}
    if repeated:
        findings.append(f"duplicate decision ids {sorted(repeated)}")
    for decision in app.decisions:
        if decision.identifier <= 0:
            findings.append(f"decision id {decision.identifier} must be "
                            "positive; 0 means no decision is pending")
        if not decision.prompt_key.strip():
            findings.append(f"decision {decision.identifier} has no prompt")
        if len(decision.option_keys) < 2:
            findings.append(
                f"decision {decision.identifier} offers "
                f"{len(decision.option_keys)} option(s); a question with one "
                "answer is not a decision")
    for chain in app.chains:
        for step in chain.steps:
            if step.action != DECISION:
                continue
            if step.decision_id not in declared:
                findings.append(
                    f"{chain.name}.{step.name} waits on decision "
                    f"{step.decision_id}, which is not declared; the chain "
                    "would wait on a question the operator cannot see")
    return findings


TYPE_KEY_PREFIXES = ("std.moduleType.", "project.moduleType.")


def _validate_type_keys(app: Application) -> list[str]:
    """A type key is an identifier in the §7.1 namespace: `std.moduleType.*`
    for a type the standard library ships, `project.moduleType.*` otherwise,
    and never the `.name` display suffix."""
    findings: list[str] = []
    for owner, key in [(app.name, app.type_key)] + [
            (m.name, m.type_key) for m in app.modules]:
        if not key:
            continue
        if (not key.startswith(TYPE_KEY_PREFIXES) or key.endswith(".name")
                or len(key) > 160 or " " in key):
            findings.append(
                f"{owner}: type key {key!r} is not a §7.1 type identifier")
    return findings


def validate(app: Application) -> list[str]:
    """Return every reason this declaration must not be emitted. Empty means go."""
    findings: list[str] = []
    line_records = [r for r in app.records if r.line_cfg]
    if app.line is not None:
        import fraktal_ab_line as line
        try:
            if not isinstance(app.line, line.Line):
                raise ValueError('only a declared line owner is supported')
            if any(type(v) is not str or not 1 <= len(v) <= 80 or not v.isascii()
                   or not v.isprintable() for v in (app.line.line_id, app.line.owner_id)):
                raise ValueError('line/owner identity must be printable ASCII')
            line.validate_calendar(app.line.utc_offset_min, app.line.shifts)
            def shape(record):
                return (record.name, record.schema_version, tuple(
                    (m.name, m.kind, m.dimension, m.initial, m.write_key, m.minimum,
                     m.maximum, m.requires_ready) for m in record.members))
            if len(line_records) != 1 or shape(line_records[0]) != shape(line.record(app.line)):
                raise ValueError('line calendar record must match the declaration')
            if app.access_users is None or not app.config_sets:
                raise ValueError('Line requires controller access/audit and set services')
        except (ValueError, TypeError, AttributeError) as error:
            findings.append('Line: ' + str(error))
    elif line_records:
        findings.append('line data cannot be published without the complete Line profile')
    for r in app.records:
        for m in r.members:
            if m.write_key and m.write_key.startswith('line.') != r.line_cfg:
                findings.append('line. keys are reserved for LINE_CFG')
        if sum((r.par_cfg, r.station_cfg, r.line_cfg)) > 1:
            findings.append('configuration record kinds must be distinct')

    if app.task_period_ms <= 0:
        findings.append("the task period must be positive; it is part of the contract")
    if app.watchdog_ms <= app.task_period_ms:
        findings.append("the watchdog must exceed the task period")
    if app.read_budget is not None:
        findings.extend(app.read_budget.validate())

    record_names = [r.name for r in app.records]
    duplicates = {n for n in record_names if record_names.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate record names {sorted(duplicates)}")
    for record in app.records:
        findings.extend(_validate_record(record))

    # One description feeds both publication and capture validation. A source
    # is a scalar owned by this root, never a free-form ST expression.
    import fraktal_ab_generate as gen
    import fraktal_ab_data_access as data_access
    findings.extend(data_access.validate(app))
    if app.access_users is not None:
        import fraktal_ab_access as access
        findings.extend(access.validate_users(app.access_users))
        if app.task_period_ms > 0 and access.login_timeout_ms(app) > 600000:
            findings.append('access provider login budget exceeds the HMI ten-minute limit')
    if app.config_sets:
        import fraktal_ab_sets as sets
        import fraktal_ab_reasons as reasons
        if len(gen.editable_values(app)) > sets.MAX_RECORDS:
            findings.append('parameter sets exceed the bounded record capacity')
        if not gen.editable_values(app):
            findings.append('parameter sets require registered editable values')
        for name, code in reasons.PARAMETER_SETS.items():
            if app.reasons.get(name) != code:
                findings.append(f'parameter sets require the registered {name} reason')
    if app.config_medium is not None:
        if not app.config_sets:
            findings.append('a configuration medium holds parameter-set documents; declare config_sets')
        if app.config_medium.store != CONFIG_STORE_FILE_JSON:
            findings.append('only the file medium is implemented; a database medium needs a named '
                            'server, schema and credentials owner')
        if app.config_medium.live_documents:
            # The restore replays documents through the authenticated set
            # transaction; it never gains a write path the operator lacks.
            if gen.station_cfg_record(app) is None:
                findings.append('live documents restore a StationCfg record; declare one')
            if app.access_users is None:
                findings.append('live documents are restored under a controller session; '
                                'declare the access provider')
    sources = {f"{prefix}.{m.name}" for prefix, members in gen.root_field_records(app)
               for m in members if not m.dimension and m.external_access != "None"}
    keys = [m.write_key for r in app.records for m in r.members if m.editable]
    duplicate_keys = {k for k in keys if keys.count(k) > 1}
    if duplicate_keys:
        findings.append(f"duplicate configuration write keys {sorted(duplicate_keys)}")
    for record in app.records:
        for member in record.members:
            if not member.capture_source:
                continue
            where = f"{record.name}.{member.name}"
            if not member.editable or not (record.par_cfg or record.station_cfg):
                findings.append(f"{where}: capture requires an editable configuration field")
            if member.dimension:
                findings.append(f"{where}: capture targets one scalar configuration field")
            if member.capture_source not in sources:
                findings.append(f"{where}: capture source must be a published root scalar")
            if app.manual_mode is None:
                findings.append(f"{where}: capture requires a declared setup/manual mode")

    findings.extend(_validate_io(app))
    findings.extend(_validate_models(app))
    findings.extend(_validate_decisions(app))
    findings.extend(_validate_type_keys(app))

    module_names = [m.name for m in app.modules]
    duplicates = {n for n in module_names if module_names.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate module names {sorted(duplicates)}")
    for module in app.modules:
        if not (DURATION_MIN_MS <= module.timeout_ms <= DURATION_MAX_MS):
            findings.append(
                f"{module.name}: timeout {module.timeout_ms} ms is outside the "
                f"checked range"
            )
        # Guarded: a non-positive period is already reported above, and dividing
        # by it here would raise instead of reporting the real finding.
        if app.task_period_ms > 0 and module.timeout_ms % app.task_period_ms:
            findings.append(
                f"{module.name}: timeout {module.timeout_ms} ms is not a whole "
                f"number of {app.task_period_ms} ms task periods, so the module "
                f"cannot count it exactly"
            )
        records = {r.name: {m.name for m in r.members} for r in app.records}
        for member, record, field in module.config:
            if field not in records.get(record, ()):
                findings.append(f"{module.name}: config {member} is bound to "
                                f"{record}.{field}, which is not declared")
        if not module.commands and not module.input:
            findings.append(f"{module.name}: a module with no commands and no input "
                            f"is neither commanded nor fed")

    mode_ordinals = [c.mode_ordinal for c in app.chains]
    duplicates = {n for n in mode_ordinals if mode_ordinals.count(n) > 1}
    if duplicates:
        findings.append(f"duplicate mode ordinals {sorted(duplicates)}")
    if app.manual_mode is not None and app.manual_mode in mode_ordinals:
        findings.append(f"mode {app.manual_mode} is the manual mode and has no "
                        f"sequence; a chain cannot run in it")
    for module in app.modules:
        findings.extend(_validate_permits(app, module))
    findings.extend(_permit_findings(app, "start", app.start_permits))
    if RUN_CONTINUOUS not in app.run_styles:
        findings.append("a Unit always runs CONTINUOUS; run_styles must include it")
    for what, member in (("ideal_cycle_member", app.ideal_cycle_member),
                         ("baseline_work_member", app.baseline_work_member)):
        if member:
            par_cfg = next((r for r in app.records if r.par_cfg), None)
            if par_cfg is None or member not in {m.name for m in par_cfg.members}:
                findings.append(f"{what} {member} is not a ParCfg member; it is "
                                f"per-model data (§3.8)")
    if app.chart_steps > 32:
        findings.append("chart_steps is at most 32: the cycle profile keeps one "
                        "statistics row per chart row, and TC3 holds 32 (Core §8.11.4)")
    if app.system_health is not None:
        h = app.system_health
        if h.max_task_cycle_us <= app.task_period_ms * 1000:
            findings.append("system_health.max_task_cycle_us must exceed the task "
                            "period, or every scan is an overrun")
        if h.max_task_jitter_us <= 0:
            findings.append("system_health.max_task_jitter_us must be above zero")
    if len(app.state_flags) > MAX_STATE_FLAGS:
        findings.append(f"{len(app.state_flags)} state flags; TC3 publishes at most "
                        f"{MAX_STATE_FLAGS} (Core §3.12)")
    keys = [flag.key for flag in app.state_flags]
    for key in sorted({k for k in keys if keys.count(k) > 1}):
        findings.append(f"state flag {key} is declared twice")
    for flag in app.state_flags:
        where = f"state flag {flag.key}"
        if not flag.key.startswith(("project.", "std.")):
            findings.append(f"{where}: not a localization key")
        if not flag.conditions:
            findings.append(f"{where}: derived from nothing")
        for condition in flag.conditions:
            if isinstance(condition, ModuleState):
                findings.extend(_module_state_findings(app, where, condition))
            else:
                findings.append(f"{where}: a state flag is derived from module states")
    if not 0 < app.task_period_ms <= 1000:
        findings.append("the task period must be 1..1000 ms: OEE carries at most "
                        "one second per scan into its seconds")
    for style in app.run_styles:
        if style not in RUN_STYLES:
            findings.append(f"run style {style} is not a Core E_RunStyle")
    for chain in app.chains:
        findings.extend(_validate_chain(app, chain))

    used = {s.number for c in app.chains for s in c.steps}
    if len(used) > app.chart_steps:
        findings.append(
            f"{len(used)} distinct steps exceed the declared chart size "
            f"{app.chart_steps}; the §3.13 marks would be truncated"
        )
    return findings


def require_valid(app: Application) -> None:
    findings = validate(app)
    if findings:
        raise DeclarationError(
            "declaration cannot be emitted:\n  " + "\n  ".join(findings)
        )


def scans_for(app: Application, milliseconds: int) -> int:
    """Convert a declared duration to whole task scans.

    The conversion lives here, next to the declared period, so the emitted logic
    never carries a magic scan count whose origin has been forgotten.
    """
    if milliseconds < DURATION_MIN_MS or milliseconds > DURATION_MAX_MS:
        raise DeclarationError(f"duration {milliseconds} ms is outside the checked range")
    if milliseconds % app.task_period_ms:
        raise DeclarationError(
            f"{milliseconds} ms is not a whole number of {app.task_period_ms} ms scans"
        )
    return milliseconds // app.task_period_ms


def chart_index(app: Application, ordered_steps: Sequence[int], number: int) -> int:
    """Index of a step in the §3.13 chart arrays."""
    return list(ordered_steps).index(number)

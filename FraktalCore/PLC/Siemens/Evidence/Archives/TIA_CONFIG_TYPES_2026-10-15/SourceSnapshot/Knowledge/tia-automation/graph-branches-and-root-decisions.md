# Native GRAPH branches and bounded root decisions

Measured on TIA V20 / simulated CPU1516 V3.0, 2026-10-12. Fraktal raw evidence:
FraktalCore/PLC/Siemens/Evidence/Archives/TIA_GRAPH_RECOVERY_DECISIONS_2026-10-12.

Native GRAPH branch references use zero-based ports. Divergences have one incoming
port0 and Cardinality outgoing ports; convergences have Cardinality incoming ports
and one outgoing port0. Alternative begin/end leg order must agree. A new branch
step needs a Direct predecessor; Jump reaches a step already attached to the chart.
Transitions are numbered1..999 even if the displayed initial step is N000.
LAD equality conjunction uses one power rail and comparison pre/out series wiring;
an FBD AND box or multiple rails is refused in LAD. Read back connections and
comparison wiring, ignoring serialization IDs/order. The nineteen-step press AUTO,
two alternatives and real simultaneous join compile/export without loss.

GRAPH host parameters are named HostStatus/HostCore/etc.; a direct Status alias
could look like another browse root. TIA still strips external flags on structured
and FB InOut aliases: this naming fix does not prove complete alias exclusion.
Only one concrete hardware-driver FB accesses the demo's logical I/O. Main has
input-read/root/output-write calls. No physical addresses or synthetic feedback.

Core decisions allocate one private slot per actual root, not per nested module
or registry slot. Only the root answers; only the raising owner consumes. Indefinite
questions require explicit answers; finite defaults must name an offered option.
Operator answers beat expiry in the same scan. Generated management withdraws on
reset/mode change/abort/fault/idle. Native private/readonly Web API gates pass.
Large test scratch records exceeded the16KB temporary stack limit, so their storage
is private DB state. This is a stack limit, not a150KB application-size limit.

Enable-TiaOpenness.ps1 writes <exe-name>/Entry. Whitelisting another candidate with
the same basename replaces that entry's path/hash. A preserved old executable is
not thereby still whitelisted. run_plan.py --driver selects the current approved
candidate explicitly. No driver rebuild was needed for this work.

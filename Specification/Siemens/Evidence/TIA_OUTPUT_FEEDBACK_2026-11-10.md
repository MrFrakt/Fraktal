# Applied-output feedback over the 1214C bridge (P8, 2026-11-10)

Owner decision 4A: the physical 1214C reports the outputs it applied, over the
existing I/O bridge. Until now a press DQ channel published its local demand
with quality FALSE, because nothing told the bench what reached the terminals'
output image.

## What changed

| Part | Change |
|---|---|
| Wire (`Framework/IoBridge/bridge.scl.in`, `fraktal_tia_io_bridge.py`) | `FRIO` version 2. The physical endpoint sends its 14 inputs in bits 0–13 and the 8 outputs it applied in bits 16–23; the controller still sends 8 demands. Version, bit mask and the PC qualification peer come from one set of Python constants substituted into the PLC template. A version-1 peer is refused, so a mismatched pair never links. |
| 1214C driver | Reads back each `%Q` it wrote, after `OUTPUT_MAPPING_CONFIRMED`, the link, peer enable, Control On, E-stop, pressure, opposite-coil and ram/door/two-hand interlocks, and sends it on the next scan. The inhibited Control On coils carry no bit. |
| Topology (`fraktal_tia_topology.py`) | Optional station `feedback_healthy` bit and per-channel `feedback` member. While the bit is TRUE the DQ value is the applied state, quality TRUE; otherwise the demand, quality FALSE. Only a driven OUTPUT may declare feedback; every other use is refused at generation. |
| Press (`press.json`, `hardware_driver.scl.in`) | Declares `OutputFeedbackHealthy`; the image members (`Applied<tag>`, one per DQ tag, so the two lamp tags sharing one demand report separately) are generated from `io.json`, private. The simulated press never writes them, so its DQ view is unchanged. |
| Bench client | Writes the applied bits per tag and `OutputFeedbackHealthy := link healthy`. |

The applied state is the 1214C's output image, not an electrical measurement:
a broken wire, blown fuse or failed coil is not seen. Part IV §10.5 records
the rule; the bridge README the wire layout.

## Measured

| Run (`%LOCALAPPDATA%\Fraktal\TiaSpikes\P8_Feedback_20261110_02`) | Result |
|---|---|
| `physical`: generated 1214C sources into a fresh copy of the saved `Press_IoBridge_1214C_20261015` project (the saved project was not opened) | program and hardware compile 0 errors / 0 warnings; native read-back 9 sources, 4 interfaces, retained boot counter |
| `client`: the press with the bridge client, fresh reserved project | both compile stages 0/0; native read-back 618 sources, 160 interfaces, 32 private I/O members; GRAPH 19/4/6/4 steps and ladder parity |
| Host gates | 299 tool tests (new: v2 frame admission, applied echo after the output writes, per-tag client storage, topology feedback publish/refusals, press declaration and private members); `tia_lint` 0; consistency and contracts clean; committed press replay 286 and physical bridge replay 5 regenerated |

Nothing was downloaded. Deploying needs both endpoints together: the physical
1214C at 192.168.0.10 and the FraktalBench CPU. The saved bench engineering
project `Press_IoBridge_Press1500_20261015` is now an empty directory, so the
bench side must first be rebuilt into the owner's FraktalBench project. Both
downloads need the owner's explicit authorization at the time; physical output
acceptance remains commissioning work.

## Host state during this run

The saved `Fraktal` simulator instance read RUN at the forcing image's web
preparation (about 21:31) and was no longer registered at the next guard check;
these runs did not stop it. A PLCSIM status query starts the runtime manager when
it is not running, so the manager now running in Softbus mode was most likely
started (22:42) by that diagnostic check. The status guard now records an
unregistered instance as `Absent`, a state compared before and after like any
other; acting on an instance still requires it to exist. Isolated test CPUs need
TCP/IP mode, so no live bench ran; switching the mode or restoring `Fraktal` is
left to the owner.

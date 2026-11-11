# P8 closure: module health, decisions and what the owner holds (2026-11-11)

P8 (I/O topology, PROFINET health and forcing) is implemented and measured on
isolated test CPUs. What remains needs the owner's hardware and authorization.

## Module-level PROFINET health

A topology node may name a module of a PROFINET device. `ModuleStates`
(existing, disabled, problem) is read once per device per 250 ms sample, at the
slot `LOG2GEO` derives from the module's hardware identifier; the module is up
only while its device is up, and its own problem is its `FAULT`.

| Run (`%LOCALAPPDATA%\Fraktal\TiaSpikes\…`) | Result |
|---|---|
| `P8_PnModule_20261111_01` (driver trial) | ET 200SP DQ `6ES7 132-6BF01-0BA0/V0.0` plugs at slot 1 (`IM_1~PnDQ`, hardware ID 265); the server module follows it |
| `P8_PnModule_20261111_02` (fresh compile and bench) | compile 0/0, read-back 262/71/17, `FrkProfinetTest` **8/8**, image `e1ac01cdb708d906cdc0686b717723fa4afbb223b9f15e86066e7433ce7094b5`; `Fraktal` RUN before and after |

The eight assertions: device and module operational; `D_ACT_DP` disables the
device; node, input and module offline at the next sample; re-enabled; node and
module operational again. Topology host tests cover the module binding, its
validation and the once-per-device read. The full HMI suite passes after the
reason-22 catalog change (871 tests, 12 opt-in skips; its catalog-size pin is 97).

## Decisions

- **OB82/OB83/OB86 are not used.** They would only shorten detection below the
  250 ms sample; generating them would claim a station's fault OBs, which
  belong to its project; an S7-1500 stays in RUN without them.
- **`GET_DIAG` detail is not republished.** The topology carries state; the
  CPU's diagnostic buffer and module diagnostics stay the source of the cause.
- **Force jobs** are annunciated as the CPU's maintenance demand (Core reason
  22, see [the annunciation record](TIA_MAINTENANCE_ANNUNCIATION_2026-11-11.md)).

## Held by the owner

- **Bridge downloads (decision 4A): done later the same day** with the owner's
  authorization, see [the deployment record](TIA_BRIDGE_V2_DEPLOYMENT_2026-11-11.md):
  both ends link on wire version 2 and the eight ordinary DQ channels are
  confirmed by the 1214C's applied-output report.
- **Physical acceptance.** Output wiring confirmation (`OUTPUT_MAPPING_CONFIRMED`,
  `EVALUATED_TWO_HAND_WIRED`) and witnessed forcing on the press are the
  commissioning engineer's; an agent never sets those gates.

## Handed to TwinCAT

Reason 22 changed TwinCAT Core sources (one `E_Reason` member and generated
reason catalogs). The patch release, build, install and TcUnit gates run on the
TwinCAT host; see the
[TwinCAT handover prompt](../../Reports/TC3_HANDOVER_PROMPT_2026-11-11.md).

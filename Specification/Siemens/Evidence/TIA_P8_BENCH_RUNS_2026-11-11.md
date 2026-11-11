# P8 bench runs: PROFINET health and live press forcing (2026-11-11)

Isolated test CPUs need PLCSIM in TCP/IP mode. At the owner's instruction the
saved `Fraktal` instance was restored with `tools/Resume-TiaSimOwner.ps1`
(registered from its persisted storage, powered on, CPU1516/TCP/IP,
169.254.212.49 and 192.168.1.1, no physical mappings); it read RUN before and
after every run below, and stayed the only preserved instance.

## PROFINET node health

`TiaGate_P8Pn_20261110_02`, the suite the native gate had compiled, downloaded
to `FrkProfinetTest` (169.254.212.58): **5/5 assertions, 0 failures**, image hash
`f80ba6c3846162aba202d592203c7c95b6552fd050ea3497250105e1fbc2c3b0`. The device
PLCSIM presents is operational through `DeviceStates`; `D_ACT_DP` disables it,
the next sample takes the node and its input offline, re-enabling returns it.
A host-injected station failure (OB86) is not covered by this suite.

## Live press forcing over the Web API

`Tests/PressTests_TIA/run_forcing.py` on the engineering press image
(`P8_PressForceLive_20261110_01`, compile 0/0, read-back 624/165/72, web user from
the DPAPI wrapper) on `FrkPressFeaturesTest` (169.254.212.56):

| Attempt | Result |
|---|---|
| 1 | probe defect, not a product finding: after 6 passing checks it read `ForceBool`, which the binding keeps private in every image (as `ForcesEnabled`); the Web API refused the read. The HMI reads neither. The probe now uses only the public surface. |
| 2 | **PASS, 38 checks, 0 failures** |

Attempt 2 proves through the real root mailbox: both build gates registered;
exactly the six declared valves forceable, only outputs, all owned by the press,
the control-power coils never, nothing forced at boot; a force is published and
audited with its value; an input, a control-power coil and an unknown path are
refused and each refusal audited; a non-canonical value is accepted and audited
verbatim (its FALSE decoding is the private set-point the native suite proves);
clear; leaving idle MANUAL withdraws every force with one root audit record and
`forceBlocked` refuses a new one; after a HOME cycle nothing resumes, and idle
MANUAL accepts and clears a new force.

The press demo's policy requires access level 0 for MANUAL, so its forces were
accepted without a login; refusal below the required level is proven natively.
A production station sets that level.

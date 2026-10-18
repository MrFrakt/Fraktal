# Reference-1500 operations checks

`make_fixture.py` generates **93 native assertions** against the shared runtime:
OEE/state priority, monotonic wrap and saturation, V3 calendar validation and
boundaries, deferred edits/target latching, resets/degradation, health/gate edges,
alarm shelving/expiry, signal tower/lamp test, sequence pacing and host rings.
The assertions execute on the PLC; the Python runner reports their actual count
and image fingerprint as JUnit. A missing/incomplete result fails the gate.

`make_frame_fixture.py` composes two real roots with shared line config, LOAD_DB,
health, nameplates, build gates, signal tower and a registered teach-capture
field. `probe_frames.py` checks line/calendar/production behavior;
`probe_features.py` checks permissions, runtime health, annunciation, lamp test
and typed capture through the real mailbox. Finish all three synthetic Unit
cycles before expecting configuration readiness: `NestedFinish` and
`InnerFinish` are independent stimuli in the inherited routing fixture.

The fixed disposable target is `bench.json`: unmapped CPU1516
`FrkOperationsTest`, `169.254.212.55` / `172.31.254.55`. Results are harvested
from the **small separate result DB**. Asking the simulator SDK to enumerate
the entire large test FB caused excessive simulator allocation; never use it
as a result container.

From the repository root:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_gate.py --output "$env:LOCALAPPDATA\Fraktal\TiaSpikes\A_NEW_GATE_NAME" --native --bench
```

The gate creates a fresh engineering project, compiles it, compares canonical
source/interfaces, downloads only to its reserved test CPU, verifies the exact
image fingerprint and releases the test instance in `finally`. It preserves the
saved `Fraktal` instance. `run_features.py` runs an already compiled/read-back
frame revision under the same ownership guard; invoke it through the existing
DPAPI credential wrapper. Credential initializers, engineering projects, load
images and private exports stay outside Git.

Run one extra simulator at a time and wait for host exit before reusing a name.
These checks qualify the simulated reference profile. Physical timing,
synchronized clock quality, abrupt loss/endurance and the complete R3/R5 matrix
remain separate gates.

# Native v38 tag-based alarm compiler continuation — 2026-10-18

The XML-import blocker recorded in
[the preceding alarm feasibility run](AB_NATIVE_ALARMS_COMPILE_2026-10-18.md)
is resolved for the exact **1756-L81E / Studio 38.00 / SDK 2.1.974** offline
target. Generated tag-based alarms compile for both EchoController and
PhysicalController and retain their condition, associated references, message,
class, initial values and ST through native export. PhysicalController is a
compiler selection; this is not a physical-controller test.

No controller operation, download, tag write, mode change or clock adjustment
was performed. The previously approved native timing observer remains loaded
on local Echo `601FC87B`. Core remains the alarm lifecycle owner; the production
generator and published ABI are unchanged.

## Import blocker and native reference

Studio's hidden offline importer exposes the detailed diagnostic omitted by
the SDK exception: `Failed to set the 'Expression' property (Invalid enumeration
value.)`. Removing that attribute reveals warnings for the obsolete spellings
and an incompatible default condition expression. The disposable projects and
diagnostics are retained; the owned Studio process was closed cleanly.

The guarded empty L81E/v38 seed was exported to L5K. A script added a BOOL
condition using the numeric expression from
[Rockwell's import/export reference, chapter 7](https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1756-rm014_-en-p.pdf).
The SDK accepted this L5K and exported the actual native XML. Its spelling,
rather than an inferred capability exclusion, resolves the blocker:

| Manual/example trial | Native v38 export used by the probe |
|---|---|
| `Expression="Input = 1"` | `Expression="= 1"` |
| `DelayOn` / `DelayOff` | `OnDelay` / `OffDelay` |
| `GroupOperExcluded` / `GroupRollupExcluded` | `AlarmSetOperIncluded` / `AlarmSetRollupIncluded` |
| `EvaluationGroup` | `EvaluationPeriod="500 millisecond"` |

The accepted generated case uses a DINT bit input (`Input=".0"`), severity 700,
no acknowledgement requirement, no native latch, zero delays, a CAM message,
class and two associated tags. All its controller tags are Read Only. The
tag-based cases declare no ALARM_DIGITAL object; the separate ALMD cases keep
their measured native Read/Write requirement. Neither is an approved external
command surface.

## Read-back and access scope

The positive ST case writes documented program controls and reads `InAlarm`,
`Acked`, `Suppressed`, `Shelved` and `Disabled`. The native alarm is asynchronous;
this offline result establishes valid instructions and configuration, not
runtime reset, shelving, evaluation latency or delivery behavior. Rockwell
documents the separate
[programmatic attribute surface](https://www.rockwellautomation.com/en-il/docs/studio-5000-logix-designer/38-03/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms/access-tag-based-alarms-in-logic/alarm-attributes-that-support-programmatic-access.html).

The status-write negative is rejected on both targets with
`RxCMP_E_AUDIT_BAD_CONFIGURED_ALARM_STATUS_FLAG_OPERATION`. However, both
compilers **accept** an assignment to `OperShelve`, contrary to the help's
programmatic Read-only designation. The initial expected-rejection gate fails
and is preserved. The final generator names this an observational discriminator,
not a supported write surface. Its successful compilation does not prove
runtime effect, external access or an authorization boundary. Do not use the
compiler as a substitute for Core §14 or native operator isolation.

The first native compile run succeeds, but its strict message comparison
correctly refuses acceptance because ElementTree merged Studio's XML wrapping
outside CDATA into the message. The corrected comparison removes only blank
text nodes outside native AlarmConfig leaf CDATA. It preserves every byte
inside CDATA, including leading/trailing spaces. The initial failed comparison
is retained; the repeated native gate is clean.

Eight mutations of an actual native export are refused despite identical tag
inventory and executable logic: expression, on-delay, off-delay, operator-set
inclusion, associated tag, severity, message and message whitespace. A unit
regression separately proves compact and wrapped CDATA compare equally while
changed payload spaces do not.

## Reproduction

From `FraktalCore/PLC/Allen-Bradley`:

```powershell
python tools/fraktal_ab_native_alarm_probe.py C:/work/echo38_5580_seed.L5X C:/work/alarms_new
python tools/fraktal_ab_native_alarm_gate.py C:/work/alarms_new/generation.json C:/work/alarms_compiled_new
```

The emitter validates the empty seed and refuses existing output directories;
the shared compiler gate checks input hashes, clean import summaries, actual
compiler rejection for negative controls and full source/export read-back.
Optional `--case` / `--target` select a bounded subset. The two original ALMD
source hashes remain identical to the preceding evidence.

Core §8.3 reset and command-latch release, the first-out and rationalization,
the fast-event ring, shelf policy and Core §14 authorization remain authoritative.
Native operator command isolation and runtime comparison are still required
before exposing a plant alarm projection. This result does not close the
overall AB port or N2 runtime acceptance.

## Validation

- **1,818 AB tests pass**, followed by **29 focused tests** after the operator
  case was named an observational discriminator. The full run includes the
  CDATA comparison and selectable-gate changes; its earlier case name is
  retained in that run's source chronology.
- **74 root tests pass**; AB spec, frozen-contract and strict consistency gates
  are clean.
- Twelve selected compiler outcomes/read-backs match: four positive builds,
  six deliberate compiler rejections, and two accepted operator-write
  discriminator builds. One additional native canonical reimport/build/export
  preserves all alarm metadata and code.
- Six generated sources reproduce exactly from the unchanged seed. Both
  earlier ALMD source hashes are unchanged. Eight actual-export metadata
  mutations are refused.
- Final exact-target read: Echo `601FC87B`, loopback/slot 0, Run and not faulted.
  Controller write count is zero. No HMI or physical acceptance is claimed.

The selected-case closure record identifies which rows of each native run
provide the final evidence; the earlier failed aggregate runs remain failures.
Validation and immutable payload hashes are recorded in the
[payload manifest](AB_TAG_ALARMS_COMPILE_2026-10-18/manifest.json).

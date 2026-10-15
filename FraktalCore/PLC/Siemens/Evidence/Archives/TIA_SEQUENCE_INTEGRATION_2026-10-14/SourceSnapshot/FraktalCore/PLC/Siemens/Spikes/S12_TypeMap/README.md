# S12 type map and S4 source round-trip

This fixture measures the complete Core DUT layout on a simulated S7-1500.
It retains Core capacities; the 1214C's 150 KB budget does not apply.
It is a type/transport experiment, not the Core runtime or a released contract.

The isolated station is `FrkS12`, CPU1516-3 V3.0, PLCSIM Advanced7.0,
at `169.254.212.49/16`. The upgrade's virtual adapter is169.254.105.123/16
(the earlier Advanced5 adapter was169.254.212.48/16).
`simulator.ps1` removes all physical adapter mappings and restores the previous
manager network mode when its owned instance exits. It does not change a host
adapter address. V3.0 is below the planned physical reference baseline of V3.1+.

`make_fixture.py` reads all88 Core structures,42 explicit enums and the
authoritative `PL_Fraktal` capacities. Enums map to DInt; String widths through254
use String, wider widths use WString. DT uses LDT by default on the1500. PVOID
uses a UDInt witness/index slot; it does not implement a pointer resolver.
Core `OPC.UA.DA=0` fields become private SIMATIC members. The parser accepts
multiple fields per line and rejects unparsed fields, duplicates and implicit
or out-of-range enum ordinals. Source hashes include the capacity declaration.
S3 and S12 share the strict parser in `tools/fraktal_tia_types.py`; the Phase2
generator can consume it without maintaining another parser.

One FC fills each structure and every array element, one type per scan. The
manifest selects first/last leaves and distinguishes the SDK/public witnesses.
The scalar probe covers integer limits, negative TIME, full254/255/480-character
strings, Unicode, a negative-lower-bound array and three timestamps. A generated
block-local constant FC checks all295 enum members and publishes EnumWitness.

The first parser omitted13 fields in ModelField, Oee and two Shift records.
Its1094 reads and268-source comparisons describe that earlier fixture only.
The corrected fixture has1405 SDK witnesses,1309 public type witnesses and269
sources, including DTL components for all timestamp leaves. Earlier attempts
remain in the dated evidence.

The Advanced7 continuation retains that layout with37 scalar LDT timestamp
witnesses, replacing296 DTL-component witnesses. It passes1146 SDK type
witnesses and1081 public native witnesses (1050 type leaves plus31 probe
leaves). Native LDT is a signed Unix-nanosecond decimal string; the gateway
converts it to a DateTime ISO UTC value with nine fractional digits. Zero keeps
Core's unset sentinel. The generic HMI date parser retains microsecond precision.
WString255/480, Unicode, punctuation and exact64-bit values pass natively.
The HMI transport/date-parser probe passes36 checks with99 Good leaves; this
does not prove a rendered Unit forest or mailbox commands.

## Run and verify

Create `station.plan` only once and preserve its project/certificates/DPAPI
password/Web API pin in `%LOCALAPPDATA%\Fraktal\TiaStations`. A classic web
password must be shorter than33 characters. Never log passwords/tokens/cookies.
Every generated directory, raw log and verifier output must be new.

Run `make_fixture.py <new-directory>`, then `run_plan.py build.plan <new-log>`
with substitutions `work`, `gen` and `export`. Imports are saved before compile
so a failed disposable build can receive a focused repair. The approved
enumeration driver is used without rebuilding it.

Use `--timestamp DTL` only to reproduce the frozen DTL control. The tested
LDT candidate project is
`%LOCALAPPDATA%\Fraktal\TiaStations\S12_Ldt_20261010\FrkS12\FrkS12.ap20`.
The original `TiaStations\FrkS12\FrkS12.ap20` remains the preserved DTL project.
They share the retained certificates and DPAPI secret. Select the candidate
work directory explicitly; `with_secret.ps1 -Action plan -Work <candidate-work>`
supports it. Do not download the older project by relying on the default work
directory. Generated inputs are `TiaSpikes\S12_Types_20261010_v11_ldt`.

The later Unit control run now owns the saved FrkS12 simulator image,
from `TiaStations\Unit_Runtime_20261011\FrkS12\FrkS12.ap20`. The S12 and R4
projects remain preserved. Select and download the intended fixture explicitly
before using its reader; the current lifecycle image does not contain S12Probe.
Its test observations are in GDB_UnitTest; see Tests/Unit/README.md.

Start `simulator.ps1 -Action host` in an owned hidden process; inspect status
before a download. Name PLC_1,169.254.212.49 and the virtual Ethernet interface
explicitly in the approved download command. Each newly registered instance
needs its own logged engineering TLS trust, never a trust flag in a plan.
Offline build/round-trip work does not download to the running CPU.
For a configured1516, the runner automatically checks the simulation identity,
TCP/IP address, zero physical mappings and explicit download interface/target.

`read_sdk.py <manifest> <new.jsonl>` checks typed layout witnesses. Harvest
S12Probe with the simulator helper, then run `verify_scalars.py <raw> <verdict>
--enum-count 295` (count derived from the manifest). SDK string tags need
ReadString/ReadWString; their PrimitiveDataType is Unspecific.

`with_secret.ps1` supplies a DPAPI secret through an environment variable and
clears it in finally. `probe.py` uses pinned HTTPS for witnesses, permissions
and read-only access diagnostics. SDK evidence does not satisfy the Web API/HMI
gate. Do not change PLC state during the one-hour clock observation.

## S4 canonical comparison

Run `verify_roundtrip.py <generated> <first-export> --second <second-export>
--out <new-verdict.json>`. It checks compiled member order/types/bounds and
publication attributes, authored versus GenerateSource, and a separately
imported/compiled/re-exported source set. Reimport in manifest dependency order.
`roundtrip.plan` takes `work`, `sources` and `export`.

The ignore list is whitespace/comments, identifier case, quoted simple
identifiers, the exact native DTL annotation, automatic OB1 title and exact
native Initial_Call/Remanence input pair. String payloads, bounds, access
attributes, statements and custom inputs remain significant. GRAPH comparison
is the separate S11 leg.

## Clock observation

OB1 calls RUNTIME once per scan, accumulates elapsed seconds after the first
call and records rejected/max deltas. `clock_sdk.py <new.jsonl>` observes a
complete hour without reset/download/settings changes. Its declared prototype
tolerance is max(1 second,0.1% of host elapsed), including both endpoint read
spans. Ready, increasing scans/clock, zero rejected deltas and no observer gap
of60 seconds are required.

The V5 manual pp87-88 says Windows suspension stops simulator clocks and
virtual time can be scaled. Record failures and settings; do not tune a scale
factor to make a host comparison pass. Hardware drift, UTC synchronization
quality remain separate gates. The later Advanced7 run proves HMI timestamp
encoding without repeating or superseding the earlier drift measurements.

## Native Web API isolation controls

`Minimal/` and `minimal.plan` replace the program only in a copied station for
an isolation comparison. Never point that plan at the preserved full station.
`web_communication.plan` takes communication_mode plus the guarded download
macro. `web_permission_control.plan` takes permissions and restores mode1;
use `with_secret.ps1 -Action plan -Permissions 24 -Download` for the baseline.
`with_secret.ps1 -Action token-controls` compares absent/invalid/valid tokens
without recording their contents. Extra rights are transient simulator tests.

The Advanced5 controls found the same symbolic denial with the minimal program,
while a protected operating-mode read succeeds with a diagnostic right. Mode0
also fails. Advanced5's documented project range ends at V18; that V20 run
required a compatible-runtime comparison. The complete station/image, mode1 and
process-data-only rights were restored and witnesses passed. See
[the isolation record](../../../../../Specification/Siemens/Evidence/TIA_S12_WEBAPI_RECOVERY_2026-10-10.md).

The owner's subsequent Advanced7 installation resolves symbolic Read/Browse
on the preserved full DTL image before any program/configuration change.
The LDT candidate then passes the native transport and canonical source gates.
The helper deliberately keeps API5's now-updated compatibility DLL; PowerOn
returns OK. Runtime versions, permissions, pin and shutdown are captured in
[the upgrade record](../../../../../Specification/Siemens/Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md).


The subsequent generator0.4 nested Unit/manual bench passes120 native checks
and104-block/40-interface canonical reimport. Current saved FrkS12 image:
TiaStations/Manifest_Runtime_20261011/FrkS12/FrkS12.ap20. Previous Unit/lifecycle/type
projects remain preserved. Full native HMI rendering and Core services remain open.

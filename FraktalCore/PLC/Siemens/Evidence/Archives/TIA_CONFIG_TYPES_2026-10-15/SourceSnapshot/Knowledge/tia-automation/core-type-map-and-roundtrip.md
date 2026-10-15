# Core type map and source round-trip on S7-1500

Working evidence: Fraktal `Specification/Siemens/Evidence/TIA_S12_TYPES_ROUNDTRIP_2026-10-10/`.
Tool authority: `C:\Projects\Fraktal\FraktalCore\PLC\Siemens\Spikes\S12_TypeMap`.
Scope: TIA V20, CPU1516-3 V3.0, Advanced5 controls followed by Advanced7. This is below the planned
physical V3.1+ baseline. The 1214C/150KB profile does not constrain this work.

- **[measured]** Complete compiled census:88 Core structures,610 direct fields,
  42 enums with295 explicit ordinals. Preserve Core capacities and declaration
  order. Map enum storage to DInt; block-local VAR CONSTANT declarations compile.
  The constant runtime count and corrected witness harvest have separate logs.
- **[measured]** STRING254, WSTRING255 and WSTRING480 compile and preserve full
  PLC-written values through Runtime API. Unicode Omega/CJK and apostrophe/quote
  survive. The later Advanced7 continuation below also proves native Web API/HMI values.
- **[measured]** SDK reads preserve Int/UInt/DInt/UDInt boundaries, LInt minimum/
  maximum, ULInt maximum and9007199254740993. TIME returns signed millisecond
  values; the negative probe is-2345. JSON representations of the Web API remain
  measured separately in the Advanced7 continuation below.
- **[measured]** DTL is a structure with YEAR/MONTH/DAY/WEEKDAY/HOUR/MINUTE/SECOND/
  NANOSECOND. LDT's2024 leap-day probe reads1709251198123456789 through the SDK.
  DATE_AND_TIME reads as a UInt64 containing eight BCD bytes; little-endian byte
  extraction gives2402292359580005. Reject invalid BCD/date/weekday values.
  These are scoped Runtime API encodings, not interchangeable HMI wire types.
- **[measured]** Eighteen Core members carry OPC.UA.DA=0. The type generator
  translates that to ExternalAccessible/ExternalVisible/ExternalWritable False;
  the complete TIA XML re-export preserves it. The final harvest manifest
  distinguishes1405 SDK witnesses and1309 public type witnesses.
- **[candidate]** The initial layout used DTL; the1500 reference now uses LDT
  after the native comparison below. PVOID uses a UDInt index
  witness only; this is not a configuration-writer implementation. Timestamp
  production resolver remains open. The1200 timestamp projection is separate.

## Parser discipline

**[measured]** Core DUTs can declare multiple fields on one line. An anchored
line regex silently omitted13 fields: ModelField.Value plus four validity flags
in Oee, ShiftRecord and ShiftRecordV3. The original1094 reads/268-source
round-trip matched that incomplete fixture, not the complete Core shape.
The strict parser now consumes every declaration, preserves recognized
publication attributes and rejects residual syntax, duplicate names and implicit
or out-of-DInt enum ordinals. None of those four types were in the frozen S3
allocation groups, so their recorded KB measurements remain scoped correctly.

## Round-trip discipline

**[measured]** GenerateSource normalizes formatting and quoted simple identifiers,
adds the native DTL annotation and OB1 title, and omits the native OB input pair
Initial_Call/Remanence. Keep a narrow canonical ignore list. String payloads,
bounds, access qualifiers, statements and application inputs must remain
significant. Reimport UDTs in model dependency order, then DBs/FCs/OBs. Preserve
raw generated/exported bytes and import/compile logs. Never run two Openness
sessions against the same station project; TIA refuses the second Open.

## Simulator transport and time

- **[help]** V5 manual p337: the web server requires the PLCSIM virtual Ethernet
  TCP/IP interface; Softbus does not provide it.
- **[measured]** FrkS12 uses the existing virtual adapter's APIPA subnet, with
  all three physical adapter mappings zero. No host adapter IP was changed.
- **[measured]** Classic password length must be less than33 characters.
  ReadTag/ModifyTag alone yield no Api.GetPermissions rights. ReadTagStatus/
  ModifyTagStatus yield read_value/write_value. The earlier Advanced5 server denied
  protected reads/browse with code2, including combined mask30, spelling/header/
  connection/mode variants. DB/member exposure is enabled. No cause is established.
  Optional-cookie login returns a token only on this instance. Never log either.
- **[help]** V5 manual pp87-88: Windows suspension stops simulator clocks; user
  program timing uses virtual time and can be scaled. Host-versus-PLC observation
  is not hardware oscillator accuracy. Record ScaleFactor, continuity and rejected
  deltas; do not compensate a failed test by tuning the scale factor.

Primary manuals:
[Web server](https://support.industry.siemens.com/cs/attachments/109977246/s71500_webserver_function_manual_en-US_en-US.pdf),
local `manuals/plcsim-advanced-v5/PLCSIM_Advanced_V5_Function_Manual_enUS.pdf`.

## Final measured S12 result

**[measured]** Corrected1405/1405 typed SDK witnesses and43/43 scalar checks
passed after download and again after restoring process-data-only mask24.
LEN returned254/255/480, WString CONCAT256 characters and MID the480-character
value's final three characters. All295 enum constants returned the expected
count. Final269-source import/compile/export comparison passes.

**[measured]** Adding only DoDiagnosis to mask30 produced mask31 and
read_diagnostics/read_value/write_value, but symbolic Read/Browse still returned2.
The extra right was removed; final mask24 reports only read_value/write_value.
ReadSystemTime succeeds when its no-parameter request omits params; params{}
was rejected as Invalid Params. No cause for symbolic denial is established.

**[measured]** The complete host hour collected117 samples and3390384 scans,
Ready TRUE/rejected deltas0. PLC3479.983755s versus host3600.001412-3603.015396s
fails the declared3.601508s tolerance. The independent ten-minute simulator
system-clock comparison has121 samples and max8.664ms difference, within500ms.
This is simulator-time consistency, not physical drift or synchronized UTC.

## Native Web API isolation continuation, 2026-10-10

**[measured]** Cold restart and CommunicationMode1->0 retain symbolic code2.
Valid token controls distinguish absent/invalid rights[] from authenticated
read_value/write_value. Mask95 permits ReadOperatingMode=run with the same token,
but PlcProgram.Read remains2. A copied station with a three-field optimized DB
also returns2 for Read/Browse; its SDK values and DB web-access flag are valid.
Restored complete program:1405/1405 type and43/43 scalar witnesses; mode1 and
mask24, original certificate pin. Host6652 unregistered07:40:03UTC, manager
mode restored. Broad mask524287 was rejected by TIA before download; no API
conclusion follows from that attempt.

**[help]** V5 function manual11/2022,A5E37039512-AE,p20 documents TIA projects
V14-V18 and simulated firmwareV3.0. Actual manager/instance product5.0.0.0,
file50.42.10.00; a V7 client DLL bundled in PLCSIM V20 does not replace that
manager. This V20 prototype needs a documented compatible runtime comparison.
The version mismatch is not a proven explanation for the denial. Keep the
native Web API/HMI gate open at that Advanced5 scope; see the completed comparison below.
Authoritative procedure/logs:
`C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_S12_WEBAPI_RECOVERY_2026-10-10.md`.

**[measured]** Independent Phase2 tooling now has a strict type/forest model in
`fraktal_tia_declaration.py`: the two-root fixture expands3 reusable types into8
planned registration rows with no superroot. Status widths and tier ordinals are
derived from Core DUTs.18 focused tests cover containment, cycles, naming, widths
and registry capacity; full Siemens suite83 tests passes. This emits an engineering
inventory, not a PLC frame or runtime registry. All four generator-dependent
source lint rules remain pending. See `TIA_R4_DECLARATION_MODEL_2026-10-10.md`.

## Advanced7 native comparison and reference timestamp selection (2026-10-10)

- **[measured]** Owner-installed manager7.0.0.0/file70.0.323.0 works through
  API5's updated compatibility DLL50.43.04.00. PowerOn returns OK. Virtual
  adapter11 is169.254.105.123/16; CPU remains169.254.212.49/16, TCPIP and all
  physical mappings0. No physical CPU or host adapter address changed.
- **[measured]** Saved full DTL image now supports symbolic Read/Browse before
  any new download/configuration change. Api.Version5; original certificate
  pin unchanged, rights mask24 read_value/write_value only.1340/1340 public
  witnesses pass. Manager, compatibility DLL and adapter changed together;
  this does not isolate one root cause for the former code2 denial.
- **[measured]** Native whole DTL read returns204; its eight members browse/read.
  LDT simple read is the decimal string1709251198123456789; raw bytes are
  17 b8 7a e8 a0 0f 39 15 (big-endian). DATE_AND_TIME raw bytes are
  24 02 29 23 59 58 00 05 (BCD), differing from SDK UInt64 byte extraction.
  Keep wire codecs transport/type-specific.
- **[measured]** The1500 reference now maps Core DT to scalar LDT, retaining
  all88 structures/610 fields/Core widths and capacities.37 LDT witnesses
  replace296 DTL components;1146/1146 SDK,1081/1081 native type/probe witnesses,
  43/43 SDK scalar checks and269-source canonical reimport/compile/export pass.
  Software/incremental hardware compile and download complete0/0.
- **[measured]** The real WebApiSessionClient emits LDT as DateTime ISO UTC with
  nine fractional digits, using signed64-bit integer arithmetic; zero is unset.
  Generic HMI parsing retains microseconds.36 live checks over99 Good leaves
  pass, including WString255/480, Unicode/punctuation and exact64-bit values.
  Tests cover negative nanoseconds, signed limits and invalid encodings clearing
  older Good values. TIME is Int32 milliseconds. Full Unit rendering/mailbox
  commands and UTC/clock accuracy are separate gates; no new drift test was run.
- **[measured]** Saved simulator image belongs to the copied LDT station
  `%LOCALAPPDATA%\Fraktal\TiaStations\S12_Ldt_20261010\FrkS12\FrkS12.ap20`.
  The original FrkS12 project remains DTL. Use explicit work paths; the secret
  and certificates are retained. Driver approved hash remains unchanged.

Evidence: `C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_S12_WEBAPI_ADVANCED7_2026-10-10.md`.
The subsequent frame/registry generator is now measured in
[generated-frames-and-registry.md](generated-frames-and-registry.md). Its R4
copied station now owns the saved FrkS12 simulator image; the S12 projects
remain preserved. Next: shared Core lifecycle, Unit facets, then full runtime,
modules and press without power control. R4/source rules remain partial.

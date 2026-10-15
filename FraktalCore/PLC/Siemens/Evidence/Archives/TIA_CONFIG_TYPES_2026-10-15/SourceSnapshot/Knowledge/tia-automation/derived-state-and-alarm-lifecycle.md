# Derived state and alarm/event lifecycle - TIA V20 / Advanced7

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_STATE_ALARMS_2026-10-11.md.
Scope: generator0.7, simulated1516 V3.0, native Web API and generic HMI. **[measured]**

- Unconditional FRK_State calls in the authored derived cyclic region declare
  bounded literal slots/keys. The generator supplies context/sweep and allocates
  StateFlags/count only on consuming types. Core12 slots/key width120, change-only
  Since, missing producer FALSE/Stale, and restoration pass native checks.
- Core-sized16 active/64 closed ST_AlarmEvent records implement AUTO_RESET close
  at gone and MANUAL_RESET WAIT_RESET. Reset closes ACTIVE or WAIT_RESET, withdraws
  issued commands, and a live condition can raise again. Duration is monotonic TIME;
  UTC synchronization remains FALSE. Overflow/overwrite reports Truncated.
- Capture must follow FRK_End so it sees the current final diagnostic. The nearest
  Unit owns the child record; an ancestor sees nested blocking through the registry.
 23 native checks prove no duplicate root/middle event, denied ancestor manual release,
  exact first-out path/text and one ancestor reset restoring the child command.
- Access/Part/unsupported-mode occurrences use AUTO_RESET event records. History
  stays diagnostic fault history. Optional event_sink binds F_... with Ev:
  ST_AlarmEvent input; private SinkEnabled is a composition setting. Native callback
  payload equality passes. No binding emits no dependency. Durable sink/shelving,
  runtime project metadata and retention remain open.
- Native96 state/alarm and122 authentication pass; earlier routing candidate120.
  Native148 blocks/45 interfaces round-trip0/0; production142/45 compiles0/0.
  HMI live login/manual/fault/reset passes with24 modules/492 entries.570 HMI tests
  plus1skip,128 tools and33 consistency tests pass. Generic root reset must recurse
  on nested blocking even after faultActive clears. Test fault text uses the
  generated TEST_FAULT reason-code localization rather than raw test.first.
- Owner VM reboot16:09:46UTC cleared registration. Fraktal's persisted CPU1516
  hardware identity/memory card survived. Register the same name and storage,
  select TCPIP/virtual link-local suite with zero mappings, and power/run the saved
  image; no download or re-pin was needed. Registering API process exit releases
  its registration when no control panel owns it. A hidden keeper now remains
  alive without expiry/unregister; post-boot23 native nested checks pass again.
  Keeper source/log/PID are in LOCALAPPDATA/Fraktal/TiaSpikes/State_Alarm_20261011.
  Do not stop it as routine cleanup. Final root/exercised nested state is READY,
  MANUAL, sessions NONE, no active/blocking alarms; pin/DPAPI preserved.

Current runtime: TiaStations/Alarm_Runtime_20261011/FrkS12/FrkS12.ap20.
Alarm_Verify_20261011 is compiler-only. Approved enumeration driver unchanged;
physical1214C untouched, no150KB reference limit, no released conformance claim.
Access archive3360 bindings and134 available prior files remain unchanged. Older
12 referenced reports/18 SHA manifests remain absent and cannot be reverified.

Next: configuration/recipe transactions and persistence, plus shelving/runtime
metadata/durable adapters and complete diagnostic/action services before complete
Core conformance; then full SCL/generated GRAPH sequences/modules/press without power.

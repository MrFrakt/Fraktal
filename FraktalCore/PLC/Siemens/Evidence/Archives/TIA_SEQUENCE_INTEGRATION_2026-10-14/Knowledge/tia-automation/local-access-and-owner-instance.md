# Local application access and owner instance - TIA V20 / Advanced7

Current owner continuation,2026-10-14: persisted Fraktal was restored after the VM
restart by Resume-TiaSimOwner.ps1. Keeper5380 is current and has no expiry; old
12728 now belongs to another process. Final RUN/CPU1516/TCPIP/169.254.212.49+
192.168.1.1/maps0. Image/certificate/address retained. See
[combined integration](sequence-restore-hmi-integration.md). The older state
and evidence below retain their original scope. **[measured]**

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_ACCESS_SESSIONS_2026-10-11.md.
Scope: generator0.6, simulated1516 V3.0, native Web API, owner Fraktal instance.

- A stopped unspecified owner instance can be adopted without unregistering it.
  Validate its original Softbus/default192.168.0.1 state and zero mappings, power
  off, set TCPIP, power on and assign the isolated169.254.212.49 suite. Setting
  CPUType alone still reports CPU1500_Unspecified; the hardware download establishes
  CPU1516. Download also reports its second configured192.168.1.1 interface with
  no physical mapping. The script/guards retain the owner instance. **[measured]**
- A top-level plan --trust-plc option does not reach a step's OnlineAnswers in
  this driver. The runner injects explicit requested trust into the in-memory
  download substitution. The first refusal is preserved; the corrected download
  logs Trusted and succeeds. Do not rebuild the driver for this runner fix or
  silently trust future targets. **[measured]**
- TIA FC VAR CONSTANT refuses an array here. Generate SHA K constants into TEMP
  assignments from the Core authority. FC string inputs omit width; explicitly
  bound PINs to32. CASE does not accept strings, and WString comparisons need
  WSTRING literals. Grouped TEMP declarations export as separate declarations;
  emit the native form rather than broadening canonical ignores. **[measured]**
- Native SHA vectors empty/abc/32bytes/48bytes match hashlib. The Core-compatible
  iterated salted PIN matches native application login with256 additional rounds.
  One compression per active scan avoids a full synchronous257-compression call.
  Private table/candidate reads200 and authority/policy writes205. **[measured]**
- LOGIN acknowledgment is consumption. Correlate LoginResultSequence and wait
  for LoginBusy=false before reading CurrentUser/CurrentLevel/LoginFailed.
  Failed attempts preserve a valid prior session. Cancellation/supersession,
  per-root isolation, idle expiry despite release polling, accepted-mutation
  activity, self-lockout bounds and STOP/RUN clearing pass122 checks. **[measured]**
- The actual generic HMI login rejects a wrong PIN, accepts operator credentials
  and renders/commands Instant under its normal OPERATOR display policy. Two
  roots/24 modules and492 entries remain, with native counter delta1. Routing
  regression120/120,129 native sources/42 interfaces round-trip0/0; production
 125/42 compiles0/0. Full HMI suite569 pass/1skip. **[measured]**

Production provider is disabled and all thresholds default NONE. The bench
provisions only private salted hashes at Initial_Call. Persistence/CRUD/provider
substitution, data classes, full MESSAGE/alarm audit and concurrent mailbox writers
remain open. Existing access traces include action/user/path and no secret, but
are ST_Diagnostic records. No physical or1200 authentication claim is made.

This resumed checkout is missing twelve newer referenced evidence reports and
all18 previously reported SHA manifests. Work logs preserve the previous audit
summary but cannot reverify absent archives. The current run freezes its own
source/raw evidence and preserves the134 available prior files. **[measured]**

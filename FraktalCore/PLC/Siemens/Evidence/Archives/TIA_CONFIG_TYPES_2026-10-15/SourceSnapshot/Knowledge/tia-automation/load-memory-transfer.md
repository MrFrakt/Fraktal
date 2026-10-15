# Native load-memory transfer - measured 13 October 2026

**[measured]** TIA V20/simulated CPU1516/PLCSIM Advanced V7 supports READ_DBL and
WRIT_DBL with optimized Byte arrays. Independent ordinary DB RAM/load values and
UNLINKED load-only banks pass125/118 checks. Private 64-byte buffers, exact full
CRC, two-slot isolation, replacement, STOP/RUN and PowerOff/PowerOn qualify. REQ
is TRUE once then FALSE while polling BUSY; keep the source stable until done.
Only successful completion acknowledges the test request. Staged arguments
without a new sequence are inert. Invalid kinds issue no native operation.

**[measured]** WRIT_DBL changes load memory without changing the target current
RAM. Altered current bank RAM does not alter later READ_DBL results. Native
IsOnlyStoredInLoadMemory is reported readonly by the observed attribute API;
derived native XML proves TRUE plus Optimized layout. Its SCL export gives the
UNLINKED keyword. Reimporting the source, compile and readback/runtime all pass.
Remove ordinary RAM access for a load-only bank. The fixture helpers assert every
substitution and preserve native declaration bytes. PRIVATE payload reads refuse
Web API200, readonly diagnostics refuse205. The variant transition/full download
returns A to zero start values: do not infer changed-image preservation.

**[measured]** Generator0.14/framework unchanged:321 baseline native files are
byte-identical; only F_ConfigBenchObserve gains the test call. Current project
Load_Memory_Only_Runtime_20261013/FrkS12/FrkS12.ap20; ordinary variant
Load_Memory_Runtime_20261013. Prior Event_Delivery_Runtime project and offline
120-source wired GRAPH/ST press remain available. Owner Fraktal RUN/CPU1516/
TCPIP/169.254.212.49 +192.168.1.1/maps0; preserve keeper12728 in earlier
Access_Persistence work dir. Approved candidate_structure_examples unchanged.
Use the exact --driver and protected DPAPI/environment wrapper. Never unregister.

**[measured]** 926 native assertions total (243 new transfer checks plus config,
access, state/alarm and manual recovery regressions); three compile checkpoints
0errors/0warnings; tools170/consistency35, lint/consistency/whitespace clean. HMI
unchanged. Final normalization MANUAL/logged-out/inactive, owner RUN.

**[planned]** The native instruction leg of S16 is complete at this scope.
Current config/set/user/policy adapters remain LOCAL_RETAIN. Next shared keyed
LOAD_DB medium: bounded tickets driven by consumer polling, private documents,
schema/generation/CRC/two slots, confirmed loss versus unreadable/retry, write-rate
limit and existing config/Start/write/login restore gates. Newest-valid slot order,
damaged/missing/unreadable images and failed writes need native qualification
before a consumer switches. Full I_PersistMedium and physical flash/endurance/
torn-write/changed-image guarantees remain open. Evidence:
C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md.

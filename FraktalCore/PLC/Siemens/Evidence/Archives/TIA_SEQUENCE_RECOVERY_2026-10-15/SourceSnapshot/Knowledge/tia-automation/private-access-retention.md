# Private user and policy retention - reference S7-1500

Scope: TIA V20, CPU1516 V3.0, PLCSIM Advanced7/API5 compatibility, Fraktal generator0.11,
2026-10-12. The operator controls the physical press acceptance; this is a simulator
service bench plus a separately compiled offline GRAPH/ST press application.

- **[measured]** Optimized global DB members declared VAR RETAIN export with
  Remanence=Retain while ExternalAccessible/Visible/Writable remain false. Live
  Web API private reads return200 and readonly policy writes205. Root sessions
  remain NonRetain. Never infer retention from the global DB's NON_RETAIN header;
  inspect each member's Remanence in the native XML.
- **[measured]** Private username/salt/hash records and keyed root policies survive
  guarded STOP/RUN and PowerOff/PowerOn/Run without startup reseeding. The current
  adapter is LOCAL_RETAIN; load-memory/card-file and other media are not established.
- **[measured]** Schema, checksum, counts, duplicate names, level domain, owner and
  timeout checks reject a complete invalid image. A commissioning marker prevents
  a cleared header from being treated as a virgin provider. Do not reseed a damaged
  image automatically. Hash/work-factor and CRC arithmetic use the Core authorities.
- **[measured]** Core registration accepts NONE..ADMIN. NONE is a valid disabled
  account, not image corruption; it grants no authenticated session. A changed
  provider generation revokes existing root sessions and pending older attempts.
- **[measured]** A damaged root policy uses ADMIN thresholds and blocks Start.
  ENGINEER acknowledgement persists that restrictive fallback; ADMIN still governs
  later policy edits. Peer root policy remains independent. Generic ConfigPersist
  distinguishes <root>.Access from <root>.AccessPolicy; users/credentials never
  appear in saved config sets.
- **[measured]** Combining loss sources by writing a public status once for config
  and again later for access creates a transient clear every scan. A Web API client
  can read that clear even while alarms and private flags remain true. Combine the
  sources in the owning status service before publishing; repeated native reads
  across scans qualify the fix.
- **[measured]** The simulator API's Run result can precede completion of the first
  PLC scan. A test witness that is NonRetain resets at restart and cannot serve as
  a monotonic startup epoch. Keep that test-only epoch Retain and wait for its
  increment after the full forest scan before inspecting restored values.
- **[measured]** Retained timeout changes outlive the access regression. The alarm
  regression previously depended on startup resetting that timeout and its admin
  session expired during read-only checks. Normalize test policy explicitly between
  suites; never restore startup reseeding to make a regression pass.
- **[measured]** A single read-only identity query was temporarily unavailable;
  a fresh query found the same RUN instance and keeper. Bound retries to identity
  reads, refuse an actual target mismatch, and never retry an uncertain mutation.

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md.
Current owner image: TiaStations/Access_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20.
Offline press: Access_Persistence_Press_Offline_20261012/FrkS12/FrkS12.ap20.
After the owner VM reboot, the same saved image restored without download.
New keeper12728 supersedes1748, which ended with the previous VM session.
Preserve the current keeper, Fraktal registration and zero physical adapter mappings.
Reuse candidate_structure_examples (ba24e6aa...); no driver rebuild or whitelist
change was needed. Durable alarm storage and broader provider/media forms are next.

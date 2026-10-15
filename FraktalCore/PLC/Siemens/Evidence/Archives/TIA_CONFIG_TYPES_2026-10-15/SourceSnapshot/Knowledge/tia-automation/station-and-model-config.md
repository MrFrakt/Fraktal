# Station config and model config - V20 / Advanced7

Evidence: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md.
Scope: generator0.8, simulated1516 V3.0, owner Fraktal. **[measured]**

- Use station config, line config and model config consistently in presentation
  and current docs. Stable serialized keys/members remain unchanged; frozen
  history is not renamed. Optional line config runtime remains open.
- One per-type definition emits both manifest capability and typed handler.
  Schema-first/nonzero records, complete model ParCfg registration, exact owner/
  key/revision, native grammar/range and effective minimum access are enforced.
  Supports Boolean/integer/TIME/STRING bounded by Core set-record widths. Wider
  text and unsupported float/enum/array forms are refused before import.
- An editable ParCfg cannot remain VAR_INPUT when passed to a mutating FC:
  six Siemens access-right warnings were resolved by owned read-only statics in
  the editable profile. Restore runs before Init; own-frame functions take their
  required components rather than an FB self pointer. No project assembly call.
- VAR RETAIN under a NON_RETAIN optimized global DB exports Remanence=Retain
  for selected fields; other VAR fields remain NonRetain. Public and hidden
  values survive STOP/RUN and simulated power cycle; hidden reads200. Seven
  native checks pass. This is simulator evidence, not physical durability.
- The consumed-size retained pool holds keyed ST_ConfigRecord plus model/schema.
  Station config and model config restore separately. Invalid model schema
  defaults that record without discarding valid station config. ENGINEER-or-higher
  acknowledges loss; public status uses Core5000ms window and store failure.
- Inactive root-model edits can proceed while BUSY without changing running values;
  explicitly naming the active catalog index still requires readiness. Children
  follow the active model; station config is outside the model transaction.
  Late child prepare failure leaves all earlier live values and identity unchanged,
  names its scope/key, and raises RECIPE_INVALID with the child's canonical source.
  Commit has no fallible validation/I/O. Model action/query share current release.
- V6 native120/120, access122/122, state/alarm96/96;190 authored blocks/52 interfaces
  canonical/reimport0/0; production183/52 compiler-only0/0.135 tools pass including
  hash-seed-independent generation. Unsorted set iteration had changed component
  signature order; sort it, never rely on one process's hash seed.570 HMI tests
  plus1skip passed before the refresh fix; the final suite passes571 with8 opt-in
  skips.35 consistency tests pass. The live Admin editor writes21, independently
  reads it from the PLC, verifies inactive-model isolation and restores10.
  The mapper uses valid current scalar readings while preserving declared
  visibility/levels/bounds; the field used to retain the cached manifest value.
 23 native checks also prove blocking restore/one acknowledgment/Start release.
- Current Python JSON/simple path rejects escaped Unicode TextValue with -32602
  before mailbox commit. Record transport scope; do not claim the PLC rejected a
  value it never received. Unicode/raw write acceptance remains unestablished.

Current runtime: Config_Runtime_20261011/FrkS12/FrkS12.ap20. Config_Verify holds the
separate compiler image. Owner Fraktal stays RUN with keeper1748; never stop it
as routine cleanup. Approved driver/pin/DPAPI preserved, physical1214C untouched.
Named config sets/import/export, other media, user/policy/alarm persistence,
line config replication, broader forms and download-loss detection remain open.

Frozen evidence verifies4487 SHA bindings (83,655,612 bytes),655 source/10 knowledge
snapshots. Previous Access3360/State3179 plus134 available older files unchanged;
12 older reports/18 manifests remain absent. Final audit stays outside the archive
at Config_Transactions_20261011/91_final_evidence_audit.json. **[measured]**

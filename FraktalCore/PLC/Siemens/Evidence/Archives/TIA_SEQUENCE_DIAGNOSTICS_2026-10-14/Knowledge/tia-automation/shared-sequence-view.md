# Shared sequence view: measured V20 integration, 2026-10-13

Current continuation: [2026-10-14 combined restore/native HMI integration](sequence-restore-hmi-integration.md)
supersedes the runtime/keeper/remaining-work pointers below. This dated section
records the original0.16 qualification.

[measured] Fraktal generator0.16 uses unchanged Core 3.13 types and optional Unit
capacities for definitions, per-leg cursors, PLC-owned history and sparse notes.
Only deployed consumers allocate work. A private typed pool owns state; the same
Unit frame controls scan/mode boundaries and publishes readonly mirrors. Static
definitions travel through the config manifest. No additional application scan
call is required. This is the Fraktal design demonstrated here, not a Siemens
library feature or a completed full-port conformance claim.

[measured] Early sequence FCs that referenced root DB/FB members caused a compile
cycle: GRAPH must compile before the owner adapter/root FB can exist. Moving work
to consumed-size typed private storage lets the helper/chart stage compile before
the root. Root publication stays in its generated frame. Both final press compile
stages are zero errors/zero warnings, with native graph readback unchanged.

[measured] UPPER_BOUND on the fixed Core CurrentStep.Conds array was rejected:
"Only ARRAYs with variable limits are permitted." Open-array parameters work.
The condition bound now derives from Core MAX_STEP_CONDS. For this generated LAD
Time argument, both T#0ms and 0ms were rejected during import. A private typed
Seq.NoTimeGuard operand is the compiled/read-back workaround. This does not prove
all time-literal forms fail. Core ST_Diagnostic has SourcePath, not LinkPath.

[measured] Step identity must be unique inside the running mode. Press load-position
locals240/260/280/300 collided with main240 and parallel300. One declared view
offset360 projects them to600/620/640/660. Main GRAPH numbers/transitions remain
unchanged. A depth argument prevents a later composite parent record from replacing
its deeper active sub-chain cursor. A mode commit clears discovery; same-mode
visits retain history. A full sparse note table retains the row's authoritative
error/warning flag; only text is dropped.

[measured] The shared reset gate correctly rejects OPERATOR_RESET without a real
blocking occurrence. A chart presentation mark alone does not open it. The native
reset test first creates a real blocking event and authenticates the operator;
the release gate was preserved. Revision tests wait for the latest metadata
mutation's quiet interval, not an already committed discovery revision. Derive
Core ordinals: MANUAL is1 here. Do not guess.

[measured] 122 native synthetic checks pass, including actual sequence helpers,
fast history, dynamic guards, manifest facets/revision stability, cursor priority,
slot reuse/full-table marks, bounds, mode/reset, root/nested isolation, privacy,
readonly access and STOP/RUN. Runtime compile0/0, press both stages0/0. Final press
168 sources, GRAPH19AUTO/4HOME, optional LAD161 networks/155 calls, MAIN3 calls.
Tool suite183 and cross-artifact35 pass; shipped lint/consistency clean. The lint
public-member map now derives from the generator; compiled source bytes are
unchanged by that Python refactor.

Current runtime is Sequence_View_Runtime_20261013/FrkS12/FrkS12.ap20 under
%LOCALAPPDATA%/Fraktal/TiaStations. It is a synthetic sequence/config bench using
LOCAL_RETAIN config. The separately compiled Sequence_View_Press_Offline_20261013
selects both the view and LOAD_DB. The previous 903 LOAD_DB regressions remain
separate evidence; they were not rerun on the current sequence fixture.

Final owner: Fraktal RUN, CPU1516,169.254.212.49/192.168.1.1, physical mappings0,
keeper12728 preserved. Both roots MANUAL/READY/loggedout, charts empty, no blocking
alarm or pending/failed config commit. Approved candidate_structure_examples
binary/hash unchanged. Native HMI rendering, combined LOAD_DB boot publication,
complete diagnostic walks/profiling, provider/line config and broader module/
deployment acceptance remain work. No physical press or loss guarantees inferred.

Evidence:
[dated scope/report](C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_SEQUENCE_VIEW_2026-10-13.md).
Fresh-chat continuation:
[handover prompt](C:/Projects/Fraktal/Specification/Siemens/Reports/TIA_IMPLEMENTATION_HANDOVER_2026-10-13.md).
Source/experiments remain in Fraktal; the KB records measured facts and links.

[measured] The final archive verifies6,748 files/637,012,841 logical bytes. A project-cache copy encountered disk full; transparent compression preserved contents and permitted complete copies/sealing. Existing engineering projects and keeper are intact. C: remains under1GB free; check available workspace before another clone/build series. The current handover includes this post-seal fact; its archived snapshot precedes that addition.

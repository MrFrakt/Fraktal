# Shared sequence recovery, 2026-10-15

[measured] Generator0.20 adds private lifecycle epochs only for consumed
sequence-view owners. The generated Unit frame captures state before sequence
execution and after FRK_End, including late kernel faults. Existing begin
helpers consume those epochs; applications add no recovery scheduling call and
MAIN remains three calls. Released Core layouts and enum ordinals are unchanged.

[measured] Faults retain the raising step and release issued child commands.
Leaving ERROR clears row errors and rearms command, delay and event state.
An accepted Start is still required. The application chooses retained-step
continuation or whole-chain restart; the wired press chooses restart. HELD
continues through the existing restorable permit without fault/reset/reissue.
Boot, mode, both abort paths and restore quiescence invalidate retained work.

[measured] Native GRAPH evaluates transitions before new step actions. Clearing
RetVal before its call stranded the generated chart on its initial step.
FRK_SeqGraphBegin preserves the preceding active scan's result for transition
evaluation; FRK_SeqStep clears it before the current action decides. Fault,
restart and rearm discard it. Ordinary fault freeze withholds the chart call.
Forced-restart idle scans call it with OFF_SQ, let INIT_SQ fall, and pulse INIT_SQ
only while running. Holding the earlier reset input through abort-in-ERROR lost
the next pulse. Inactive step/delay helpers cannot publish rows/progress timers.

[measured] Native GRAPH recovery79 checks pass. Runtime466 blocks/111 interfaces
and press424/101 canonical witness subsets match. Press GRAPH19AUTO/4HOME and
LAD161 networks/155 calls match native readback; replay24/184 passes. The
[qualification report](../../../Fraktal/Specification/Siemens/Evidence/TIA_SEQUENCE_RECOVERY_2026-10-15.md)
states final regression/normalization counts and source-witness exclusions.
The press is compiled offline; physical and full branched-process acceptance
remain separate. Broader configuration-provider, line-config, module/HAL,
baseline/reset/OEE and deployment gates remain open.

[measured] Current projects: Sequence_Recovery_Runtime_20261014 and
Sequence_Recovery_Press_Offline_20261015 under AppData/Local/Fraktal/TiaStations.
The work prefix uses October14 UTC; the report uses October15 Europe/London.
Keeper13476, the Fraktal CPU1516/Advanced7 instance, image, storage, addresses,
pin and DPAPI credentials are preserved. Never act blindly on a historical PID.
The approved candidate_structure_examples executable remains unchanged:
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.

[measured] Fixture controls copy complete arguments on RequestSeq, committed
alone and last. Abort is a protected PLC input, not an HMI ABORT ordinal; the
fixture drives it through PLC wiring. Quiescence drops the operator session,
so recovery needs a fresh login. Native test-source import first compiles a
bootstrap chart/Unit set, then its adapter and final frames. Every final compile
is zero errors/zero warnings. New builds/whitelists are unnecessary for source
plans using the existing driver. Do not generate another handover prompt.

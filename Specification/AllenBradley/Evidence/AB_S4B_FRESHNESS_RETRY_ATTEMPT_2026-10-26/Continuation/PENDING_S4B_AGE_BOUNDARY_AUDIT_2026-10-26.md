# Read-only audit during the frozen freshness qualification

Do not edit the running session's bound source. Session `retry_freshness_01`
is active under `call_9f47a022b96c480b81af9d85ec59f551:0`.

Before final desktop/freshness acceptance, review two conservative-age boundaries:

1. `CipReadPlan._group` currently assigns `sampledAtUs = now` after awaiting the
   entire coherent read. OPCUA_TRANSPORT defines conservative accepted age from
   before I/O. A clock-controlled delayed transport should prove that the
   accepted row age includes its pre-counter/body/post-counter latency. Capture
   the last accepted attempt's start in the plan's own monotonic clock, not a
   guessed timestamp after resuming a future. Keep all guard checks intact.
2. `CipSessionEngine.snapshot` currently sets `responseProcessingMs` after
   `plan.snapshot()` and path expansion, although row ages were calculated
   earlier. Bracket handling immediately before the age calculation so later
   projection/serialization work remains in the repository's transit allowance.
   This must be conservative; no freshness limit or payload policy should change.

These are source-level audit findings, not a measured explanation of a native
failure. Do not change frozen artifacts or count them as fixed. First finish
the approved qualification, rollback and seal; then implement/review/test the
necessary corrections before claiming complete freshness conformance.

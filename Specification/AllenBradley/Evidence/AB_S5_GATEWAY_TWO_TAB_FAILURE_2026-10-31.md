# S5 two-tab browser failure; genealogy restored

Recorded 2026-10-31T14:36:56.019512+00:00 under standing O3,
following [sealed preparation](AB_S5_GATEWAY_BROWSER_HELP_PREPARATION_2026-10-31.md).
Echo 601FC87B, L81E v38.011, 127.0.0.1 slot 0. Unchanged candidate ACD
95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012, Capacity 66%.

All 12 automatic C1–C11/C13 cases passed, including both 100-second idle
checks and exact PartSlide movement/return. Four configuration pages matched
1,100 independent scalar comparisons. A fresh Chrome profile opened only after
the nonce and native MANUAL/idle/logged-out boundary were captured. No clicks,
login, command or checklist response were automated.

The owner reports: “seccond tab at first showed connection error page, then
connected and keeps reconnecting and disconnecting”. The exact reply and failed
checklist are preserved. After stopping, the owner confirmed MANUAL, logged out
and both tabs closed. The native boundary was MANUAL/idle/logged out, ACK33
(before22). Both gateways reported ready; no upstream CIP disconnection was
logged. C12 fails despite the successful automatic cases. No pass is inferred
from command consumption or gateway readiness.

The existing logs expose shared profile changes when a second client joins and
when one client requests detail rows. They do not record the browser's exact
freshness refusal. Investigation will distinguish a tier-aggregation defect
from other browser timing causes; no product fix has been native-qualified.

Independent reads passed: 5,238 occupied paths, seven-module acquisition and raw
capture replay, four configuration pages / 1,100 scalar comparisons. TASK
cumulative maximum was 7,759 µs, zero overlaps over 11,138 monitored samples
and 20 final observations. These independent successes do not manufacture a
successful combined session: S5 remains open.

The automatic finally path downloaded a hash-checked copy of the genealogy
pin, restored all five original documents, passed 31/31 baseline cases and all
final checks, preflight and baseline timing. Echo ended Run/not faulted,
scanning, MANUAL/idle/logged out, not restoring, saved documents equal to live.
No dumps, fault/TASK clears, clock changes, power/vendor-state operations or
Echo hard kills. Only owned gateway/test/browser processes stopped.

Payload manifest SHA-256: 0879D0C77BE859ACA537D658D2BBFA31230DA0DDCEB57E0837DC930D2C12D298.
No credentials, ACD/L5X, binaries, caches or browser profiles are archived.

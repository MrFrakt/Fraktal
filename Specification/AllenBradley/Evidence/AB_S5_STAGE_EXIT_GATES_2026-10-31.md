# S5 final tree gates

Recorded 2026-11-01T04:37:38.193709+00:00 under owner
date 2026-10-31. This supplements the
[runtime qualification](AB_S5_GATEWAY_QUALIFICATION_2026-10-31.md); its original
baseline failure and separate successful recovery remain immutable.

Fresh final-tree checks pass: 2,357 AB tests by discovery from the binding's
tools directory, 74 root tests, AB specification/contracts checks and strict
consistency. The logs retain expected negative CLI/refusal output. No tests or
assertions were weakened to obtain the result. The unchanged dual-v38 compiler/
read-back and 66% exact-image Capacity proofs remain bound by source/image
hashes in the qualification/preparation records.

HMI/package validation remains the fresh 802 passed / 12 existing skips,
analyzer, locked dependencies, gateway tests and Web/Windows/gateway/installer
builds recorded in preparation. The final documentation update changes no
compiled PLC/HMI inputs. Source/evidence review covers 8,094 files (77,679,766
bytes), including 136 decompressed gzip payloads; no fixture credential values,
binaries, caches, ACD/L5X or outside-scope edits are selected. The final Git
stage audit also checks the complete subsequently added gate records.

O1 authorizes the stage commit and normal push to main. Its pre-commit hook is
enabled and must run; no hook bypass or force push is authorized or needed.
No additional controller operation is performed by these gates. Echo remains
on the verified genealogy baseline; S6 and deferred S7 remain open.

Payload manifest SHA-256: F2891B836C7A7BE07FEAE96F5F4817FF9E9BD11BE5541E1F379065971E2B3EBD.

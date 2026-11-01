# S5 detail-refresh preparation: authorization separation

The [preparation](AB_S5_GATEWAY_DETAIL_REFRESH_PREPARATION_2026-10-31.md)
accidentally bound the unarmed authorization as a frozen source input. No
controller access or session start occurred. Its original payload and runtime
files are preserved. This closure separates only the actual authorization,
matching session18: the template and all other 869 bindings
remain unchanged. The strict exact-image/scope authorize() validator and the
session-start approval hash remain required. No controller guard is relaxed.

Standing O3 arms this exact existing image/session. No new write vector is
added. Every freshness, proof, retry and rollback rule is unchanged. The
attached final binding and approval hashes govern the session. All original
gate results remain applicable. Payload hash: 45DA008A29B155F239A13463835986642EFB977CD2EA50A23D989CEDAD1757B2.

# Phase 6 - selected model configuration page reads

Date: 2026-10-04. Result: shared HMI checks PASS; corrected Web client deployed;
owner browser acceptance pending. No PLC source/artifact, memory, controller value
or gateway process changed.

The owner reports creating M-101: the catalog lists it but selecting it shows
that the recipe is unavailable. Exact-serial read-only inspection at
2026-10-04T21:14:07.443382Z confirms 7036B510, manifest 66C4A00ABDB4FCC3,
four catalog codes and four valid schema-4 recipe banks. Native projection has
pages for all four; the running gateway exposes the same catalog and 227 actual
configuration-page paths. This is a readback, not an armed command regression,
completed Studio download proof or physical created-model retention test.

The shared HMI invented TC3-style double-segment array paths and optional leaves
for targeted response reads. AB publishes flat Entries[i] paths and a smaller
page. One undiscovered path rejects an entire read batch. The old fallback then
parsed shared cyclic values, which could be replaced during post-ack cleanup.

Targeted config/report reads now use the exact discovered subtree, accepting
flat/container array forms and absent optional leaves. Configuration queries
capture their own immutable response before awaited cleanup; manifest hydration
and inactive-model selection share that code. Unreadable or invalid page headers
return unavailable instead of another model's cached values. Operator model
queries yield polling as interactive work; background hydration keeps its
existing scheduling. Normal PLC permissions and Changeover remain unchanged.

Regression fixtures query the fourth model using flat AB and limited TC3 paths,
with a periodic snapshot replacing cached values during cleanup. They verify
selected values, unchanged running model, no undiscovered read, and refusal to
substitute cached active values when the payload read fails. Two assertion
mutants are killed: restored TC3-only interactive paths and discarded captured
reply. The original mutation attempt stopped on initial-hydration timeouts; its
log is retained and is not counted as a semantic kill. Source was restored
byte-for-byte after both mutation runs.

Validation: AB 1,563 PASS; HMI 492 PASS with seven intentional live-environment
skips; analyzer clean; Web release PASS. Root consistency reports zero errors/warnings;
all 33 root tool tests pass. No TC3 PLC source changed.

Deployment: main.dart.js SHA-256
888C0A81B61FCE4C11E15D0FD1A27B2E2EDAD73249C446CB8BC58D3D4912F6AE.
main.dart.js, flutter_bootstrap.js and index.html return HTTPS 200, validate the
press.localhost TLS identity and match release bytes. Prior assets remain at
C:/work/press70_model_access_web_backup_01. The owner must hard-refresh the
existing Chrome tab and query M-101 for browser acceptance. No import/download
or gateway restart is needed for this HMI correction.

Line data is absent in AB, including the requested weekday/duration calendar;
it is queued port work, not repaired by this Web release. Before any future
PLC download, preserve all four commissioned model codes/banks: the old
three-seed-only initial-image helper cannot yet migrate an expanded catalog.
The final AB project guide and TC3 handoff refresh remain completion outputs.

The [machine-readable record](AB_PHASE6_HMI_MODEL_PAGE_READ_2026-10-04.json)
binds source, gate logs, exact readback, mutation outcomes and deployment hashes.

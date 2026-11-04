# S6 WP6.4 — V6.11 host-service layouts, offline

2026-11-04, America/Mexico_City. Entry commit `2c5f9b2c9`, with the
uncommitted S6 working tree. This is offline engineering evidence for the
[V6.11 wire draft](../AB_CANONICAL_PUBLICATION_S6_HOST_SERVICES_WIRE_DRAFT_2026-11-04.md),
under O4. It makes no native claim. No controller or Echo service was
contacted, no image was generated or downloaded, and nothing was committed.

## What was built

| Source | Role |
|---|---|
| `fraktal_ab_host_service_binding.py` | Client protocol, declaration-free: table rules, Template schema negotiation, `encode`/`write_plan` (0x4D request write plus a separate DINT commit), `next_sequence`, `outcome` |
| `fraktal_ab_host_services.py` | Engineering: V6.11 types, descriptor rows, tags, the generic ingress `ingress`/`finish` ST and job helpers |
| `fraktal_ab_canonical_manifest.py` | V6.11 header, `HostServiceBindings` normalization, content hash; host roots must be command roots; a ring needs its owner-read row |
| `fraktal_ab_canonical_reader.py` | S1 snapshot accepts minor 11. It refuses host ingress records in cyclic captures, covers rings in the owner scope and negotiates each root's ingress schema |
| `fraktal_ab_owner_read_bindings.py` | A whole-scope owner row may cover a HostEvents ring its row names |
| `cip_manifest.dart` | The Dart decoder accepts V6.11 with the same rules and hash body |

`Gates/source_bindings_01.json` binds these files and the draft. Its tools
hashes equal those the full suite ran against. `Gates/source_bindings_02.json`
rebinds after the closing document corrections.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`, all exits 0):

- **Focused:** 29 tests (ResourceWarnings as errors). 21 run the generated
  ingress ST in the executed-ST model; 8 cover the Template schema, the encoder
  and the V6.11 manifest table built on the V6.10 owner fixture.
- **Mutations:** `mutate_host_services_01.py` makes 14 source mutations, and
  each one is killed by a named test:
  - 10 in the ingress: commit re-read, the half-circle bound, abandon on a
    refused claim, key extents, the first scan, job identity, chunk order,
    one reply copy per changed scan, the full-width text wipe and the
    manifest revision;
  - 4 in the client: the writer advances from Serial, one ingress per root,
    the exact text width and the request size bound.
- **Full AB discovery:** 2,450 tests pass (877 s); all 391 Python module hashes
  are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

`Investigation/run_gates_02.py` (`Gates/gate_summary_02.json`, all exits 0):

- **Golden:** `write_v611_golden_01.py` regenerates the Dart fixture
  byte-identically (SHA-256 `C0F9CA91…FAE6`).
- **Dart:** the focused decoder tests pass 13/13, and the Python-normalized
  V6.11 golden decodes with the identical content hash `5592DD18…2F5C`.
  `flutter analyze` and the client-package `dart analyze` are clean, and the
  full HMI suite passes **842**, with 12 intentional skips (Flutter 3.47.5).
- **Documents:** the AB specification gate and strict consistency are clean
  again after the plan and review edits.

`Investigation/run_gates_03.py` reruns both document gates after the closing
corrections. Those corrections remove "the Dart decoder refuses minor 11",
which became untrue during this checkpoint.

## Failures during development (not gate runs)

The executed-ST tests failed in early unrecorded development runs, and each
cause was in the tests or the fixture:

- The model's CPS gives its destination new storage, but the tests held stale
  references.
- One test treated a rewrite of the identical commit as a replay. It is
  correctly invisible.
- One test treated 0xFFFFFFFF as a wrap from serial 0. It is correctly behind
  serial 0.
- The fixture stored uint32 bits in DINT fields without the signed
  reinterpretation.
- Two first mutants used `TRUE`/`FALSE` literals the model may not parse. The
  recorded mutation script uses semantic mutations instead.

During the same development, the ingress design itself changed once. A first
scan with `Armed` = 1 had swallowed a changed commit. A writer advancing from
`Serial` would then repeat that value and never be seen. Only a download now
seeds the serial; a later first scan abandons the job and still consumes the
commit. No PLC or native defect is claimed from any of this.

## Boundary

These are synthetic layouts. They do not establish the native Template layout,
the 2,232-byte request size, a one-packet reply, CPS reply atomicity or the
2 s acknowledgement budget. The S1 snapshot's V6.11 path awaits a full V6.11
capture. Still open:
- the service routines, declaration opt-in and emission, the ring owner
  revision in the publication routine and the host adapter (WP6.5);
- WP6.6, both v38 builds, exact-image Capacity and scan, and S6-Q.

S6 has not exited, and nothing is committed under O1.

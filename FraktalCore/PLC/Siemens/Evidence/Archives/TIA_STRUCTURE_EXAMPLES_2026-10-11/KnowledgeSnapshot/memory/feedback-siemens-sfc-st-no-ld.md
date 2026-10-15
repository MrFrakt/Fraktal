---
name: feedback-siemens-sfc-st-no-ld
description: "Fraktal/TIA — ST/GRAPH remain primary; owner added unwired ST/LD/GRAPH examples on 2026-10-11"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 557e92d1-b71c-4c7c-8e05-907ccca6dc19
  modified: 2026-10-08T04:10:17.406Z
---

For the Siemens (Fraktal/TIA, Part IV) port, use SFC + ST for the integrated port.
The owner explicitly changed the earlier restriction on 2026-10-11: add ST and
LD sequence/permissive examples, keep them unwired; the owner will wire/test them
as in TC3. The earlier no-Ladder directive does not prohibit these examples.

**Why:** user directive 2026-10-08 ("use SFC + ST for sequences and permisives instead of LD as AB port"). Core §5.5/§6.8 already name SFC the default language.

**How to apply:** SFC = S7-GRAPH, unavailable on S7-1200. The reference target is
simulated S7-1500 with no 150KB cap. Generate every native LAD/GRAPH graph and
read back TIA's exports. `Examples/PressDemo` owns AUTO/HOME and ST/LD release
examples; shared typed device APIs own the handshake. See [[project-siemens-port]].

---
name: feedback-siemens-sfc-st-no-ld
description: "Fraktal/TIA (Siemens) port — sequences and permissives in SFC (S7-GRAPH) + ST (SCL), never Ladder like the AB port"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 557e92d1-b71c-4c7c-8e05-907ccca6dc19
  modified: 2026-10-08T04:10:17.406Z
---

For the Siemens (Fraktal/TIA, Part IV) port, write sequences as SFC + ST and permissives in ST; do not use LD the way the Allen-Bradley port did (AB press80 carries AUTO in ladder only).

**Why:** user directive 2026-10-08 ("use SFC + ST for sequences and permisives instead of LD as AB port"). Core §5.5/§6.8 already name SFC the default language.

**How to apply:** SFC = S7-GRAPH, which TIA V20 supports only on S7-1500 (and 300/400), not S7-1200 — so an S7-1200 target carries the SCL `CASE` rendition and the GRAPH rendition is proved on S7-1500 (PLCSIM until hardware). Never generate ladder renditions for Siemens. See [[project-siemens-port]].

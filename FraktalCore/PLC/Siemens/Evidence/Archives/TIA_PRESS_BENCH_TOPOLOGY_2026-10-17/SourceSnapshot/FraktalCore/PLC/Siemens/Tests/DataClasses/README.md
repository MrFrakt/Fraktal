# Data class policy bench

`make_fixture.py` adds independent root policies to the operations fixture.
The same CM/EM/Unit types receive the calling root's policy during the typed
ownership walk; shared line values also use the referencing root's policy.
The fixture includes16 PLC assertions using the common `FRK_TestAssert` service.

Finish offline imports/compiles before starting the simulator download. One
extra CPU is not sufficient protection against disk pressure if a second TIA
compiler process overlaps its full download. Early stop may be requested
through the session's stop file; the owner still waits for host cleanup.

`run_live.py` uses the reserved operations CPU1516 at169.254.212.55, one extra
simulator at a time. It downloads once, tests the real Web API mailbox and
performs actual simulated power cycles. The saved original Fraktal instance and
physical1214C remain outside its target guard. Existing DPAPI credentials are
provided through `Tests/Access/with_credentials.ps1`.

The probe checks public classes below blanket thresholds, raised minima,
undeclared-class fallback, metadata with blanked values, readonly policy
storage, audited class edits and per-record set access. It poisons only the
fixture's retained class cache to prove LOAD_DB restoration, then damages both
anchors of only StationA's class document to test restrictive recovery and
explicit acknowledgement. The ordinary action policy and StationB's class
policy must survive independently.

Native alternative review (roadmap§7): Siemens UMAC/web-server roles authenticate
transport or operator identities. They do not implement Core§3.8d's per-root
class defaults, runtime policy edits, raise-only minima, manifest redaction and
atomic set authorization. These remain one shared Fraktal service; storage
continues using native `Serialize`, `WRIT_DBL` and `READ_DBL`.

Class declarations use the stable root identity:

```json
"data_classes": {
  "PressDemo": [
    {"id":"operator", "label":"press.config.operator",
     "read_level":0, "write_level":1}
  ]
}
```

A registered config field selects it with `"class_id":"operator"` and may
raise `min_read`/`min_write`. Omitting `class_id` keeps DATA_READ/DATA_WRITE.
An undeclared class or invalid threshold resolves to ADMIN. Class loss blocks
writes until acknowledged; its fallback levels remain ADMIN until deliberately
recommissioned. New class documents are appended after existing persistence
documents; `ST_AccessPolicy` and its image retain their existing layout.

This bench is an engineering fixture. It is not generated into production
stations. Native simulator results do not qualify physical loss/endurance or
full-download retention.

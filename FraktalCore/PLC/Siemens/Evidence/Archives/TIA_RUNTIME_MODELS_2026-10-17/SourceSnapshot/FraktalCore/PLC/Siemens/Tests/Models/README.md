# Runtime model catalog

Core §3.8 / HMI contract request37. Opt in at the composition root:

```json
"model_config": {
  "models": ["MODEL_A", "MODEL_B"],
  "initial": "MODEL_A",
  "capacity": 3
},
"config_sets": {"capacity": 4}
```

Missing/zero capacity keeps the static provider and does not publish
`ModelCapacity`. A nonzero capacity must cover the ordered seed catalog and fit
`MAX_RECIPES`. Every root owns its own catalog, including roots of the same FB
type. Nested Units share their root's provider. Model codes are bounded printable
ASCII; indices only append during normal creation.

`CREATE_MODEL`: `NameValue` is the new code; `IntValue` is the source index
(0=current). `BoolValue=TRUE` instead selects the complete saved model set named
by `TextValue`. The operation requires CONFIG_SET and each source value's read
and write access. It checks the complete typed schema and reserves every cache
destination before committing any row. Creation may run BUSY: it does not call
the project's recipe staging or commit phases and does not change the active
model. Activate it through ordinary SET_MODEL/changeover.

The shared set workspace validates the source in one scan; there is no project
wiring call. Scalar writes, set loads and clones use one row commit and one
persistence notification. A missing set-load cache row can be reserved and
repaired; a full pool refuses before any row commit. Complete typed model sets
may be imported/exported with a code absent from the local catalog so they can
serve as recovery sources. Loading such a set is refused until it has a known
catalog identity.

LOAD_DB stores the catalog and **all runtime-created model data in one atomic
document per root**, appended after the existing station, seed-model, access,
user, set, line and class documents. Its key derives from the canonical root,
never from a runtime name. The runtime record count is bounded by
`(capacity - seed count) × registered model fields per root <= MAX_SET_RECORDS`;
the document must also fit `MAX_PERSIST_DOC_BYTES`. Oversized profiles are
refused during declaration admission.

The request acknowledges acceptance of the creation transaction. Public count,
indices and ConfigRev advance only after the document has been saved and read
back; ConfigPersist.Pending covers that interval. Concurrent changes to an
existing model coalesce into the same durable snapshot. LOCAL_RETAIN uses the
same complete validation/commit and publishes without asynchronous storage I/O.
Download remains a separate boundary.

At LOAD_DB startup the cache is cleared before restore. Only a fully validated
document can restore the created catalog and its data. Missing/corrupt
commissioned storage falls back to the complete seed catalog and publishes a
configuration loss requiring explicit acknowledgment; it never reconstructs
identities from orphan rows. Peers and class/action policies have independent
storage. The fixture deliberately poisons retained catalog data and damages
the model document anchors to exercise that boundary.

`make_fixture.py` extends the class fixture with model admission/reservation
assertions and private fault-injection controls. `run_live.py` requires an
already compiled/read-back-verified revision under the fixed private Models
workspace, then downloads once to the reserved unmapped `.55` CPU and always
releases it. Keep offline compilation and simulator downloads sequential.

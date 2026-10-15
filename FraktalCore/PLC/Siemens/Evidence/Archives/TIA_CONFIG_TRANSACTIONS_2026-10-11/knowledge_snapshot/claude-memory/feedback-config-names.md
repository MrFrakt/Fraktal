# Consistent config category names

Owner instruction2026-10-11: use "station config", "line config" and "model config"
consistently. Do not mix those category labels with "station data", "model params"
or "model data". Apply to new code terminology, current docs and HMI presentation.
Existing serialized keys/canonical members (ParCfg, StationCfg, LINE_CFG, modelData
layout key) retain compatibility; their visible labels use the consistent names.
Frozen evidence is historical and never rewritten for terminology changes.

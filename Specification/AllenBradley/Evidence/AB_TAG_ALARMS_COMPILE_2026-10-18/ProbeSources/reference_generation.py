"""Reproduce the disposable L5K bridge from the SDK-exported empty seed.

Reference only: the shipping XML emitter owns the accepted probe configuration.
Pass new output paths; invoke export_sdk/Export.exe for each offline conversion.
"""
from pathlib import Path
import sys

seed, output = map(Path,sys.argv[1:])
if output.exists():
    raise ValueError('new L5K output required')
text=seed.read_text(encoding='utf-8-sig')
assert text.count('TAG\n\tEND_TAG')==1 and text.count('CONFIG OpcUa')==1
text=text.replace('TAG\n\tEND_TAG','TAG\n\t FRK_NativeAlarmInput : BOOL (ExternalAccess := Read Only) := 0;\n\tEND_TAG')
alarm='''
ALARM_CONDITION Projected (Name := "Projected", Input := "FRK_NativeAlarmInput", ConditionType := "TRIP", Limit := 0.0, Severity := 700, OnDelay := 0, OffDelay := 0, DefaultShelveDuration := 1, MaxShelveDuration := 1, Deadband := 0.0, Used := true, InFault := false, AckRequired := false, Latched := false, AlarmSetOperIncluded := false, AlarmSetRollupIncluded := true, EvaluationPeriod := 2, Expression := 128, AlarmClass := "FraktalProbe")
END_ALARM_CONDITION
'''
output.write_text(text.replace('CONFIG OpcUa',alarm+'\nCONFIG OpcUa'))

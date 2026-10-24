from pathlib import Path
import json
P=Path(__file__).parent;OLD=P.parent/'retry_fc306d330cc642499a52abbb53bae945'
t=(OLD/'prepare_retry.py').read_text()
assert t.count("OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'")==1
t=t.replace("OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'","OLD=P.parent/'retry_fc306d330cc642499a52abbb53bae945'")
t=t.replace("RetryOf='Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md'", "RetryOf='Evidence/AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23.md'")
t=t.replace("template.update(Scope=", "template.update(ReadTimingDiagnosticsAuthorized=False,Scope=")
t=t.replace("'; unchanged-even polls paced at one millisecond inside the original budget'", "'; diagnostic timing/generation samples and last-attempt frames; eight read-only TASK mirrors after acquisition failure only'")
with (P/'prepare_retry.py').open('x') as f:f.write(t)

from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'
t=(OLD/'prepare_retry.py').read_text()
t=t.replace("P=Path(__file__).parent;OLD=P.parent/'prepare_5822102a73e348ec95ff7082959ef940'", "P=Path(__file__).parent;OLD=P.parent/'retry_9d1da9a04d564b03bc2b176f5b17ea42'")
t=t.replace("template['Scope']+'; qualified single-owner socket multiplex, four connections and one outstanding read per connection'", "template['Scope']+'; unchanged-even polls paced at one millisecond inside the original budget'")
t=t.replace("RetryOf='Evidence/AB_S3H_CANONICAL_ATTEMPT_2026-10-23.md'", "RetryOf='Evidence/AB_S3H_CANONICAL_RETRY_ATTEMPT_2026-10-23.md'")
with (P/'prepare_retry.py').open('x') as f:f.write(t)

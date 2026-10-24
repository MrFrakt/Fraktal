"""Bind measured Capacity and the untouched predecessor; no calibration update."""
import hashlib,json
from pathlib import Path
W=Path(__file__).parent
capacity=json.loads((W/'capacity_auto_01.json').read_text())
prior=json.loads((W/'baseline_capacity.json').read_text())
assert capacity['VerifiedFit'] and capacity['CanonicalSha256']==(W/'canonical.sha256').read_text().strip()
for name in ('Sha256','UsedStandardBlocks','AvailableBlocks','TotalBlocks'):
    capacity['Baseline'+name]=prior['CanonicalSha256' if name=='Sha256' else name]
capacity['DeltaUsedStandardBlocks']=capacity['UsedStandardBlocks']-prior['UsedStandardBlocks']
with (W/'capacity_review.json').open('x') as f:json.dump(capacity,f,indent=2)
compare=json.loads((W/'prepared_readback_01.log').read_text())
assert compare['Equivalent']
with (W/'canonical_prepared_compare.json').open('x') as f:json.dump(compare,f,indent=2)
forecast=json.loads((W/'capacity_forecast_01.json').read_text())
print(json.dumps(dict(passed=True,usedBlocks=capacity['UsedStandardBlocks'],availableBlocks=capacity['AvailableBlocks'],
    totalBlocks=capacity['TotalBlocks'],deltaBlocks=capacity['DeltaUsedStandardBlocks'],
    advisoryForecastFits=forecast['planningFits'],advisoryForecastErrorBlocks=forecast['estimatedUsedBlocks']-capacity['UsedStandardBlocks'])))

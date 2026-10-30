"""Require the authorization record to derive from the exact measured image."""
FIELDS=('UsedStandardBlocks','AvailableBlocks','TotalBlocks','DisplayedUsagePercent')
def validate(template,measurement,canonical):
    if measurement['CanonicalSha256']!=canonical or measurement['Provider']!='StudioUIAutomation' \
       or measurement['CapacityUnit']!='Blocks' \
       or any(measurement[k] is not True for k in ('VerifiedFit','Measured','Offline','SourceUnchanged')):
        raise ValueError('pinned automatic Capacity measurement required')
    actual=template['OwnerCapacityConfirmed']
    if any(type(actual.get(k)) is not int or actual[k]!=measurement[k] for k in FIELDS):
        raise ValueError('Capacity confirmation differs from measured image')
    used,available,total,percent=(actual[k] for k in FIELDS)
    if used<0 or available<0 or total<=0 or used+available!=total or 100*used//total!=percent:
        raise ValueError('Capacity arithmetic differs')
    return True

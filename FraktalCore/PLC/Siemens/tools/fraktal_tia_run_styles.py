"""Generated per-mode capability table; pacing is owned by the shared Unit."""
from fraktal_tia_binding import READONLY


def declarations(catalog):return ['    RunStyle'+READONLY+' : DInt;',
    '    SupportedRunStylesPublished'+READONLY+' : Array[0..%d] of Bool;'%max(catalog.enums['E_RunStyle'].values())]


def frame(t,catalog):
    styles=catalog.enums['E_RunStyle'];modes=catalog.enums['E_Mode'];table=dict(t.run_styles)
    body=[]
    for style,number in styles.items():
        choices=[mode for mode,values in table.items() if style in values]
        expression='TRUE' if style=='CONTINUOUS' else ' OR '.join('#Unit.Mode = %d'%modes[mode] for mode in choices) or 'FALSE'
        body+=['    #SupportedRunStylesPublished[%d] := '%number+expression+';']
    return body+['    "FRK_RunStylePrepare"(Owner := #Core.RegIndex, Startup := #Startup OR #Core.EvModeChanged OR #Unit.EvReset, Exec := #Core.Exec, Access := #Access, Supported := #SupportedRunStylesPublished);',
        '    "FRK_RunStyleRequest"(Owner := #Core.RegIndex, Scope := #Status.Name, Exec := #Core.Exec, Supported := #SupportedRunStylesPublished, Unit := #Unit, Access := #Access, Response := #HmiResponse);']


def mirror():return ['    IF #Core.RegIndex > 0 THEN #RunStyle := "FRK_Registry".Rows[#Core.RegIndex].RunStyle; END_IF;']

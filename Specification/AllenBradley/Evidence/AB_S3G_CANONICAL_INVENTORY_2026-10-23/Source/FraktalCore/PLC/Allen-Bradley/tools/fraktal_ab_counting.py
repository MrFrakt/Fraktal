"""Own the legacy mark-based loop verdict when traceability is off.

A loop which declares both scrap and finish-good marks needs a per-visit
verdict: a rejected part cannot become good at the shared safe-return finish.
The generator derives the owner from consumed marks. Projects add no reset or
wiring call. Carrier-enabled applications use the carrier's commit owner.
"""
import fraktal_ab_declaration as decl

GOOD = 'Ctx.GoodCount := Ctx.GoodCount + 1'
NOK = 'Ctx.ScrapCount := Ctx.ScrapCount + 1'
FINISH = 'Ctx.CycleCount := Ctx.CycleCount + 1'


def chains(app):
    return tuple(c for c in app.chains if c.loops and
                 any(NOK in s.marks for s in c.steps) and
                 any(GOOD in s.marks and FINISH in s.marks for s in c.steps))


def enabled(app):
    return bool(chains(app))


def tracks(app, step):
    return any(step in c.steps for c in chains(app))


def type_name():
    return 'FRK_T_CycleVerdictV1'


def members():
    return (decl.scalar('SchemaVersion', initial=1), decl.boolean('Nok'))


def tag(app):
    return f'FRK_{app.name}_CycleVerdict'


def reference(names):
    return 'CycleVerdict' if names.in_aoi else tag(names.app)


def st_mark(mark, names):
    verdict, unit = reference(names), names.unit
    if mark == GOOD:
        return [f'IF {verdict}.Nok = 0 THEN {unit}.GoodCount := {unit}.GoodCount + 1; END_IF;']
    if mark == NOK:
        return [f'{unit}.ScrapCount := {unit}.ScrapCount + 1;', f'{verdict}.Nok := 1;']
    return None


def ld_mark(mark, names):
    verdict, unit = reference(names), names.unit
    if mark == GOOD:
        # Both paths preserve rung power: suppressing a good count must never
        # suppress the following finish/advance/start-latch release.
        return [f'[EQU({verdict}.Nok,0)ADD({unit}.GoodCount,1,{unit}.GoodCount),NEQ({verdict}.Nok,0)]']
    if mark == NOK:
        return [f'ADD({unit}.ScrapCount,1,{unit}.ScrapCount)', f'MOV(1,{verdict}.Nok)']
    return None


def reset():
    return ['IF (Ctx.ModeRequest <> Ctx.Mode) OR (Ctx.ResetRequest <> 0) OR (Ctx.AbortRequest <> 0) THEN',
            'CycleVerdict.Nok := 0;', 'END_IF;']

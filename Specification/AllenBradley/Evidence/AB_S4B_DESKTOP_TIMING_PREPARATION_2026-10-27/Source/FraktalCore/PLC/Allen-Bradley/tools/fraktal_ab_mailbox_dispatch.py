"""R4: one bounded manual dispatcher, with declaration-owned routing tables.

Only generated wiring touches module contexts. No project call is added and
manual acceptance keeps its existing mode/catalog/Busy predicate. A missing
directional permit is reported; the device still owns HELD behavior.
"""
from dataclasses import replace
import fraktal_ab_declaration as decl

MODULE='FRK_T_MailRouteModuleV1'
COMMAND='FRK_T_MailRouteCommandV1'
WORK='FRK_T_MailRouteWorkV1'


def enabled(app):return app.canonical_publication_stage>=13
def modules_tag(app):return f'FRK_{app.name}_MailRouteModules'
def commands_tag(app):return f'FRK_{app.name}_MailRouteCommands'
def work_tag(app):return f'FRK_{app.name}_MailRouteWork'
def find_routine(app):return f'FRK_{app.name}_MailRouteFind'
def cache_routine(app):return f'FRK_{app.name}_MailRouteCache'


def module_members():
    return tuple(decl.scalar(n) for n in ('FirstSlot','CommandCount','Busy','Requested','Pending'))


def command_members():
    return tuple(decl.scalar(n) for n in ('Value','Permitted','PermitKey'))


def work_members():
    return tuple(decl.scalar(n,initial=-1 if n in ('ModuleIndex','CommandIndex') else 0)
                 for n in ('ModuleIndex','CommandIndex','FirstSlot','EndSlot','Cursor','CommandCount'))


def rows(app):
    modules=[];commands=[]
    for module in app.modules:
        modules.append(dict(FirstSlot=len(commands),CommandCount=len(module.commands),Busy=0,Requested=0,Pending=0))
        commands.extend(dict(Value=c.ordinal,Permitted=1,PermitKey=0) for c in module.commands)
    return modules,commands


def records(app):
    if not enabled(app):return []
    return [decl.Record(MODULE,module_members()),decl.Record(COMMAND,command_members()),decl.Record(WORK,work_members())]


def tags(app):
    if not enabled(app):return []
    import fraktal_ab_generate as gen
    modules,commands=rows(app)
    def elements(members,values):
        return [tuple(replace(m,initial=row[m.name]) for m in members) for row in values]
    return [gen._structure_tag(work_tag(app),WORK,work_members(),'None'),
            *([gen._structure_array_tag(modules_tag(app),MODULE,elements(module_members(),modules),'None')] if modules else []),
            *([gen._structure_array_tag(commands_tag(app),COMMAND,elements(command_members(),commands),'None')] if commands else [])]


def cache(app):
    if not enabled(app):return []
    import fraktal_ab_generate as gen
    import fraktal_ab_manifest as manifest
    modules,commands=rows(app);lines=[];slot=0
    for i,module in enumerate(app.modules):
        lines.append(f'{modules_tag(app)}[{i}].Busy := {gen.ctx_tag_for(app,module.name)}.Busy;')
        for command in module.commands:
            row=f'{commands_tag(app)}[{slot}]'
            lines += [f'{row}.Permitted := 1;',f'{row}.PermitKey := 0;']
            lines += gen.permit_chain(app,replace(module,commands=(command,)),str(command.ordinal),
                lambda p,row=row:[f'{row}.Permitted := 0;',f'{row}.PermitKey := {manifest.numeric_key(app,p.key)};'],[])
            slot+=1
    return lines


def apply(app,module):
    if not enabled(app) or not module.commands:return []
    import fraktal_ab_generate as gen
    i=app.modules.index(module);row=f'{modules_tag(app)}[{i}]';ctx=gen.ctx_tag_for(app,module.name)
    return [f'IF {row}.Pending <> 0 THEN',f'{ctx}.Execute := 0;',
            f'{ctx}.ManualCmd := {row}.Requested;',f'{row}.Pending := 0;','END_IF;']


def find(app):
    import fraktal_ab_mailbox as mb
    modules,commands=rows(app);w=work_tag(app);m=modules_tag(app);c=commands_tag(app)
    target=mb._request(app,mb.MANUAL_TARGET_MEMBER);value=mb._request(app,'IntValue')
    lines=[f'{w}.ModuleIndex := -1;',f'{w}.CommandIndex := -1;']
    if not modules or not commands:return lines
    candidate=f'{w}.ModuleIndex'
    return lines+[f'IF ({target} >= 1) AND ({target} <= {len(modules)}) THEN',
        f'{candidate} := {target} - 1;',f'{w}.FirstSlot := {m}[{candidate}].FirstSlot;',
        f'{w}.CommandCount := {m}[{candidate}].CommandCount;',
        f'IF ({w}.FirstSlot < 0) OR ({w}.FirstSlot > {len(commands)}) THEN',f'{candidate} := -1;',
        f'ELSIF ({w}.CommandCount <= 0) OR ({w}.CommandCount > {len(commands)} - {w}.FirstSlot) THEN',
        f'{candidate} := -1;','ELSE',f'{w}.EndSlot := {w}.FirstSlot + {w}.CommandCount - 1;',
        f'FOR {w}.Cursor := {w}.FirstSlot TO {w}.EndSlot DO',
        f'IF {c}[{w}.Cursor].Value = {value} THEN',f'{w}.CommandIndex := {w}.Cursor;',
        'END_IF;','END_FOR;','END_IF;','END_IF;']


def manual_dispatch(app):
    import fraktal_ab_mailbox as mb
    lines=[f'{mb.MANUAL_COMMAND}: (* MANUAL_COMMAND *)']
    if app.manual_mode is None or not any(m.commands for m in app.modules):
        return lines+mb._refuse(app,mb.MANUAL_MODE_REQUIRED_KEY)
    w=work_tag(app);selected=f'{w}.ModuleIndex';row=f'{modules_tag(app)}[{selected}]'
    return lines+[f'IF FRK_{app.name}_Unit.Mode <> {app.manual_mode} THEN',
        *mb._refuse(app,mb.MANUAL_MODE_REQUIRED_KEY),'ELSE',f'JSR({find_routine(app)},0);',
        f'IF {selected} < 0 THEN',*mb._refuse(app,mb.TARGET_KEY),
        f'ELSIF {w}.CommandIndex < 0 THEN',*mb._refuse(app,mb.MANUAL_COMMAND_UNKNOWN_KEY),
        f'ELSIF {row}.Busy <> 0 THEN',*mb._refuse(app,mb.MANUAL_BUSY_KEY),'ELSE',
        *mb._accept(app,f'{row}.Requested := {mb._request(app,"IntValue")};',f'{row}.Pending := 1;'),
        'END_IF;','END_IF;']


def manual_report(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    report=gen.release_report_tag(app);w=work_tag(app);selected=f'{w}.ModuleIndex'
    row=f'{modules_tag(app)}[{selected}]';command=f'{commands_tag(app)}[{w}.CommandIndex]'
    unsupported=app.reasons.get('UNSUPPORTED_COMMAND',0);held=app.reasons.get('INTERLOCK_DROPPED',0)
    def add(key,reason,source,kind):return gen.report_add(report,mb._key(app,key),reason,source,kind,key,app=app)
    lines=gen.report_open(report,app=app)
    if app.access_users is not None:
        import fraktal_ab_access as access
        lines+=access.report(app,report,'2')
    if app.manual_mode is not None:
        lines += [f'IF FRK_{app.name}_Unit.Mode <> {app.manual_mode} THEN',
            *add(mb.MANUAL_MODE_REQUIRED_KEY,0,0,'MODE'),'END_IF;']
    if not any(m.commands for m in app.modules):
        return lines+add(mb.TARGET_KEY,unsupported,0,'OTHER')+gen.report_close(report,app=app)
    return lines+[f'JSR({find_routine(app)},0);',f'IF {selected} < 0 THEN',
        *add(mb.TARGET_KEY,unsupported,0,'OTHER'),f'ELSIF {w}.CommandIndex < 0 THEN',
        *add(mb.MANUAL_COMMAND_UNKNOWN_KEY,unsupported,f'{selected} + 1','INTERLOCK'),'ELSE',
        f'IF {row}.Busy <> 0 THEN',*add(mb.MANUAL_BUSY_KEY,0,f'{selected} + 1','OTHER'),'END_IF;',
        f'IF {command}.Permitted = 0 THEN',
        *gen.report_add(report,f'{command}.PermitKey',held,f'{selected} + 1','INTERLOCK',app=app),
        'END_IF;','END_IF;',*gen.report_close(report,app=app)]


def routines(app):return [(cache_routine(app),cache(app)),(find_routine(app),find(app))] if enabled(app) else []

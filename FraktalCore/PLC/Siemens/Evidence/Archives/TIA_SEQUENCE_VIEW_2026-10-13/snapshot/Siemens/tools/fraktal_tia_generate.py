"""Generate reference-1500 contract frames, typed HAL calls and registry setup.

The shared-runtime option includes the owning command kernel. Structural-only
tests use separately located boundary probes and do not claim runtime behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from fraktal_tia_binding import Catalog, PRIVATE, READONLY, REPO, literal, type_source
import fraktal_tia_declaration as DECL

HERE = Path(__file__).resolve().parent
VERSION = "0.16"
KIND = "fraktal.tia.generated.frames.v1"
ROLES = ("ParCfg", "ParCmd", "OutCmd", "OutImm")
RESERVED_BLOCKS = {"frk_core", "frk_registry", "frk_registryrow", "frk_setidentity",
                   "frk_syncregistry", "frk_begin", "frk_end", "fb_fraktalmain",
                   "gdb_fraktalmain", "gdb_fraktalhal", "st_fraktalhal", "main",
                   "frk_clock", "frk_clocktick", "frk_elapsed", "frk_cleardiag",
                   "frk_rationalize", "frk_diagnostic", "frk_fault", "frk_adoptfault",
                   "frk_hold", "frk_holddiag", "frk_pending", "frk_complete",
                   "frk_start", "frk_routeabort", "frk_recordtiming"}
RESERVED_BLOCKS |= {'frk_unit', 'frk_access', 'frk_carrier', 'frk_carriers', 'frk_releasecommand',
                    'frk_unitprepare', 'frk_unitoperation', 'frk_unitmailbox', 'frk_unitconsume',
                    'frk_unitmode', 'frk_unitmoderesolve', 'frk_unitfinish', 'frk_descendantsready',
                    'frk_partreceived', 'frk_partstarted', 'frk_partprocessed', 'frk_partaborted', 'frk_partevent'}
RESERVED_BLOCKS |= {'frk_unitscratch','frk_manualconditionrow','frk_historyevent','frk_pathowned',
                    'frk_unitrelease','frk_manualcommon','frk_manualcondition','frk_manualapply',
                    'frk_manualfinish','frk_unitcascade','frk_unitfollow'}
RESERVED_BLOCKS |= {'frk_configcursor','frk_configbegin','frk_configappend','frk_configfinish',
                    'frk_configrevision','frk_configcatalog','frk_configunit'}
RESERVED_BLOCKS |= {'frk_localusers','frk_sha256pin','frk_accessnext','frk_accesslogin',
                    'frk_accesslogout','frk_accessdropsession','frk_accesscancel','frk_accessaudit','frk_accesscyclic','frk_accessfinish'}
RESERVED_BLOCKS |= {'frk_alarmlog','frk_alarmnotify','frk_alarmrefresh','frk_alarmbegin',
                    'frk_alarmraise','frk_alarmclose','frk_alarmgone','frk_alarmoperatorreset',
                    'frk_alarmmessage','frk_alarmcapture','frk_alarmend','frk_alarmtreeblocking',
                    'frk_state','frk_statesweep'}


def definition(model):
    return {"schema_version": 1, "target_family": "S7-1500",
            "registry_capacity": model.registry_capacity,
            "records": dict(model.records),
            "types": [{"name": t.name, "tier": t.tier, "type_key": t.type_key,
                       "children": [{"name": c.name, "type": c.type_name} for c in t.children],
                       "contract": dict(t.contract), "hal": t.hal, "capabilities": t.capabilities,
                       "logic": dict(t.logic), "commands": [{"id": i, "label": label} for i, label in t.commands],
                       "timeout": t.timeout, "storage": t.storage,
                       **({'station_config': t.station_config} if t.station_config else {}),
                       **({'config': list(t.config)} if t.config else {}),
                       **({'sequence_view': dict(zip(('capacity', 'branches', 'annotations'), t.sequence_view))} if t.sequence_view else {}),
                       **({'unit': {'modes': list(t.unit_modes), 'initial': t.unit_initial, 'run_command': t.unit_run}} if t.unit_modes else {})} for t in model.types],
            "roots": [{"name": r.name, "type": r.type_name} for r in model.roots],
            **({'event_sink':model.event_sink} if model.event_sink else {}),
            **({'model_config': {'models': list(model.model_config), 'initial': model.initial_model}} if model.model_config else {}),
            **({'config_sets': {'capacity': model.config_set_capacity}} if model.config_set_capacity else {}),
            **({'alarm_history': {'scopes': list(model.alarm_history_scopes)}} if model.alarm_history_scopes else {}),
            **({'alarm_recovery': {'scopes': list(model.alarm_recovery_scopes)}} if model.alarm_recovery_scopes else {}),
            **({'alarm_delivery': {'scopes':list(model.alarm_delivery_scopes),'capacity':model.alarm_delivery_capacity,'stream_id':model.alarm_delivery_stream}} if model.alarm_delivery_scopes else {}),
            **({'persistence': {'medium':'LOAD_DB','minimum_write_ms':model.persistence_min_write_ms,'queue_capacity':model.persistence_queue_capacity}} if model.persistence_min_write_ms else {})}


def state_calls(body, catalog):
    """Validate unconditional state declarations and inject frame-owned context."""
    from tia_lint import strip_comments
    code = strip_comments(body)
    masked = re.sub(r"'(?:\$.|[^'])*'",lambda m:' '*len(m[0]),code)
    matches = list(re.finditer(r'"FRK_State"\s*\(',masked,re.I))
    indexes = set()
    inserts = []
    for call in matches:
        depth = 0
        for token in re.findall(r'\b(?:END_IF|END_CASE|END_FOR|END_WHILE|END_REPEAT|IF|CASE|FOR|WHILE|REPEAT)\b',masked[:call.start()],re.I):
            depth += -1 if token.upper().startswith('END_') else 1
        if depth:
            raise DECL.DeclarationError('T-CORE','state','derived flags must be published unconditionally')
        pos=call.end(); nesting=1
        while pos<len(masked) and nesting:
            if masked[pos]=='(':nesting+=1
            elif masked[pos]==')':nesting-=1
            pos+=1
        if nesting:raise DECL.DeclarationError('T-GEN','state','unclosed state call')
        args=body[call.end():pos-1]
        idx=re.search(r'\bIdx\s*:=\s*(\d+)\s*(?=,|$)',args,re.I)
        key=re.search(r"\bKey\s*:=\s*'((?:\$.|[^'])*)'",args,re.I)
        if not idx or not key or {n.upper() for n in re.findall(r'(\w+)\s*:=',masked[call.end():pos-1])} != {'IDX','KEY','OK'}:
            raise DECL.DeclarationError('T-GEN','state','state takes literal Idx/Key and an Ok expression')
        width=int(re.search(r'\[(\d+)\]',next(f['native_type'] for f in catalog.resolve(['ST_StateFlag'])['ST_StateFlag'] if f['member']=='Key'))[1])
        index=int(idx[1])
        if index in indexes or not 1<=index<=catalog.capacities['MAX_STATE_FLAGS'] or not 1<=len(key[1])<=width:
            raise DECL.DeclarationError('T-WIDTH','state','duplicate/out-of-range state index or key width')
        indexes.add(index)
        inserts.append((pos-1,', Flags := #StateFlags, Count := #StateFlagCount, Touched := #StateTouched'))
    for pos,text in reversed(inserts):body=body[:pos]+text+body[pos:]
    return body,bool(matches)


def build(model, shared_runtime=False):
    catalog = Catalog.read(model.records)
    config_runtime = bool(model.config_set_capacity or model.model_config or any(t.config or t.station_config for t in model.types))
    config = None
    if config_runtime:
        from fraktal_tia_config import Layout
        config = Layout(model, catalog)
    unit_runtime = shared_runtime and any(t.unit_modes for t in model.types)
    states = any(state_calls(dict(t.logic).get('cyclic',''),catalog)[1] for t in model.types)
    if (states or model.event_sink) and not shared_runtime:
        raise DECL.DeclarationError('T-GEN','runtime','state and event services require the shared runtime')
    if model.alarm_history_scopes and (not shared_runtime or not unit_runtime):
        raise DECL.DeclarationError('T-GEN','alarm_history','retained history needs the shared Unit runtime')
    if model.event_sink and not unit_runtime:
        raise DECL.DeclarationError('T-GEN','event_sink','event sink needs a Unit runtime')
    lookup = {t.name.casefold(): t for t in model.types}
    ordered = []

    def order(name):
        t = lookup[name.casefold()]
        if t in ordered:
            return
        for child in t.children:
            order(child.type_name)
        ordered.append(t)

    for root in model.roots:
        order(root.type_name)
    requests = ["ST_ModuleStatus", "ST_ModuleTiming"]
    hal_names = {}
    for t in ordered:
        if unit_runtime and t.tier == 'UNIT' and not t.unit_modes:
            raise DECL.DeclarationError('T-GEN', t.name, 'every Unit in a Unit runtime forest requires a mode profile')
        from tia_lint import LIFECYCLE, strip_comments
        for region, body in t.logic:
            code = strip_comments(body)
            if region == 'Release':
                calls = re.findall(r'"(FRK_\w+)"\s*\(',code)
                names = re.findall(r'#(\w+)',code)
                if calls != ['FRK_UnitSetPermit'] or any(n not in ('Unit','Hal') for n in names) or re.search(r'#\w+(?:\.\w+)*\s*:=|\b(IF|CASE|FOR|WHILE)\b',code,re.I):
                    raise DECL.DeclarationError('T-CORE',t.name,'Unit release is one pure HAL predicate, shared by cyclic management and queries')
            elif '"FRK_UnitSetPermit"' in code:
                raise DECL.DeclarationError('T-CORE',t.name,'Unit common release belongs to the pure Release region')
            if region == 'ManRelease':
                calls = re.findall(r'"(FRK_\w+)"\s*\(', code)
                if not unit_runtime or any(n != 'FRK_ManualCondition' for n in calls) or re.search(r'#\w+(?:\.\w+)*\s*:=|\b(IF|CASE|FOR|WHILE)\b', code, re.I):
                    raise DECL.DeclarationError('T-CORE', t.name, 'manual release declares unconditional conditions only')
                slots=[int(n) for n in re.findall(r'\bSlot\s*:=\s*(\d+)\s*[,)]',code,re.I)]
                values=[int(n) for n in re.findall(r'\bValue\s*:=\s*(\d+)\s*[,)]',code,re.I)]
                if len(slots) != len(calls) or len(set(slots)) != len(slots) or any(n < 1 or n > catalog.capacities['MAX_PERMINTLK_COND'] for n in slots) or len(values) != len(calls) or any(n not in {0,*(c for c,label in t.commands)} for n in values):
                    raise DECL.DeclarationError('T-GEN', t.name, 'manual conditions need unique bounded literal slots and declared command values')
            if re.search(r"%[IQM]\b|%[IQM][BWD]?\d", code, re.I):
                raise DECL.DeclarationError("T-IO", t.name, "module logic cannot access raw mapped I/O")
            if re.search(r"\bRETURN\b", code, re.I) or re.search(r"//\s*----", body):
                raise DECL.DeclarationError("T-GEN", t.name, "authored region cannot bypass the generated frame")
            if re.search(r'"FRK_(Begin|End|RouteAbort|Start|ClockTick|SyncRegistry|SetIdentity|RecordTiming|UnitPrepare|UnitMailbox|UnitConsume|UnitMode|UnitModeResolve|UnitFinish|UnitRunStart)"\s*\(', code, re.I):
                raise DECL.DeclarationError("T-CORE", t.name, "authored region cannot invoke lifecycle assembly functions")
            if re.search(r'#LatchedParCmd(?:\.\w+)?\s*:=', code, re.I):
                raise DECL.DeclarationError("T-CORE", t.name, "authored region cannot write accepted command parameters")
            for reference in re.finditer(r'#(?:OutImm|OutCmd|Busy|Done|Error|Aborted|Held|ErrorID|Timing)\b(?:\.\w+|\[[^\]]+\])*', code, re.I):
                if not re.match(r'\s*:=', code[reference.end():]) and not re.search(r'=>\s*$', code[:reference.start()]):
                    raise DECL.DeclarationError('T-GEN', t.name, 'own output read is not warning-clean; use private device storage')
            writes = re.findall(r"#Core\.(\w+)\s*:=", code, re.I)
            if (any(name.casefold() in LIFECYCLE | {'timeoutms'} for name in writes)
                    or re.search(r"#Core\s*:=|#\w+(?:\.\w+)*\.Core(?:\.\w+)?\s*:=", code, re.I)):
                raise DECL.DeclarationError("T-CORE", t.name, "authored region writes lifecycle storage")
            if re.search(r'#Unit(?:\.\w+)?\s*:=', code, re.I):
                raise DECL.DeclarationError('T-CORE', t.name, 'authored region writes Unit lifecycle storage')
            if re.search(r'#(?:ConfigRev|ConfigCursor|Catalog|CatalogCount)\b[^;]*:=|"FRK_Config\w*"\s*\(', code, re.I):
                raise DECL.DeclarationError('T-CORE', t.name, 'manifest revision, pager and catalog belong to the generated frame')
            if config_runtime and re.search(r'#(?:\w+\.)*(?:ParCfg|StationCfg|ConfigPersist|ModelId|ConfigStage\w*|ConfigDefault\w*|ConfigStaged|AvailableModelCount|AvailableModels|ConfigSets|ConfigSetCount|ConfigSetDocument|ConfigSetDocumentLine|ConfigSetDocumentLines)(?:\[[^\]]*\]|\.\w+)*\s*:=|"FRK_(?:Cfg|Set|Json)\w*"\s*\(|"FRK_(?:Config(?:Store|Scratch|Runtime)|Set(?:Store|Runtime))"', code, re.I):
                raise DECL.DeclarationError('T-CORE', t.name, 'editable config, staging and model identity belong to the owning handlers')
            if re.search(r'#Access\b[^;]*:=|"FRK_Access\w*"\s*\(|"FRK_(?:LocalUsers|AccessPolicies|AccessStorage)"', code, re.I):
                raise DECL.DeclarationError('T-CORE', t.name, 'access authority belongs to generated services and composition injection')
            if re.search(r'#(?:StateFlags|StateFlagCount|StateTouched)\b|"FRK_StateSweep"\s*\(',code,re.I) or (region!='cyclic' and '"FRK_State"' in code):
                raise DECL.DeclarationError('T-CORE',t.name,'state lifecycle is owned by the frame; publish from unconditional cyclic')
            if re.search(r'"FRK_Alarm(?:History|Recovery)\w*"|"FRK_(?:Delivery\w*|EventDelivery\w*)"',code,re.I):
                raise DECL.DeclarationError('T-CORE',t.name,'retained alarm history belongs to the owning frame')
            if re.search(r'#AlarmLog(?:\.\w+|\[[^\]]+\])*\s*:=|"FRK_Alarm(?:Begin|End|Close|Capture|Notify|Refresh|OperatorReset|TreeBlocking)"\s*\(',code,re.I):
                raise DECL.DeclarationError('T-CORE',t.name,'alarm assembly and reset belong to the owning frame')
            if re.search(r'#(?:SequenceSteps|SequenceStepDef|SequenceStepCount|SequenceAnnotations|SequenceAnnotationCount|ActiveSteps|CurrentStep\w*|SequenceView\w*)\b[^;]*:=|"FRK_View(?:Begin|End)"\s*\(',code,re.I):
                raise DECL.DeclarationError('T-CORE',t.name,'sequence view assembly belongs to the owning frame')
        if len(t.contract) != len(ROLES):
            raise DECL.DeclarationError("T-GEN", t.name, "source generation requires all four typed contract records")
        if t.name.casefold() in RESERVED_BLOCKS:
            raise DECL.DeclarationError("T-COLLIDE", t.name, "generated system block collision")
        requests.extend(dict(t.contract)[role] for role in ROLES)
        if t.storage:
            requests.append(t.storage)
        if t.station_config:
            requests.append(t.station_config)
        if t.unit_modes:
            requests.extend(('ST_HmiRequest', 'ST_HmiResponse', 'ST_ModePolicy', 'ST_AccessPolicy', 'ST_PartContext', 'ST_UserRecord', 'ST_AlarmEvent', 'ST_DecisionRequest'))
            if not shared_runtime:
                raise DECL.DeclarationError('T-GEN', t.name, 'Unit profile requires the shared runtime')
        if t.tier == "CONTROL_MODULE":
            if not t.hal:
                raise DECL.DeclarationError("T-IO", t.name, "CM source generation requires a leaf HAL record")
            hal_names[t.name] = t.hal
            requests.append(t.hal)
        else:
            if not t.children:
                raise DECL.DeclarationError("T-IO", t.name, "empty composite HAL is not implemented")
            name = "ST_" + t.name.removeprefix("FB_") + "Hal"
            if name.casefold() in {n.casefold() for n in catalog.records}:
                raise DECL.DeclarationError("T-COLLIDE", name, "derived HAL bundle collides with a declared record")
            hal_names[t.name] = name
            catalog.records[name] = [{"name": c.name, "type": hal_names[lookup[c.type_name.casefold()].name],
                                      "accessible": False} for c in t.children]
            requests.append(name)
        cfg = catalog.records.get(dict(t.contract)["ParCfg"], [])
        if not cfg or cfg[0]["name"] != "SchemaVersion" or cfg[0]["type"].split(":=")[0].strip().upper() != "UINT":
            raise DECL.DeclarationError("T-GEN", t.name, "ParCfg must start with SchemaVersion : UINT")
        if t.timeout and not any(f['name'] == t.timeout and f['type'].split(':=')[0].strip().upper() == 'TIME' for f in cfg):
            raise DECL.DeclarationError("T-GEN", t.name, "command timeout must name a TIME member of ParCfg")
    if "st_fraktalhal" in {n.casefold() for n in catalog.records}:
        raise DECL.DeclarationError("T-COLLIDE", "ST_FraktalHal", "composition HAL name is reserved")
    catalog.records["ST_FraktalHal"] = [{"name": r.name, "type": hal_names[lookup[r.type_name.casefold()].name],
                                         "accessible": False} for r in model.roots]
    requests.append("ST_FraktalHal")
    if unit_runtime:
        requests.append('ST_CommandInfo')
    if config_runtime:
        if not unit_runtime or not shared_runtime:
            raise DECL.DeclarationError('T-GEN', 'config', 'editable config requires the Unit shared runtime')
        requests.extend(('ST_ConfigRecord', 'ST_ConfigPersistStatus', 'ST_ModelId'))
        if model.persistence_min_write_ms: requests.append('ST_PersistResult')
        if model.config_set_capacity:
            requests.append('ST_ConfigSetInfo')
    if states:
        requests.append('ST_StateFlag')
    if any(t.sequence_view for t in ordered):
        requests.extend(('ST_SequenceStepDef', 'ST_SequenceStep', 'ST_SequenceCursor', 'ST_SequenceAnnotation', 'ST_StepRecord'))
    types = catalog.resolve(requests)
    unused = set(dict(model.records)) - set(types)
    if unused:
        raise DECL.DeclarationError("T-GEN", "records", "unconsumed application records: " + ", ".join(sorted(unused)))
    names = [*types, *(t.name for t in ordered), *(r.name for r in model.roots)]
    typed_services={route_name(t).casefold() for t in ordered} | {release_name(t).casefold() for t in ordered} | {config_name(t).casefold() for t in ordered}
    if unit_runtime and any(n.casefold() in typed_services for n in names):
        raise DECL.DeclarationError('T-COLLIDE','declaration','module or root collides with its generated typed service')
    if len({n.casefold() for n in names}) != len(names) or any(n.casefold() in RESERVED_BLOCKS for n in names if n != "ST_FraktalHal"):
        raise DECL.DeclarationError("T-COLLIDE", "declaration", "type/FB/DB or reserved block names collide")
    sources = {}
    for index, (name, fields) in enumerate(types.items()):
        sources["00_%03d_%s.udt" % (index, name)] = type_source(name, fields)
    row_fields = [("Valid", "Bool"), ("Parent", "DInt"), ("ModuleType", "DInt"),
                  ("TypeId", "DInt"), ("Capabilities", "DWord"), ("Exec", "DInt"),
                  ("ReasonCode", "DInt"), ("Severity", "DInt")]
    if unit_runtime:row_fields.append(('AlarmBlocking','Bool'))
    sources["01_FRK_RegistryRow.udt"] = type_source("FRK_RegistryRow", [
        {"member": n, "native_type": v, "accessible": False, "initial": ""} for n, v in row_fields])
    cap = model.registry_capacity
    sources["04_FRK_Registry.db"] = db("FRK_Registry", [
        'Count%s : DInt;' % PRIVATE, 'Fault%s : Bool;' % PRIVATE,
        'Rows%s : Array[0..%d] of "FRK_RegistryRow";' % (PRIVATE, cap)])
    template = HERE / "templates/registry.scl"
    sources["10_Registry.scl"] = template.read_text(encoding="ascii").replace("@CAPACITY@", str(cap)).replace("@NAME_WIDTH@", str(model.core.name_width))
    type_ids = {t.name: index for index, t in enumerate(model.types, 1)}
    if config:
        config.prepare(ordered)
    ready = catalog.enums["E_ExecState"]["READY"]
    for index, t in enumerate(ordered):
        text = frame(t, model, lookup, hal_names, type_ids[t.name], ready, catalog, unit_runtime, config)
        if unit_runtime:
            if len(t.commands) > catalog.capacities['MAX_CMD_CATALOG']:
                raise DECL.DeclarationError('T-WIDTH', t.name, 'command catalog exceeds Core capacity')
            text += route(t, lookup, hal_names, catalog)
            text += config.texts[t.name] if config else config_walk(t, lookup)
            text += alarm_walk(t, lookup)
        sources["20_%03d_%s.scl" % (index, t.name)] = text
    for root in model.roots:
        t = lookup[root.type_name.casefold()]
        sources["25_%s.db" % root.name] = '\n'.join(['DATA_BLOCK "' + root.name + '"',
            "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN', '"' + t.name + '"', 'BEGIN', 'END_DATA_BLOCK', ''])
    sources["25_GDB_FraktalHal.db"] = db("GDB_FraktalHal", ['Data%s : "ST_FraktalHal";' % PRIVATE])
    calls = ['    "%s"(ParentIndex := 0, Startup := #Startup, Hal := "GDB_FraktalHal".Data.%s);' % (r.name, r.name) for r in model.roots]
    if config:
        sources.update(config.sources())
        calls.insert(0, '    "FRK_ConfigBoot"(Startup := #Startup);')
        if config.sets:
            calls.insert(1, '    "FRK_SetBoot"(Startup := #Startup);')
    if unit_runtime:
        calls.insert(0, '    "FRK_AccessStoreBoot"(Startup := #Startup);')
        if model.alarm_recovery_scopes:calls.insert(0,'    "FRK_AlarmRecoveryPrepare"(Startup := #Startup);')
    sources["30_FB_FraktalMain.scl"] = '\n'.join(['FUNCTION_BLOCK "FB_FraktalMain"',
        "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'VAR_INPUT', '    Startup%s : Bool;' % PRIVATE,
        'END_VAR', 'BEGIN', '    IF #Startup THEN', '        "FRK_Registry".Count := 0;',
        '        "FRK_Registry".Fault := FALSE;', '    END_IF;', '    "FRK_ClockTick"();', *calls, 'END_FUNCTION_BLOCK', ''])
    sources["35_GDB_FraktalMain.db"] = '\n'.join(['DATA_BLOCK "GDB_FraktalMain"',
        "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN', '"FB_FraktalMain"', 'BEGIN', 'END_DATA_BLOCK', ''])
    sources["40_Main.scl"] = '\n'.join(['ORGANIZATION_BLOCK "Main"',
        "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'VAR_INPUT',
        '    Initial_Call : Bool;', '    Remanence : Bool;', 'END_VAR', 'BEGIN',
        '    "GDB_FraktalMain"(Startup := #Initial_Call);', 'END_ORGANIZATION_BLOCK', ''])
    runtime_metadata = None
    if shared_runtime:
        if any(not t.commands for t in model.types):
            raise DECL.DeclarationError('T-GEN', 'runtime', 'every runtime type requires declared commands and a ParCfg timeout')
        import fraktal_tia_runtime
        runtime_sources, runtime_metadata = fraktal_tia_runtime.build(unit_runtime,model.event_sink,states,bool(model.alarm_history_scopes),bool(model.alarm_recovery_scopes),bool(model.alarm_delivery_scopes))
        if config:
            from fraktal_tia_config import TEMPLATE as config_template
            runtime_metadata['authority_inputs'][config_template.relative_to(REPO).as_posix()] = hashlib.sha256(config_template.read_bytes()).hexdigest()
            if config.sets:
                from fraktal_tia_config_sets import TEMPLATE as set_template, LINE_AUTHORITY
                runtime_metadata['authority_inputs'][set_template.relative_to(REPO).as_posix()] = hashlib.sha256(set_template.read_bytes()).hexdigest()
                runtime_metadata['authority_inputs'][LINE_AUTHORITY.relative_to(REPO).as_posix()] = hashlib.sha256(LINE_AUTHORITY.read_bytes()).hexdigest()
        unit_instances = [i for i in model.inventory()['instances'] if i['path'] in model.alarm_history_scopes]
        history_cases = '\n'.join('    IF #Scope = '+literal(i['path'])+' THEN #FRK_AlarmHistoryIndex := '+str(slot)+'; RETURN; END_IF;' for slot,i in enumerate(unit_instances,1))
        recovery_instances = [i for i in model.inventory()['instances'] if i['path'] in model.alarm_recovery_scopes]
        recovery_cases = '\n'.join('    IF #Scope = '+literal(i['path'])+' THEN #FRK_AlarmRecoveryIndex := '+str(slot)+'; RETURN; END_IF;' for slot,i in enumerate(recovery_instances,1))
        recovery_owners = '\n'.join('        '+str(slot)+': #FRK_AlarmRecoveryScope := '+literal(i['path'])+';' for slot,i in enumerate(recovery_instances,1))
        delivery_instances=[i for i in model.inventory()['instances'] if i['path'] in model.alarm_delivery_scopes]
        delivery_cases='\n'.join('    IF #Scope = '+literal(i['path'])+' THEN #FRK_DeliveryIndex := '+str(slot)+'; RETURN; END_IF;' for slot,i in enumerate(delivery_instances,1))
        delivery_owners='\n'.join('        '+str(slot)+': #FRK_DeliveryScope := '+literal(i['path'])+';' for slot,i in enumerate(delivery_instances,1))
        delivery_roots=[r.name for r in model.roots if any(n.split('.')[0]==r.name for n in model.alarm_delivery_scopes)]
        delivery_root_cases='\n'.join('    IF #RootScope = '+literal(root)+' THEN #FRK_DeliveryRootIndex := '+str(slot)+'; RETURN; END_IF;' for slot,root in enumerate(delivery_roots,1))
        runtime_sources={n:body.replace('@DELIVERY_INDEX@',delivery_cases).replace('@DELIVERY_OWNERS@',delivery_owners).replace('@DELIVERY_COUNT@',str(len(delivery_instances))).replace('@DELIVERY_ROOT_COUNT@',str(len(delivery_roots))).replace('@DELIVERY_ROOT_INDEX@',delivery_root_cases).replace('@DELIVERY_CAPACITY@',str(model.alarm_delivery_capacity)).replace('@DELIVERY_STREAM@',model.alarm_delivery_stream) for n,body in runtime_sources.items()}
        runtime_sources = {n: body.replace('@RECOVERY_INDEX@', recovery_cases).replace('@RECOVERY_OWNERS@', recovery_owners).replace('@RECOVERY_COUNT@',str(len(model.alarm_recovery_scopes))).replace('@UNIT_INDEX@', history_cases).replace('@CAPACITY@', str(cap)).replace('@UNIT_COUNT@', str(len(model.alarm_history_scopes))).replace('@ROOT_COUNT@',str(len(model.roots))).replace('@NAME_WIDTH@',str(model.core.name_width)) for n,body in runtime_sources.items()}
        if set(runtime_sources) & set(sources):
            raise DECL.DeclarationError('T-COLLIDE', 'runtime', 'runtime source filename collision')
        sources.update(runtime_sources)
        if any(t.sequence_view for t in ordered):
            from fraktal_tia_sequence_view import build as view_build
            view_sources, view_inputs = view_build(model, catalog)
            sources.update(view_sources)
            runtime_metadata['authority_inputs'].update(view_inputs)
        if model.persistence_min_write_ms:
            from fraktal_tia_persistence import Medium, FACTS as persistence_facts
            medium=Medium(config)
            medium.adapt(sources)
            runtime_metadata['authority_inputs'].update(medium.inputs())
            runtime_metadata['persistence']={'medium':'LOAD_DB','header_bytes':persistence_facts['header_bytes'],'minimum_write_ms':model.persistence_min_write_ms,
                'documents':[{'index':d.index,'key':d.key,'root':d.root,'role':d.role,'capacity':d.capacity} for d in medium.documents]}
    # The same global namespace holds framework FCs/DBs and project roots.
    # Derive it from emitted declarations, so a new service cannot shadow a root.
    emitted = [n.casefold() for body in sources.values() for n in re.findall(
        r'^(?:TYPE|FUNCTION_BLOCK|FUNCTION|DATA_BLOCK|ORGANIZATION_BLOCK)\s+"([^"]+)"', body, re.M)]
    if len(emitted) != len(set(emitted)):
        duplicate = next(n for n in emitted if emitted.count(n) > 1)
        raise DECL.DeclarationError('T-COLLIDE', duplicate, 'project and framework global declarations collide')
    return sources, {"kind": KIND, "generator_version": VERSION, "declaration": definition(model),
                     "inventory": model.inventory(), "core_inputs": catalog.inputs,
                     "types": types, "type_ids": type_ids, "hal_types": hal_names,
                     "runtime_dependencies": ["FRK_Core", "FRK_Begin", "FRK_RouteAbort", "FRK_End", "FRK_ClockTick", "FRK_Start"] + ([model.event_sink] if model.event_sink else []),
                     "shared_runtime": shared_runtime, "runtime": runtime_metadata,
                     "template_sha256": hashlib.sha256(template.read_bytes()).hexdigest()}


def db(name, declarations):
    return '\n'.join(['DATA_BLOCK "' + name + '"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
                      'NON_RETAIN', 'VAR', *['    ' + d for d in declarations], 'END_VAR', 'BEGIN', 'END_DATA_BLOCK', ''])


def route_name(t):
    return 'FRK_Route_' + t.name.removeprefix('FB_')


def release_name(t):
    return 'FRK_Release_' + t.name.removeprefix('FB_')


def config_name(t):
    return 'FRK_Config_' + t.name.removeprefix('FB_')


def config_walk(t, lookup):
    """Typed ownership walk: the pager holds one window, never the whole tree."""
    lines = ['FUNCTION "'+config_name(t)+'" : Void', "{ S7_Optimized_Access := 'TRUE' }",
             'VERSION : 0.1', 'VAR_INPUT', '    ReadLevel : DInt;', '    Readable : Bool;',
             'END_VAR', 'VAR_IN_OUT', '    Module : "'+t.name+'";',
             '    Cursor : "FRK_ConfigCursor";', '    Page : "ST_ConfigPage";', 'END_VAR', 'BEGIN']
    service = 'FRK_ConfigUnit' if t.unit_modes else 'FRK_ConfigCatalog'
    facet = 'Policy := #Module.ModePolicy, ModelCount := 0' if t.unit_modes else 'Catalog := #Module.Catalog, Count := #Module.CatalogCount'
    lines += ['    "%s"(Scope := #Module.Status.Name, %s, ReadLevel := #ReadLevel, Readable := #Readable, Cursor := #Cursor, Page := #Page);' % (service, facet)]
    if t.sequence_view:
        lines += ['    "FRK_ViewManifest"(Scope := #Module.Status.Name, Defs := #Module.SequenceStepDef, Count := #Module.SequenceStepCount, ReadLevel := #ReadLevel, Readable := #Readable, Cursor := #Cursor, Page := #Page);']
    for child in t.children:
        lines += ['    "%s"(Module := #Module.%s, ReadLevel := #ReadLevel, Readable := #Readable, Cursor := #Cursor, Page := #Page);' % (config_name(lookup[child.type_name.casefold()]), child.name)]
    return '\n'.join([*lines, 'END_FUNCTION', ''])


def route(t, lookup, hals, catalog):
    lines=['FUNCTION "'+route_name(t)+'" : Bool', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
           'VAR_INPUT', '    Request : "ST_HmiRequest";', 'END_VAR', 'VAR_IN_OUT',
           '    Module : "'+t.name+'";', '    Hal : "'+hals[t.name]+'";',
           '    Report : "ST_ReleaseReport";', 'END_VAR', 'VAR_TEMP',
           '    RouteMatched : Bool;', '    Index : Int;', 'END_VAR', 'BEGIN',
           '    #'+route_name(t)+' := FALSE;',
           '    IF NOT "FRK_PathOwned"(OwnerPath := #Module.Status.Name, TargetPath := #Request.TargetPath) THEN RETURN; END_IF;']
    if t.unit_modes:
        if dict(t.logic).get('Release','').strip():
            lines += ['    "%s"(Unit := #Module.Unit, Hal := #Hal);' % release_name(t)]
        lines += ['    "FRK_ManualCommon"(Core := #Module.Core, Unit := #Module.Unit, Status := #Module.Status, Report := #Report);']
    lines += ['    IF #Request.TargetPath = STRING_TO_WSTRING(#Module.Status.Name) THEN']
    if not t.unit_modes:
        lines += ['        FOR #Index := 1 TO %d DO #Module.ManConditions[#Index].Used := FALSE; END_FOR;' % catalog.capacities['MAX_PERMINTLK_COND']]
        body=dict(t.logic).get('ManRelease','')
        # The owning reaction is written once; typed edges supply its module/HAL.
        body=re.sub(r'#(Core|Status|Device|ManConditions)\b',r'#Module.\1',body)
        if body.strip():lines += ['        // ---- AUTHORED: OnManRelease',body,'        // ---- GENERATED: manual release end']
        lines += ['        "FRK_ManualApply"(Core := #Module.Core, Status := #Module.Status, Request := #Request, Commands := #Module.Catalog, Count := #Module.CatalogCount, Conditions := #Module.ManConditions, Report := #Report, Execute := #Module.Execute, Command := #Module.Command, ManualOwned := #Module.ManualOwned);']
    else:
        lines += ['        "FRK_ReleaseReason"(Report := #Report, Description := WSTRING#\'std.error.unsupportedHmiRequest\', Reason := %d, Path := STRING_TO_WSTRING(#Module.Status.Name), Kind := %d);' % (catalog.enums['E_Reason']['UNSUPPORTED_COMMAND'],catalog.enums['E_ReleaseKind']['OTHER'])]
    lines += ['        #'+route_name(t)+' := TRUE;', '        RETURN;', '    END_IF;']
    for child in t.children:
        lines += ['    #RouteMatched := "%s"(Module := #Module.%s, Hal := #Hal.%s, Request := #Request, Report := #Report);' % (route_name(lookup[child.type_name.casefold()]),child.name,child.name),
                  '    #'+route_name(t)+' := #'+route_name(t)+' OR #RouteMatched;']
    return '\n'.join(lines+['END_FUNCTION',''])


def alarm_walk(t,lookup):
    if t.unit_modes:return ''
    lines=['FUNCTION "FRK_Capture_'+t.name.removeprefix('FB_')+'" : Void',
           "{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1','VAR_IN_OUT',
           '    Module : "'+t.name+'";','    AlarmLog : "FRK_AlarmLog";','END_VAR','BEGIN',
           '    "FRK_AlarmCapture"(AlarmLog := #AlarmLog, Core := #Module.Core, Status := #Module.Status);']
    for child in t.children:
        if not lookup[child.type_name.casefold()].unit_modes:
            lines+=['    "FRK_Capture_%s"(Module := #Module.%s, AlarmLog := #AlarmLog);'%(child.type_name.removeprefix('FB_'),child.name)]
    return '\n'.join(lines+['END_FUNCTION',''])


def frame(t, model, lookup, hals, type_id, ready, catalog, unit_runtime=False, config=None):
    contract, logic = dict(t.contract), dict(t.logic)
    derived,has_states=state_calls(logic.get('cyclic','// No cyclic extension declared.'),catalog)
    from tia_lint import strip_comments
    guarded = t.tier == 'CONTROL_MODULE' and not strip_comments(logic.get('Cyclic', '')).strip()
    inputs = ['Execute%s : Bool;' % READONLY, 'Abort%s : Bool;' % READONLY, 'Command%s : DInt;' % READONLY,
              'ParCfg%s : "%s";' % (READONLY, contract['ParCfg']), 'ParCmd%s : "%s";' % (READONLY, contract['ParCmd']),
              'ParentIndex%s : DInt;' % PRIVATE, 'Startup%s : Bool;' % PRIVATE]
    outputs = [n + READONLY + ' : ' + v + ';' for n, v in [('Busy','Bool'), ('Done','Bool'), ('Error','Bool'),
               ('Aborted','Bool'), ('Held','Bool'), ('ErrorID','DWord'), ('Timing','"ST_ModuleTiming"'),
               ('OutCmd','"' + contract['OutCmd'] + '"'), ('OutImm','"' + contract['OutImm'] + '"')]]
    owned_par_cfg = config and any(f.member.startswith('ParCfg.') for f in config.fields[t.name])
    if owned_par_cfg:
        inputs = [d for d in inputs if not d.startswith('ParCfg')]
    lines = ['// Generated frame v' + VERSION + '; change the declaration, then regenerate.',
             'FUNCTION_BLOCK "' + t.name + '"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
             'VAR_INPUT', *['    ' + x for x in inputs], 'END_VAR', 'VAR_OUTPUT', *['    ' + x for x in outputs],
             'END_VAR', 'VAR_IN_OUT', '    Hal : "%s";' % hals[t.name], 'END_VAR', 'VAR',
             '    Status%s : "ST_ModuleStatus";' % READONLY, '    Core%s : "FRK_Core";' % PRIVATE,
             *(['    ParCfg'+READONLY+' : "'+contract['ParCfg']+'";'] if owned_par_cfg else []),
             '    LatchedParCmd%s : "%s";' % (PRIVATE, contract['ParCmd']),
             *(['    StateFlags%s : Array[1..%d] of "ST_StateFlag";' % (READONLY,catalog.capacities['MAX_STATE_FLAGS']),
                '    StateFlagCount%s : Int;' % READONLY,
                '    StateTouched%s : Array[1..%d] of Bool;' % (PRIVATE,catalog.capacities['MAX_STATE_FLAGS'])] if has_states else []),
             *(['    Device%s : "%s";' % (PRIVATE, t.storage)] if t.storage else []),
             *(config.declarations(t) if config else []),
             *(__import__('fraktal_tia_sequence_view').declarations(t) if t.sequence_view else []),
             *(['    Catalog%s : Array[1..%d] of "ST_CommandInfo";' % (PRIVATE,catalog.capacities['MAX_CMD_CATALOG']),
                '    CatalogCount%s : Int;' % PRIVATE,
                '    ManConditions%s : Array[1..%d] of "FRK_ManualConditionRow";' % (PRIVATE,catalog.capacities['MAX_PERMINTLK_COND']),
                '    ManualOwned%s : Bool;' % PRIVATE] if unit_runtime and not t.unit_modes else []),
             *(['    Unit%s : "FRK_Unit";' % PRIVATE,
                '    HmiRequest : "ST_HmiRequest";',
                '    ModePolicy%s : Array[0..%d] of "ST_ModePolicy";' % (PRIVATE,len(catalog.enums['E_Mode'])-1),
                '    Access%s : "FRK_Access";' % READONLY,
                '    HmiResponse%s : "ST_HmiResponse";' % READONLY,
                '    ConfigRev%s : UDInt;' % READONLY,
                '    ConfigCursor%s : "FRK_ConfigCursor";' % PRIVATE,
                '    Part%s : "ST_PartContext";' % READONLY,
                '    Decision%s : "ST_DecisionRequest";' % READONLY,
                '    DecisionAnswer%s : Int;' % READONLY,
                '    History%s : Array[1..%d] of "ST_Diagnostic";' % (READONLY,catalog.capacities['MAX_DIAG_RING']),
                '    HistoryHead%s : Int;' % READONLY,
                '    AlarmLog%s : "FRK_AlarmLog";' % READONLY,
                '    ModeActivePublished%s : DInt;' % READONLY,
                '    RunningPublished%s : Bool;' % READONLY,
                '    StopPendingPublished%s : Bool;' % READONLY,
                '    SupportedModesPublished%s : Array[0..%d] of Bool;' % (READONLY,len(catalog.enums['E_Mode'])-1),
                *['    '+n+READONLY+' : UDInt;' for n in ('GoodCount','NokCount','ReworkCount')],
                '    NokReason%s : DInt;' % READONLY] if t.unit_modes else []),
             *['    %s%s : "%s";' % (c.name, READONLY, lookup[c.type_name.casefold()].name) for c in t.children],
             'END_VAR', 'VAR_TEMP', '    InstancePath : WString[254];',
             *(['    RouteMatched : Bool;', '    ManualMatched : Bool;'] if t.unit_modes else []),
             *(['    ConfigRootIndex : Int;'] if config and t.name in config.roots else []),
             'END_VAR', 'VAR CONSTANT',
             '    EXEC_READY : DInt := %d;' % ready,
             '    %s : DInt := %d;' % ('MODULE_CM' if guarded else 'MODULE_TIER', model.core.tiers[t.tier]),
             'END_VAR', 'BEGIN', '    // ---- GENERATED: setup', '    IF #Startup OR NOT #Core.Named THEN',
             '        #InstancePath := GetInstancePath(SIZE := 0);',
             '        "FRK_SetIdentity"(Core := #Core, Status := #Status, InstancePath := #InstancePath,',
             '            ModuleType := %d, TypeId := %d, Capabilities := DWORD#16#%08X, ParentIndex := #ParentIndex, TypeKey := %s);' %
             (model.core.tiers[t.tier], type_id, t.capabilities, literal(t.type_key))]
    if unit_runtime and not t.unit_modes:
        lines += ['        #CatalogCount := %d;' % len(t.commands)]
        for index,(command_id,label) in enumerate(t.commands,1):
            lines += ['        #Catalog[%d].Value := %d;' % (index,command_id),
                      '        #Catalog[%d].Label := %s;' % (index,literal(label)),
                      '        #Catalog[%d].Style := %d;' % (index,catalog.enums['E_CommandStyle']['ONESHOT'])]
    lines += ['    END_IF;']
    if config:
        from fraktal_tia_config import name as config_service
        if config.fields[t.name]:
            lines += ['    IF #Startup THEN '+config.call(t, 'Restore', '#')+'; END_IF;']
        if t.name in config.roots:
            lines += ['    #ConfigRootIndex := "FRK_ConfigRoot"(RegIndex := #Core.RegIndex);',
                      '    IF #Core.ParentIndex = 0 THEN #AvailableModelCount := %d; ELSE #AvailableModelCount := 0; END_IF;'%len(model.model_config)]
            for index, code in enumerate(model.model_config, 1):
                lines += ['    #AvailableModels[%d].ModelCode := %s;'%(index, literal(code))]
    if has_states:
        lines += ['    "FRK_StateSweep"(Flags := #StateFlags, Count := #StateFlagCount, Touched := #StateTouched, Startup := #Startup);']
    if guarded:
        from tia_lint import QUIET_RELEASE_GUARD
        lines.append('    IF ' + QUIET_RELEASE_GUARD + ' THEN')
    if t.unit_modes:
        lines += ['    IF #Startup OR #ConfigRev = 0 THEN #ConfigRev := "FRK_ConfigRevision"(Previous := #ConfigRev); END_IF;']
        for mode,ordinal in catalog.enums['E_Mode'].items():
            lines += ['    #SupportedModesPublished[%d] := %s;' % (ordinal,'TRUE' if mode in t.unit_modes else 'FALSE')]
        lines += ['    "FRK_UnitPrepare"(Core := #Core, Unit := #Unit, Policy := #ModePolicy, Request := #HmiRequest, Response := #HmiResponse, Startup := #Startup, InitialMode := %d);' % catalog.enums['E_Mode'][t.unit_initial],
                  '    "FRK_AlarmBegin"(AlarmLog := #AlarmLog, Startup := #Startup);',
                  *(['    "FRK_AlarmHistoryBoot"(AlarmLog := #AlarmLog, Startup := #Startup, Scope := #Status.Name);'] if model.alarm_history_scopes else []),
                  *(['    "FRK_DeliveryBoot"(AlarmLog := #AlarmLog, Startup := #Startup, Scope := #Status.Name);'] if model.alarm_delivery_scopes else []),
                  *(['    "FRK_AlarmRecoveryBoot"(AlarmLog := #AlarmLog, Startup := #Startup, Scope := #Status.Name);',
                     '    "FRK_AlarmRecoveryTick"(AlarmLog := #AlarmLog);'] if model.alarm_recovery_scopes else []),
                  *(['    "FRK_DeliveryStatus"(AlarmLog := #AlarmLog, Scope := #Status.Name);'] if model.alarm_delivery_scopes else []),
                  '    "FRK_AccessPolicyBoot"(Access := #Access, Startup := #Startup, Root := #Core.ParentIndex = 0, Scope := #Status.Name);',
                  '    "FRK_AccessCyclic"(Access := #Access, Startup := #Startup, SourcePath := STRING_TO_WSTRING(#Status.Name), AlarmLog := #AlarmLog, Revision := #ConfigRev);',
                  *(['    IF #Core.ParentIndex = 0 THEN "FRK_DeliveryMailbox"(RootScope := #Status.Name, Access := #Access, AlarmLog := #AlarmLog); END_IF;'] if model.alarm_delivery_scopes else []),
                  '    "FRK_UnitMailbox"(Core := #Core, Unit := #Unit, Status := #Status, Policy := #ModePolicy, Access := #Access, Request := #HmiRequest, Response := #HmiResponse, Supported := #SupportedModesPublished);']
        if config and t.name in config.roots:
            lines += ['    "FRK_ConfigStatus"(RootIndex := #ConfigRootIndex, Scope := #Status.Name, PolicyLost := #Access.PolicyLost, UsersLost := "FRK_AccessStorage".UsersLost, Persist := #ConfigPersist, AlarmLog := #AlarmLog);',
                      '    #Unit.ConfigEnabled := #Core.ParentIndex = 0;',
                      '    #Unit.ConfigSetsEnabled := '+('TRUE' if config.sets else 'FALSE')+' AND #Core.ParentIndex = 0;',
                      '    #Unit.ModelEnabled := #AvailableModelCount > 0;',
                      '    #Unit.ConfigBlocked := #ConfigPersist.RestoreLost AND NOT #ConfigPersist.RestoreAcknowledged AND #ConfigPersist.RestorePolicy = %d;'%catalog.enums['E_ConfigRestorePolicy']['BLOCK_UNTIL_ACKNOWLEDGED']]
    if t.unit_modes:
        block = '#Unit.ConfigBlocked OR #Access.PolicyLost' if config and t.name in config.roots else '#Access.PolicyLost'
        lines += ['    #Unit.ConfigBlocked := '+block+';']
    execute = '#Unit.RunReq' if t.unit_modes else '#Execute'
    abort = '(#Abort OR #Unit.AbortReq)' if t.unit_modes else '#Abort'
    command = str(t.unit_run) if t.unit_modes else '#Command'
    lines += ['    // ---- GENERATED: begin',
              '    "FRK_Begin"(Core := #Core, Status := #Status, Execute := %s, Abort := %s, Command := %s);' % (execute,abort,command)]
    from tia_lint import strip_comments
    def reaction(event):
        if strip_comments(logic.get(event, '')).strip():
            lines.extend(['    IF #Core.Ev' + event + ' THEN', '    // ---- AUTHORED: ' + event,
                          logic[event], '    // ---- GENERATED: reaction end', '    END_IF;'])
    reaction('Init')
    lines += ['    IF #Core.EvCommandStart THEN', '        #LatchedParCmd := #ParCmd;']
    if t.commands:
        lines += ['        CASE #Core.Command OF']
        for command, label in t.commands:
            if t.unit_modes:
                lines += ['            %d: "FRK_UnitRunStart"(Core := #Core, Status := #Status, Timeout := #ParCfg.%s, Label := %s);' % (command,t.timeout,literal(label))]
            else:
                lines += ['            %d: "FRK_Start"(Core := #Core, Status := #Status, Supported := TRUE, Timeout := #ParCfg.%s, Label := %s);' % (command, t.timeout, literal(label))]
        lines += ['            ELSE "FRK_Start"(Core := #Core, Status := #Status, Supported := FALSE, Timeout := T#0ms, Label := \'\');', '        END_CASE;']
    lines += ['    END_IF;']
    reaction('CommandStart')
    if strip_comments(logic.get('Cyclic', '')).strip():
        lines += ['    // ---- AUTHORED: cyclic management', logic['Cyclic'], '    // ---- GENERATED: end management']
    if t.unit_modes:
        if logic.get('Release','').strip():
            lines += ['    "%s"(Unit := #Unit, Hal := #Hal);' % release_name(t)]
        lines += ['    IF #Core.RegIndex > 0 THEN "FRK_Registry".Rows[#Core.RegIndex].AlarmBlocking := #AlarmLog.Blocking; END_IF;',
                  '    #Unit.AlarmBlocking := "FRK_AlarmTreeBlocking"(Owner := #Core.RegIndex)'+(' OR "FRK_AlarmRecoveryTreeBlocking"(Scope := #Status.Name)' if model.alarm_recovery_scopes else '')+';']
        lines += ['    "FRK_UnitConsume"(Core := #Core, Unit := #Unit, Status := #Status, Policy := #ModePolicy, Access := #Access, Response := #HmiResponse, Supported := #SupportedModesPublished);',
                  '    "FRK_UnitMode"(Core := #Core, Unit := #Unit);']
        reaction('ModeExit')
        lines += ['    "FRK_UnitModeResolve"(Core := #Core, Unit := #Unit, Status := #Status, Policy := #ModePolicy, Timeout := #ParCfg.%s);' % t.timeout]
        reaction('ModeChanged')
        if t.sequence_view:
            lines += [__import__('fraktal_tia_sequence_view').frame_call('Begin', t, model)]
        lines += ['    "FRK_DecisionCyclic"(Owner := #Core.RegIndex, Busy := #Core.Exec = %d, Reset := #Startup OR #Unit.EvReset OR #Core.EvModeChanged, AlarmLog := #AlarmLog);'%catalog.enums['E_ExecState']['BUSY']]
        lines += ['    "FRK_UnitFollow"(Core := #Core, Unit := #Unit, Status := #Status, Policy := #ModePolicy, Access := #Access, Supported := #SupportedModesPublished);']
        lines += ['    IF #Unit.RequestPending AND (#Unit.Request.Kind = %d OR #Unit.Request.Kind = %d) THEN' % (catalog.enums['E_HmiRequestKind']['MANUAL_COMMAND'],catalog.enums['E_HmiRequestKind']['RELEASE_MANUAL']),
                  '        #ManualMatched := FALSE;']
        for child in t.children:
            child_type=lookup[child.type_name.casefold()]
            lines += ['        #RouteMatched := "%s"(Module := #%s, Hal := #Hal.%s, Request := #Unit.Request, Report := #HmiResponse.Report);' % (route_name(child_type),child.name,child.name),
                      '        #ManualMatched := #ManualMatched OR #RouteMatched;']
        lines += ['        IF NOT #ManualMatched THEN',
                  '            "FRK_ReleaseReason"(Report := #HmiResponse.Report, Description := WSTRING#\'std.error.unsupportedHmiRequest\', Reason := %d, Path := #Unit.Request.TargetPath, Kind := %d);' % (catalog.enums['E_Reason']['UNSUPPORTED_COMMAND'],catalog.enums['E_ReleaseKind']['OTHER']),
                  '        END_IF;',
                  '        #HmiResponse.Accepted := #Unit.Request.Kind = %d OR #HmiResponse.Report.Released;' % catalog.enums['E_HmiRequestKind']['RELEASE_MANUAL'],
                  '        IF #Unit.Request.Kind = %d THEN' % catalog.enums['E_HmiRequestKind']['MANUAL_COMMAND'],
                  '            IF #HmiResponse.Accepted THEN #HmiResponse.Diagnostic := WSTRING#\'std.audit.manualCommandAccepted\'; ELSE #HmiResponse.Diagnostic := WSTRING#\'std.audit.manualCommandRejected\'; END_IF;',
                  '        END_IF;', '    END_IF;']
        lines += ['    IF #Unit.EvReset THEN "FRK_AlarmOperatorReset"(AlarmLog := #AlarmLog); END_IF;']
        if strip_comments(logic.get('OperatorReset','')).strip():
            lines += ['    IF #Unit.EvReset THEN','    // ---- AUTHORED: OperatorReset',logic['OperatorReset'],'    // ---- GENERATED: reset reaction end','    END_IF;']
    else:
        for event in ('ModeExit', 'ModeChanged'): reaction(event)
    if t.children:
        release = '#Core.ReleasePending' + (' OR #Unit.ReleaseChildren' if t.unit_modes else '')
        lines += ['    IF '+release+' THEN']
        for child in t.children:
            lines += ['        "FRK_ReleaseCommand"(Core := #%s.Core, Execute := #%s.Execute);' % (child.name,child.name)]
        lines += ['    END_IF;']
    for child in t.children:
        child_type=lookup[child.type_name.casefold()]
        if t.unit_modes and child_type.unit_modes:
            lines += ['    "FRK_UnitCascade"(ParentUnit := #Unit, Core := #%s.Core, Unit := #%s.Unit, Status := #%s.Status, Policy := #%s.ModePolicy, Access := #%s.Access, Supported := #%s.SupportedModesPublished, AlarmLog := #AlarmLog);' % ((child.name,)*6)]
        lines += ['    // ---- GENERATED: child call', '    #%s(ParentIndex := #Core.RegIndex, Startup := #Startup, Hal := #Hal.%s);' % (child.name, child.name)]
        if unit_runtime and not child_type.unit_modes:
            lines += ['    "FRK_ManualFinish"(Core := #%s.Core, Execute := #%s.Execute, ManualOwned := #%s.ManualOwned);' % ((child.name,)*3)]
    if t.unit_modes:
        lines += ['    #Unit.CascadePending := FALSE;']
        if config and t.name in config.roots:
            lines += ['    '+config.call(t, 'Operation', '#')+';']
            if config.sets:
                lines += ['    '+config.call(t, 'SetOperation', '#', Startup='#Startup')+';',
                          '    IF #Unit.RequestPending AND #Core.ParentIndex = 0 THEN "FRK_SetResult"(Request := #Unit.Request, Response := #HmiResponse, Persist := #ConfigPersist, AlarmLog := #AlarmLog, Scope := #Status.Name, RootIndex := #ConfigRootIndex); END_IF;']
            lines += ['    "FRK_ConfigStatus"(RootIndex := #ConfigRootIndex, Scope := #Status.Name, PolicyLost := #Access.PolicyLost, UsersLost := "FRK_AccessStorage".UsersLost, Persist := #ConfigPersist, AlarmLog := #AlarmLog);']
        else:
            lines += ['    IF #Unit.RequestPending AND #Unit.Request.Kind = %d THEN' % catalog.enums['E_HmiRequestKind']['QUERY_CONFIG'],
                  '        #HmiResponse.Accepted := FALSE;',
                  '        #HmiResponse.Report.Count := 0;', '        #HmiResponse.Report.Released := TRUE;',
                  '        #HmiResponse.Diagnostic := WSTRING#\'\';',
                  '        "FRK_ConfigBegin"(Cursor := #ConfigCursor, Page := #HmiResponse.ConfigPage, PageIndex := #Unit.Request.IntValue, Revision := #ConfigRev);',
                  '        IF #Unit.Request.DurationMs <> 0 THEN',
                  '            #HmiResponse.Diagnostic := WSTRING#\'std.error.modelNotAvailable\';',
                  '        ELSIF #Unit.Request.IntValue < 0 OR #Unit.Request.IntValue > 32767 THEN',
                  '            #HmiResponse.Diagnostic := WSTRING#\'std.error.hmiRequestRejected\';',
                  '        ELSE',
                  '            "FRK_ConfigUnit"(Scope := #Status.Name, Policy := #ModePolicy, ModelCount := 0, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #ConfigCursor, Page := #HmiResponse.ConfigPage);']
            for child in t.children:
                if config:
                    lines += ['            "%s"(Module := #%s, Access := #Access, RootIndex := "FRK_ConfigRoot"(RegIndex := #Core.RegIndex), ModelIndex := 0, Cursor := #ConfigCursor, Page := #HmiResponse.ConfigPage);' % (config_name(lookup[child.type_name.casefold()]), child.name)]
                else:
                    lines += ['            "%s"(Module := #%s, ReadLevel := #Access.Policy.Required[0], Readable := #Access.CurrentLevel >= #Access.Policy.Required[0], Cursor := #ConfigCursor, Page := #HmiResponse.ConfigPage);' % (config_name(lookup[child.type_name.casefold()]),child.name)]
            lines += ['            "FRK_ConfigFinish"(Cursor := #ConfigCursor, Page := #HmiResponse.ConfigPage);',
                      '            #HmiResponse.Accepted := TRUE;', '        END_IF;', '    END_IF;']
    lines += ['    "FRK_RouteAbort"(Core := #Core, Abort := %s);' % abort]
    reaction('Abort')
    reaction('AbortInError')
    if t.unit_modes:
        lines += ['    IF #Core.EvAbort THEN', '        "FRK_PartAborted"(Core := #Core, Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog);', '    END_IF;']
    if strip_comments(logic.get('Sequences', '')).strip():
        lines += ['    // ---- AUTHORED: unconditional sequence policy', logic['Sequences'],
                  '    // ---- GENERATED: sequence policy end']
    if strip_comments(logic.get('dispatch', '')).strip():
        lines += ['    IF #Core.Dispatch AND #Core.RegIndex > 0 AND NOT "FRK_Registry".Fault THEN',
                  '    // ---- AUTHORED: dispatch', logic['dispatch'],
                  '    // ---- GENERATED: end dispatch', '    END_IF;']
    lines += ['    "FRK_End"(Core := #Core, Status := #Status,',
              '        Busy => #Busy, Done => #Done, Error => #Error, Aborted => #Aborted, Held => #Held, ErrorID => #ErrorID, Timing => #Timing);']
    if t.unit_modes:
        lines += ['    "FRK_DecisionCyclic"(Owner := #Core.RegIndex, Busy := #Core.Exec = %d, Reset := #Startup OR #Unit.EvReset OR #Core.EvModeChanged, AlarmLog := #AlarmLog);'%catalog.enums['E_ExecState']['BUSY'],
                  '    "FRK_DecisionPublish"(Owner := #Core.RegIndex, Decision := #Decision, DecisionAnswer := #DecisionAnswer);']
        lines += ['    IF NOT #Unit.EvReset THEN',
                  '        "FRK_AlarmCapture"(AlarmLog := #AlarmLog, Core := #Core, Status := #Status);']
        for child in t.children:
            if not lookup[child.type_name.casefold()].unit_modes:
                lines += ['        "FRK_Capture_%s"(Module := #%s, AlarmLog := #AlarmLog);'%(child.type_name.removeprefix('FB_'),child.name)]
        lines += ['        "FRK_AlarmEnd"(AlarmLog := #AlarmLog);','    END_IF;',
                  '    IF #Core.RegIndex > 0 THEN "FRK_Registry".Rows[#Core.RegIndex].AlarmBlocking := #AlarmLog.Blocking; END_IF;',
                  '    #Unit.AlarmBlocking := "FRK_AlarmTreeBlocking"(Owner := #Core.RegIndex)'+(' OR "FRK_AlarmRecoveryTreeBlocking"(Scope := #Status.Name)' if model.alarm_recovery_scopes else '')+';']
        lines += ['    "FRK_AccessPersist"(Access := #Access, Unit := #Unit, Response := #HmiResponse, SourcePath := STRING_TO_WSTRING(#Status.Name), AlarmLog := #AlarmLog);']
        lines += ['    "FRK_AccessFinish"(Access := #Access, Unit := #Unit, Response := #HmiResponse, SourcePath := STRING_TO_WSTRING(#Status.Name), AlarmLog := #AlarmLog, Revision := #ConfigRev);',
                  '    "FRK_UnitFinish"(Core := #Core, Unit := #Unit, Response := #HmiResponse, Status := #Status, Part := #Part, AlarmLog := #AlarmLog, History := #History, Head := #HistoryHead);',
                  '    #ModeActivePublished := #Unit.Mode;','    #RunningPublished := #Core.Exec = %d;' % catalog.enums['E_ExecState']['BUSY'],
                  '    #StopPendingPublished := #Unit.StopReq AND #Core.Exec = %d;' % catalog.enums['E_ExecState']['BUSY'],
                  '    #GoodCount := #Unit.Good;','    #NokCount := #Unit.Nok;','    #ReworkCount := #Unit.Rework;','    #NokReason := #Unit.NokReason;']
    if guarded:
        lines.append('    END_IF;')
    if t.sequence_view:
        lines += [__import__('fraktal_tia_sequence_view').frame_call('End', t, model)]
    lines += ['    // ---- AUTHORED: unconditional cyclic/derived data', derived,
              '    // ---- GENERATED: frame end', 'END_FUNCTION_BLOCK', '']
    text='\n'.join(lines)
    if t.unit_modes and logic.get('Release','').strip():
        text='\n'.join(['FUNCTION "'+release_name(t)+'" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
            'VAR_IN_OUT', '    Unit : "FRK_Unit";', '    Hal : "'+hals[t.name]+'";', 'END_VAR', 'BEGIN',
            logic['Release'], 'END_FUNCTION',''])+text
    return text


def generate(model, directory, shared_runtime=False):
    sources, manifest = build(model, shared_runtime)
    directory.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items():
        (directory / name).write_bytes(text.encode('ascii'))
    manifest['generated'] = {name: hashlib.sha256(text.encode('ascii')).hexdigest() for name, text in sources.items()}
    (directory / 'manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('ascii'))
    return manifest


def verify(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='ascii'), object_pairs_hook=DECL.unique_json_object)
    if manifest.get('kind') != KIND:
        raise ValueError('not a generated frame manifest')
    sources, expected = build(DECL.validate(manifest['declaration']), manifest.get('shared_runtime', False))
    for field in ('core_inputs', 'inventory', 'types', 'type_ids', 'hal_types', 'template_sha256', 'generator_version', 'shared_runtime', 'runtime', 'runtime_dependencies'):
        if manifest.get(field) != expected[field]:
            raise DECL.DeclarationError('T-GEN', field, 'generated metadata is stale or changed')
    names = {p.name for p in directory.iterdir() if p.suffix in ('.scl', '.udt', '.db')}
    if names != set(sources):
        raise DECL.DeclarationError('T-GEN', str(directory), 'generated source inventory differs')
    for name, text in sources.items():
        data = (directory / name).read_bytes()
        if data != text.encode('ascii') or manifest['generated'].get(name) != hashlib.sha256(data).hexdigest():
            raise DECL.DeclarationError('T-GEN', name, 'source differs from its declaration/template')
    return len(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('declaration', type=Path, nargs='?')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--shared-runtime', action='store_true', help='include the shared command kernel; requires command catalogs/timeouts on all types')
    args = parser.parse_args()
    try:
        if args.verify:
            print(json.dumps({'verified_sources': verify(args.verify)}))
        elif args.declaration and args.out:
            result = generate(DECL.read(args.declaration), args.out, args.shared_runtime)
            print(json.dumps({'generated_sources': len(result['generated']), 'instances': len(result['inventory']['instances'])}))
        else:
            parser.error('provide declaration --out or --verify')
    except (ValueError, OSError) as error:
        print(error)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

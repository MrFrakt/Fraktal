library;

const availableLanguages = <String, String>{
  'en': 'std.languageName.en',
  'es': 'std.languageName.es',
  'de': 'std.languageName.de',
  'fr': 'std.languageName.fr',
  'it': 'std.languageName.it',
  'pt': 'std.languageName.pt',
  'zh': 'std.languageName.zh',
  'ja': 'std.languageName.ja',
  'ko': 'std.languageName.ko',
};

/// Standard-owned defaults. Project/module defaults live in their own catalog
/// and never overwrite this map.
const standardEnglish = <String, String>{
  'std.app.title': 'Fraktal HMI',
  'std.common.cancel': 'Cancel',
  'std.common.save': 'Save',
  'std.common.apply': 'Apply',
  'std.common.confirm': 'Confirm',
  'std.common.import': 'Import',
  'std.common.export': 'Export',
  'std.common.delete': 'Delete',
  'std.common.edit': 'Edit',
  'std.common.moveUp': 'Move up',
  'std.common.moveDown': 'Move down',
  'std.common.undo': 'Undo',
  'std.common.redo': 'Redo',
  'std.common.close': 'Close',
  'std.common.none': 'None',
  'std.common.language': 'Language',
  'std.decision.defaultSuffix': ' (default)',
  'std.common.standard': 'Standard',
  'std.common.project': 'Project',
  'std.languageName.en': 'English',
  'std.languageName.es': 'Español',
  'std.languageName.de': 'Deutsch',
  'std.languageName.fr': 'Français',
  'std.languageName.it': 'Italiano',
  'std.languageName.pt': 'Português',
  'std.languageName.zh': '中文',
  'std.languageName.ja': '日本語',
  'std.languageName.ko': '한국어',
  'std.connection.title': 'Connect Fraktal HMI',
  'std.connection.step': 'Step 2 of 3 · Configure the PLC or gateway endpoint.',
  'std.connection.type': 'Connection type',
  'std.connection.gateway': 'PLC / gateway endpoint',
  'std.connection.simulation': 'Built-in simulation',
  'std.connection.endpoint': 'PLC or gateway endpoint',
  'std.connection.saveConnect': 'Save and connect',
  'std.connection.endpointInvalid': 'Enter a complete endpoint URI.',
  'std.connection.schemeInvalid':
      'Use ws, wss, http, https, opc.tcp, or ads.',
  'std.connection.adsNetIdInvalid':
      'An ADS AmsNetId has six parts, e.g. ads://192.168.1.6.1.1:851.',
  'std.connection.transportHelp':
      'External connectivity requires a deployed OPC UA or Web gateway adapter; an IP address or ping alone is not a PLC data connection.',
  'std.connection.adsHelp':
      'ADS (native TwinCAT): ads://<AmsNetId>:<port>. The AmsNetId is the six-part local/target ID from TwinCAT\'s “Choose Target System” dialog (e.g. 192.168.1.6.1.1); the port is the PLC runtime — 851 for the first runtime, 852/853/… for additional ones.',
  'std.connection.connecting': 'Connecting to PLC…',
  'std.connection.loading': 'Loading connection settings…',
  'std.connection.edit': 'Edit connection settings',
  'std.connection.loadingLocked':
      'The operator interface remains locked until startup is complete.',
  'std.connection.connectingLocked':
      'Operator interaction is disabled until a live PLC subscription is established.',
  'std.connection.startFailed':
      'Connection could not be started. Correct the settings and try again.',
  'std.connection.stateConnecting': 'Transport state: connecting',
  'std.connection.stateLive': 'Transport state: live',
  'std.connection.stateStale': 'Transport state: stale',
  'std.connection.stateDown': 'Transport state: offline',
  'std.languages.firstTitle': 'Select HMI languages',
  'std.languages.firstHelp':
      'Step 1 of 3 · Enable the languages available to operators. The detected device language is selected by default.',
  'std.languages.active': 'Initial language',
  'std.languages.continue': 'Continue',
  'std.languages.settings': 'Language settings',
  'std.languages.catalogHelp':
      'Import or export one CSV per language and scope. Standard and project keys remain separate.',
  'std.languages.standardCatalog': 'Standard language file',
  'std.languages.projectCatalog': 'Project language file',
  'std.units.selectTitle': 'Select Unit modules',
  'std.units.selectHelp':
      'Step 3 of 3 · Choose the root Units this HMI may display and command. An administrator can change this assignment later.',
  'std.units.selectOne': 'Select at least one Unit.',
  'std.units.save': 'Save assignment',
  'std.login.title': 'Login',
  'std.login.user': 'User',
  'std.login.pin': 'PIN',
  'std.login.success': 'Logged in',
  'std.login.failed': 'Login failed',
  'std.login.failedDetail':
      'Login failed. Check the user name and PIN, then try again.',
  'std.login.required': 'Enter both a user name and PIN.',
  'std.login.unavailable':
      'The PLC did not complete the login request. Check the connection and try again.',
  'std.nav.modules': 'Modules',
  'std.nav.fieldbus': 'Fieldbus',
  'std.fieldbus.openModule': 'Open owning module',
  'std.fieldbus.loading': 'Loading fieldbus topology…',
  'std.nav.overview': 'Plant overview',
  'std.nav.language': 'Change language',
  'std.nav.languageSettings': 'Manage language catalogs',
  'std.module.info': 'Information',
  'std.module.description': 'Module description',
  'std.module.noDescription': 'No module description configured.',
  'std.module.documents': 'Documentation',
  'std.module.uploadPdf': 'Upload PDF',
  'std.module.noDocuments': 'No documentation uploaded.',
  'std.module.sectionAccess': 'Section access',
  'std.module.sectionAccessHelp':
      'Minimum access required to view each section of this module.',
  'std.module.documentTitle': 'Document title',
  'std.module.pdfOnly': 'Select a PDF file.',
  'std.module.pdfTooLarge': 'The PDF exceeds the configured size limit.',
  'std.module.infoSection': 'Information',
  'std.module.operationsSection': 'Operations',
  'std.module.diagnosticsSection': 'Diagnostics',
  'std.module.configurationSection': 'Configuration',
  'std.module.documentationSection': 'Documentation',
  'std.module.historySection': 'History',
  'std.moduleType.clamp.name': 'Clamp',
  'std.moduleType.clamp.description':
      'Coordinates the clamp actuators and verifies clamped/unclamped state.',
  'std.moduleType.powerGroup.name': 'Control-power group',
  'std.moduleType.powerGroup.description':
      'Controls a functional power group subject to safety and fieldbus permission.',
  'std.moduleType.cylinder.name': 'Cylinder',
  'std.moduleType.cylinder.description':
      'Controls a two-position pneumatic cylinder with position feedback.',
  'std.moduleType.configurableCylinder.name': 'Configurable cylinder',
  'std.moduleType.configurableCylinder.description':
      'Controls a configurable pneumatic cylinder with validated sensor topology.',
  'std.moduleType.twoHand.name': 'Two-hand start',
  'std.moduleType.twoHand.description':
      'Publishes raw button status and a functional start edge from the certified two-hand-control result.',
  'std.access.none': 'Open',
  'std.access.operator': 'Operator',
  'std.access.technician': 'Technician',
  'std.access.engineer': 'Engineer',
  'std.access.admin': 'Administrator',
  'std.error.catalogInvalid': 'The CSV catalog is invalid.',
  'std.error.catalogImported': 'Language catalog imported.',
  'std.error.fieldbusNodeMappingInvalid':
      'A fieldbus node mapping is incomplete or out of range.',
  'std.error.fieldbusMappingInvalid':
      'The fieldbus I/O mapping is invalid. Commissioning is required.',
  'std.error.fieldbusChannelMappingInvalid':
      'An I/O channel mapping is incomplete or out of range.',
  'std.error.fieldbusValueMappingInvalid':
      'A live I/O value references an unknown channel.',
  'std.error.fieldbusTopologyEmpty': 'The fieldbus topology contains no nodes.',
  'std.error.fieldbusChannelIdentityDuplicate':
      'Two I/O channels use the same electrical tag or audit path.',
  'std.error.passiveInputHasNoCommand':
      'This passive input module has no executable command.',
  'std.error.airPressureSwitchConflict':
      'The low-pressure and operating-pressure switches are active together.',
  'std.moduleType.airPressure.name': 'Air pressure monitor',
  'std.moduleType.airPressure.description':
      'Monitors low and operating pneumatic-pressure switches.',
  'std.release.insufficientStartStop': 'Insufficient access for Start/Stop.',
  'std.release.manualReset': 'A manual-reset alarm is active — reset required.',
  'std.release.controlPowerOff': 'Control power is off.',
  'std.release.notRunnable': 'Unit is not in a runnable mode.',
  'std.release.insufficientAction': 'Insufficient access for this action.',
  'std.release.changeoverRunning':
      'Changeover is not allowed while running — stop first.',
  'std.release.noBlockingAlarm': 'No blocking alarm to reset.',
  'std.release.manualModeRequired': 'Unit must be in MANUAL mode.',
  'std.release.insufficientManual': 'Insufficient access for manual commands.',
  'std.release.outsideAssignment': 'Unit is outside this HMI assignment.',
  'std.release.modeChangePending': 'A mode change is pending.',
  'std.release.modeChangeAlreadyPending': 'A mode change is already pending.',
  'std.release.manualHasNoAutoSequence':
      'MANUAL mode has no automatic run sequence.',
  'std.release.unitNotReady': 'Unit is not ready (not idle).',
  'std.release.controlDomainNotReady':
      'The assigned control domain is not ready (safety, power, or rearm).',
  'std.release.startBlocked': 'Start blocked',
  'std.release.manualBlocked': 'Manual command blocked',
  'std.release.checking': 'Checking release conditions…',
  'std.release.noDetails':
      'The PLC rejected the action but published no release details.',
  'std.command.powerOn': 'Power On',
  'std.command.powerOff': 'Power Off',
  'std.command.extend': 'Extend',
  'std.command.retract': 'Retract',
  'std.command.toHome': 'To Home',
  'std.command.toWork': 'To Work',
  'std.command.clamp': 'Clamp',
  'std.command.unclamp': 'Unclamp',
  'std.command.trigger': 'Trigger',
  'std.command.triggerRead': 'Trigger read',
  'std.command.inspect': 'Inspect',
  'std.manual.commandAccepted': 'Manual command accepted and logged.',
  'std.manual.commandRejected':
      'Manual command rejected. Review the release conditions.',
  'std.error.recipeSchemaInvalid': 'Recipe schema validation failed.',
  'std.error.unsupportedCylinderCommand': 'Unsupported cylinder command.',
  'std.error.unsupportedManualTarget': 'Unsupported manual-command target.',
  'std.error.cylinderBothSensors': 'Both cylinder position sensors are active.',
  'std.error.cylinderRetractTimeout':
      'Cylinder did not reach retracted position.',
  'std.error.cylinderExtendTimeout':
      'Cylinder did not reach extended position.',
  'std.error.cylinderHomeTimeout': 'Cylinder did not reach home in time.',
  'std.error.cylinderWorkTimeout': 'Cylinder did not reach work in time.',
  'std.error.cylinderConfigurationInvalid':
      'Cylinder sensor count, travel, or timeout configuration is invalid.',
  'std.error.cylinderSensorDiscrepancy':
      'Redundant cylinder position sensors disagree.',
  'std.error.cylinderPositionImplausible':
      'Cylinder home and work positions are both confirmed.',
  'std.error.undefinedStep': 'The module entered an undefined sequence step.',
  'std.error.powerEnableWithheld':
      'Safety permission or fieldbus health withheld control power.',
  'std.error.unsupportedPowerCommand': 'Unsupported control-power command.',
  'std.error.powerOnFeedbackTimeout': 'Control-power ON feedback timed out.',
  'std.error.powerOffFeedbackTimeout': 'Control-power OFF feedback timed out.',
  'std.error.undefinedPowerStep':
      'The control-power module entered an undefined sequence step.',
  'std.error.unsupportedClampCommand': 'Unsupported clamp command.',
  'std.error.unsupportedCodeReaderCommand': 'Unsupported code-reader command.',
  'std.error.unsupportedVisionCommand': 'Unsupported vision command.',
  'std.error.unexpectedVisionReply':
      'The vision device returned an unexpected reply.',
  'std.error.heartbeatBadReply':
      'The device refused the heartbeat or returned a bad reply.',
  'std.error.heartbeatResultInvalid': 'The heartbeat result is invalid.',
  'std.error.heartbeatLapsed': 'The device heartbeat elapsed.',
  'std.error.deviceConnectionNotConfigured':
      'The device channel or host is not configured.',
  'std.error.deviceResponseOverflow':
      'An unterminated device response exceeded the receive buffer.',
  'std.error.transportChannelFault': 'The device transport channel faulted.',
  'std.error.byteChannelStateInvalid': 'The byte-channel state is invalid.',
  'std.error.deviceResponseTimeout':
      'The device did not answer within its response timeout.',
  'std.error.deviceNotConnected':
      'A request was made while the device was disconnected.',
  'std.error.identityAlarmRequestNotSupported':
      'This transport cannot yet resolve an alarm identity to its PLC slot.',
  'std.error.emptyHmiRequest': 'The HMI request operation is empty.',
  'std.error.unsupportedHmiRequest':
      'The HMI request operation is unsupported.',
  'std.error.hmiRequestRejected': 'The PLC rejected the HMI request.',
  'std.error.unsupportedModeRequest': 'The requested mode ordinal is invalid.',
  'std.error.unsupportedRunStyleRequest':
      'The requested run-style ordinal is invalid.',
  'std.error.unsupportedGatedActionRequest':
      'The requested gated-action ordinal is invalid.',
  'std.release.transportUnavailable':
      'The PLC transport or request acknowledgement is unavailable.',
  'std.error.twoHandHasNoCommand':
      'The two-hand status module does not accept commands.',
  'std.interlock.directionPermitted':
      'The commanded cylinder direction is permitted.',
  'std.diagnostic.stepStalled':
      'The active sequence step is waiting for a condition.',
  'std.step.current': 'Step {number} · {name}',
  'std.step.awaitingModule': 'Awaiting: {module}',
  'std.step.awaitingCondition': "Awaiting '{condition}' = FALSE",
  'std.step.expectedMaximum': 'Expected ≤ {seconds} s',
  'std.audit.loginFailed': 'Login failed',
  'std.audit.login': 'Login',
  'std.audit.logout': 'Logout',
  'std.audit.autoLogout': 'Automatic logout',
  'std.audit.accessDenied': 'Access denied',
  'std.audit.manualCommandWrongMode':
      'Manual command rejected because the Unit is not in MANUAL.',
  'std.audit.manualCommandAccepted': 'Manual command accepted.',
  'std.audit.manualCommandRejected': 'Manual command rejected.',
  'std.audit.oeeReset': 'OEE counters reset.',
  'std.audit.alarmShelved': 'Alarm shelved.',
  'std.audit.alarmUnshelved': 'Alarm unshelved.',
  'std.changeover.requestRejected':
      'Changeover could not start. Check access, mode, alarms, control power, and the selected recipe.',
  'std.module.tab.overview': 'Overview',
  'std.module.tab.description': 'Description',
  'std.module.tab.motion': 'Motion',
  'std.module.tab.vision': 'Vision',
  'std.module.tab.codeReader': 'Code reader',
  'std.module.tab.rfid': 'RFID',
  'std.module.tab.custom': 'Custom',
  'std.module.tab.guidance': 'Operator guidance',
  'std.module.tabs.noneVisible':
      'No module tabs are available at the current access level.',
  'std.module.control.text': 'Text',
  'std.module.control.value': 'Value / output',
  'std.module.control.indicator': 'LED indicator',
  'std.module.control.chart': 'Trend chart',
  'std.module.control.button': 'Button',
  'std.module.control.textInput': 'Text input',
  'std.module.control.image': 'Image',
  'std.module.action.none': 'No action',
  'std.module.action.manualCommand': 'PLC manual command',
  'std.module.action.unitStart': 'Start Unit',
  'std.module.action.unitStop': 'Stop Unit',
  'std.module.action.operatorReset': 'Operator reset',
  'std.module.action.decisionAnswer': 'Answer operator decision',
  'std.module.action.writeConfig': 'Write PLC configuration',
  'std.module.editor.active':
      'ADMIN EDIT MODE · Changes are saved on this HMI.',
  'std.module.editor.startEditing': 'Edit module tabs',
  'std.module.editor.finishEditing': 'Finish editing',
  'std.module.editor.publish': 'Publish',
  'std.module.editor.publishTitle': 'Publish module layout',
  'std.module.editor.changeComment': 'Change note (optional)',
  'std.module.editor.discardDraft': 'Discard draft',
  'std.module.editor.history': 'Layout history',
  'std.module.editor.noHistory': 'No earlier published layout is available.',
  'std.module.editor.restore': 'Restore',
  'std.module.editor.addTab': 'Add tab',
  'std.module.editor.editTab': 'Edit tab',
  'std.module.editor.deleteTab': 'Delete tab',
  'std.module.editor.deleteTabConfirm': "Delete the '{title}' tab?",
  'std.module.editor.tabTitle': 'Tab title',
  'std.module.editor.tabKind': 'Tab type',
  'std.module.editor.customTab': 'Custom module tab',
  'std.module.editor.guidanceTab': 'Sequence guidance tab',
  'std.module.editor.minimumAccess': 'Minimum access to view',
  'std.module.editor.localizedHelp':
      'This text can be translated through the language catalogs.',
  'std.module.editor.required': 'A value is required.',
  'std.module.editor.guidanceTriggerHelp':
      'Open this guidance screen when either configured step identity matches.',
  'std.module.editor.triggerStepNumber': 'Trigger step number (optional)',
  'std.module.editor.triggerStepName': 'Trigger step name (optional)',
  'std.module.editor.triggerWildcardHelp':
      "Use * to open for every WAIT_OPERATOR step.",
  'std.module.editor.invalidNumber': 'Enter a valid non-negative number.',
  'std.module.editor.addControl': 'Add control',
  'std.module.editor.editControl': 'Edit control',
  'std.module.editor.controlKind': 'Control type',
  'std.module.editor.controlWidth': 'Responsive width',
  'std.module.width.quarter': 'Quarter',
  'std.module.width.third': 'Third',
  'std.module.width.half': 'Half',
  'std.module.width.twoThirds': 'Two thirds',
  'std.module.width.full': 'Full width',
  'std.module.editor.label': 'Label',
  'std.module.editor.text': 'Text',
  'std.module.editor.binding': 'Published PLC value',
  'std.module.editor.bindingSearch': 'Search published OPC UA tags',
  'std.module.editor.bindingSelected': 'Linked OPC UA tags',
  'std.module.editor.bindingHelp':
      'Select a published scalar tag owned by this module.',
  'std.module.editor.bindingRequired': 'Select at least one OPC UA tag.',
  'std.module.editor.tooManyBindings': 'Too many OPC UA tags are selected.',
  'std.module.editor.multiBindingHelp':
      'Charts can display up to {maximum} numeric tags.',
  'std.module.editor.bindingLimitReached':
      'Maximum number of linked tags selected.',
  'std.module.editor.bindingUnavailable':
      'Not present in the current module snapshot. The link is preserved for reconnect or import recovery.',
  'std.module.editor.unit': 'Engineering unit',
  'std.module.editor.samplePeriod': 'Sampling period',
  'std.module.editor.historyPoints': 'History points',
  'std.module.editor.action': 'PLC-validated action',
  'std.module.editor.manualCommand': 'Published manual command',
  'std.module.editor.decisionOption': 'Published decision option',
  'std.module.editor.catalogActionHelp':
      'Only choices currently published by the PLC can be selected.',
  'std.module.editor.catalogRequired':
      'The PLC is not publishing a selectable choice.',
  'std.module.editor.confirmAction': 'Require operator confirmation',
  'std.module.editor.confirmActionHelp':
      'Recommended for commands and state-changing actions.',
  'std.module.editor.actionValue': 'Command / answer value',
  'std.module.editor.targetPath': 'Target module path (optional)',
  'std.module.editor.plcWriteNotice':
      'The PLC mailbox, access rules, release report, and command catalog remain authoritative.',
  'std.module.editor.noImage': 'No image selected',
  'std.module.editor.chooseImage': 'Choose image',
  'std.module.editor.imageTooLarge': 'The image exceeds the 5 MB limit.',
  'std.module.editor.imageRequired': 'Choose an image.',
  'std.module.editor.tabIcon': 'Tab icon',
  'std.module.editor.backgroundImage': 'Overview background image',
  'std.module.editor.backgroundHelp':
      'The image stays behind the live Overview controls and is included in customization export/import.',
  'std.module.editor.noBackgroundImage': 'No background image selected',
  'std.module.editor.backgroundImageTooLarge':
      'The background image exceeds the 10 MB limit.',
  'std.module.editor.backgroundFit': 'Image sizing preset',
  'std.module.editor.backgroundPosition': 'Image position',
  'std.module.editor.backgroundMargins': 'Image margins',
  'std.module.editor.margin.left': 'Left',
  'std.module.editor.margin.top': 'Top',
  'std.module.editor.margin.right': 'Right',
  'std.module.editor.margin.bottom': 'Bottom',
  'std.module.editor.range': 'Enter a value from {minimum} to {maximum}.',
  'std.module.editor.emptyTab':
      'This tab is empty. Use Add control to build it.',
  'std.module.custom.empty': 'No content has been configured for this tab.',
  'std.module.custom.trend': 'Trend',
  'std.module.background.fit.contain': 'Contain (keep ratio)',
  'std.module.background.fit.cover': 'Cover (keep ratio)',
  'std.module.background.fit.fitWidth': 'Fit width (keep ratio)',
  'std.module.background.fit.fitHeight': 'Fit height (keep ratio)',
  'std.module.background.position.topLeft': 'Top left',
  'std.module.background.position.topCenter': 'Top center',
  'std.module.background.position.topRight': 'Top right',
  'std.module.background.position.centerLeft': 'Center left',
  'std.module.background.position.center': 'Center',
  'std.module.background.position.centerRight': 'Center right',
  'std.module.background.position.bottomLeft': 'Bottom left',
  'std.module.background.position.bottomCenter': 'Bottom center',
  'std.module.background.position.bottomRight': 'Bottom right',
  'std.module.icon.widgets': 'Widgets',
  'std.module.icon.dashboard': 'Dashboard',
  'std.module.icon.tune': 'Adjustments',
  'std.module.icon.monitoring': 'Monitoring',
  'std.module.icon.chart': 'Chart',
  'std.module.icon.information': 'Information',
  'std.module.icon.build': 'Tools',
  'std.module.icon.science': 'Process / lab',
  'std.module.icon.machine': 'Machine',
  'std.module.icon.camera': 'Camera',
  'std.module.icon.scanner': 'Scanner',
  'std.module.icon.contactless': 'RFID / contactless',
  'std.module.icon.checklist': 'Checklist',
  'std.module.icon.guidance': 'Guidance',
  'std.module.icon.image': 'Image',
  'std.module.icon.description': 'Document',
  'std.module.icon.settings': 'Settings',
  'std.module.icon.speed': 'Performance',
  'std.module.icon.electrical': 'Electrical',
  'std.module.editor.exportTitle': 'Export HMI customization',
  'std.module.editor.importTitle': 'Import HMI customization',
  'std.module.editor.importConfirmTitle': 'Merge HMI customization?',
  'std.module.editor.importConfirmBody':
      'Imported tabs, access policies, controls, images, documents, and localized text will update matching items. Target-only customization is preserved. Connection settings are not changed.',
  'std.module.editor.imported': 'HMI customization imported.',
  'std.module.editor.importSummary':
      'Exact modules: {exact} · Remapped: {remapped} · Deferred: {deferred}',
  'std.module.editor.remappedPaths': 'Remapped module paths',
  'std.module.editor.deferredPaths': 'Deferred module profiles',
  'std.module.editor.deferredHelp':
      'These profiles were preserved under their original paths because no unique current module match was safe. They can apply if that module returns or be reconciled in a later import.',
  'std.module.editor.invalidBundle':
      'The selected HMI customization file is invalid.',
  'std.module.motion.actualPosition': 'Actual position',
  'std.module.motion.targetPosition': 'Target position',
  'std.module.motion.velocity': 'Velocity',
  'std.module.motion.positionError': 'Position error',
  'std.module.motion.axisState': 'Axis state',
  'std.module.motion.homed': 'Homed',
  'std.module.motion.moving': 'Moving',
  'std.module.motion.fault': 'Fault',
  'std.module.motion.nonSafetyNotice':
      'Motion controls shown by the standard HMI are not safety functions.',
  'std.module.motion.notPublished': 'No motion facet is published.',
  'std.module.vision.noResult': 'No inspection result',
  'std.module.vision.ok': 'Inspection OK',
  'std.module.vision.ng': 'Inspection NG',
  'std.module.vision.trigger': 'Trigger inspection',
  'std.module.vision.imageUnavailable': 'Inspection image not published',
  'std.module.vision.imagePublicationHelp':
      'Result data remains live. Image and overlay history appears only when the device module publishes that optional data.',
  'std.module.reader.triggers': 'Triggers',
  'std.module.reader.goodReads': 'Good reads',
  'std.module.reader.noReads': 'No reads',
  'std.module.reader.lastResult': 'Last decoded result',
  'std.module.reader.trigger': 'Trigger',
  'std.module.reader.noRead': 'No read',
  'std.module.reader.matchOk': 'Match OK',
  'std.module.reader.linked': 'Linked',
  'std.module.rfid.currentTag': 'Current tag',
  'std.module.rfid.read': 'Read',
  'std.module.rfid.tagPresent': 'Tag present',
  'std.module.rfid.quality': 'Quality',
  'std.module.custom.writeAccepted': 'Configuration write accepted.',
  'std.module.custom.writeRejected': 'Configuration write rejected by PLC.',
  'std.module.custom.actionAccepted': 'Action accepted.',
  'std.module.custom.actionRejected': 'Action rejected by PLC.',
  'std.module.custom.catalogUnavailable':
      'The configured choice is not in the current PLC catalog.',
  'std.module.custom.confirmActionTitle': 'Confirm PLC action',
  'std.module.custom.confirmActionBody': 'Run “{action}”?',
  'std.release.configBlocked': 'Configuration write blocked',
  'std.release.stopBlocked': 'Stop blocked',
  'std.release.resetBlocked': 'Reset blocked',
  'std.guidance.step': 'Step {number} · {name}',
};

const standardSpanish = <String, String>{
  'std.common.cancel': 'Cancelar',
  'std.common.save': 'Guardar',
  'std.common.apply': 'Aplicar',
  'std.common.confirm': 'Confirmar',
  'std.common.import': 'Importar',
  'std.common.export': 'Exportar',
  'std.common.delete': 'Eliminar',
  'std.common.edit': 'Editar',
  'std.common.moveUp': 'Mover arriba',
  'std.common.moveDown': 'Mover abajo',
  'std.common.undo': 'Deshacer',
  'std.common.redo': 'Rehacer',
  'std.common.close': 'Cerrar',
  'std.common.none': 'Ninguno',
  'std.common.language': 'Idioma',
  'std.common.standard': 'Estándar',
  'std.common.project': 'Proyecto',
  'std.connection.title': 'Conectar Fraktal HMI',
  'std.connection.step':
      'Paso 2 de 3 · Configure el punto de conexión del PLC o gateway.',
  'std.connection.type': 'Tipo de conexión',
  'std.connection.gateway': 'PLC / gateway',
  'std.connection.simulation': 'Simulación integrada',
  'std.connection.endpoint': 'Dirección del PLC o gateway',
  'std.connection.saveConnect': 'Guardar y conectar',
  'std.connection.endpointInvalid': 'Introduzca una URI de destino completa.',
  'std.connection.schemeInvalid': 'Use ws, wss, http, https, opc.tcp o ads.',
  'std.connection.adsNetIdInvalid':
      'Un AmsNetId de ADS tiene seis partes, p. ej. ads://192.168.1.6.1.1:851.',
  'std.connection.adsHelp':
      'ADS (TwinCAT nativo): ads://<AmsNetId>:<puerto>. El AmsNetId es el identificador local/destino de seis partes del diálogo «Choose Target System» de TwinCAT (p. ej. 192.168.1.6.1.1); el puerto es el runtime del PLC: 851 para el primero, 852/853/… para los siguientes.',
  'std.connection.connecting': 'Conectando al PLC…',
  'std.connection.loading': 'Cargando configuración de conexión…',
  'std.connection.edit': 'Editar configuración de conexión',
  'std.connection.transportHelp':
      'La conexión externa requiere un adaptador OPC UA o gateway Web desplegado; una dirección IP o el ping no son una conexión de datos del PLC.',
  'std.connection.startFailed':
      'No se pudo iniciar la conexión. Corrija la configuración e intente de nuevo.',
  'std.connection.stateConnecting': 'Estado del transporte: conectando',
  'std.connection.stateLive': 'Estado del transporte: conectado',
  'std.connection.stateStale': 'Estado del transporte: datos obsoletos',
  'std.connection.stateDown': 'Estado del transporte: sin conexión',
  'std.languages.firstTitle': 'Seleccionar idiomas de la HMI',
  'std.languages.firstHelp':
      'Paso 1 de 3 · Habilite los idiomas disponibles. El idioma detectado queda seleccionado por defecto.',
  'std.languages.active': 'Idioma inicial',
  'std.languages.continue': 'Continuar',
  'std.languages.settings': 'Configuración de idiomas',
  'std.languages.catalogHelp':
      'Importe o exporte un CSV por idioma y ámbito. Las claves estándar y de proyecto permanecen separadas.',
  'std.languages.standardCatalog': 'Archivo de idioma estándar',
  'std.languages.projectCatalog': 'Archivo de idioma del proyecto',
  'std.units.selectTitle': 'Seleccionar módulos Unit',
  'std.units.selectHelp':
      'Paso 3 de 3 · Elija los Unit raíz que esta HMI puede mostrar y comandar.',
  'std.units.selectOne': 'Seleccione al menos un Unit.',
  'std.units.save': 'Guardar asignación',
  'std.login.title': 'Iniciar sesión',
  'std.login.user': 'Usuario',
  'std.login.pin': 'PIN',
  'std.login.success': 'Sesión iniciada',
  'std.login.failed': 'Inicio de sesión fallido',
  'std.login.failedDetail':
      'No se pudo iniciar sesión. Verifique el usuario y el PIN e inténtelo de nuevo.',
  'std.login.required': 'Ingrese el usuario y el PIN.',
  'std.login.unavailable':
      'El PLC no completó la solicitud de inicio de sesión. Verifique la conexión e inténtelo de nuevo.',
  'std.nav.modules': 'Módulos',
  'std.nav.fieldbus': 'Bus de campo',
  'std.fieldbus.openModule': 'Abrir el módulo propietario',
  'std.fieldbus.loading': 'Cargando topología de bus de campo…',
  'std.nav.overview': 'Vista general',
  'std.nav.language': 'Cambiar idioma',
  'std.nav.languageSettings': 'Gestionar catálogos de idioma',
  'std.module.info': 'Información',
  'std.module.description': 'Descripción del módulo',
  'std.module.noDescription': 'No hay descripción configurada.',
  'std.module.documents': 'Documentación',
  'std.module.uploadPdf': 'Subir PDF',
  'std.module.noDocuments': 'No hay documentación cargada.',
  'std.module.sectionAccess': 'Acceso por sección',
  'std.module.documentTitle': 'Título del documento',
  'std.module.infoSection': 'Información',
  'std.module.operationsSection': 'Operación',
  'std.module.diagnosticsSection': 'Diagnóstico',
  'std.module.configurationSection': 'Configuración',
  'std.module.documentationSection': 'Documentación',
  'std.module.historySection': 'Historial',
  'std.access.none': 'Abierto',
  'std.access.operator': 'Operador',
  'std.access.technician': 'Técnico',
  'std.access.engineer': 'Ingeniero',
  'std.access.admin': 'Administrador',
  'std.error.catalogInvalid': 'El catálogo CSV no es válido.',
  'std.error.catalogImported': 'Catálogo de idioma importado.',
  'std.error.identityAlarmRequestNotSupported':
      'Este transporte aún no puede resolver la identidad de la alarma a su posición en el PLC.',
  'std.error.emptyHmiRequest': 'La operación solicitada por la HMI está vacía.',
  'std.error.unsupportedHmiRequest':
      'La operación solicitada por la HMI no es compatible.',
  'std.error.hmiRequestRejected': 'El PLC rechazó la solicitud de la HMI.',
  'std.error.unsupportedModeRequest':
      'El ordinal del modo solicitado no es válido.',
  'std.error.unsupportedRunStyleRequest':
      'El ordinal del estilo de ejecución no es válido.',
  'std.error.unsupportedGatedActionRequest':
      'El ordinal de la acción protegida no es válido.',
  'std.release.transportUnavailable':
      'El transporte o la confirmación de la solicitud del PLC no está disponible.',
  'std.release.startBlocked': 'Inicio bloqueado',
  'std.release.manualBlocked': 'Comando manual bloqueado',
  'std.release.checking': 'Verificando condiciones de liberación…',
  'std.release.noDetails':
      'El PLC rechazó la acción, pero no publicó detalles de liberación.',
  'std.error.fieldbusNodeMappingInvalid':
      'Un nodo de bus de campo está incompleto o fuera de rango.',
  'std.error.fieldbusMappingInvalid':
      'El mapeo de E/S del bus no es válido. Se requiere puesta en marcha.',
  'std.error.fieldbusChannelMappingInvalid':
      'Un canal de E/S está incompleto o fuera de rango.',
  'std.error.fieldbusValueMappingInvalid':
      'Un valor de E/S referencia un canal desconocido.',
  'std.error.fieldbusTopologyEmpty': 'La topología de bus no contiene nodos.',
  'std.error.fieldbusChannelIdentityDuplicate':
      'Dos canales usan la misma etiqueta eléctrica o ruta de auditoría.',
  'std.error.passiveInputHasNoCommand':
      'Este módulo de entrada pasiva no tiene comandos ejecutables.',
  'std.error.airPressureSwitchConflict':
      'Los interruptores de presión baja y de operación están activos simultáneamente.',
  'std.moduleType.airPressure.name': 'Monitor de presión de aire',
  'std.moduleType.airPressure.description':
      'Supervisa los interruptores de presión neumática baja y de operación.',
  'std.changeover.requestRejected':
      'No se pudo iniciar el cambio de modelo. Revise acceso, modo, alarmas, Control On y la receta seleccionada.',
  'std.module.tab.overview': 'Vista general',
  'std.module.tab.description': 'Descripción',
  'std.module.tab.motion': 'Movimiento',
  'std.module.tab.vision': 'Visión',
  'std.module.tab.codeReader': 'Lector de códigos',
  'std.module.tab.rfid': 'RFID',
  'std.module.tab.custom': 'Personalizada',
  'std.module.tab.guidance': 'Guía del operador',
  'std.module.tabs.noneVisible':
      'No hay pestañas disponibles para el nivel de acceso actual.',
  'std.module.editor.active':
      'MODO DE EDICIÓN ADMIN · Los cambios se guardan en esta HMI.',
  'std.module.editor.startEditing': 'Editar pestañas del módulo',
  'std.module.editor.finishEditing': 'Terminar edición',
  'std.module.editor.publish': 'Publicar',
  'std.module.editor.publishTitle': 'Publicar diseño del módulo',
  'std.module.editor.changeComment': 'Nota del cambio (opcional)',
  'std.module.editor.discardDraft': 'Descartar borrador',
  'std.module.editor.history': 'Historial del diseño',
  'std.module.editor.noHistory':
      'No hay un diseño publicado anterior disponible.',
  'std.module.editor.restore': 'Restaurar',
  'std.module.editor.addTab': 'Agregar pestaña',
  'std.module.editor.editTab': 'Editar pestaña',
  'std.module.editor.deleteTab': 'Eliminar pestaña',
  'std.module.editor.deleteTabConfirm': "¿Eliminar la pestaña '{title}'?",
  'std.module.editor.tabTitle': 'Título de pestaña',
  'std.module.editor.tabKind': 'Tipo de pestaña',
  'std.module.editor.customTab': 'Pestaña personalizada',
  'std.module.editor.guidanceTab': 'Pestaña de guía de secuencia',
  'std.module.editor.minimumAccess': 'Acceso mínimo para verla',
  'std.module.editor.localizedHelp':
      'Este texto se puede traducir mediante los catálogos de idioma.',
  'std.module.editor.required': 'Se requiere un valor.',
  'std.module.editor.guidanceTriggerHelp':
      'Abre esta guía cuando coincida cualquiera de las identidades de paso.',
  'std.module.editor.triggerStepNumber': 'Número de paso (opcional)',
  'std.module.editor.triggerStepName': 'Nombre de paso (opcional)',
  'std.module.editor.triggerWildcardHelp':
      'Use * para abrir en cada paso WAIT_OPERATOR.',
  'std.module.editor.invalidNumber': 'Ingrese un número no negativo válido.',
  'std.module.editor.addControl': 'Agregar control',
  'std.module.editor.editControl': 'Editar control',
  'std.module.editor.controlKind': 'Tipo de control',
  'std.module.editor.controlWidth': 'Ancho adaptable',
  'std.module.width.quarter': 'Un cuarto',
  'std.module.width.third': 'Un tercio',
  'std.module.width.half': 'Mitad',
  'std.module.width.twoThirds': 'Dos tercios',
  'std.module.width.full': 'Ancho completo',
  'std.module.editor.label': 'Etiqueta',
  'std.module.editor.text': 'Texto',
  'std.module.editor.binding': 'Valor publicado por el PLC',
  'std.module.editor.bindingSearch': 'Buscar etiquetas OPC UA publicadas',
  'std.module.editor.bindingSelected': 'Etiquetas OPC UA vinculadas',
  'std.module.editor.bindingHelp':
      'Seleccione una etiqueta escalar publicada que pertenezca a este módulo.',
  'std.module.editor.bindingRequired':
      'Seleccione al menos una etiqueta OPC UA.',
  'std.module.editor.tooManyBindings':
      'Se seleccionaron demasiadas etiquetas OPC UA.',
  'std.module.editor.multiBindingHelp':
      'Las gráficas pueden mostrar hasta {maximum} etiquetas numéricas.',
  'std.module.editor.bindingLimitReached':
      'Se alcanzó el máximo de etiquetas vinculadas.',
  'std.module.editor.bindingUnavailable':
      'No está presente en la captura actual del módulo. El vínculo se conserva para reconexión o recuperación de importación.',
  'std.module.editor.unit': 'Unidad de ingeniería',
  'std.module.editor.samplePeriod': 'Periodo de muestreo',
  'std.module.editor.historyPoints': 'Puntos de historial',
  'std.module.editor.action': 'Acción validada por el PLC',
  'std.module.editor.manualCommand': 'Comando manual publicado',
  'std.module.editor.decisionOption': 'Opción de decisión publicada',
  'std.module.editor.catalogActionHelp':
      'Solo pueden seleccionarse opciones publicadas actualmente por el PLC.',
  'std.module.editor.catalogRequired':
      'El PLC no publica una opción seleccionable.',
  'std.module.editor.confirmAction': 'Solicitar confirmación del operador',
  'std.module.editor.confirmActionHelp':
      'Recomendado para comandos y acciones que cambian el estado.',
  'std.module.editor.actionValue': 'Valor de comando / respuesta',
  'std.module.editor.targetPath': 'Ruta del módulo destino (opcional)',
  'std.module.editor.plcWriteNotice':
      'El buzón, acceso, reporte de liberación y catálogo de comandos del PLC siguen siendo autoritativos.',
  'std.module.editor.noImage': 'Sin imagen seleccionada',
  'std.module.editor.chooseImage': 'Elegir imagen',
  'std.module.editor.imageTooLarge': 'La imagen supera el límite de 5 MB.',
  'std.module.editor.imageRequired': 'Seleccione una imagen.',
  'std.module.editor.tabIcon': 'Ícono de pestaña',
  'std.module.editor.backgroundImage': 'Imagen de fondo del resumen',
  'std.module.editor.backgroundHelp':
      'La imagen permanece detrás de los controles activos del resumen y se incluye al exportar/importar la personalización.',
  'std.module.editor.noBackgroundImage': 'Sin imagen de fondo',
  'std.module.editor.backgroundImageTooLarge':
      'La imagen de fondo supera el límite de 10 MB.',
  'std.module.editor.backgroundFit': 'Preajuste de tamaño',
  'std.module.editor.backgroundPosition': 'Posición de imagen',
  'std.module.editor.backgroundMargins': 'Márgenes de imagen',
  'std.module.editor.margin.left': 'Izquierda',
  'std.module.editor.margin.top': 'Arriba',
  'std.module.editor.margin.right': 'Derecha',
  'std.module.editor.margin.bottom': 'Abajo',
  'std.module.editor.range': 'Ingrese un valor de {minimum} a {maximum}.',
  'std.module.editor.emptyTab':
      'Esta pestaña está vacía. Use Agregar control para construirla.',
  'std.module.custom.empty': 'No hay contenido configurado en esta pestaña.',
  'std.module.custom.trend': 'Tendencia',
  'std.module.background.fit.contain': 'Contener (mantener proporción)',
  'std.module.background.fit.cover': 'Cubrir (mantener proporción)',
  'std.module.background.fit.fitWidth':
      'Ajustar al ancho (mantener proporción)',
  'std.module.background.fit.fitHeight':
      'Ajustar a la altura (mantener proporción)',
  'std.module.background.position.topLeft': 'Arriba izquierda',
  'std.module.background.position.topCenter': 'Arriba centro',
  'std.module.background.position.topRight': 'Arriba derecha',
  'std.module.background.position.centerLeft': 'Centro izquierda',
  'std.module.background.position.center': 'Centro',
  'std.module.background.position.centerRight': 'Centro derecha',
  'std.module.background.position.bottomLeft': 'Abajo izquierda',
  'std.module.background.position.bottomCenter': 'Abajo centro',
  'std.module.background.position.bottomRight': 'Abajo derecha',
  'std.module.icon.widgets': 'Controles',
  'std.module.icon.dashboard': 'Panel',
  'std.module.icon.tune': 'Ajustes',
  'std.module.icon.monitoring': 'Monitoreo',
  'std.module.icon.chart': 'Gráfica',
  'std.module.icon.information': 'Información',
  'std.module.icon.build': 'Herramientas',
  'std.module.icon.science': 'Proceso / laboratorio',
  'std.module.icon.machine': 'Máquina',
  'std.module.icon.camera': 'Cámara',
  'std.module.icon.scanner': 'Escáner',
  'std.module.icon.contactless': 'RFID / sin contacto',
  'std.module.icon.checklist': 'Lista de verificación',
  'std.module.icon.guidance': 'Guía',
  'std.module.icon.image': 'Imagen',
  'std.module.icon.description': 'Documento',
  'std.module.icon.settings': 'Configuración',
  'std.module.icon.speed': 'Rendimiento',
  'std.module.icon.electrical': 'Eléctrico',
  'std.module.editor.exportTitle': 'Exportar personalización HMI',
  'std.module.editor.importTitle': 'Importar personalización HMI',
  'std.module.editor.importConfirmTitle': '¿Combinar personalización HMI?',
  'std.module.editor.importConfirmBody':
      'Las pestañas, accesos, controles, imágenes, documentos y textos importados actualizarán los elementos coincidentes. Se conserva la personalización exclusiva del destino. La conexión no cambia.',
  'std.module.editor.imported': 'Personalización HMI importada.',
  'std.module.editor.importSummary':
      'Módulos exactos: {exact} · Reasignados: {remapped} · Diferidos: {deferred}',
  'std.module.editor.remappedPaths': 'Rutas de módulo reasignadas',
  'std.module.editor.deferredPaths': 'Perfiles de módulo diferidos',
  'std.module.editor.deferredHelp':
      'Estos perfiles se conservaron en sus rutas originales porque no había una coincidencia actual única y segura. Podrán aplicarse si el módulo regresa o reconciliarse en otra importación.',
  'std.module.editor.invalidBundle':
      'El archivo de personalización HMI no es válido.',
  'std.module.control.text': 'Texto',
  'std.module.control.value': 'Valor / salida',
  'std.module.control.indicator': 'Indicador LED',
  'std.module.control.chart': 'Gráfica de tendencia',
  'std.module.control.button': 'Botón',
  'std.module.control.textInput': 'Entrada de texto',
  'std.module.control.image': 'Imagen',
  'std.module.action.none': 'Sin acción',
  'std.module.action.manualCommand': 'Comando manual del PLC',
  'std.module.action.unitStart': 'Iniciar Unit',
  'std.module.action.unitStop': 'Detener Unit',
  'std.module.action.operatorReset': 'Reinicio del operador',
  'std.module.action.decisionAnswer': 'Responder decisión del operador',
  'std.module.action.writeConfig': 'Escribir configuración del PLC',
  'std.module.motion.actualPosition': 'Posición actual',
  'std.module.motion.targetPosition': 'Posición objetivo',
  'std.module.motion.velocity': 'Velocidad',
  'std.module.motion.positionError': 'Error de posición',
  'std.module.motion.axisState': 'Estado del eje',
  'std.module.motion.homed': 'Referenciado',
  'std.module.motion.moving': 'En movimiento',
  'std.module.motion.fault': 'Falla',
  'std.module.motion.nonSafetyNotice':
      'Los controles de movimiento de la HMI estándar no son funciones de seguridad.',
  'std.module.motion.notPublished': 'No se publicó la faceta de movimiento.',
  'std.module.vision.noResult': 'Sin resultado de inspección',
  'std.module.vision.ok': 'Inspección OK',
  'std.module.vision.ng': 'Inspección NG',
  'std.module.vision.trigger': 'Disparar inspección',
  'std.module.vision.imageUnavailable': 'Imagen de inspección no publicada',
  'std.module.vision.imagePublicationHelp':
      'Los resultados permanecen activos. La imagen y sus capas aparecen cuando el módulo publica esos datos opcionales.',
  'std.module.reader.triggers': 'Disparos',
  'std.module.reader.goodReads': 'Lecturas correctas',
  'std.module.reader.noReads': 'Sin lectura',
  'std.module.reader.lastResult': 'Último resultado decodificado',
  'std.module.reader.trigger': 'Disparar',
  'std.module.reader.noRead': 'Sin lectura',
  'std.module.reader.matchOk': 'Coincidencia OK',
  'std.module.reader.linked': 'Conectado',
  'std.module.rfid.currentTag': 'Etiqueta actual',
  'std.module.rfid.read': 'Leer',
  'std.module.rfid.tagPresent': 'Etiqueta presente',
  'std.module.rfid.quality': 'Calidad',
  'std.module.custom.writeAccepted': 'Escritura de configuración aceptada.',
  'std.module.custom.writeRejected':
      'El PLC rechazó la escritura de configuración.',
  'std.module.custom.catalogUnavailable':
      'La opción configurada no está en el catálogo actual del PLC.',
  'std.module.custom.confirmActionTitle': 'Confirmar acción del PLC',
  'std.module.custom.confirmActionBody': '¿Ejecutar “{action}”?',
  'std.module.custom.actionAccepted': 'Acción aceptada.',
  'std.module.custom.actionRejected': 'El PLC rechazó la acción.',
  'std.release.configBlocked': 'Escritura de configuración bloqueada',
  'std.release.stopBlocked': 'Paro bloqueado',
  'std.release.resetBlocked': 'Reinicio bloqueado',
  'std.guidance.step': 'Paso {number} · {name}',
};

const projectEnglish = <String, String>{
  'project.module.StationA.name': 'Station A',
  'project.module.StationA.description':
      'Clamp and inspection station for the current product model.',
  'project.module.ConveyorB.name': 'Conveyor B',
  'project.module.ConveyorB.description':
      'Independent material-transfer conveyor.',
  'project.module.clampStation.name': 'Clamp station',
  'project.module.clampStation.description':
      'Runs the clamp and unclamp sequence for the configured product.',
  'project.reason.cylinderTimeout':
      'Cylinder did not reach the commanded position.',
  'project.reason.airPressureLow':
      'Air pressure is below the operating threshold.',
  'project.reason.toolChange': 'Tool change advised.',
  'project.status.awaitingReset': 'Cleared — awaiting operator reset.',
  'project.status.clampStep': 'Clamping part.',
  'project.status.transporting': 'Transporting.',
  'project.status.heartbeatLost': 'Heartbeat lapsed.',
  'project.reason.clampNotConfirmed': 'Clamp not confirmed.',
  'project.interlock.cylinderPosition': 'Cylinder is not at position.',
  'project.interlock.areaSafe': 'The working area is safe.',
  'project.command.toHome': 'To Home',
  'project.command.toWork': 'To Work',
  'project.step.transport': 'Transport',
  'project.step.commandClamp': 'Command clamp',
  'project.step.awaitClamp': 'Wait for clamp',
  'project.step.commandUnclamp': 'Command unclamp',
  'project.step.awaitUnclamp': 'Wait for unclamp',
  'project.error.clampNotConfirmedAfterSettle':
      'Clamp was not confirmed after the settling time.',
  'project.safety.doorNorth': 'North access guard closed and locked.',
  'project.safety.lightCurtain': 'Infeed light curtain clear.',
  'project.safety.safeValve': 'Safe pneumatic supply available.',
  'project.hardware.ethercatMaster':
      'Primary real-time fieldbus master for this controller.',
  'project.hardware.ek1100': 'EtherCAT station coupler for the clamp cell.',
  'project.hardware.el1008': 'Eight-channel 24 V DC digital-input terminal.',
  'project.hardware.cx2030':
      'CX2030 controller and EtherCAT master for the training press.',
  'project.hardware.ek1200':
      'EK1200-5000 EtherCAT Box coupler for the press I/O station.',
  'project.hardware.el1809': 'Sixteen-channel 24 V DC digital-input terminal.',
  'project.hardware.el2809': 'Sixteen-channel 24 V DC digital-output terminal.',
  'project.hardware.el6001':
      'Single-channel RS232 serial-interface terminal; no press HAL consumer is assigned.',
  'project.hardware.el9011': 'EtherCAT end terminal for the press I/O station.',
  'project.io.101B301A': 'Part feeder retracted / slide inside sensor.',
  'project.io.101B301B': 'Part feeder extended / slide outside sensor.',
  'project.io.101B201A': 'Press access door closed sensor.',
  'project.io.101B201B': 'Press access door open sensor.',
  'project.io.101B202A': 'Press ram down sensor.',
  'project.io.101B202B': 'Press ram up sensor.',
  'project.io.101S101': 'Right two-hand-control pushbutton raw input.',
  'project.io.101S102': 'Left two-hand-control pushbutton raw input.',
  'project.io.000MB085A_2': 'Compressed-air pressure below 0.3 bar.',
  'project.io.000MB085A_4': 'Compressed-air pressure above 4.5 bar.',
  'project.io.101B601': 'Part-present sensor.',
  'project.io.000K911_Y32': 'Control On feedback.',
  'project.io.000K910A':
      'Ordinary emergency-stop healthy mirror (not a safety input).',
  'project.io.101K301A': 'Command part feeder backward / slide inside.',
  'project.io.101K301B': 'Command part feeder forward / slide outside.',
  'project.io.101K201A': 'Command press access door closed.',
  'project.io.101K201B': 'Command press access door open.',
  'project.io.101K202A': 'Command press ram downward.',
  'project.io.101K202B': 'Command press ram upward.',
  'project.io.101P101': 'Right two-hand-control indicator lamp.',
  'project.io.101P102': 'Left two-hand-control indicator lamp.',
  'project.io.000K951_A1': 'Switch Control On functional request.',
  'project.io.000K911_A1': 'Enable Control On functional request.',
  'project.io.cylBWorkFb1': 'Primary work-position feedback for cylinder B.',
  'project.io.cylBWorkFb2': 'Redundant work-position feedback for cylinder B.',
  'project.io.guardClosed':
      'Guard-door closed input from the safety interface.',
  'project.config.mesEndpointIp': 'MES endpoint IP address',
  'project.config.mesPort': 'MES port',
  'project.config.clampSettleTime': 'Clamp settling time',
  'project.decision.toolWorn':
      'The tool is worn. Replace it now or finish the batch?',
  'project.decision.replaceNow': 'Replace now',
  'project.decision.finishBatch': 'Finish batch',
  'project.module.pneumaticPress.name': 'Pneumatic press',
  'project.module.pneumaticPress.description':
      'Pneumatic press with an interlocked access door, part-transfer slide, two-hand start and controlled pneumatic power.',
  'project.module.partPresentSensor.name': 'Part-present sensor',
  'project.module.partPresentSensor.description':
      'Detects the part at the press loading position.',
  'project.controlDomain.press.name': 'Press safety and pneumatic-power domain',
  'project.safety.estopNc': 'Normally closed emergency-stop circuit healthy.',
  'project.safety.pressGuard':
      'Press access guard position from the safety system.',
  'project.safety.twoHandControl':
      'Certified two-hand-control evaluation and button status.',
  'project.safety.pressSafeValve':
      'Safety-rated pneumatic dump valve feedback.',
  'project.interlock.doorCloseRequiresSlideInside':
      'The door may close only when the part slide is fully inside and stopped.',
  'project.interlock.doorOpenPermitted': 'Opening the press door is permitted.',
  'project.interlock.slideMoveRequiresDoorOpen':
      'The part slide may move only while the door is fully open and stopped.',
  'project.interlock.slideOutsideRequiresDoorOpen':
      'The part slide may move outside only while the door is fully open and stopped.',
  'project.interlock.pressRequiresGuardSlideTwoHandPower':
      'Ram down requires the door closed, slide inside, two-hand control active and pneumatic power proven.',
  'project.interlock.pressRetractPermitted': 'Ram retraction is permitted.',
  'project.condition.twoHandStart': 'Two-hand start accepted',
  'project.condition.partPresent': 'Part present at the loading position',
  'project.condition.airPressureOk':
      'Compressed-air pressure above the operating threshold',
  'project.error.pressRecipeInvalid':
      'The press or transfer settling time is outside the validated range.',
  'project.error.pressModeHasNoSequence':
      'The selected press mode has no automatic sequence.',
  'project.error.twoHandReleasedDuringPress':
      'The evaluated two-hand signal was released during the press dwell.',
  'project.error.pressAirPressureLost':
      'Compressed-air pressure was lost during the press cycle.',
  'project.error.pressDownSensorTimeout':
      'Press ram did not reach DOWN sensor _101B202A (EL1809 channel 5).',
  'project.error.pressUpSensorTimeout':
      'Press ram did not reach UP sensor _101B202B (EL1809 channel 6).',
  'project.error.pressPositionSensorsConflict':
      'Press position sensors _101B202A and _101B202B are active together.',
  'project.error.doorClosedSensorTimeout':
      'Door did not reach CLOSED sensor _101B201A (EL1809 channel 3).',
  'project.error.doorOpenSensorTimeout':
      'Door did not reach OPEN sensor _101B201B (EL1809 channel 4).',
  'project.error.doorPositionSensorsConflict':
      'Door position sensors _101B201A and _101B201B are active together.',
  'project.error.slideInsideSensorTimeout':
      'Part slide did not reach INSIDE sensor _101B301A (EL1809 channel 1).',
  'project.error.slideOutsideSensorTimeout':
      'Part slide did not reach OUTSIDE sensor _101B301B (EL1809 channel 2).',
  'project.error.slidePositionSensorsConflict':
      'Slide position sensors _101B301A and _101B301B are active together.',
  'project.alarmAction.pressInterlock':
      'Check the E-stop, safety valve, door, part slide, two-hand controls and pneumatic pressure before resetting.',
  'project.alarmConsequence.pressInterlock':
      'The press sequence is stopped and functional pneumatic requests are withdrawn.',
  'project.step.pressAutoInitialize': 'Initialize automatic press cycle',
  'project.step.pressAutoComplete': 'Complete automatic press cycle',
  'project.step.pressRecordResult': 'Record press result',
  'project.step.pressAwaitTwoHand': 'Wait for two-hand start',
  'project.step.pressCommandRamUp': 'Command press ram up',
  'project.step.pressAwaitRamUp': 'Wait for press ram up',
  'project.step.pressCommandDoorOpen': 'Command press door open',
  'project.step.pressAwaitDoorOpen': 'Wait for press door open',
  'project.step.pressCommandSlideInside': 'Command part slide inside',
  'project.step.pressAwaitSlideInside': 'Wait for part slide inside',
  'project.step.pressTransferSettle': 'Settle transferred part',
  'project.step.pressCommandDoorClose': 'Command press door closed',
  'project.step.pressAwaitDoorClosed': 'Wait for press door closed',
  'project.step.pressCommandRamDown': 'Command press ram down',
  'project.step.pressAwaitRamDown': 'Wait for press ram down',
  'project.step.pressDwell': 'Hold press force for recipe dwell',
  'project.step.pressCommandSlideOutside': 'Command part slide outside',
  'project.step.pressAwaitSlideOutside': 'Wait for part slide outside',
  'project.step.pressSafePositionRamUp':
      'Move press ram up for the shared safe load position',
  'project.step.pressSafePositionDoorOpen':
      'Open press door for the shared safe load position',
  'project.step.pressSafePositionSlideOutside':
      'Move part slide outside for the shared safe load position',
  'project.step.pressSafePositionComplete':
      'Shared safe load position established',
  'project.step.pressHomeRam': 'Home press ram up',
  'project.step.pressHomeDoor': 'Home press door open',
  'project.step.pressHomeSlide': 'Home part slide outside',
  'project.step.pressHomeInitialize': 'Initialize press homing',
  'project.step.pressHomeComplete': 'Press homing complete',
  'project.step.pressChangeoverInitialize': 'Initialize press changeover',
  'project.step.pressChangeoverComplete': 'Press changeover complete',
  'project.step.pressChangeoverValidateModel':
      'Validate selected changeover model',
  'project.step.pressChangeoverRamUp': 'Move press ram up for changeover',
  'project.step.pressChangeoverDoorOpen': 'Open press door for changeover',
  'project.step.pressChangeoverSlideOutside':
      'Move part slide outside for changeover',
  'project.step.pressChangeoverRequestConfirmation':
      'Request tooling and material confirmation',
  'project.step.pressChangeoverAwaitConfirmation':
      'Wait for changeover confirmation',
  'project.condition.pressModelSelected': 'A model recipe is selected',
  'project.condition.pressChangeoverConfirmation':
      'Tooling and material setup confirmed',
  'project.decision.pressChangeoverConfirm':
      'Confirm that tooling and material match the active model recipe.',
  'project.decision.confirmChangeover': 'Confirm changeover',
  'project.decision.repeatChangeoverPosition':
      'Repeat safe changeover positioning',
};

/// Shipped project translation for the demo. Imported project CSV values still
/// take precedence, so integrators can change terminology without PLC edits.
const projectSpanish = <String, String>{
  'project.step.pressAutoInitialize': 'Inicializar ciclo automatico de prensa',
  'project.step.pressAutoComplete': 'Completar ciclo automatico de prensa',
  'project.step.pressRecordResult': 'Registrar resultado de prensado',
  'project.step.pressHomeInitialize': 'Inicializar referenciado de la prensa',
  'project.step.pressHomeComplete': 'Referenciado de la prensa completo',
  'project.step.pressChangeoverInitialize':
      'Inicializar cambio de modelo de la prensa',
  'project.step.pressChangeoverComplete':
      'Cambio de modelo de la prensa completo',
  'project.module.partPresentSensor.name': 'Sensor de presencia de pieza',
  'project.module.partPresentSensor.description':
      'Detecta la pieza en la posición de carga de la prensa.',
  'project.hardware.cx2030':
      'Controlador CX2030 y maestro EtherCAT de la prensa de entrenamiento.',
  'project.hardware.ek1200':
      'Acoplador EtherCAT Box EK1200-5000 de la estación de E/S de la prensa.',
  'project.hardware.el1809':
      'Terminal de entradas digitales de 24 V CC y 16 canales.',
  'project.hardware.el2809':
      'Terminal de salidas digitales de 24 V CC y 16 canales.',
  'project.hardware.el6001':
      'Terminal de interfaz serie RS232 de un canal; no tiene consumidor HAL asignado en la prensa.',
  'project.hardware.el9011':
      'Terminal final EtherCAT de la estación de E/S de la prensa.',
  'project.io.101B301A': 'Alimentador retraído / sensor de corredera adentro.',
  'project.io.101B301B': 'Alimentador extendido / sensor de corredera afuera.',
  'project.io.101B201A': 'Sensor de puerta de acceso cerrada.',
  'project.io.101B201B': 'Sensor de puerta de acceso abierta.',
  'project.io.101B202A': 'Sensor de prensa abajo.',
  'project.io.101B202B': 'Sensor de prensa arriba.',
  'project.io.101S101': 'Entrada directa del pulsador bimanual derecho.',
  'project.io.101S102': 'Entrada directa del pulsador bimanual izquierdo.',
  'project.io.000MB085A_2': 'Presión de aire comprimido menor de 0.3 bar.',
  'project.io.000MB085A_4': 'Presión de aire comprimido mayor de 4.5 bar.',
  'project.io.101B601': 'Sensor de presencia de pieza.',
  'project.io.000K911_Y32': 'Realimentación de Control On.',
  'project.io.000K910A':
      'Espejo ordinario de paro de emergencia sano (no es entrada de seguridad).',
  'project.io.101K301A': 'Orden de alimentador atrás / corredera adentro.',
  'project.io.101K301B': 'Orden de alimentador adelante / corredera afuera.',
  'project.io.101K201A': 'Orden de cerrar la puerta de acceso.',
  'project.io.101K201B': 'Orden de abrir la puerta de acceso.',
  'project.io.101K202A': 'Orden de mover la prensa hacia abajo.',
  'project.io.101K202B': 'Orden de mover la prensa hacia arriba.',
  'project.io.101P101': 'Lámpara del pulsador bimanual derecho.',
  'project.io.101P102': 'Lámpara del pulsador bimanual izquierdo.',
  'project.io.000K951_A1': 'Solicitud funcional Switch Control On.',
  'project.io.000K911_A1': 'Solicitud funcional Enable Control On.',
  'project.error.pressDownSensorTimeout':
      'La prensa no alcanzó el sensor ABAJO _101B202A (EL1809 canal 5).',
  'project.error.pressUpSensorTimeout':
      'La prensa no alcanzó el sensor ARRIBA _101B202B (EL1809 canal 6).',
  'project.error.pressPositionSensorsConflict':
      'Los sensores de prensa _101B202A y _101B202B están activos simultáneamente.',
  'project.error.doorClosedSensorTimeout':
      'La puerta no alcanzó el sensor CERRADA _101B201A (EL1809 canal 3).',
  'project.error.doorOpenSensorTimeout':
      'La puerta no alcanzó el sensor ABIERTA _101B201B (EL1809 canal 4).',
  'project.error.doorPositionSensorsConflict':
      'Los sensores de puerta _101B201A y _101B201B están activos simultáneamente.',
  'project.error.slideInsideSensorTimeout':
      'La corredera no alcanzó ADENTRO _101B301A (EL1809 canal 1).',
  'project.error.slideOutsideSensorTimeout':
      'La corredera no alcanzó AFUERA _101B301B (EL1809 canal 2).',
  'project.error.slidePositionSensorsConflict':
      'Los sensores de corredera _101B301A y _101B301B están activos simultáneamente.',
  'project.step.pressChangeoverValidateModel':
      'Validar el modelo seleccionado para el cambio',
  'project.step.pressChangeoverRamUp':
      'Subir la prensa para el cambio de modelo',
  'project.step.pressChangeoverDoorOpen':
      'Abrir la puerta para el cambio de modelo',
  'project.step.pressChangeoverSlideOutside':
      'Mover la corredera afuera para el cambio de modelo',
  'project.step.pressSafePositionRamUp':
      'Subir la prensa para la posiciÃ³n segura de carga compartida',
  'project.step.pressSafePositionDoorOpen':
      'Abrir la puerta para la posiciÃ³n segura de carga compartida',
  'project.step.pressSafePositionSlideOutside':
      'Mover la corredera afuera para la posiciÃ³n segura de carga compartida',
  'project.step.pressSafePositionComplete':
      'PosiciÃ³n segura de carga compartida establecida',
  'project.step.pressChangeoverRequestConfirmation':
      'Solicitar confirmación de herramental y material',
  'project.step.pressChangeoverAwaitConfirmation':
      'Esperar confirmación del cambio de modelo',
  'project.condition.pressModelSelected':
      'Hay una receta de modelo seleccionada',
  'project.condition.pressChangeoverConfirmation':
      'Herramental y material confirmados',
  'project.decision.pressChangeoverConfirm':
      'Confirme que el herramental y el material coinciden con la receta activa.',
  'project.decision.confirmChangeover': 'Confirmar cambio de modelo',
  'project.decision.repeatChangeoverPosition':
      'Repetir posicionamiento seguro para cambio',
};

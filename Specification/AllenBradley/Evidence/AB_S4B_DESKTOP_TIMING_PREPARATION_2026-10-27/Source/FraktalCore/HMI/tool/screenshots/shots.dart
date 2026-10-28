/// The screenshot catalog: every feature of the generic HMI, each staged on
/// the integrated demo at the moment that shows it. One entry = one picture in
/// `doc/screenshots`, with the caption and spec clauses the docs print under it.
///
/// A script only does what an operator, an engineer or the plant would do:
/// log in, navigate, press, wait for the plant (SimTour) to get there.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/content/module_content_controller.dart';
import 'package:fraktal_hmi/data/repository_factory.dart'
    show ConnectionStartupException;
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

import 'demo_content.dart';
import 'hmi_driver.dart';

class Shot {
  final String id;
  final String group;
  final String title;
  final String caption;
  final List<String> spec;
  final Future<void> Function(HmiDriver d) stage;
  const Shot(
      this.id, this.group, this.title, this.caption, this.spec, this.stage);
}

/// The groups, in the order the catalog presents them.
const groups = {
  'overview': 'Plant and stations',
  'sequence': 'Sequences and diagnosis',
  'alarms': 'Alarms and release',
  'performance': 'Performance',
  'hardware': 'Hardware, safety and I/O',
  'devices': 'Device modules',
  'manual': 'Manual operation',
  'config': 'Configuration data',
  'authoring': 'Authored views',
  'access': 'Access and settings',
  'setup': 'First run and connection',
  'look': 'Themes, languages and panel sizes',
};

// ---- staging helpers ----

/// A production-like demo station, logged in as [user], authored content in.
Future<void> station(HmiDriver d,
    {String user = 'admin1',
    String theme = 'processGrey',
    bool commissioning = false,
    bool content = true,
    String language = 'en',
    ControlScale scale = ControlScale.compact,
    Size size = const Size(1440, 900),
    SimRepository? repository}) async {
  await d.boot(
      repository: repository ??
          SimRepository(commissioning: commissioning, epoch: demoEpoch),
      theme: theme,
      language: language,
      scale: scale,
      size: size);
  if (content) await seedDemoContent(d);
  if (user.isNotEmpty) await d.login(user);
}

/// Runs the plant to just past the clamp jam: CylB has timed out and the
/// station stopped ON N40 (§6.9, §8.3).
Future<void> toJam(HmiDriver d, {Duration after = Duration.zero}) async {
  await d.until('cylinder B jammed', () => d.node('StationA').faultActive,
      within: const Duration(seconds: 160));
  if (after > Duration.zero) await d.advance(after);
}

bool _atStep(HmiDriver d, String path, int step) =>
    d.node(path).step?.stepNo == step;

final List<Shot> shots = [
  // ==== overview ====
  Shot(
      'overview',
      'overview',
      'Plant overview',
      'The landing screen: one tile per root Unit of the forest, each with its '
          'model, mode, counters and the metrics an administrator authored for '
          'the station TYPE, so a dozen stations read as one table.',
      ['§3.1a', '§3.13', 'LOC §7.5'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 12));
    await d.overview();
  }),
  Shot(
      'station-overview',
      'overview',
      'Station overview',
      'A root Unit\'s Overview tab: current step, mode and model, derived state '
          'flags with how long each has held, counters, OEE and the live signal '
          'tower - all rendered from published data, no station-specific code.',
      ['§3.12', '§3.13', '§6.5', '§8.13'], (d) async {
    await station(d);
    await d.until('Station A clamping', () => _atStep(d, 'StationA', 40));
    await d.open('StationA', tab: 'overview');
  }),
  Shot(
      'nested-unit',
      'overview',
      'Recursive Units',
      'Packer C contains its own Unit: the Labeler runs a mode and a chain of '
          'its own and is commanded by the packer like any other child module.',
      ['§3.1', '§3.3'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 6));
    d.app.toggleExpand('PackerC.Labeler');
    await d.open('PackerC.Labeler', tab: 'sequence');
  }),

  // ==== sequence ====
  Shot(
      'sequence-chart',
      'sequence',
      'Sequence flow chart',
      'The §3.13 chart of the AUTO chain, built from the steps the PLC '
          'recorded: the live cursor with its elapsed time against the declared '
          'guard, a parallel fork whose two legs run on rows of their own, and '
          'a handled warning kept as history on the row that raised it.',
      ['§3.13', '§6.9(e)', '§6.12'], (d) async {
    await station(d);
    await d.until(
        'fork running after a reader retry',
        () =>
            _atStep(d, 'StationA', 45) &&
            d
                .node('StationA')
                .sequenceSteps
                .any((s) => s.stepNo == 55 && (s.warningActive || s.active)) &&
            d
                .node('StationA')
                .sequenceSteps
                .any((s) => s.stepNo == 55 && s.warningActive));
    await d.open('StationA', tab: 'sequence');
  }),
  Shot(
      'sequence-fault',
      'sequence',
      'A step that faulted',
      'Cylinder B timed out: the chain stopped ON N40, the row carries the '
          'error and blinks, and tapping it drills into the module that '
          'actually failed - the first-out is produced by the contract, '
          'not hand-coded per step.',
      ['§6.9', '§3.13', '§8.2'], (d) async {
    await station(d);
    await toJam(d);
    await d.open('StationA', tab: 'sequence');
  }),
  Shot(
      'stall-pending',
      'sequence',
      'A stall is pending, not a fault',
      'Before the cylinder\'s own timeout the step only outruns its guard: a '
          'LOW pending diagnostic names what the chain waits for and which '
          'condition is false, while nothing has faulted yet.',
      ['§6.9(b)', '§6.5'], (d) async {
    await station(d);
    await d.until(
        'clamp step past its guard',
        () =>
            _atStep(d, 'StationA', 40) &&
            d.node('StationA').currentStepTimedOut &&
            !d.node('StationA').faultActive,
        within: const Duration(seconds: 160));
    await d.open('StationA', tab: 'overview');
  }),

  // ==== alarms ====
  Shot(
      'alarm-path',
      'alarms',
      'Event path and first-out',
      'The fault tints every ancestor from the root to its source, the '
          'global banner names the worst active event, and the module shows its '
          'first-out with the electrical tag of the sensor involved.',
      ['§3.13', '§8.2', '§8.3', 'HMI §I/O identity'], (d) async {
    await station(d);
    await toJam(d);
    d.app.toggleExpand('StationA.ClampStation');
    await d.open('StationA.ClampStation.CylB', tab: 'overview');
  }),
  Shot(
      'release-why',
      'alarms',
      'Why will it not start?',
      'Act-or-explain: a blocked Start opens the full release report - the '
          'manual-reset alarm, the safety circuit, control power that must be '
          're-armed - every reason at once, never just the first.',
      ['§7.8', '§8.3(b)', '§9.8'], (d) async {
    await station(d);
    await toJam(d, after: const Duration(seconds: 4));
    await d.open('StationA', tab: 'overview');
    await d.app.showReleaseReportStart('StationA');
    await d.settle();
  }),
  Shot(
      'events',
      'alarms',
      'Active events and history',
      'Active events carry the §8.9 rationalization - what to do and what '
          'happens if nobody does - and the history keeps every closed event '
          'with its duration, including operator actions as audit entries.',
      ['§8.3', '§8.9', '§8.10'], (d) async {
    await station(d);
    await toJam(d, after: const Duration(seconds: 12));
    await d.open('StationA', tab: 'events');
  }),
  Shot(
      'shelved',
      'alarms',
      'Shelving an annunciation',
      'A rationalized, shelvable warning can be shelved for 30 minutes: its '
          'annunciation is suppressed and logged, the event stays listed and '
          'control is unaffected. Safety reasons are never shelvable.',
      ['§8.10'], (d) async {
    await station(d, user: 'tech1');
    await d.until('air pressure dip',
        () => d.node('ConveyorB.AirMonitor').activeEvents.isNotEmpty,
        within: const Duration(seconds: 60));
    await d.sim.shelveAlarm('ConveyorB', 'ConveyorB.AirMonitor',
        'project.reason.airPressureLow', const Duration(minutes: 30));
    await d.advance(const Duration(seconds: 1));
    await d.open('ConveyorB', tab: 'events');
  }),
  Shot(
      'decision',
      'alarms',
      'Operator decision',
      'A chain asks instead of guessing: the worn robot tool raises a §6.11 '
          'decision with a default, answered from the panel and logged.',
      ['§6.11'], (d) async {
    await station(d);
    await d.until('tool decision', () => d.node('StationA').decision != null,
        within: const Duration(seconds: 100));
    await d.open('StationA', tab: 'overview');
  }),

  // ==== performance ====
  Shot(
      'statistics',
      'performance',
      'Counters, OEE and shifts',
      'Good, NOK and rework counts, OEE with its factors and trend, and the '
          'current shift against its production target with the closed shifts '
          'before it - accounting the line calendar drives, not a scheduler.',
      ['§8.5.1', '§8.5.2', '§8.11.2'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 20));
    await d.open('StationA', tab: 'statistics');
  }),
  Shot(
      'cycle-analysis',
      'performance',
      'Cycle-time analysis',
      'Why cycle time moved: the trend splits each cycle into work and wait '
          'classes, the Gantt shows the last cycle against its guards, the '
          'Pareto ranks steps over time, and command timing drills to the module '
          'command that consumed the time.',
      ['§8.11.4'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 20));
    await d.open('StationA', tab: 'statistics');
    await d.scrollTo(find.textContaining('Cycle-time trend'));
  }),

  // ==== hardware ====
  Shot(
      'hardware',
      'hardware',
      'Hardware and safety',
      'Certified safety mirrored read-only (muting shown, never granted), the '
          'control domain shared by two peer Units with its power groups, '
          'controller and clock health, the signal tower and the digital '
          'nameplate.',
      ['§9.8', '§2.7', '§8.12', '§8.13', '§3.10.1'], (d) async {
    await station(d);
    await d.until(
        'infeed muting', () => d.node('StationA').safety!.mutingActive,
        within: const Duration(seconds: 40));
    await d.open('StationA', tab: 'hardware');
  }),
  Shot(
      'safety-demand',
      'hardware',
      'Guard opened: outputs withdrawn',
      'The guard opened to free the jam: the safety circuit holds the safe '
          'state, the valve zones trip and stay off until Control On is pressed '
          'again - nothing resumes on its own.',
      ['§9.8', 'SAFETY profile'], (d) async {
    await station(d);
    await toJam(d, after: const Duration(seconds: 4));
    await d.open('StationA', tab: 'hardware');
  }),
  Shot(
      'fieldbus',
      'hardware',
      'Fieldbus and forcing',
      'The physical bus beside the module tree: live channel values under '
          'their electrical tags, a terminal identity mismatch found at '
          'commissioning, and an output forced in MANUAL - offered only because '
          'a commissioning gate is declared, and announced by the gate strip.',
      ['§10.5.1', '§7.5', 'HMI §I/O identity'], (d) async {
    await station(d, user: 'tech1', commissioning: true);
    await d.sim.setMode('StationA', UnitMode.manual);
    await d.sim.forceChannel('StationA', 'StationA.Separator1.Extend',
        force: true, boolValue: true);
    await d.advance(const Duration(seconds: 2));
    await d.fieldbus();
    await d.tapIconBeside('=A1+S1-A10', Icons.chevron_right);
    await d.tapText('=A1+S1-A13');
  }),
  Shot(
      'link-lost',
      'hardware',
      'Device link lost',
      'The conveyor loses its heartbeat to the line controller: the link facet '
          'says so, and a derived flag it can no longer compute turns stale - '
          'shown as unknown, never as a confident "false".',
      ['Annex D', '§3.12'], (d) async {
    await station(d);
    await d.until(
        'heartbeat lost', () => d.node('ConveyorB').link?.linked == false,
        within: const Duration(seconds: 90));
    await d.open('ConveyorB', tab: 'overview');
    await d.scrollTo(find.text('Link lost'));
  }),

  // ==== devices ====
  Shot(
      'vision',
      'devices',
      'Vision camera',
      'A camera module gets a vision view '
          'from what it publishes: the last judgement and its result string, the '
          'trigger command and the device link.',
      ['§7.6.1', 'Annex D'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 8));
    await d.open('StationA.Camera', tab: 'vision');
  }),
  Shot(
      'code-reader',
      'devices',
      'Code reader',
      'Reads, no-reads and the last '
          'code, recognised from the module\'s published outputs.',
      ['§7.6.1'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 8));
    await d.open('StationA.CodeReader', tab: 'code-reader');
  }),
  Shot(
      'rfid',
      'devices',
      'RFID reader',
      'The pallet tag currently in front of '
          'the reader, its quality and a read command.',
      ['§7.6.1', '§3.16'], (d) async {
    await station(d);
    await d.until('tag read', () => _atStep(d, 'StationA', 30));
    await d.open('StationA.RfidReader', tab: 'rfid');
  }),
  Shot(
      'motion',
      'devices',
      'Robot motion',
      'Position, target, velocity and '
          'following error of the robot axis while it picks, with the explicit '
          'non-safety notice.',
      ['Annex G', 'Annex I'], (d) async {
    await station(d, user: 'op1');
    await d.open('StationA.Robot', tab: 'motion');
    await d.until(
        'robot moving', () => d.node('StationA.Robot').motion!.moving);
  }),
  Shot(
      'part-data',
      'devices',
      'Part traceability',
      'The part in the robot gripper: its identity, verdict and the measured '
          'values against their limits.',
      ['§3.16', 'Annex E'], (d) async {
    await station(d);
    await d.advance(const Duration(seconds: 14));
    await d.open('StationA.Robot', tab: 'overview');
  }),

  // ==== manual ====
  Shot(
      'manual',
      'manual',
      'Manual commands',
      'In MANUAL a module offers its '
          'published command catalog, routed through the module so interlocks '
          'still defend, with the module\'s own inputs and outputs beside it.',
      ['§7.6.1', '§3.4'], (d) async {
    await station(d, user: 'tech1');
    await d.sim.setMode('StationA', UnitMode.manual);
    await d.sim.manualCommand('StationA', 'StationA.ClampStation.CylB', 2);
    await d.advance(const Duration(seconds: 2));
    d.app.toggleExpand('StationA.ClampStation');
    await d.open('StationA.ClampStation.CylB', tab: 'overview');
  }),
  Shot(
      'hold-to-run',
      'manual',
      'Hold-to-run jog',
      'Held commands are hold-to-run: '
          'the panel refreshes the request while the button is down and the PLC '
          'stops the motion the moment the asking stops. Not a dead-man.',
      ['§7.6.1a'], (d) async {
    await station(d, user: 'tech1');
    await d.sim.setMode('StationA', UnitMode.manual);
    await d.advance(const Duration(seconds: 1));
    await d.open('StationA.Robot', tab: 'overview');
  }),
  Shot(
      'manual-blocked',
      'manual',
      'A manual command that is not released',
      'Pressing a command that is not released explains itself instead of '
          'doing nothing: here the Unit is in AUTO and the PLC policy asks '
          'for TECHNICIAN where an OPERATOR is logged in.',
      ['§7.6.0', '§7.8', '§7.7'], (d) async {
    await station(d);
    // The PLC policy an administrator set: manual commands need TECHNICIAN.
    await d.sim
        .setAccessLevel('StationA', GatedAction.manual, AccessLevel.technician);
    await d.login('op1');
    await d.open('StationA.Separator1', tab: 'overview');
    await d.app.showReleaseReportManual('StationA', 'StationA.Separator1', 1);
    await d.settle();
  }),

  // ==== config ====
  Shot(
      'configuration',
      'config',
      'Model and station data',
      'Model data per model, editable for any model without a changeover; '
          'station data grouped by data class with the levels the PLC '
          'computed; flags as checkboxes, choices as translated lists, units '
          'from the published unit code.',
      ['§3.8a', '§3.8d', '§3.10.2'], (d) async {
    await station(d);
    await d.open('StationA', tab: 'configuration');
  }),
  Shot(
      'line-calendar',
      'config',
      'Line data and the shift calendar',
      'Line data owned by one station and mirrored by its neighbour: the '
          'weekly shift calendar with weekday selection and a production '
          'target per shift.',
      ['§3.8e', '§8.5.2'], (d) async {
    await station(d);
    await d.open('StationA', tab: 'configuration');
    await d.scrollTo(find.byKey(const ValueKey('cfg-card-lineCfg')));
  }),
  Shot(
      'data-classes',
      'config',
      'Data classes for an operator',
      'The same page for an OPERATOR, once the panel opens Configuration to '
          'operators: quality values are theirs to read, the MES integration '
          'class is listed but its values withheld by the PLC.',
      ['§3.8d'], (d) async {
    await station(d, user: 'op1');
    // An ADMIN's panel policy (LOC §6): Configuration defaults to ENGINEER.
    await d.content.setRequiredLevel(
        'StationA', ModuleSection.configuration, AccessLevel.operator);
    await d.open('StationA', tab: 'configuration');
    await d.scrollTo(find.text('Data class: quality'));
  }),
  Shot(
      'parameter-sets',
      'config',
      'Parameter sets',
      'Named sets of a root\'s values, saved and loaded all-or-nothing on the '
          'PLC, exported as documents another station can import.',
      ['§3.8b'], (d) async {
    await station(d);
    await d.sim
        .saveConfigSet('StationA', 'commissioned-2026-10', CfgKind.stationCfg);
    await d.sim.saveConfigSet('StationA', 'night-shift', CfgKind.lineCfg);
    await d.open('StationA', tab: 'configuration');
    await d.tapTooltip('Parameter sets');
  }),
  Shot(
      'durability',
      'config',
      'Durability is displayed',
      'Accepted means live, not durable: a configuration image that could not '
          'be restored is annunciated, naming the module, until an engineer '
          'accepts the loss.',
      ['§3.8b'], (d) async {
    await station(d,
        repository: SimRepository(
            commissioning: false,
            epoch: demoEpoch,
            restoreLost: true,
            restoreLostPath: 'StationA.ClampStation.CylB'));
    await d.advance(const Duration(seconds: 4));
    await d.open('StationA', tab: 'overview');
  }),

  // ==== authoring ====
  Shot(
      'custom-view',
      'authoring',
      'Maintenance view on a machine picture',
      'An administrator-authored maintenance view: live state drawn on the '
          'machine picture at fractions of the image, so it stays on the sensor '
          'it annotates at any panel size, with a switchable I/O-tag layer.',
      ['LOC §7.2', 'LOC §7.4'], (d) async {
    await station(d);
    await d.until('part clamped',
        () => d.node('StationA').publishedValues['OutImm/ClampClosed'] == true);
    await d.open('StationA', tab: 'cell-view');
  }),
  Shot(
      'guidance',
      'authoring',
      'Changeover guidance',
      'During CHANGEOVER the chain waits for the operator to swap the gripper '
          'fingers; the authored guidance opens by itself on that '
          'WAIT_OPERATOR step - and never advances the step by being dismissed.',
      ['LOC §7', '§6.11', '§3.4'], (d) async {
    await station(d);
    await d.sim.setMode('StationA', UnitMode.changeover);
    await d.sim.setModel('StationA', 'A200');
    await d.open('StationA', tab: 'overview');
    await d.sim.start('StationA');
    await d.until('waiting for the operator', () => _atStep(d, 'StationA', 30));
    await d.advance(const Duration(seconds: 1));
  }),
  Shot(
      'layout-editor',
      'authoring',
      'Arranging a module\'s tabs',
      'An ADMIN arranges cards, columns, tabs and the default tab per module or '
          'per module type; changes stay a local draft until published, with '
          'revisions kept for rollback.',
      ['LOC §7', 'HMI_CONTRACT'], (d) async {
    await station(d);
    await d.open('StationA', tab: 'overview');
    await d.tapTooltip('Edit module tabs');
  }),
  Shot(
      'documents',
      'authoring',
      'Information and documents',
      'Localizable module information and the PDFs attached to the module.',
      ['LOC §5'], (d) async {
    await station(d);
    await d.open('StationA', tab: 'description');
  }),

  // ==== access ====
  Shot(
      'login',
      'access',
      'Login',
      'Per-root login against the PLC\'s own '
          'access provider; every control re-checks its level on the PLC.',
      ['§7.7'], (d) async {
    await station(d, user: '');
    await d.open('StationA', tab: 'description');
    await d.tapText('Login');
  }),
  Shot(
      'access-policy',
      'access',
      'PLC access policy',
      'The PLC-authoritative policy: the minimum level per gated action and the '
          'read and write levels of each data class, edited from the panel and '
          'enforced by the controller.',
      ['§7.7', '§3.8d(b)'], (d) async {
    await station(d);
    // Thresholds an administrator commissioned, through the PLC policy path.
    for (final (action, level) in const [
      (GatedAction.dataWrite, AccessLevel.technician),
      (GatedAction.manual, AccessLevel.technician),
      (GatedAction.changeover, AccessLevel.technician),
      (GatedAction.modeChange, AccessLevel.operator),
      (GatedAction.startStop, AccessLevel.operator),
      (GatedAction.alarmHistory, AccessLevel.operator),
      (GatedAction.alarmReset, AccessLevel.operator),
      (GatedAction.alarmShelve, AccessLevel.technician),
      (GatedAction.powerControl, AccessLevel.technician),
      (GatedAction.configSet, AccessLevel.engineer),
      (GatedAction.accessPolicy, AccessLevel.admin),
    ]) {
      await d.sim.setAccessLevel('StationA', action, level);
    }
    await d.open('StationA', tab: 'overview');
    await d.tapKey('settings');
    await d.tapKey('edit-plc-access-policy');
  }),
  Shot(
      'settings',
      'access',
      'Settings',
      'Theme, size preset, language, '
          'keyboard and the admin entries for connection, Unit assignment and '
          'policy - one place.',
      ['HMI_CONTRACT'], (d) async {
    await station(d);
    await d.overview();
    await d.tapKey('settings');
  }),

  // ==== setup ====
  Shot(
      'setup-language',
      'setup',
      'First run: languages',
      'Before anything else '
          'the panel asks which languages it offers.',
      ['LOC §2'], (d) async {
    await d.bootSetup();
  }),
  Shot(
      'setup-connection',
      'setup',
      'First run: connection',
      'The connection '
          'wizard: the built-in simulation, a gateway or a direct OPC UA/ADS '
          'endpoint.',
      ['OPCUA_TRANSPORT'], (d) async {
    await d.bootSetup(
        settings: const ConnectionSettings(
            enabledLanguageCodes: ['en', 'es'],
            activeLanguageCode: 'en',
            languageSelectionComplete: true,
            appearanceSetupComplete: true));
  }),
  Shot(
      'setup-units',
      'setup',
      'First run: Unit assignment',
      'Which root Units '
          'of the discovered forest this panel shows and may command.',
      ['§3.1a', 'HMI_CONTRACT'], (d) async {
    await d.bootSetup(
        settings: const ConnectionSettings(
            transport: ConnectionTransport.simulation,
            endpoint: '',
            everConnected: true,
            enabledLanguageCodes: ['en'],
            activeLanguageCode: 'en',
            languageSelectionComplete: true,
            appearanceSetupComplete: true));
    await d.advance(const Duration(seconds: 2));
    await d.tapKey('unit-select-StationA');
    await d.tapKey('unit-select-ConveyorB');
  }),
  Shot(
      'connection-blocked',
      'setup',
      'No PLC, no controls',
      'Without a live link the operator shell is withdrawn rather than left '
          'showing stale values; editing the connection unlocks after 30 s.',
      ['HMI_CONTRACT', '§14'], (d) async {
    await d.bootSetup(
        settings: const ConnectionSettings(
            transport: ConnectionTransport.gateway,
            endpoint: 'wss://press-hmi.plant.local/fraktal',
            everConnected: true,
            selectedUnitPaths: ['StationA'],
            unitSelectionComplete: true,
            enabledLanguageCodes: ['en'],
            activeLanguageCode: 'en',
            languageSelectionComplete: true,
            appearanceSetupComplete: true),
        // What the real factory throws when its TCP preflight fails.
        repository: () => throw const ConnectionStartupException(
            stage: 'tcp-preflight',
            message:
                'press-hmi.plant.local:443 is not reachable: connection refused.',
            remediation: 'Start the Fraktal gateway and verify its address, '
                'port, firewall, and route.'));
    await d.advance(const Duration(seconds: 31));
  }),

  // ==== look ====
  for (final (theme, label) in const [
    ('processGreyDark', 'Process Grey Dark'),
    ('likeABosch', 'Like a Bosch'),
    ('midnightConsole', 'Midnight Console'),
    ('neonCyan', 'Neon Cyan'),
    ('glassMidnight', 'Midnight Glass'),
    ('aetherBlueprint', 'Aether Blueprint'),
    ('ivoryTeal', 'Ivory Teal'),
    ('highContrastDark', 'High contrast dark'),
  ])
    Shot(
        'theme-$theme',
        'look',
        'Theme: $label',
        'The same station in the $label theme. Status colours keep their §8.1 '
            'meaning in every theme; only the shade adapts to the surface.',
        ['HMI §Status colours'], (d) async {
      await station(d, theme: theme);
      await d.until('Station A clamping', () => _atStep(d, 'StationA', 40));
      await d.open('StationA', tab: 'sequence');
    }),
  Shot(
      'language-es',
      'look',
      'Spanish',
      'Every string resolves through the '
          'runtime catalog: standard texts and the project\'s own, per language.',
      ['LOC §2'], (d) async {
    await station(d, language: 'es');
    await d.until('Station A clamping', () => _atStep(d, 'StationA', 40));
    await d.open('StationA', tab: 'overview');
  }),
  Shot(
      'touch-keyboard',
      'look',
      'On-screen keyboard',
      'A touch panel gets its '
          'own keyboard beside - never over - the field it feeds.',
      ['HMI_CONTRACT'], (d) async {
    await d.boot(
        repository: SimRepository(commissioning: false, epoch: demoEpoch),
        floatingKeyboard: true);
    await d.login('admin1');
    await d.open('StationA', tab: 'configuration');
    await d.tester.tap(find.byType(EditableText).first);
    await d.settle();
  }),
  Shot(
      'large-controls',
      'look',
      'Large touch preset',
      'Control size is a '
          'panel preset: touch targets, icons, rail and tree rows grow together '
          'for gloves.',
      ['HMI_CONTRACT'], (d) async {
    await station(d, scale: ControlScale.large);
    await d.open('StationA', tab: 'overview');
  }),
  Shot(
      'phone',
      'look',
      'Phone width',
      'The same HMI at phone width: the tree '
          'becomes a drawer and the view switch moves into the bar.',
      ['HMI_CONTRACT'], (d) async {
    await station(d, size: const Size(412, 892));
    await d.open('StationA', tab: 'sequence');
  }),
  Shot(
      'engineering-gates',
      'look',
      'A commissioning build says so',
      'A build with commissioning gates announces each one on a permanent, '
          'non-dismissible strip - the weakest alarm in the system, on purpose.',
      ['§7.5.2'], (d) async {
    await station(d, commissioning: true);
    await d.advance(const Duration(seconds: 6));
    await d.overview();
  }),
];

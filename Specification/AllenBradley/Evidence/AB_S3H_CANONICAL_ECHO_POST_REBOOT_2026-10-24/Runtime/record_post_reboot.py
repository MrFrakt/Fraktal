from pathlib import Path
import json

R = Path(__file__).parent
AB = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley')
NAME = 'AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24'
value = json.loads((R / 'post_reboot_observation_01.json').read_text())
assert not value['controllerReady'] and value['controllerChangingOperations'] == 0
assert value['sameExceptionCodeAndModuleOffset'] and value['sameLibCommsFrameOffsets']

summary = f'''**Latest, 2026-10-24: Windows reboot did not recover the virtual controller.**
Windows booted at 06:25:37 UTC; Echo's automatic startup exited with code 1
at 06:26:46 UTC. The service is Running, but exact controller 601FC87B is
enabled/ClosedExternally, RemoteProgram/Remote, not faulted, with no emulator
process or CIP listener. The fresh dump repeats 0xC0000005 in libComms.dll
at offset 0x50C2A4 and the same seven libComms frame offsets. The cause remains
unconfirmed. The observed reboot is not an agent power-state retry.

This continuation performed read-only checks only. All 159 project and two
diagnostic source pins, and the unused C6 deployment image, remain exact.
The diagnostic approval b76d12f2… remains recorded and unused. Its baseline
identity/session/document guards cannot pass while the controller is absent;
no upload, download, mode command or tag write ran. Controller definitions
and retained-state files were preserved. The consumed restart approval does
not authorize a further restart/reset/recreation. Rockwell's published next
step after unsuccessful reboot is technical support; no underlying ASLR or
retained-state cause has been established. Read
[post-reboot evidence](Evidence/{NAME}.md).
S3h remains incomplete and V2 inactive. No commit or push.

'''
short = f'''**Latest, 2026-10-24: the owner rebooted Windows; the virtual controller
still crashes during startup.** Echo service is Running, but 601FC87B remains
ClosedExternally with no emulator/CIP listener. The fresh dump repeats the
same libComms.dll exception and frame offsets. This continuation was read-only;
the existing diagnostic approval remains unused. Current baseline readiness
is unverified, S3h incomplete and V2 inactive. Continue from the
[post-reboot evidence](Evidence/{NAME}.md) and plan §2; another power/reset/
recreation operation needs its own authorized scope. No commit or push.

'''
for filename, anchor, replacement in (
    ('AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md', '## 2. State at hand-over (2026-10-20)\n\n', summary),
    ('AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md', '## Current continuation state (2026-10-20)\n\n', short),
    ('AB_CANONICAL_PUBLICATION_S3H_NOTES_2026-10-23.md', '# S3h preparation: Part, host events, identity and signal tower\n\n', short),
):
    path = AB / filename
    text = path.read_text(encoding='utf-8')
    assert text.count(anchor) == 1 and NAME not in text
    old = '**Latest, 2026-10-23: authorized Echo restart failed during emulator startup.**'
    assert text.count(old) == 1
    text = text.replace(old, '**Earlier, 2026-10-23: authorized Echo restart failed during emulator startup.**', 1)
    path.write_text(text.replace(anchor, anchor + replacement, 1), encoding='utf-8')

path = AB / 'AB_FROZEN_CONTRACTS_V2.json'
document = json.loads(path.read_text())
assert not document['active']
document['approvedTraceabilityCorrection'].update(
    windowsRebootObserved=True, windowsRebootRecoveredController=False,
    postRebootEvidence='Evidence/' + NAME + '.md',
    diagnosticSessionApprovalConsumed=False, diagnosticNativeDownloadAttempted=False,
    diagnosticBlockedByEmulatorStartupCrash=True, currentBaselineReadinessVerified=False)
path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')

references = dict(
    releaseNotes='https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?v1=66077',
    gettingResultsGuide='https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/9310-gr001_-en-p.pdf',
    consultedDate='2026-10-24',
    relevantGuidance='Release notes recommend host reboot for possible initialization/ASLR failures and contacting technical support if it persists. Getting Results Guide chapter 4 describes Diagnostics Viewer and Data Collector.',
    aslrConfirmedHere=False, stateCorruptionConfirmedHere=False,
    vendorCollectorRun=False,
    collectorNotRunReason='The documented collector includes controller memory data; this evidence exports selected logs and crash metadata only, with no project memory/credential archive.')
with (R / 'vendor_references_01.json').open('x') as out:
    json.dump(references, out, indent=2)

report = f'''# Echo startup after Windows reboot — 2026-10-24

**The host reboot completed; the virtual controller still fails during startup.**
This continuation performed read-only checks and exported selected logs and crash
metadata. It made no controller-changing operation. The already approved S3h
diagnostic session has not begun, and its approval remains recorded and unused.

| Check | Observed result |
|---|---|
| Windows last boot | 2026-10-24 06:25:37.500 UTC (00:25:37.500 America/Mexico_City) |
| Echo service | Running, version 4.0.1437; personalized license active |
| Automatic controller startup | 06:26:38 UTC; emulator exits with code 1 at 06:26:46 UTC |
| Target | GUID 91dec7d6-8ac3-45c9-ab2e-0d039c7006fd, serial 601FC87B, 127.0.0.1, slot 0, v38.011 |
| SDK post-state | Enabled, ClosedExternally, RemoteProgram, Remote, not faulted |
| Native emulator / TCP 44818 listener | Absent / absent |
| Native exception | 0xC0000005, libComms.dll +0x50C2A4, parameters [0, 0] |
| S3h diagnostic upload/download/tag writes | Not started / not started / zero |
| Agent power changes / mode commands / fault clears / clock changes | 0 / 0 / 0 / 0 |

The fresh native dump has a new timestamp (06:26:46.869812 UTC), fault thread
21232 and size 1,035,743,890 bytes. Its exception code/module offset and seven
libComms frame offsets match the preceding authorized restart failure:
50C2A4, 53068B, 5306B4, 36BC94, 465761, 23DF2E and AB024. This is an x86
EBP-chain observation without private vendor symbols. It confirms recurrence,
not the underlying cause. Neither ASLR nor retained-state corruption is proved.

Controller SDK project/path strings are empty while no emulator is available;
they do not establish that the retained PLC image is empty. Controller definitions
and state files remain in the original vendor locations. The dump, power-down
image and credential files are not copied into the payload. Only bounded
exception/module metadata and frame-chain control addresses are exported.
State files have hashes/lengths/timestamps only. The initial metadata probe
looked in Root/FaultDump.dmp, which was absent; the existing reader correctly
finds the dump under sd/RockwellAutomation/601FC87B/Faults.

The installed local FactoryTalk Diagnostics SQLite buffer was opened with
mode=ro and query_only enabled. It contains zero rows. This does not establish
whether other Diagnostics Viewer destinations hold messages. The vendor's
full Data Collector was not run: its documented output includes controller
memory, while this report deliberately keeps the project and credentials out
of evidence payloads.

Rockwell's [Echo 4.00 release notes]({references['releaseNotes']})
recommend contacting technical support when an initialization problem persists
after host reboot. The [Getting Results Guide, chapter 4]({references['gettingResultsGuide']})
describes Diagnostics Viewer and support data collection. These sources do not
identify this particular libComms failure. The selected startup logs, version,
controller identity and repeated crash offsets are ready for vendor diagnosis.
No state reset, controller recreation or firmware/network/security setting
change was attempted or inferred from the earlier restart approval.

Verification and acceptance boundary:

- All 159 project source bindings and both diagnostic wrapper bindings match.
  The unused prepared ACD remains C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC.
- Existing exact-source 2,149 AB tests, two-target v38 builds/read-backs and 79%
  Capacity evidence are reused; no production code or PLC image changed.
- The spec, contracts and strict consistency gates, 74 root tests and whitespace
  check pass in the attached new logs. Flutter is not applicable; no HMI change.
- All 37 predecessor records / 8,576 artifacts are re-hashed by the payload seal.
- The original diagnostic approval call_b76d12f2f038411386f83c339fcd94e0:0 remains
  unused. Its original baseline guards stop execution before backup/download.
  The prior one-shot restart approval is already consumed and was not repeated.
- S3h's 41 candidate checks, native timing and current final baseline checks
  were not run. The previous 39 comparisons and 31 baseline checks remain
  historical evidence at their recorded scope. S3h is incomplete; V2 inactive.

Work folder: `{R.as_posix()}`. New append-only
[payload manifest]({NAME}/manifest.json). No commit or push.
'''
with (AB / 'Evidence' / (NAME + '.md')).open('x', encoding='utf-8') as out:
    out.write(report)
print(json.dumps(dict(recorded=True, controllerReady=False, diagnosticApprovalConsumed=False)))

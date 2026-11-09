# S6-Q — Native Qualification of Collapsed Profiles on Echo 601FC87B and Baseline Switch

2026-11-08 / 2026-11-09, America/Mexico_City (04:15–06:05 UTC on 2026-11-09). Repository
head preceding WP6.7/WP6.8. Guarded Native Session S6-Q on the workstation FactoryTalk
Logix Echo emulator `0x601FC87B` (slot 0, v38.011, `127.0.0.1`) under standing owner
decision O3, following plan §4 and §5.3.

**The session passed completely across all three candidate images, the standing
reason-21 shelving acceptance check, and the official baseline switch under owner decision O6.**

Physical controller S7 remains deferred without date under owner decision O2. Protected
unrelated files (`.vscode/settings.json`, `FraktalCore/PLC/Siemens/Tests/Manifest/README.md`,
and `analysis_options.yaml`) remain byte-for-byte untouched and unstaged.

---

## 1. Session Authorization and Initial Guard

- **Standing Authorization (O3)**: Recorded in `C:\work\fraktal-ab-s6-q-20261108\session_01\authorization.json`.
  Scope covers initial backup upload, deployment of collapsed genealogy candidate, deployment of
  shelving acceptance candidate, deployment of normal collapsed press candidate, and baseline switch
  to collapsed genealogy under O6. No fault/TASK clears, clocks, power, or vendor-state edits authorized.
- **Initial Baseline Backup**:
  `S6QSession.exe backup` uploaded the running image to `echo_before_s6_genealogy.ACD` and exported
  `echo_before_s6_genealogy.L5X`.
  Backup SHA-256: `902831B45F348B4EB907B0A2643E197607DDC7A1ED32103E3FBDCD51DCE1E5C4`.
- **Preflight Check**:
  `preflight.py` verified controller state: MANUAL, idle, level 0, 5 configuration documents
  matched seed (`preflight.json`).

---

## 2. Stages and Results

| Stage | Candidate / Action | ACD SHA-256 | Studio Capacity | Execution Gate | Timing Gate | Result |
|---|---|---|---|---|---|---|
| **0** | Backup Legacy Baseline | `902831B4…E5C4` | — | Preflight equal | — | **PASS** |
| **1** | Collapsed Genealogy Candidate | `1C7D4F52…0D1A` | 59% (1,862,228 Blocks) | 31/31 canonical cases pass | LastScan: 978 µs, Max: 9,011 µs, Overlaps: 0 | **PASS** |
| **2** | Collapsed Shelving Acceptance | `EFE901D1…4713` | 54% (1,726,244 Blocks) | 4/4 read-only rows pass, standing r21 present | LastScan: 1,721 µs, Max: 8,150 µs, Overlaps: 0 | **PASS** |
| **3** | Collapsed Normal Press Candidate | `3DFA02F7…B824` | 54% (1,726,208 Blocks) | 15/15 press rows, 23/23 canonical cases (ST/SFC/LD) pass | LastScan: 1,739 µs, Max: 8,151 µs, Overlaps: 0 | **PASS** |
| **4** | Official Baseline Switch (O6) | `7B69BB92…B1C5` | 59% (1,862,228 Blocks) | 31/31 canonical baseline cases pass | LastScan: 977 µs, Max: 8,835 µs, Overlaps: 0 | **PASS** |

---

## 3. Detailed Candidate Qualifications

### 3.1 Candidate 1: Collapsed Genealogy (`genealogy_s6.ACD`)
- **ACD SHA-256**: `1C7D4F522D730D1A6969A45666E9C53ECC7E4A81C8CFE7EFCCE5CD851440D1CE`.
- **Capacity Gate**: 59% (1,862,228 used of 3,145,728 standard blocks, 1,283,500 available) measured offline via Studio automation (`genealogy_capacity.json`).
- **Download & Readback**: Downloaded via `S6QSession.exe deploy-genealogy`; read back to `genealogy_s6_downloaded.L5X`. Controller returned to Run mode.
- **Canonical Execution**: Executed `fraktal_ab_genealogy_execute.py` with gateway harness (`FRAKTAL_AB_DECLARATION=fraktal_ab_genealogy_s6_collapse_demo`, `echo_admin` credentials).
  - All 31 canonical cases passed 100% (`genealogy_candidate_cases.json`).
  - Configuration preserved across 5 documents at revision 7,290,764.
  - Manual refusal, independent power gating, signal tower outputs, and genealogy transactions verified.
  - Fixture stopped clean, restored `true`.
- **Scan Timing**: Measured via `measure_timing.py --candidate` over 20 samples (`genealogy_candidate_timing.json`):
  - `LastScanUs`: 978 µs.
  - `MaxScanUs`: 9,011 µs (< 10,000 µs threshold).
  - `OverlapCount`: 0.

### 3.2 Candidate 2: Shelving Acceptance (`shelving_s6.ACD`)
- **ACD SHA-256**: `EFE901D11B56F5ED7CC5FE819669527D7BD75A9C590E8CD045D6BD5692A44713`.
- **Capacity Gate**: 54% (1,726,244 used of 3,145,728 standard blocks, 1,419,484 available) measured offline via Studio automation (`shelving_capacity.json`).
- **Download & Readback**: Downloaded via `S6QSession.exe deploy-shelving`; read back to `shelving_s6_downloaded.L5X`. Controller returned to Run mode.
- **Bootstrap & Preflight**: Bootstrapped 5 configuration documents via `echo_admin` (`StationCfg.SchemaVersion = 3`, `Restoring = 0`).
- **Shelving Live Acceptance**: Executed `fraktal_ab_phase6_execute.py --shelving` against Echo:
  - All 4 read-only rows passed 100% (`shelving_preflight_live.json`):
    1. `capture_is_registered_beside_its_editable_value`: PASS
    2. `fixture_starts_stopped`: PASS
    3. `shelving_contract_present`: PASS
    4. `shelving_session_can_be_restored`: PASS
  - Standing reason-21 event verified live on controller health owner without simulated alarm slot injection.
- **Scan Timing**: Measured via `measure_timing.py --candidate` over 20 samples (`shelving_candidate_timing.json`):
  - `LastScanUs`: 1,721 µs.
  - `MaxScanUs`: 8,150 µs (< 10,000 µs threshold).
  - `OverlapCount`: 0.

### 3.3 Candidate 3: Collapsed Normal Press (`press_s6.ACD`)
- **ACD SHA-256**: `3DFA02F7C08AC814548CF7006A540ACBD3108F1066F1185D9609C9A78F80B824`.
- **Capacity Gate**: 54% (1,726,208 used of 3,145,728 standard blocks, 1,419,520 available) measured offline via Studio automation (`press_capacity.json`).
- **Download & Readback**: Downloaded via `S6QSession.exe deploy-press`; read back to `press_s6_downloaded.L5X`. Controller returned to Run mode.
- **Bootstrap**: Restored 5 configuration documents (`StationCfg.SchemaVersion = 3`, `CurrentLevel = 0`, `Restoring = 0`).
- **Fixture Execution**:
  - `fraktal_ab_press_execute.py`: All 15 execution rows passed 100% (0 errors, `press_candidate_execution.json`).
  - `fraktal_ab_press_canonical_execute.py`: Standalone canonical runner exercised all 23 rows (2 preconditions + 7 core cases × 3 languages) in an isolated press medium (`press_candidate_canonical_cases.json`):
    - ST: `OK`, `handled_NOK`, `HELD_resume`, `abort`, `held_mode_change`, `adopted_fault`, `single_reset_restart` — All PASS.
    - SFC: `OK`, `handled_NOK`, `HELD_resume`, `abort`, `held_mode_change`, `adopted_fault`, `single_reset_restart` — All PASS.
    - LD: `OK`, `handled_NOK`, `HELD_resume`, `abort`, `held_mode_change`, `adopted_fault`, `single_reset_restart` — All PASS.
    - Final state: `restored: true`, `originalMediumUnchanged: true`, `liveDocumentsVerified: true`.
- **Scan Timing**: Measured via `measure_timing.py --candidate` over 20 samples (`press_candidate_timing.json`):
  - `LastScanUs`: 1,739 µs.
  - `MaxScanUs`: 8,151 µs (< 10,000 µs threshold).
  - `OverlapCount`: 0.

---

## 4. Official Baseline Switch (Owner Decision O6)

Under owner decision O6 (approved 2026-10-27 and reconfirmed 2026-11-08):
- Executed `S6QSession.exe switch-baseline`:
  - Hash verified `genealogy_s6.ACD` source.
  - Downloaded byte-checked copy to Echo slot 0 (`7B69BB92993B0A871AB51F7E9D1395376E4A3348F2EE598E806AD4C0284EB1C5`).
  - Switched controller to Run mode.
  - Exported `genealogy_s6_baseline_downloaded.L5X`.
  - Logged in `baseline_switch_attempt.json`.
- **Canonical Baseline Cases**:
  - Ran `fraktal_ab_genealogy_execute.py` with gateway harness (`baseline_switch_cases.json`).
  - All 31 canonical baseline cases passed 100% (`restored: true`, 0 errors).
- **Baseline Timing**:
  - Measured via `measure_timing.py --candidate` over 20 samples (`baseline_switch_timing.json`):
  - `LastScanUs`: 977 µs.
  - `MaxScanUs`: 8,835 µs (< 10,000 µs threshold).
  - `OverlapCount`: 0.

The controller rests safely in Run mode on the qualified collapsed genealogy baseline. The legacy genealogy image is archived and no longer downloaded.

---

## 5. Artifacts and Evidence Log

All evidence files are preserved in `C:\work\fraktal-ab-s6-q-20261108\session_01`:
- `echo_before_s6_genealogy.{ACD,L5X}`: Initial legacy baseline backup.
- `candidates_prepared.json`: Verified candidate images and hashes.
- `genealogy_candidate_{cases,timing}.json`: Candidate 1 qualification logs.
- `shelving_preflight_live.json`, `shelving_candidate_timing.json`: Candidate 2 qualification logs.
- `press_candidate_{execution,canonical_cases,timing}.json`: Candidate 3 qualification logs.
- `genealogy_s6_baseline_downloaded.L5X`: Exported post-switch baseline project.
- `baseline_switch_{cases,timing}.json`: Qualified baseline switch execution and timing records.
- `authorization.json`: Signed O3 session authorization.

Native Session S6-Q is complete and closed. The project is cleared to proceed to WP6.7 (legacy retirement and gate updates) and WP6.8 (spec activation).

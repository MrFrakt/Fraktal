# TC3 maintenance detector acceptance — 2026-11-11

Core **0.26.9.0**, Modules **0.18.0.1**. Owner-approved native force-status
notice implemented; see [review](../Reports/TC3_MAINTENANCE_DETECTOR_REVIEW_2026-11-11.md).

| Gate | Measured result |
|---|---|
| CheckAllObjects | 6 solutions, zero errors / warnings |
| Core/Modules runtime | 355/355 tests, 54 suites |
| Press runtime | 9/9 tests, 2 suites |
| Native probe, 4026.24 | available TRUE, demanded FALSE; both native flags FALSE |
| Absent native declarations | isolated Core compile passes, zero errors / warnings |
| PLC lint | modern and 4024, 469 files clean |
| TC3 tool / consistency tests | 79 OK (one skip) / 36 OK |
| Strict consistency | zero errors / warnings |
| Cross-contract / Siemens tool tests | 49 / 304 OK |
| Generated input/package replays | AB/TIA contracts, TIA lint and all three replays pass |
| Reason catalog | 97 entries; --check clean |

Target only **UmRT_Default 192.168.1.6.1.1:851**, autostart disabled. PressTests
is stopped in Run mode. No live force job or physical-machine acceptance.
Older-declaration fallback was compiled with missing identifiers on the installed
4026 compiler; native 4024 execution was not tested. Both runtime summaries were
independently validated. Initial failed attempts are retained.

The [SHA-256 receipt](2026-11-11_TC3_MaintenanceDetector.json) binds 45 artifacts and
522 source inputs. Its baseline ZIP preserves the preceding accepted
513-source snapshot; all 58 artifacts in that older receipt remain unchanged.
Changes remain uncommitted and unpushed; user settings are unchanged.

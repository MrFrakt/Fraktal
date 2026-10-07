# AB press79 — native download failed linking: out of memory

Recorded 2026-10-07. The owner downloaded press79 to `FraktalPhase0` from the
licensed desktop and supplied the transcript
([excerpt](AB_PRESS79_NATIVE_LINK_MEMORY_FAILURE_2026-10-07_DOWNLOAD_EXCERPT.txt)).
Verify and compile completed without error; the download wrote data types,
controller tags, AOIs and the program, then reported **"Error: Out of memory in
the controller."** while linking and cancelled: `Complete - 1 error(s), 0
warning(s)`. The transcript does not name the file; its routine set (AUTO in ST,
SFC with its runner and LD; 33 program routines) and the manifest it left behind
match `C:/work/press79.L5X` (`3074710A…B134`). It does not include a Capacity
Estimate.

Press79 added 3,132 ST source bytes and 28 statements to press78, with no data
(see the [offline record](AB_PRESS79_LIVE_DOCUMENTS_OFFLINE_2026-10-07.md)), and
press78's margin had never been measured. A source delta of that size was
enough to exhaust it, which bounds press78's free compiled memory as smaller than
press79's compiled growth; it does not measure either.

## Controller state afterwards, read-only

Serial-guarded reads of `7036B510` (1769-L24ER-QB1B, 33.14), no write:

- `fraktal_ab_manifest_read.py` reads a coherent manifest `E5F914E06055CD3B /
  15071508`, 68,048 bytes, equal to the press79 declaration
  (`C:/work/press79_after_failed_download_manifest_read_01.json`): the controller
  tags, including the manifest's values, were downloaded before linking failed.
- 123 controller tags and the program `FRK_PressProgram` are listed.
- `FRK_Press_ScanCount` reads 0 and stays 0 over one second: **no program is
  scanning.** The bench does not run press78 any more and does not run press79.

A gateway at `3d77e7a` refuses this manifest; a gateway at press79's commit
accepts it but reads a station that does not scan. The press needs a download
that fits before any native acceptance. The owner's instruction of the same day
is to keep only the ladder AUTO sequence and the permissives and remove what only
the ST and SFC renditions used; see the press80 record.

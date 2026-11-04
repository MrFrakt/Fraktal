# S6 source line endings restored to LF

2026-11-04, America/Mexico_City. A follow-up to the sealed
[V6.11 layout record](AB_S6_HOST_SERVICE_LAYOUT_OFFLINE_2026-11-04.md), which
stays unchanged. No controller was contacted, and nothing was committed.

## Cause

The session's edit scripts wrote with Python's `Path.write_text`, which emits
CRLF on Windows. The repository stores bytes verbatim (`.gitattributes`:
`* -text`), and these sources were LF before. The layout record's gates
therefore ran against, and bound, CRLF bytes. `git diff --check` found it after
sealing: every line of each file showed as changed.

## Step

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`, all exits 0):

1. `normalize_lf_01.py` converts 10 sources (`Gates/normalization_01.json`). It
   first requires each file to equal the CRLF bytes its gates bound and to
   contain no lone CR. It then requires the new bytes to equal those bytes with
   CRLF replaced by LF. All 10 changed only in line endings.
   - Nine are the layout checkpoint's Python and Dart sources.
   - The tenth, `test_fraktal_ab_canonical_live.py`, was converted by an
     earlier S6 edit script the same way.
2. `git diff --check` over the converted files is clean.
3. On the LF bytes, the suites pass:
   - the 29 focused tests;
   - full AB discovery, **2,450 tests** (890 s), with all 391 module hashes
     unchanged during the run;
   - the Dart focused tests (13), `flutter analyze` and the full HMI suite
     (842 passed, 12 intentional skips).

The three S6 census JSONs are also CRLF, because the census tool writes text
mode on Windows. Sealed evidence pins their current bytes, so they are left
unchanged. Writing them with `newline='\n'` is a follow-up for the census
tool's next output, not a rewrite of these.

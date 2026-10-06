# AB press77 — native final-link memory failure

Recorded 2026-10-05 from the owner's download transcript, completed offline
estimate transcript and Capacity screenshot. **Press77 reaches compilation
and linking, then download fails with Out of memory in the controller.**
The overall result is 1 error, 0 warnings; completed download is not accepted.
The estimate completes without a syntax error and reports:

| Memory area | Total bytes | Used / max bytes | Available bytes |
| --- | ---: | ---: | ---: |
| I/O | 1048576 | 2640 | 1045936 |
| Data and logic | 786432 | 799860 | 0 |

Data/logic is **13428 bytes over**. Its largest free block is -13428;
the I/O largest free block is 1045312. These are owner-reported offline
measurements, not the press75 online measurement or an estimate derived from ST.

The complete estimate matches every one of press77's 33 named program routines;
the initial download read also showed their compilation and linking messages.
The owner is following the prior instruction to import `C:/work/press77.L5X`,
SHA-256 `069C81EB94B2BDF5801BDE071CE0A48DC39F04A40CAA7657ED459957247C8A6B`; the transcripts themselves
contain no SHA. All five AOI logic and 33 program routines reach compilation.
All named routine-link messages occur before the final global memory error;
the log does not name one failing routine.

The complete estimate is retained byte-for-byte:
[estimate](AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05_ESTIMATE.txt), SHA-256 `D12D39B0871EA4216E69479CBE29999BC8B2E2CDB9C55DE64CF126C981E32380`.
The older interrupted-turn download attachment expired after its initial read.
Only its exact observed final excerpt is retained:
[download excerpt](AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05_DOWNLOAD_EXCERPT.txt), SHA-256 `D1435C0A313AAF38854F72D3C1876C60B40CCCC79446D3B12F528ADDE9806E76`.
This is an excerpt transcribed from the tool result, not a complete raw log.
Machine record [AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.json](AB_PRESS77_NATIVE_LINK_MEMORY_FAILURE_2026-10-05.json), SHA-256 `99E8C5509A5ED4349ED100A04A1AC1CAB09241CBAEB15D7E802EA0151B4A6492`.
Earlier offline cleanup evidence remains unchanged; this record supersedes
its pending native gate with this scoped compile/link result and failed fit.

The four-space layout and clean routine organization remain useful, but zero
declared-data growth and fewer ST terminators did not establish controller fit.
Source text is also relevant: Rockwell states that embedded ST action comments
are downloaded into controller memory ([1756-PM006, p.67](https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm006_-en-p.pdf)).
No exact byte attribution to whitespace, comments, routine overhead or compiled
logic is established by this transcript. The correction must remove repeated
runtime code and repeat exact-artifact Capacity/Verify/completed linking.

# HMI device symbols, clock-quality diagnosis, and Bosch event colors

Date: 2026-10-05 (America/Mexico_City). Scope: current source inspection and HMI
validation. This work changes HMI presentation; it does not configure a time
master, download a controller, or establish new runtime synchronization evidence.

## Persistent clock indication

The three deployments share the display, but not the same underlying cause:

| Deployment | Source finding | What remains to commission |
|---|---|---|
| TwinCAT x64 / TwinCAT x32 Press | `00_System/MAIN.TcPOU` feeds `TimeAvailable := USE_SIMULATION` and `TimeSynchronized := USE_SIMULATION` to `FB_TcSystemHealthProbe`. Outside simulation the source is `UNCONFIGURED`; valid-looking Windows time is not evidence of synchronization. | A documented PTP/NTP source for the controller's wall clock, plus real source quality/offset/last-sync inputs to the probe. |
| Allen-Bradley Press | The probe reads `GSV(TimeSynchronize,,IsSynchronized,...)` and `PTPEnable`. The adapter publishes those measurements rather than inventing success. The [2026-10-01 S3 evidence](../AllenBradley/Evidence/AB_S3_HEALTH_AND_TIMING_2026-10-01.md) recorded both as zero. | Commission a synchronization source supported by the station and verify the controller's synchronization status. The prior bench measurement is not a fresh reading of today's deployed controller. |

This is missing station integration/commissioning in the TwinCAT real fixture,
and a correctly reported unsynchronized AB bench baseline. It is not an x32/x64
licensing symptom. The framework implements quality publication, timestamp
quality flags, and the `TIME_SYNC_LOST` health event (Core §2.7, TC3 §2.7).
It does not discipline the clock automatically.

There was also an HMI presentation defect: `SystemHealthCard` collapsed
`Available=FALSE` and `Available=TRUE,Synchronized=FALSE` into the same caption.
It now shows **TIME QUALITY UNAVAILABLE** for missing quality and **TIME
UNSYNCHRONIZED** for measured loss of synchronization, with explanatory localized
tooltips. The PLC's `Healthy` and event flags remain authoritative and conspicuous.

The screenshot's 10,000 µs task period and 9,000 µs jitter have a separate source:
the Press probe call hard-codes `ExpectedCycleUs := 1000`, while both current XAE
wrappers declare a 10 ms `PlcTask`. The difference is a mismatched expected period,
not evidence that the task randomly jitters by 9 ms. The platform adapter should
provide the actual configured task period together with its time-quality inputs;
this HMI change does not edit the user's PLC task configuration.

Vendor references: Beckhoff documents
[F_GetSystemTime as an operating-system timestamp reader](https://infosys.beckhoff.com/content/1033/tcplclib_tc2_system/3622991755.html);
Rockwell documents
[the TimeSynchronize quality attributes](https://www.rockwellautomation.com/en-dk/docs/studio-5000-logix-designer/37-02/contents-ditamap/instruction-set/input-output-instructions/access-the-timesynchronize-object.html).
Neither a readable wall clock nor a gateway/HMI host's clock proves the source
controller synchronized.

## Device and application symbols

One shared `ui/hmi_icons.dart` resolves module symbols from the published
`Status.TypeKey`, with a motion-capability fallback and honest unknown-type
fallback. It never identifies devices from translated instance names. Navigation,
module headers, and overview tiles share this resolver. Every shipped CM/EM
type has a distinct symbol; cylinder, configurable-cylinder, separator, and
two-hand symbols are small vector engineering pictograms, including the Core
vision-camera and code-reader modules in the same shared catalogue.

Hardware terminals/channels now use their published channel kind/direction;
safety devices and control-power groups use their declared kinds. Runtime tabs
and the layout editor share the same icon catalogue. Appearance, recipe data,
operator decisions, and mode-release icons now depict their subjects. Status dots,
navigation arrows, and other icons that already represent their actual function
retain those meanings. No PLC contract, enum ordinal, stored icon-preset name,
dependency, or read-tier surface changes.

## Like a Bosch event bar

The main active-event bar uses opaque fills with white message text/icons:
error `#E60012`, warning dark gold `#9B6A00`, information blue `#005C8F`.
Each fill passes at least 4.5:1 contrast with white. The additional-event count
uses an inverse white badge; worst-first ordering, shelving, and tap-to-source
behavior are preserved. The multicolor top strip remains.

Validation logs and source-byte backups are retained under
`artifacts/hmi-icons-clock-events-2026-10-05/`. New tests cover shipped-type
coverage, distinct rendered engineering symbols, clock-quality cases, event-bar
contrast, and source drill-down. Full-suite/build outcomes are recorded in that
folder's delivery receipt after completion.

# Specification

**The root of this directory holds the standard itself. Nothing else.**

Everything here that is *about* the standard — how to apply it, what has been
audited, what a spike measured, what a port is planning — lives in a subfolder,
so that opening `Specification/` shows you what a conforming implementation must
satisfy without first filtering out fifty working documents.

## The standard (this directory)

| File | What it is |
|---|---|
| [`Fraktal_Core_Part_I.md`](Fraktal_Core_Part_I.md) | **Part I** — the platform-neutral normative core (§1–14). Every `shall` starts here. |
| [`Fraktal_TC3_Part_II.md`](Fraktal_TC3_Part_II.md) | **Part II** — the TwinCAT 3 binding. Every clause binds a Core clause and cites it. |
| [`Fraktal_AB_Part_III.md`](Fraktal_AB_Part_III.md) | **Part III** — the Allen-Bradley Logix binding (draft; Phase 0). |
| [`HMI_CONTRACT.md`](HMI_CONTRACT.md) | The symbol → widget bind table the generic HMI implements. |
| [`OPCUA_TRANSPORT.md`](OPCUA_TRANSPORT.md) | The OPC UA transport, config manifest and read tiers. |
| [`SAFETY_AND_CONTROL_POWER_PROFILE.md`](SAFETY_AND_CONTROL_POWER_PROFILE.md) | The §9.8 profile a station with Control On/off or power groups **shall** implement. |
| [`LOCALIZATION_AND_MODULE_CONTENT.md`](LOCALIZATION_AND_MODULE_CONTENT.md) | The localization and module-content contract. |
| [`reason_rationalization.json`](reason_rationalization.json) | The §8.9 rationalization registry — **machine-read**, and the authority behind the generated alarm catalog on both the PLC and HMI sides. |
| [`Annexes/`](Annexes/) | The worked-example annex set A–K (Core §12), which exercises every contract end-to-end. |

A document belongs in this directory when an implementation is measured against
it. If it instead tells you *how* to do something, or records what happened, it
belongs below.

## Subfolders

| Folder | Holds | Rule of thumb |
|---|---|---|
| [`Guides/`](Guides/) | Procedures: first project, XAE workflow, gateway deployment, the fieldbus adapter, I/O architecture, quick start. | Non-normative. Tells you *how*; the standard tells you *what*. |
| [`Reports/`](Reports/) | Audits, status, plans and one-off analyses: objectives audit and its review, the automation/AI review, the implementation roadmap, the ADS migration, and the press-bench records. | Describes what **is** or what was **decided**, never what **shall** be. |
| [`Evidence/`](Evidence/) | Dated TwinCAT runtime evidence — logs, JUnit, SHA-256s. | Append-only. Never edit a past record to match the present. |
| [`AllenBradley/`](AllenBradley/) | The Fraktal/AB working set: port plan, implementation plan, handover prompts, engineering runbooks, the frozen contracts, and `Evidence/` for the R- and S-gate spikes. | Part III itself stays at the root; everything used to *produce* it lives here. |

Two conventions worth knowing before you edit anything here:

- **Evidence is history, not documentation.** A dated record in `Evidence/` (or
  `AllenBradley/Evidence/`) states what a specific run produced on a specific
  day. It is not updated when the code moves on — a superseding record is added
  instead. Rewriting one to match today breaks the SHA-256 bindings that make it
  worth keeping at all.
- **Some of this is machine-read.** `reason_rationalization.json`,
  `AllenBradley/AB_FROZEN_CONTRACTS_V1.json`, Part III and
  `Guides/TWINCAT_XAE_WORKFLOW.md` are parsed by gates in `tools/` and by
  `FraktalCore/HMI/tool/generate_reason_catalog.dart`. Moving or renaming one is
  a code change, not a filing change.

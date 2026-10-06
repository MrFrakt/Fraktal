# Press75 HMI filter recovery ? 2026-10-05

**Published and verified for recovery, not elimination of genuine expiry.** The
owner's brief Connecting frame exposed a detail remount that the previous
between-frame navigation repair did not cover. No PLC build, storage, policy or
gateway change is required.

The shared HMI retains only the tab ID and each module/view's time-class and
event-severity choices. STALE/DOWN still withdraws samples and permissions and
removes the interactive shell. Recovery renders current accepted data in the
previous view. Removed modules discard their presentation state. Schema-4 settings
also retain completed language setup on reload.

Filter chip drawer animation caused repeated chart layout/paint. The regression
first observed 12 paints versus 2 at the selection change. Immediate geometry
and independent card/control repainting remove those repeated paints; this alone
was insufficient to preserve a remounted tab, so the presentation owner is required.

The isolated production-endpoint Chrome probe attempted 200 filter changes under
2? CPU throttling, executed 199, and skipped one while correctly gated. It observed
106 complete samples and zero unexpected tab returns. A painted Statistics gap
recovered to Statistics. A separate 2,500 ms outbound snapshot delay painted the
connection gate for both Statistics and Events; all six time choices and three
severity choices matched before/after, with the correct selected tab restored.
Only inert QUERY_CONFIG mailbox batches were allowed; no operator mutation was
forwarded. The owned headless browser was closed; the user's gateway remained running.

Baseline and final use different settings schemas/themes/presets; this is a
recovery test, not a controlled performance benchmark. Headless CanvasKit resource
failures were fulfilled from the matching bundled renderer. Accepted authentication
was scoped to press.localhost. The owner Chrome profile was not accessed. Genuine
sample expiry still displays Connecting under load; freshness limits were not widened.
The owner's optional hard-refresh/filter confirmation is pending at recording.

Validation: 527 HMI tests pass, seven deployment-gated skips; analyzer clean;
release JavaScript build passes; consistency 0/0 and 33 gate tests pass. The
existing freshness tests still prove shell/command withdrawal during stalled reads.
Press75's owner memory baseline remains 758,568/786,432 data/logic bytes.

Production main.dart.js SHA-256:
`3200C6269BCB593F45E9A9DD38CA15CA06546C5BA34094B66574AD71E87D0EEA`.
HTTPS checks for main.dart.js, bootstrap and index returned 200, matched bytes and
validated the press.localhost TLS host. Publication needs a Chrome hard refresh,
without a gateway restart or PLC download.

Machine record: [AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.json](AB_PRESS75_HMI_FILTER_RECOVERY_2026-10-05.json),
SHA-256 `B0E5756667067FA87A9F0224C6A926B5822625381584B803A38E31F042130232`. Artifact/source hashes and the failed baseline/intermediate
attempts are recorded there. Previous evidence bytes remain unchanged.

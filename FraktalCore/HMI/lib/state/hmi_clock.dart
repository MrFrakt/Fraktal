/// The wall clock the panel measures elapsed time against ("seen 4 s ago",
/// "elapsed 12 min", "held for 3 m", chart sampling).
///
/// One seam instead of scattered `DateTime.now()` calls, so a simulated or
/// recorded session can make the panel and the plant agree on what "now" is:
/// the integrated demo's tooling points it at the plant clock while it renders
/// a reproducible screenshot. A live panel leaves it alone.
library;

DateTime Function() hmiNow = DateTime.now;

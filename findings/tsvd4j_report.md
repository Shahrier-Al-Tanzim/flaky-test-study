# TSVD4J: Findings Summary

TSVD4J looks for thread-safety violations by pausing threads for 100ms at
specific points in a program and checking whether another thread touches
the same data during that window. Testing followed two stages: first,
replicating the paper's own results on `Java-WebSocket`, one of its six
GitHub subjects; then, pushing further to test the tool's own behavior,
not just its output.

## Limitations identified

The central one: **TSVD4J cannot distinguish a thread-safe class from an
unsafe one.** This was confirmed in two stages. First, a small,
purpose-built test: two threads sharing a `ConcurrentHashMap` — a class
Java itself guarantees is safe for concurrent use — was flagged as a
violation anyway. That result is suggestive but weak as evidence, since
the test was written specifically to try to trigger the mistake.

The same failure was then found in code nobody wrote to test TSVD4J.
Apache's own `commons-dbcp` (a widely-used database connection pool)
produced 6 conflicting pairs under testing. Each one was checked against
the actual source directly, rather than taking the tool's report at face
value. All 6 turned out to be operations on `ConcurrentHashMap`-backed
fields, spanning two separate libraries — `commons-dbcp` itself and a
pooling library it depends on internally. None are real bugs. **Every
single result from that run was a false alarm.**

The paper reports 55 conflicting pairs across 12 applications and never
checks how many of them are genuine. Given this result, that figure is
likely an overcount, though by how much remains unknown, since no
verification method exists for it in the original work.

Sixteen further bugs and limitations in the tool itself surfaced while
getting it to run reliably, including a performance defect that turns a
fast test run into a multi-hour stall (an internal list that grows without
bound and is never cleared) and a safety timeout that is silently ignored
(one test remained stuck for over three hours despite a 45-minute limit
being set). The full list is kept separately
(`findings/tsvd4j_known_issues.md`) rather than included here in full.

## Unexpected behavior

The clearest surprise: watching *more* produced *fewer* results than
watching *less*. Running both trackers together (the paper's default
configuration) found 18 conflicting pairs on `Java-WebSocket`; running the
field tracker alone found 22. If broader tracking were strictly more
powerful, that gap shouldn't exist — it suggests the tool's timing-based
detection is noisier between runs than a single evaluation pass can
reveal.

A second, sharper case: on `marine-api`, a real ship-navigation library
the paper evaluates directly, testing produced **zero** conflicting pairs
in every tracking mode, across two independent runs. This isn't a case of
numbers landing close to the paper's — it's a complete miss against the
paper's own reported 4, 1, and 5 for that exact project. Both runs were
confirmed to be genuinely active (test execution slowed by over 100× in
places), ruling out a silent instrumentation failure. The tool ran
correctly and still found nothing.

A third case concerns reliability rather than results: the first attempt
to run TSVD4J at all failed silently on Windows — the build reported
success, but zero tests had actually run, with no error shown anywhere.
Tracing the cause required a full debug log; the actual problem was a
stray quote character in a file path that Windows doesn't permit.

## Disagreements between these results and the paper's

Beyond the `marine-api` miss above, the `Java-WebSocket` numbers came out
close to the paper's but not identical: 22 against a reported 25
(field-only), 18 against 25 (default). Since the tool is inherently
timing-dependent and the paper appears to report only a single run per
project, some variance is expected — but it means the specific counts in
its results table shouldn't be read as fixed, reproducible facts.

No second concurrency-detection tool has been run yet for a direct
tool-vs-tool comparison (RV-Predict, which the paper itself compares
against, or iDFlakies from the broader reading list) — that comparison is
listed under next steps below, rather than a completed result.

## Opportunities to improve the technique

The false-positive problem has a low-cost fix available: the tool already
excludes certain packages (`java.`, `javax.`, and others) from tracking
entirely; extending that same exclusion list to cover
`java.util.concurrent` and other known-safe classes would eliminate this
entire category of false alarm.

The performance defect (the unbounded internal list) has a straightforward
fix at the source level, rather than only the workaround used to get
around it during testing.

More broadly, a small benchmark of known-safe concurrency patterns, run
against every concurrency-bug detection tool under review, would produce
an actual false-positive rate per tool — a number none of the surveyed
papers currently report.

## Next steps

- Run the same false-positive check against one or two additional real
  projects, to establish how often this occurs rather than only that it
  can.
- Check the paper's remaining five GitHub subjects for reported pairs that
  touch known thread-safe classes directly — already ruled out for
  `Java-WebSocket`, not yet checked for the others.
- Run RV-Predict or iDFlakies against the same projects, to obtain a
  genuine tool-vs-tool disagreement rather than only tool-vs-paper.

# Flaky-Test Study

Research notes and findings from exploring tools in the flaky-test and
concurrency-bug detection space, produced as part of an ongoing PhD
research exploration. Work so far has focused entirely on **TSVD4J**, a
tool that detects thread-safety violations in Java programs by injecting
timed delays at shared-data access points and checking for cross-thread
overlap.

## Start here

**[findings/tsvd4j_report.md](findings/tsvd4j_report.md)** — a short,
readable summary of what was tried, what was found, and a proposed
research direction. This is the best entry point for anyone wanting the
headline results without digging through raw logs.

## Headline findings

- **TSVD4J cannot distinguish a thread-safe class from an unsafe one.**
  Confirmed on real, unmodified production code (`commons-dbcp`, a widely
  used Apache connection pool): every one of 6 reported conflicting pairs
  in one run was a safe `ConcurrentHashMap` operation, not a real bug.
- **The paper's own reported numbers don't always reproduce.** One of its
  six evaluated GitHub projects (`marine-api`) produced zero results in
  every tracking mode, across two independent runs, against the paper's
  reported 4/1/5.
- **16 separate bugs and limitations** were found in the tool itself while
  getting it to run reliably — including a silent crash on Windows, a
  performance defect that turns fast runs into multi-hour stalls, and a
  safety timeout that doesn't work.
- The paper never measures its own false-positive rate. This work suggests
  an unknown share of its 55 reported conflicting pairs may not be real
  bugs.

Full detail for each of these lives in the files below.

## Repository structure

```
findings/
  tsvd4j_report.md          — short summary (start here)
  tsvd4j_findings.md        — full chronological findings log, run by run
  tsvd4j_known_issues.md    — 16 catalogued bugs/limitations in TSVD4J itself
  six_pairs_explained.md    — every flagged pair from the main result, with source code
  research_gaps.md          — open questions framed as research directions
  logs/                     — saved output from every test run
  reports/                  — raw TSVD4J output (conflicting-pairs, per-test results)

papers/
  The four papers from the reading list (FlakeSync, RankF, FlakyLens,
  TSVD4J), plus extracted plain-text versions for reference.

Observations.md              — a running log of test-execution notes and
                                observations across the whole study
```

## Branches

The commit history is organized into checkpoints matching the stages of
the TSVD4J replication: environment setup, build sanity check, subject
project preparation, staged execution, and results reporting. `main`
contains the cumulative, final state; each stage branch marks where that
step was completed.

## Status

The TSVD4J replication and false-positive investigation are complete.
Next steps (outlined in `findings/research_gaps.md`) include extending the
false-positive check to additional real-world projects and exploring
concrete fixes to reduce the false-positive rate.

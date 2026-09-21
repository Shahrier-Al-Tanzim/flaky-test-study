# Comparative report — IDoFT, NonDex, iDFlakies

> A synthesis across the three tools tested so far. Pulls from
> [idoft_findings.md](idoft_findings.md), [nondex_findings.md](nondex_findings.md),
> and [idflakies_findings.md](idflakies_findings.md) — read those for full
> command-by-command detail. This file exists to answer directly:
> where do these tools/datasets agree, disagree, and what did each one
> teach us that the others couldn't have.

---

## 1. What each tool actually targets

| Tool | IDoFT category it maps to | What it looks for |
| --- | --- | --- |
| **IDoFT** | (the dataset itself) | A pre-built catalog of flaky tests other researchers already found and categorized, across many real projects |
| **NonDex** | `ID` (Implementation-Dependent) | Tests that secretly depend on Java behavior that was never guaranteed — e.g. `HashMap`/`HashSet` iteration order |
| **iDFlakies** | `OD` / `OD-Vic` / `OD-Brit` (Order-Dependent) | Tests that pass or fail depending on what ran before them |

IDoFT's own dataset is dominated by `ID` (5,191 tests) over `OD` (1,074) by roughly 5×
([idoft_findings.md](idoft_findings.md)) — so NonDex is aimed at the single
largest category in the whole dataset, while iDFlakies targets a smaller
but still substantial one.

---

## 2. Coverage — which projects each tool actually touched

| Project | In IDoFT? | NonDex run? | iDFlakies run? |
| --- | --- | --- | --- |
| `delight-nashorn-sandbox` | Yes (3 hits) | ✅ Primary target | — |
| `rxjava2-extras` | Yes (6 hits) | (not run) | ✅ Attempted — tool-level failure |
| `marine-api` | Yes (12 hits, all `OD-Vic`) | (not run) | ✅ Primary target — full result below |
| `Java-WebSocket` | Yes (~40+ hits) | (not run — TSVD4J only) | — |
| `openpojo` | Yes (20 hits) | (not run) | — |
| `fluent-logger-java` | Yes (7 hits) | (not run) | — |
| `commons-dbcp`, `commons-pool` | **No** (0 hits) | — | — |

Only `marine-api` has been tested by both IDoFT (as a dataset) and iDFlakies
(as a live tool) so far — which is what makes its result below the
strongest cross-check available right now.

---

## 3. The headline result: iDFlakies vs IDoFT on `marine-api`

This is the one genuine, complete agreement found so far.

| What | Result |
| --- | --- |
| IDoFT's record | 12 `OD-Vic` tests, tied to accepted PR [#109](https://github.com/ktuukkan/marine-api/pull/109), at commit `af00038...` |
| iDFlakies at that **exact** commit, 5 rounds | **12/12 — identical test names**, independently rediscovered |
| iDFlakies at the **current** (newer) commit, 20 rounds | **0 flaky tests** — confirmed at full rigor, not just a 3-round guess |

**Reading this together:** iDFlakies and IDoFT agree completely. The bug
IDoFT documented was real, iDFlakies independently found the exact same
12 tests using a totally different method (random reordering vs.
whatever IDoFT's own pipeline used), and the fix that IDoFT's row links to
(PR #109) genuinely holds on current code — iDFlakies found nothing wrong
there, twice, at increasing rigor.

This is not a disagreement — it's the opposite: two independent
techniques, run at two points in time, telling a coherent, verifiable
story. Full detail: [idflakies_findings.md](idflakies_findings.md).

---

## 4. The disagreement: iDFlakies vs `rxjava2-extras`

Where NonDex was never run, but iDFlakies was — and failed for a reason
that has nothing to do with flakiness.

`rxjava2-extras` builds and passes cleanly on its own. iDFlakies reported
`BUILD SUCCESS` but **ran zero tests**. Root cause: the project's pom has
`<argLine>@{argLine}</argLine>` — a placeholder normally filled in by
JaCoCo during a full `mvn test` lifecycle, which invoking a plugin goal
directly (as both NonDex and iDFlakies do) skips entirely.

This is a real limitation to report: **a tool can claim success while
silently testing nothing**, and the failure mode is invisible unless you
specifically check (test counts, exit codes, `surefire-reports`) rather
than trusting the banner.

---

## 5. A pattern across *three* separate tools, not just one

The most interesting meta-finding across this whole study isn't any single
bug — it's that **the same class of "false success" bug has now shown up
independently in three unrelated tools**:

| Tool | Symptom | Root cause |
| --- | --- | --- |
| TSVD4J (earlier study, issue 5) | Reported success, ran zero tests | `argLine` collision between the tool and the project's own Surefire config |
| iDFlakies, on `rxjava2-extras` | `BUILD SUCCESS`, `Found 0 tests` | Same `argLine`/JaCoCo placeholder pattern |
| NonDex, `debug` goal | `BUILD FAILURE` (this one crashed loudly, didn't hide) | Windows path corruption via `Properties`-file escape parsing, unrelated cause but same family: fragile handling of a project's real environment |

Three different research tools, three different specific bugs, one shared
underlying weakness: **Maven's plugin-goal invocation model is fragile
around environment/lifecycle assumptions, and these tools don't defend
against it.** That's a stronger, more general finding than any one bug on
its own — worth leading with in this report.

---

## 6. Timing and overhead, side by side

| Tool | Target | Baseline (1 clean run) | Full tool run | Overhead |
| --- | --- | --- | --- | --- |
| NonDex | `delight-nashorn-sandbox` | 1m 43.65s | 19m 22s (4 runs: 1 clean + 3 shuffled) | ~2.8× raw test time |
| iDFlakies | `marine-api` (current, 20 rounds) | ~17-20s | 1m 26.8s | ~4-5× raw test time |
| iDFlakies | `marine-api-oldsha` (old commit, 5 rounds) | ~17s | 56.7s | ~6.7× raw test time |

Both tools cost noticeably more than "rounds × baseline" would suggest —
the gap is each tool's own bookkeeping (writing `.nondex\`/`.dtfixingtools\`
output, generating reports per run), not slower test execution.

---

## 7. What each tool found — clean vs. null vs. real

| Tool + target | Result | Category |
| --- | --- | --- |
| NonDex, `delight-nashorn-sandbox` | 0 hits, all 4 runs clean | **Genuine null result** — no hidden ordering assumptions |
| iDFlakies, `marine-api` (current, 20 rounds) | 0 hits | **Genuine null result** — confirmed at full rigor |
| iDFlakies, `marine-api` (old commit) | 12/12 hits, exact IDoFT match | **Genuine positive result**, independently verified |
| iDFlakies, `rxjava2-extras` | 0 hits | **False null** — not a real result, a tool/project incompatibility |

The plan's own instruction — *"write down the null results, they're
real"* — held up in two of these four cases, and was correctly overridden
in the third (`rxjava2-extras`) only after checking underneath the
surface result rather than trusting it.

---

## 8. What this adds to the study's four research categories

| Category | What this comparison contributes |
| --- | --- |
| "A tool does not behave as you expected" | iDFlakies crashing on JDK 16+ (reflection), NonDex's `debug` goal corrupting Windows paths, iDFlakies' `argLine` false-success |
| "Limitations you identify" | Direct plugin-goal invocation skips the Maven lifecycle steps these tools quietly depend on — a structural limitation, not a one-off bug |
| **"Disagreements between tools or datasets"** | `rxjava2-extras`: iDFlakies vs. its own project setup. Previously the empty box in this whole study — now filled |
| "Opportunities for improving existing techniques" | Same false-success pattern in 3 independent tools suggests a shared, fixable root cause worth flagging upstream (defensive checks for `argLine` state before running) |

---

## 9. Honest gaps — what this comparison does *not* cover yet

- NonDex was only run against one project (`delight-nashorn-sandbox`) —
  no NonDex vs. IDoFT `ID`-category comparison exists yet, since none of
  the tested NonDex targets happen to have `ID` hits recorded in IDoFT.
- `rxjava2-extras`, `Java-WebSocket`, `openpojo`, `fluent-logger-java` all
  have real IDoFT entries but haven't been tested live by either tool yet.
- Module 5 (Docker route, Windows-break test) and Module 6's formal
  cross-check table are not part of this report — this file covers only
  what Modules 2–4 have produced so far.

---

## 10. FlakeSync — a repair tool, not a detector, added 2026-09-21

Full detail: [flakesync_findings.md](flakesync_findings.md),
[flakesync_report.md](reports/flakesync/flakesync_report.md).

Unlike the three tools above, FlakeSync repairs async flaky tests rather than
detecting order-dependence or unguaranteed-order flakiness. It doesn't slot
directly into the ID/OD table above, but two of its findings connect
directly to what this study has already established:

| Connection to earlier findings | What FlakeSync adds |
| --- | --- |
| Same result shape as the iDFlakies default-configuration finding | The artifact's own shipped delay schedule (max 25,600ms) is half the paper's stated `MAX_DELAY` (51,200ms) — a silent under-reporting risk baked into the artifact, independent of anything about this replication's environment |
| Same result shape as "argLine collision" / config-dependent results across this whole study | FlakeSync's own critical-point search produced two different (though related) answers across 6 repetitions of one pipeline run on one machine — direct evidence the technique is not fully deterministic, which the paper never discloses |
| A new category this study didn't have yet | The artifact's own evaluation-input row for `elastic-job-lite` uses `master` instead of a pinned SHA — the only row that does — and it broke, concretely, within this study's own run. Filed as `[AVAILABILITY]`/`[STALENESS]`-adjacent: even a well-maintained artifact can carry one silent, unpinned reference that ages worse than everything around it |

**Cross-project note:** `apache/dubbo` is both a FlakeSync subject (M7–M11)
and RankF's worked example project — unexamined overlap, left for a future
session.

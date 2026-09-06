# TSVD4J — Findings log

> **What this file is for.** A running log of everything observed while
> testing TSVD4J — surprises, errors, things that worked, things that did
> not. This log *is* the research output, written so each entry reads like
> a notebook page meant to be revisited later, or read by an advisor.

> **How to use it.** Copy the template below for each run. Replace every
> `…` with what was actually observed. Old runs are never deleted — all of
> them are kept so shifts in understanding stay visible over time.

---

## Run template — copy this for each new run

```markdown
## Run YYYY-MM-DD-NN — <short name>

**Project under test:** `<project>`, commit `<sha>`, ~<N> kLOC, <M> tests
**TSVD4J version:** `<commit hash built>` (from `git rev-parse HEAD`)
**Artifact state:** pristine `<sha>` / pristine + `<M-number from tsvd4j_run.md Appendix A>`
**Subject state:** `git status` clean? upstream pom + plugin block only?
**Workarounds used:** none / W1 / W2 / W3 / W4 / W5 / W6 (see tsvd4j_run.md Appendix B)
**Comparable to paper Table II?** yes / no — <why>
**Host OS:** <Windows 11 / Ubuntu 22.04 / macOS 14>
**Java:** `java -version` → <paste output>
**Maven:** `mvn -version` → <paste output>

### Exact command line

```
<paste the full mvn command, including every -D flag>
```

> Never record a number without the command that produced it. Delay, excludes
> and fork settings all change the result.

### Timing

| Step | Wall-clock time |
| --- | --- |
| Build TSVD4J (`mvn clean install -DskipTests`) | … |
| Sanity project (Step 4) | … |
| Baseline `mvn clean test` (no TSVD4J) | … |
| Stage A — `-Dapi`, full suite | … |
| Stage B — `-Dfield`, one class | … |
| Stage C — `-Dfield`, suite minus autobahn/example | … |
| Stage D — default (both) | … |
| **Overhead multiplier** (instrumented ÷ baseline) | …× |

### Configuration used

- Tracking mode: default (both) / `-Dapi` / `-Dfield`
- Injected delay: 100 ms (hard-coded in the artifact; not configurable — see M1)
- Fork setting: `reuseForks` = true / false, `forkCount` = …
- Surefire excludes: …
- `-Dsurefire.timeout`: … seconds
- `MAVEN_OPTS`: …
- Wall-clock cap and did I hit it: … (paper allowed 6 h per application)
- Any pom.xml edits beyond the plugin snippet: …

### Output

- Did the run finish, or was it killed/timed out? …
- `.tsvd4j\Conflicting-Pairs.txt` present? … (absent ⇒ the JVM was killed
  before its shutdown hook; recover from the per-test files instead)
- Raw count (`Conflicting-Pairs.txt` lines): …
- Deduplicated count (`Sort-Object -Unique`): …
- Recovered-from-per-test-files count, if the run was killed: …
- Number of per-test files with at least one pair: …
- Tests that failed under instrumentation but passed at baseline: …
  (this diff measures how invasive the tool is — keep both
  `target\surefire-reports\` folders)

### Repetitions — TSVD4J is non-deterministic

The authors ran each project **once** (`for i in {1..1}` in
`scripts/run-tsvd4j.sh`), so a single differing number is noise, not a finding.

| Repetition | Pairs (raw) | Pairs (dedup) | Time |
| --- | --- | --- | --- |
| 1 | … | … | … |
| 2 | … | … | … |
| 3 | … | … | … |
| 4 | … | … | … |
| 5 | … | … | … |
| **min / median / max** | … | … | … |

- Compared to paper Table II for this project: paper says <N>, my median is
  <M>. Difference = <explain>. Is the gap stable across all 5 runs? …

### Per-test breakdown

| Test name | Conflicting-pairs | Notes |
| --- | --- | --- |
| com.example.Foo.testBar | 3 | Both pairs in the project's own code; one is read-write, two are write-write |
| … | … | … |

### Things I expected but did not see

- …

### Things I did not expect but did see

- …

### Errors / warnings that looked weird

- …

### Tool disagreements

- (If RV-Predict or another detector was also run: did it flag the same
  pairs, different pairs, or none?)
- …

### Improvement ideas (the gold)

- …

### Next run — what I want to try

- …
```

---

## Run 2026-09-04-01 — Java-WebSocket baseline (no TSVD4J yet, Step 5a)

This is **not** a TSVD4J run. It is the "before" measurement — running the
project's own tests with no instrumentation at all — so later TSVD4J numbers
can be compared against it.

**Project under test:** TooTallNate/Java-WebSocket, commit `aad6654`, 16 kLOC
**TSVD4J version:** not built/run yet — Module 2 not started
**Artifact state:** TSVD4J tree untouched. Java-WebSocket `git status` clean,
HEAD at `aad6654`, no plugin block added yet.
**Workarounds used:** none
**Host OS:** Windows 11
**Java:** `openjdk version "1.8.0_412"` (Amazon Corretto)
**Maven:** Apache Maven 3.9.11

### Exact command line

```
mvn clean test *> baseline-run.log
```
(Timed separately with `Measure-Command { mvn clean test }`.)

### Timing

| Step | Wall-clock time |
| --- | --- |
| Baseline `mvn clean test` (no TSVD4J) | 2 min 36 sec (Maven's own report) / 2.617 min (`Measure-Command`) — the two agree |

### Output

- `Tests run: 720, Failures: 1, Errors: 0, Skipped: 1`
- Final result: `BUILD FAILURE` (caused by the 1 failing test below)

### Per-test breakdown

| Test name | Result | Notes |
| --- | --- | --- |
| `Issue256Test.runReconnectSocketClose[0]` | FAIL | Test retries itself 3 times internally. Run 1: PASS. Run 2 and Run 3: "Found 16 zombie thread(s)". Already known — see `Observations.md`, "Zombie Threads" bullet. |

### Things I expected but did not see

- Expected 641 tests (the paper's count for this project, Table I). Got
  **720**. Likely cause: Java-WebSocket ships `AllTests`-style suite classes
  that run the same individual tests a second time (see
  `tsvd4j_known_issues.md`, issue 8). Not investigated further yet.

### Things I did not expect but did see

- A `BindException: Address already in use` cascade appeared in the console
  during the run, with `WebSocketWorker` thread names climbing into the
  thousands. This looked alarming but did **not** show up in the final
  `Failures`/`Errors` count — so either it was caught internally by the
  library, or it affected a test that still passed. Logged in
  `Observations.md` as a pre-existing flakiness source, separate from the one
  real failure above. Open question for a later pass: which specific test(s)
  triggered it.

### Errors / warnings that looked weird

- The `BindException` cascade (see above) — looked like a serious crash in
  the console but the build only reports 1 real failure.

### Next run — what I want to try

- Move to Module 3 / Step 5b: add the TSVD4J plugin block to `pom.xml`, then
  Step 5c to check for an `argLine` collision, before running any TSVD4J
  stage.

---

## Run 2026-09-04-02 — Stage A, API-only, first working TSVD4J run

**Headline: 0 conflicting pairs across 596 tests — which matches the paper.**
Table II says API-only on this project = 0. Partial replication of that cell
succeeded. Also the first run where TSVD4J executed at all.

**Project under test:** TooTallNate/Java-WebSocket, commit `aad6654`, 16 kLOC
**Artifact state:** pristine `4958a7f` **+ local fix** — `TSVD4JMojo.java`
line 79, removed the literal quote marks around the agent jar path. See
[TSVD4Jfix.md](TSVD4Jfix.md) and issue 11 in
[tsvd4j_known_issues.md](tsvd4j_known_issues.md). **Without this fix the tool
produces zero output on this machine in any mode**, so this run was not
possible before it.
**Subject state:** upstream pom + TSVD4J plugin block only. No `argLine`
collision (5c clean).
**Workarounds used:** none (single reused fork, default settings)
**Comparable to paper Table II?** Partially — right mode and right project,
but only 54 of 74 test classes completed, and the artifact carries the line-79
fix.
**Host OS:** Windows 11
**Java:** `openjdk version "1.8.0_412"` (Amazon Corretto)
**Maven:** Apache Maven 3.9.11 · Surefire resolved to **3.2.5** (from the
project's own pom, not TSVD4J's pinned 2.22.0 — worth noting, the version gap
may matter)

### Exact command line

```
mvn tsvd4j:clean
mvn tsvd4j:tsvd4j -Dapi *> logs\stage-a.log
```

### Timing

| Step | Wall-clock time |
| --- | --- |
| Baseline `mvn clean test` (no TSVD4J, run 01) | 2 min 36 s |
| Startup before first test class finished | **~8 min** (class rewriting) |
| First ~30 classes (simple, single-threaded) | **34 s total** |
| `issues.AllIssueTests` alone | **15 min** |
| Stalled on `issues.Issue941Test` | **40 min, no progress — killed** |
| Total before Ctrl+C | **~95 min for 54 of 74 classes** |
| **Overhead vs baseline** | **≥35×, and rising non-linearly** |

### Output

- Run finished? **No** — killed with Ctrl+C after 40 min of no progress.
- `.tsvd4j\Conflicting-Pairs.txt` present? **No** — as expected, it is only
  written by a clean-shutdown hook, and this was a hard kill.
- `.tsvd4j\` contained **only** `listener.log` (96 KB): 596 `Test started`
  lines, 593 `Test finished`, and **zero other lines**.
- Per-test result files: **none**. TSVD4J only creates one when a test finds
  something, so no files = no findings.
- **Distinct conflicting pairs: 0**
- Paper's Table II, P1 API-only: **0** → **agreement**
- The 596/593 gap = 3 tests still in flight at kill time, including the hung
  one.

### Is the zero real, or was the tool not looking?

**Real.** Positive evidence the API tracking was active and firing — this
appeared in the log during `Issue1203Test`:

```
at edu.utexas.ece.tsvd4j.agent.Utility.delay(Utility.java:44)
at edu.utexas.ece.tsvd4j.agent.Utility.onCall(Utility.java:305)
at edu.utexas.ece.tsvd4j.agent.Proxy.clear(Proxy.java:384)
at org.java_websocket.AbstractWebSocket$1.run(AbstractWebSocket.java:208)
```

That is TSVD4J intercepting a real `Collection.clear()` call and injecting its
delay. So the instrumentation ran and genuinely found nothing — distinct from
the pre-fix runs, which reported 0 because nothing was ever instrumented.

### Things I did not expect but did see

- **The stall is a quadratic slowdown, not a hang.** The forked JVM had
  accumulated **14,776 seconds of CPU time in ~79 minutes of wall clock** —
  saturating ~3 cores, fully busy, not blocked. Cause: TSVD4J searches
  ever-growing `ArrayList`s with `.contains()` on every interception point and
  never prunes them, so cost per operation grows with operations already done.
  Matches the timing profile exactly (30 classes in 34 s early → 25+ min per
  class late). This **corrects** the earlier heap/GC explanation in issue 2.
- **`Issue941Test` stalled under instrumentation, but not deterministically.**
  It calls `pingLatch.await()` with no timeout; the injected delays are enough
  to stop the ping arriving *sometimes*. **Update (run 03 below): the same
  test passed in 5s when re-run alone in a fresh process** — so this is TSVD4J's
  overhead making an existing flaky test more likely to fail, not a guaranteed
  permanent hang. See issue 13.
- **`AllIssueTests` cost 15 minutes on its own**, because suite classes re-run
  every test in their group (issue 8). Substantial wasted time.
- **~8 minutes of startup** before a single test finished, all of it ASM
  rewriting classes on load. Not mentioned in the paper.

### Errors / warnings that looked weird

- `OutOfMemoryError: Some error` in `Issue1160Test` — **not** a real memory
  problem; that test deliberately throws one to check the library's handling.
  Ignore it.
- `BindException: Address already in use` cascade in server tests, same as the
  baseline run. Pre-existing, not caused by TSVD4J.

### Improvement ideas (the gold)

- Replace the three `ArrayList` + `.contains()` hot paths with hash-based sets
  — removes the quadratic blowup without changing which pairs get reported.
  This alone may be the difference between "unusable on real suites" and
  "usable".
- Report progress/heartbeat output. A user cannot currently distinguish
  "working slowly" from "hung" without inspecting process CPU time by hand.
- Never report `BUILD SUCCESS` when Surefire failed (issue 12).

### Next run — what I want to try

1. Finish Stage A: run the remaining 16 safe classes with
   `-DreuseForks=false -Dsurefire.timeout=600`, so the growing lists reset per
   class. Then the 4 known-bad classes separately.
2. Then Stage B — `-Dfield` on **one** test class only, to measure the
   slowdown before attempting a full field-mode run. Field mode is where all
   25 of the paper's pairs come from, and it watches far more operations than
   API mode, so the quadratic problem will be much worse.

---

## Run 2026-09-05-03 — Stage A completed, in 2 more batches

**Headline: Stage A is finished. 71 of 71 real test classes, 0 conflicting
pairs, exact match with the paper's Table II value (0) for API-only tracking
on this project.**

Continuing from run 02, which stopped at 54/74 classes. No `tsvd4j:clean` was
run between any of these batches — output accumulated correctly across all of
them.

### Batch 2 — 16 remaining "safe" classes

```
mvn tsvd4j:tsvd4j -Dapi -DreuseForks=false "-Dsurefire.timeout=600" "-Dmaven.test.failure.ignore=true" "-Dtest=<16 class names>" *> logs\stage-a-part2.log
```

- First attempt failed in 0.4s with `Unknown lifecycle phase ".timeout=600"`
  — a copy-paste accident split `-Dsurefire.timeout=600` into two words at the
  dot. **Not TSVD4J's fault**, and no data was lost (failed before touching
  the project). Fixed by quoting every `-D` flag whose name contains a dot —
  now standard practice in [tsvd4j_run.md](tsvd4j_run.md).
- Second attempt: **succeeded**, 2m22s, 182 tests, 0 conflicting pairs, 7
  errors — all `TestTimedOut test timed out after 2000 milliseconds` in
  `Issue962Test`/`Issue997Test`. Confirms both the `-DreuseForks=false` fix
  (no stall this time) and TSVD4J's invasiveness (2s test timeouts blown by
  injected delays — see issue 13, and the `Issue825Test` precedent).

### Batch 3 — the 4 remaining classes

```
mvn tsvd4j:tsvd4j -Dapi -DreuseForks=false "-Dsurefire.timeout=600" "-Dmaven.test.failure.ignore=true" "-Dtest=Issue941Test,AutobahnClientTest,AutobahnServerTest,AutobahnSSLServerTest" *> logs\stage-a-part3.log
```

- **`Issue941Test` passed in 5s** — no hang at all this time, run alone in a
  fresh process. Corrects the run-02 entry above: this is a flaky test whose
  failure probability TSVD4J's overhead raises, not a deterministic hang.
- **The 3 `Autobahn*Test` classes never ran — correctly.** Confirmed by
  reading the source: none of the three (`AutobahnClientTest`,
  `AutobahnServerTest`, `AutobahnSSLServerTest`) has a single `@Test`
  annotation. Each has a `public static void main(...)` instead — they are
  standalone demo programs in the `example` package that happen to live under
  `src/test` and be named `*Test`, meant to be run by hand against an
  external Autobahn conformance tool. Maven compiles them; JUnit correctly
  finds 0 test methods and silently skips them. **Not a bug, not a gap** —
  the true denominator for this project is 71 test classes, not 74.

### Final tally for Stage A (API-only)

| | |
| --- | --- |
| Real test classes | 71 (of 74 files; 3 are non-tests, see above) |
| Completed | 71 / 71 |
| Tests run (total across all batches) | 596 + 182 + 1 = 779 |
| Conflicting pairs | **0** |
| Paper's Table II, P1, API-only | **0** |
| **Match?** | **Yes** |

### Next run — what I want to try

Move to Stage B (`-Dfield`), starting with one test class only, per the plan
already in [tsvd4j_run.md](tsvd4j_run.md). Field mode is where all 25 of this
project's paper-reported pairs should come from, and it watches far more
operations than API mode — expect the quadratic slowdown to bite much harder,
so batching by `-Dtest=` subsets with `-DreuseForks=false` from the start,
rather than attempting a full-suite run first, as run 02 tried.

---

## Run 2026-09-05-04 — Stage C, field mode, full suite (partial: 54/71)

**Headline: field mode found 22 distinct conflicting pairs, against the
paper's reported 25 — with 17 of 71 classes still unrun.** This is the first
run of the whole study to produce any findings at all.

**Project under test:** TooTallNate/Java-WebSocket, commit `aad6654`
**Artifact state:** pristine `4958a7f` + local fix ([TSVD4Jfix.md](TSVD4Jfix.md),
`TSVD4JMojo.java` line 79)
**Workarounds used:** W2 (`-DreuseForks=false`), W3 (`-Xmx4g`),
W4 (`-Dsurefire.timeout=2700` — **did not work, see below**), W5
**Java:** Corretto `1.8.0_412` · **Maven:** 3.9.11 · Surefire **3.2.5**

### Exact command line

```
$env:MAVEN_OPTS = "-Xmx4g"
mvn tsvd4j:clean
mvn tsvd4j:tsvd4j "-Dfield" -DreuseForks=false "-Dsurefire.timeout=2700" "-Dmaven.test.failure.ignore=true" "-Dsurefire.excludes=**/example/**" *> logs\stage-field-full.log
```

### Result

| | |
| --- | --- |
| Classes completed | 54 of 71 |
| Tests finished | 538 |
| **Raw pairs** (`Conflicting-Pairs.txt` lines) | **38** |
| **Distinct pairs** (`sort -u`) | **22** |
| Paper's Table II, P1, Field-only | **25** |
| Run status | **Killed** — stuck 3h15m on `Issue941Test` |

Raw 38 vs distinct 22 is the expected cost of `-DreuseForks=false`: TSVD4J
dedups only within one JVM, and each class gets its own, so the same pair gets
re-reported across forks. **Report the distinct count.**

### The 22 distinct pairs

All in the project's own source, and they cluster into four sites:

```
org/java_websocket/client/WebSocketClient|344,345,346,410,508,509 : WebSocketClient|75
org/java_websocket/client/WebSocketClient|348,349,350,371,374,375,376 : WebSocketClient|526
org/java_websocket/drafts/Draft_6455|351,1142,1150 : Draft_6455|809
org/java_websocket/drafts/Draft_6455|370,1145,1151 : Draft_6455|810
org/java_websocket/WebSocketImpl|615,784 : WebSocketImpl|596
org/java_websocket/issues/Issue621Test$TestPrintStream|58 : (itself)|58
```

Note the shape: many *different* lines all conflicting against a *single*
partner line (`WebSocketClient:75`, `:526`, `Draft_6455:809`, `:810`,
`WebSocketImpl:596`). That suggests a handful of shared fields each being
touched from many places, rather than 22 independent bugs. **Worth reading
those specific lines to identify which fields they are** — that turns a pair
count into an actual explanation.

### Which tests produced them

Only 9 test methods, across 3 classes:

```
Issue256Test.runReconnectCloseBlocking[0], runReconnectSocketClose[0,1,2]
Issue580Test.runNoCloseBlockingTestScenario[6]
Issue879Test.QuickStopTest[1,2,3,13]
```

All three are reconnect / close / stop scenarios — i.e. **shutdown-path
concurrency**. That is a coherent, explainable cluster, not scattered noise.

### Things I did not expect but did see

- **`-Dsurefire.timeout=2700` did not fire.** It should have killed
  `Issue941Test` after 45 minutes; the class sat there for **3 hours 15
  minutes** and had to be killed manually. Either the property is not being
  honoured through the TSVD4J mojo's re-invocation of Surefire, or it does
  not apply to this kind of hang. **This invalidates W4 as a safety net** —
  do not rely on it; the only reliable protection is excluding known-bad
  classes up front.
- **`Issue941Test` hung again**, and again at exactly class 54 of the run —
  the same class and same position as the API-mode run (run 02). Combined
  with it passing in 5s when run alone (run 03), this is now a repeatable
  pattern: it hangs when reached late in a long run, passes when run fresh.
- **Field mode is not uniformly slower.** 54 classes finished in ~37 minutes
  (01:33 → 02:10), which is far better than API mode's first attempt managed.
  `-DreuseForks=false` from the start is what made the difference.

### Next run — what I want to try

1. Resume the remaining 17 classes, **excluding `Issue941Test`**, with no
   `tsvd4j:clean` so the 22 pairs are preserved. See whether the total reaches
   25.
2. Then read the actual source at `WebSocketClient:75`, `:526`,
   `Draft_6455:809`, `:810`, `WebSocketImpl:596` to name the shared fields
   involved — the paper reports counts but never says *what* the 25 pairs
   are, so this is new ground.
3. Re-run the full field mode 5× to check stability of the distinct count,
   per the non-determinism caution in Step 8.

---

## Run 2026-09-05-05 — Stage C, field mode: closing out the run

**Headline: 70 of 71 real test classes completed under field mode. Final
result: 22 distinct conflicting pairs, against the paper's 25.
`Issue941Test` could not be completed under instrumentation, in 3 separate
attempts, and is excluded from the denominator with cause.**

This entry closes out the field-mode effort started in run 04. Combines two
follow-up batches on top of that run's 54/71.

### Batch: 16 remaining classes (excluding `Issue941Test`)

```
mvn tsvd4j:tsvd4j "-Dfield" -DreuseForks=false "-Dmaven.test.failure.ignore=true" "-Dtest=<16 class names>" *> logs\stage-field-part2.log
```

- First attempt: interrupted at the very start by an `InterruptedException:
  sleep interrupted` — same signature as the earlier accidental interruption
  in run 04, almost certainly another accidental `Ctrl+C` (see the "Checking
  progress" section added to [tsvd4j_run.md](tsvd4j_run.md) as a direct
  result of this happening twice).
- Restarted, this time completed **all 16 classes**, 6m20s, 179 tests, 9
  errors, `BUILD SUCCESS`. **0 new distinct pairs** — still 22.
- 9 errors were `TestTimedOut ... after 2000 milliseconds` (the by-now
  familiar invasiveness pattern — `Issue962Test`, `Issue997Test`) plus one
  new symptom: `java.lang.NoClassDefFoundError: edu/utexas/ece/tsvd4j/agent/Proxy`
  appearing partway through, immediately after another `sleep interrupted`
  event. Likely cause: the interruption left the JVM's classloading in a
  bad state; the run continued and still completed, so this was not fatal,
  but is worth a line in [tsvd4j_known_issues.md](tsvd4j_known_issues.md) if
  it recurs.

### Attempt: `Issue941Test` alone, 3rd try

```
mvn tsvd4j:tsvd4j "-Dfield" -DreuseForks=false "-Dmaven.test.failure.ignore=true" "-Dtest=org.java_websocket.issues.Issue941Test" *> logs\stage-field-part3.log
```

- **Hung.** Diagnosed as genuinely stuck, not slow, using CPU accounting:
  after ~15 minutes wall-clock, the two Java processes involved had used a
  combined **~15 CPU-seconds** — roughly 1–2% utilization. Contrast with the
  quadratic-slowdown hang in run 04's predecessor (API mode), which
  saturated ~3 cores continuously. **Near-zero CPU + total silence = blocked
  on a wait, not computing** — the signature of `pingLatch.await()` with no
  timeout (documented in `Observations.md`), not the list-growth slowdown.
- No per-test file was ever created for this attempt — confirms it never got
  far enough to record anything, consistent with a hang very early in the
  test.
- **Third attempt, third hang** in this project's history, but the *first*
  attempt (run 03) passed in 5s when run alone with nothing else going on.
  Updated understanding: it is not "flaky" in the sense of random 50/50 — it
  appears to hang specifically when run **after** other tests/load in the
  same session, and pass when run in isolation on a freshly idle machine.
  Worth testing deliberately: run it alone, immediately after a fresh
  `mvn tsvd4j:clean`, with nothing else having touched the JVM/network first.

### Final tally for Stage C (field mode)

| | |
| --- | --- |
| Real test classes | 71 |
| Completed | **70** |
| Excluded, with cause | `Issue941Test` (hung 3/3 attempts when not run in isolation) |
| **Distinct conflicting pairs** | **22** |
| Paper's Table II, P1, Field-only | **25** |
| Gap | 3 pairs — plausibly located in the untested class |

### Improvement ideas (the gold)

- The tool gives no way to bound a single test's runtime independent of the
  whole Surefire fork — `-Dsurefire.timeout` does not reach it (see run 04).
  A per-test watchdog inside TSVD4J itself (it already wraps every call in
  `Runtime.onCall` — a timeout there would be cheap to add) would let a hang
  like this be skipped automatically rather than requiring a human to notice
  and interrupt.
- 70/71 with a known, explained exclusion is arguably a *more* honest result
  than the paper's own single unexplained run of each project — worth stating
  plainly in any write-up rather than treating it as an incomplete
  replication.

### Next run — what I want to try

1. Try `Issue941Test` once more, alone, immediately after a fresh JVM/clean
   state, to test the "hangs only under load" theory above.
2. Read the actual source at the 5 clustered sites (`WebSocketClient:75`,
   `:526`, `Draft_6455:809`, `:810`, `WebSocketImpl:596`) and name the shared
   fields — still outstanding from run 04.
3. Move to Stage D (both trackers together) only after deciding whether
   `Issue941Test` is worth continuing to chase, or whether 70/71 is the
   accepted final denominator for this project.

---

## Run 2026-09-05-06 — Stage D, default mode (both trackers), full suite

**Headline: 18 distinct conflicting pairs, against the paper's 25 for default
mode — fewer than Stage C (field-only) found on its own (22). Run completed
cleanly, no interruption, but with a much larger fraction of tests
failing/erroring than any earlier stage.**

**Project under test:** TooTallNate/Java-WebSocket, commit `aad6654`
**Artifact state:** pristine `4958a7f` + local fix ([TSVD4Jfix.md](TSVD4Jfix.md))
**Subject state:** upstream pom + TSVD4J plugin block only
**Workarounds used:** W2 (`-DreuseForks=false`), W4 (`-Dsurefire.timeout=2700`
— present but, as already verified, doesn't actually do anything), W5
**Comparable to paper Table II?** Partially — right mode (default = both
trackers), 70 of 71 real classes, `Issue941Test` excluded with cause (see
run 05)
**Java:** Corretto `1.8.0_412` · **Maven:** 3.9.11 · Surefire **3.2.5**

### Exact command line

```
mvn tsvd4j:clean
mvn tsvd4j:tsvd4j -DreuseForks=false "-Dsurefire.timeout=2700" "-Dmaven.test.failure.ignore=true" "-Dsurefire.excludes=**/example/**,**/Issue941Test.java" *> logs\stage-d-full.log
```

### Timing

| Step | Wall-clock time |
| --- | --- |
| Baseline `mvn clean test` (no TSVD4J, run 01) | 2 min 36 s |
| Stage D — default mode, full suite | **1 h 14 min** |
| **Overhead multiplier** (1h14m ÷ 2m36s) | **≈28×** |

`AllTests` alone (the first, biggest fork — see
[tsvd4j_known_issues.md](tsvd4j_known_issues.md) issue 14) took **30 min** of
that hour on its own (184 tests, 1810 s elapsed).

### Output

| | |
| --- | --- |
| Run status | **Finished cleanly** — `BUILD SUCCESS`, proper `Total time` / `Finished at` lines. **Not** an interruption: a killed run never produces `Conflicting-Pairs.txt` at all (shutdown hook), and this run has one. |
| Classes run | 70 of 71 (`Issue941Test` excluded, same as Stage C) |
| Total tests | 628 |
| Total failures | 14 |
| Total errors | 111 |
| **Raw pairs** (`Conflicting-Pairs.txt` lines) | **34** |
| **Distinct pairs** (`Sort-Object -Unique`) | **18** |
| Paper's Table II, P1, default (both) | **25** |

### The 18 distinct pairs

```
org/java_websocket/WebSocketImpl|615:org/java_websocket/WebSocketImpl|596
org/java_websocket/WebSocketImpl|784:org/java_websocket/WebSocketImpl|596
org/java_websocket/client/WebSocketClient|344:org/java_websocket/client/WebSocketClient|75
org/java_websocket/client/WebSocketClient|345:org/java_websocket/client/WebSocketClient|75
org/java_websocket/client/WebSocketClient|346:org/java_websocket/client/WebSocketClient|75
org/java_websocket/client/WebSocketClient|348:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|349:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|350:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|371:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|374:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|375:org/java_websocket/client/WebSocketClient|526
org/java_websocket/client/WebSocketClient|376:org/java_websocket/client/WebSocketClient|526
org/java_websocket/drafts/Draft_6455|269:org/java_websocket/enums/HandshakeState|14
org/java_websocket/drafts/Draft_6455|351:org/java_websocket/drafts/Draft_6455|809
org/java_websocket/drafts/Draft_6455|370:org/java_websocket/drafts/Draft_6455|810
org/java_websocket/drafts/Draft_6455|728:org/java_websocket/drafts/Draft_6455|805
org/java_websocket/issues/Issue598Test|164:org/java_websocket/enums/Opcode|7
org/java_websocket/issues/Issue621Test$TestPrintStream|58:(itself)|58
```

Producing tests (per-test files with content):
`Issue256Test.runReconnectCloseBlocking[0,2]`,
`Issue256Test.runReconnectSocketClose[0,1,4]`,
`Issue598Test.runAboveSplitLimitBytebuffer`,
`Issue598Test.runBelowSplitLimitString`,
`Issue879Test.QuickStopTest[3,7]` — same reconnect/close/shutdown cluster as
Stage C, plus `Issue598Test` newly appearing.

### Things I did not expect but did see

- **Default mode found *fewer* distinct pairs than field-only mode did**
  (18 vs Stage C's 22), even though default mode watches strictly more
  (API + field together). 4 of Stage C's 22 pairs (`WebSocketClient:410`,
  `:508`, `:509`, and one `Draft_6455:1142`/`1150`/`1145`/`1151` group) did
  not reappear here; 3 new ones did
  (`Draft_6455:269→HandshakeState:14`, `Draft_6455:728→805`,
  `Issue598Test:164→Opcode:7`). Most likely explanation: TSVD4J is
  delay-and-race based and inherently non-deterministic (paper itself only
  ever ran once per project — see Step 8 caution 1), so a single run of any
  mode can miss pairs another single run of a *different* mode happens to
  catch, independent of which mode is "supposed" to be more powerful. **This
  is exactly the kind of tool disagreement worth flagging** — on this
  evidence alone I cannot conclude default mode is strictly a superset of
  field mode, even though that's the intuitive expectation.
- **Much higher failure/error rate than any earlier stage**: 125 of 628
  tests (~20%) failed or errored, vs single digits in Stage A/C. Two extreme
  cases: `Issue847Test` — **42 of 42 tests errored** (100%), and
  `AllIssueTests`/`Issue256Test`/`Issue580Test`/`Issue879Test` each failed or
  errored on most of their runs. Combining both trackers roughly doubles the
  number of injected-delay points versus either alone, and this is the
  clearest evidence yet of how much that changes program timing — see issue
  13 in [tsvd4j_known_issues.md](tsvd4j_known_issues.md).
- **`AllTests` (the first, biggest fork) alone accounted for 30 of the 74
  total minutes**, and was where issue 14 (`-DreuseForks=false` can't reset
  state inside a suite) was first noticed live — see that issue for the
  mechanism.

### Final tally for Stage D (default, both trackers)

| | |
| --- | --- |
| Real test classes | 71 |
| Completed | **70** (`Issue941Test` excluded, same cause as Stage C) |
| **Distinct conflicting pairs** | **18** |
| Paper's Table II, P1, default | **25** |
| Gap vs paper | 7 pairs |
| Gap vs own Stage C (field-only) | **−4 pairs** (18 vs 22 — unexpected direction) |

### Improvement ideas (the gold)

- The default-mode-found-fewer-pairs-than-field-only-mode result is worth a
  repeat run (or several) specifically to check whether it's noise (see
  Step 8's optional 5×-repetition check) or a real, reproducible pattern —
  if reproducible, it would suggest turning on more instrumentation can
  *reduce* the delay's effectiveness at exposing some races (e.g. by
  changing relative timing between threads enough that a race that
  triggered under field-only no longer lines up under default mode).
- The ~20% failure/error rate under default mode is itself a number worth
  reporting alongside the pair count — a detector that breaks a fifth of the
  test suite to find its results has a real invasiveness cost that Table II
  never surfaces.

### Next run — what I want to try

1. This completes all four stages (A, B, C, D) planned in
   [tsvd4j_run.md](tsvd4j_run.md) for Java-WebSocket. Decide whether to
   pursue the optional 5×-repetition check (Step 8) for statistical
   confidence, or move on to the next tool/project per
   [next_steps.md](next_steps.md) / the advisor's broader task list.
2. Read the actual source at all clustered sites across Stage C and D
   (`WebSocketClient:75`, `:526`, `Draft_6455:809`, `:810`, `:805`,
   `WebSocketImpl:596`, `HandshakeState:14`, `Opcode:7`) to name the shared
   fields — still outstanding.

---

## Run 2026-09-05-07 — Tier 3, false-positive check on `tsvd4j-sanity`

**Headline: 1 of 3 tested "should be safe" patterns produced a false
positive.** `ConcurrentHashMap.put()` — a standard-library class explicitly
designed to be safe for concurrent writes — was reported as a conflicting
pair anyway. This is the first direct test of a question the paper never
asks: how often is TSVD4J wrong, not just "does it find something."

**Project under test:** `tsvd4j-sanity` (my own controlled test project, not
a real-world project)
**Artifact state:** pristine `4958a7f` + local fix ([TSVD4Jfix.md](TSVD4Jfix.md))
**Java:** Corretto `1.8.0_412` · **Maven:** 3.9.11

### What I added

Four new test methods in `UnsafeTest.java`, alongside the original
`twoWriters` sanity test, each testing a different "this code should
already be safe" scenario:

| Test | Pattern | Expected |
| --- | --- | --- |
| `twoWritersCollectionAdd` | Two threads, plain `ArrayList.add()` | Silent, but for the wrong reason (issue 4's off-by-one bug) |
| `twoWritersSynchronized` | Two threads, writes inside `synchronized(lock)` | Silent — genuinely safe |
| `twoWritersConcurrentHashMap` | Two threads, `ConcurrentHashMap.put()` | Silent — genuinely safe (this is the one that *should* have stayed quiet) |
| `sequentialWritersNoOverlap` | `t1.join()` fully before `t2.start()` | Silent — threads never overlap in time |

### Exact command line

```
mvn tsvd4j:clean
mvn tsvd4j:tsvd4j
```

### Output

```
Conflicting pairs found: com/example/UnsafeTest|put|92:com/example/UnsafeTest|put|92
Conflicting pairs found: com/example/UnsafeTest|21:com/example/UnsafeTest|21
Conflicting pairs found: com/example/UnsafeTest|put|20:com/example/UnsafeTest|put|20
Total # Conflicting items are = 3
```

- Tests run: 5, all passed (0 failures, 0 errors)
- 3 pairs total, all self-pairs (same line reported against itself, same
  format as the original sanity run)

### Mapping each pair back to source

| Line | Code | Verdict |
| --- | --- | --- |
| 20 (`put`) | `shared.put(...)` in the original `twoWriters` test | Expected — same as the very first sanity run |
| 21 | `counter = counter + i` in the original `twoWriters` test | Expected — same as the very first sanity run |
| **92 (`put`)** | **`concurrentShared.put(...)` in `twoWritersConcurrentHashMap`** | **False positive** |

### Things I did not expect but did see

- **`ConcurrentHashMap.put()` triggered a pair.** `ConcurrentHashMap` is from
  `java.util.concurrent`, built and documented specifically so many threads
  can call `.put()` at once with no external locking needed. TSVD4J flagged
  it exactly like an unsafe `HashMap`. It tracks by method signature
  (`Map.put(...)`) with no awareness of which concrete class is calling it,
  so it cannot tell a genuinely dangerous collection from a genuinely safe
  one. Written up as issue 15 in
  [tsvd4j_known_issues.md](tsvd4j_known_issues.md).
- **The other two "should be safe" tests were correctly silent** —
  `synchronized`-protected writes and non-overlapping threads both produced
  nothing. So TSVD4J isn't simply over-eager across the board; it
  specifically fails on the "safe collection class" case.
- **`twoWritersCollectionAdd` (plain `ArrayList.add()`) was also silent** —
  but that's the already-known issue 4 bug (the first line of `API.txt` is
  dropped, and it happens to be `Collection.add`), not evidence the tool
  understood anything about safety here. Silence has two different causes
  in this one run, which is itself worth remembering when reading any
  "0 pairs" result.

### Improvement ideas (the gold)

- A false-positive rate of 1-in-3 on a deliberately small, controlled sample
  is a real number worth quoting directly in any write-up — the paper
  reports pairs found across 12 real projects but never once measures this.
- Cheap fix: add `java.util.concurrent` (and other known-safe classes like
  `Hashtable`, `Vector`, `CopyOnWriteArrayList`) to `Agent.blackListContains`
  — the same blacklist mechanism already used to skip `java.`, `javax.`,
  `org.junit.`, etc. (issue 9).

### Next run — what I want to try

1. Test a few more standard-library thread-safe classes the same way
   (`CopyOnWriteArrayList`, `AtomicInteger`, `Collections.synchronizedMap`)
   to see how widespread this blind spot is.
2. Check whether any of the 22/18 pairs found on Java-WebSocket in Stage C/D
   actually involve a `java.util.concurrent` class — if so, those specific
   pairs should be treated as suspect, not confirmed bugs.

---

## Run 2026-09-05-09 — `marine-api`, Stages A and C (real-world false-positive follow-up)

**Headline: 0 pairs found in both API-only and field-only mode — despite the
agent genuinely running (field mode took 185× longer than baseline). This
doesn't confirm or deny the `ConcurrentHashMap` false positive on real
code — it just means this run found nothing at all, on either of the two
fields I was specifically watching or anything else.**

**Project under test:** `ktuukkan/marine-api`, commit `af00038`, 16 kLOC,
926 tests (paper's Table I count matches exactly)
**Artifact state:** pristine `4958a7f` + local fix ([TSVD4Jfix.md](TSVD4Jfix.md))
**Subject state:** upstream pom + TSVD4J plugin block only, no `argLine`
collision
**Java:** Corretto `1.8.0_412` · **Maven:** 3.9.11

**Why this project:** a follow-up to the `ConcurrentHashMap` false positive
in run 07. `marine-api` genuinely uses `ConcurrentHashMap` as real, shared
state — not a hand-written example — specifically:
`SentenceReader.java:73` (a `listeners` field) and `SentenceFactory.java`
(a static `parsers` registry, built via `ConcurrentHashMap` at line 283,
assigned at line 331). Full setup in
[marine-api_run.md](marine-api_run.md).

### Timing

| Step | Wall-clock time |
| --- | --- |
| Baseline `mvn clean test` (no TSVD4J) | ~11 s (a first attempt read 61 s, but JDK wasn't confirmed for that run — 11 s is the JDK-verified number) |
| Stage A — API-only, full suite | not separately timed, but finished normally |
| Stage C — field-only, full suite | **33 min 56 s** |
| **Overhead multiplier (Stage C)** | **≈185×** |

### Stage A (API-only)

| | |
| --- | --- |
| Tests run | 926 (matches paper's Table I exactly) |
| Classes completed | 71 / 71 |
| Failures | 1 — `SentenceReaderTest.testStartAndStop` |
| **Distinct pairs** | **0** |
| Paper's Table II, marine-api, API-only | **4** |

**The 1 failure is invasiveness, not a real bug** (same pattern as issue 13):
`testStartAndStop` does `reader.start(); Thread.sleep(500); assertNotNull(sentence);` —
a fixed 500ms budget for a background thread to process a sentence.
TSVD4J's injected delays slowed that background thread down enough that it
missed the window this run.

### Stage C (field-only)

| | |
| --- | --- |
| Build result | `BUILD SUCCESS` |
| **Distinct pairs** | **0** |
| Paper's Table II, marine-api, field-only | **1** |
| `.tsvd4j\Conflicting-Pairs.txt` present? | **No** — confirms 0, not a killed run (a killed run also produces no file, but here the build finished cleanly with `BUILD SUCCESS`, so absence here means genuinely nothing found) |

### How I confirmed this wasn't a silent failure (like issue 11's old bug)

Checked for any trace of `edu.utexas.ece.tsvd4j` in the log — found zero
mentions, which *looked* suspicious at first. But that phrase only appears
in a log when a JUnit timeout interrupts a thread mid-`Thread.sleep()` — its
absence doesn't mean the agent never attached. The real proof is the
**185× slowdown** versus baseline: that only happens if tens of thousands of
100ms delays actually fired throughout the run. The agent was genuinely
active; it just didn't find anything to report.

### Things I did not expect but did see

- **Two tracking modes, one project, zero pairs in both** — same
  "TSVD4J reports 0 despite real activity" pattern already flagged for
  `openpojo` in [next_steps.md](next_steps.md), but `openpojo`'s leading
  theory is heavy reflection defeating the instrumenter, which doesn't
  apply here — `marine-api` is a plain parsing library with no reflection
  to speak of. So this looks like the *same symptom* with a *different*
  (still unknown) cause.
- **This specifically fails to answer the question I ran this project
  for.** I confirmed `marine-api` genuinely uses `ConcurrentHashMap` as
  real shared state, and confirmed the agent was genuinely active and
  slowing the run down — but it still found nothing there. Two honest
  explanations, not mutually exclusive: TSVD4J's own non-determinism (a
  different run might catch what this one missed — same caution as Gap 2 in
  [research_gaps.md](research_gaps.md)), or the actual concurrent access to
  `listeners`/`parsers` just didn't happen to overlap closely enough in
  time during this particular test execution to trigger the delay check.

### Stage D (both trackers together) — update, same run

**Result: 0 pairs, again. `marine-api` is now 3 for 3 zero.**

| | |
| --- | --- |
| Build result | `BUILD SUCCESS` |
| Total time | **36 min 29 s** |
| Tests run | 926, 1 failure (`SentenceReaderTest.testStartAndStop` — same known invasiveness issue, not new) |
| **Distinct pairs** | **0** |
| Paper's Table II, marine-api, default (both) | **5** |
| `.tsvd4j\Conflicting-Pairs.txt` present? | **No** — only `listener.log`, same as Stage A and C |

No hang this time either — unlike `Issue941Test` on Java-WebSocket, nothing
here got permanently stuck; it simply took its 36 minutes and finished
cleanly on its own.

### Final tally for `marine-api`, all three modes

| Mode | Paper says | I found |
| --- | --- | --- |
| API-only | 4 | **0** |
| Field-only | 1 | **0** |
| Default (both) | 5 | **0** |

**This project found nothing, in any mode, at all.** Not "fewer than the
paper" — literally zero, every time, across three separate runs that each
genuinely executed (confirmed by the massive overhead each showed, and by
71/71 or near-71/71 classes completing with only one already-explained
failure throughout).

### Next run — what I want to try

1. ~~Run Stage D~~ — done, also 0.
2. **`marine-api` should now be treated the same way as `openpojo`: a
   project where TSVD4J finds nothing at all, for a reason that isn't yet
   understood.** `openpojo`'s leading theory (heavy reflection) doesn't
   apply here, so this is a second, independently-caused instance of the
   same symptom — which is itself worth a line in
   [tsvd4j_known_issues.md](tsvd4j_known_issues.md): **on at least 2 of the
   paper's 12 projects, running the tool exactly as prescribed produces zero
   output, for reasons that differ project to project and remain
   unexplained.**
3. For the original goal (real-world evidence of the `ConcurrentHashMap`
   false positive) — `marine-api` is now a dead end. A third candidate
   project should be picked, or the repetition experiment (5× reruns) tried
   first to rule out "just one/three unlucky runs" before giving up on this
   project entirely.

### Run 2 — full repeat, confirms the result is stable

Repeated all three stages a second time, independently (fresh
`tsvd4j:clean` before each, same commands, script:
[run-repeat.ps1](../flaky-study/marine-api/run-repeat.ps1)).

| Mode | Run 1 | Run 2 |
| --- | --- | --- |
| API-only | 0 (BUILD SUCCESS, ~2 min) | 0 (BUILD SUCCESS, 3m25s) |
| Field-only | 0 (BUILD SUCCESS, 33m56s) | 0 (BUILD SUCCESS, 33m54s) |
| Default (both) | 0 (BUILD SUCCESS, 36m29s) | 0 (BUILD SUCCESS, 36m25s) |

**6 for 6 across two independent full runs — this is no longer "one
unlucky run," it's a confirmed, stable, repeatable result.** Timing is
nearly identical between the two runs for every stage, which itself
confirms both runs genuinely executed the same way (not a fluke of one run
happening to skip work). This settles the "is it noise?" question raised
after run 1 — it is not noise, `marine-api` reliably produces zero pairs
for TSVD4J in every tracking mode.

**What this means for each open question:**
- **The `ConcurrentHashMap` false-positive question**: confirmed dead end
  on this project — not "maybe unlucky," genuinely closed. A third
  candidate project is needed.
- **The reproducibility question (issue 16 / Gap 3)**: strengthened, not
  weakened — this is now backed by 2 independent full runs, not 1, making
  it a much more solid claim that this specific paper result (Table II's
  marine-api row) does not reproduce.

---

## Run 2026-09-06-10 — `commons-dbcp`, Stage A stalls immediately on the very first class

**Headline: Stage A (the fast, cheap mode) hit the quadratic-slowdown bug
(issue 2) on the *first* test class, in a *fresh* JVM — something that took
~55 classes to happen on Java-WebSocket. Root cause identified precisely
this time: one test spins up 200 real threads doing 1,000,000 total
connection-pool operations.**

**Project under test:** `apache/commons-dbcp`, release tag
`rel/commons-dbcp-2.14.0`
**Artifact state:** pristine `4958a7f` + local fix ([TSVD4Jfix.md](TSVD4Jfix.md))
**Subject state:** upstream pom + TSVD4J plugin block only. Known
pre-existing `argLine` collision at pom.xml:247 (issue 5) — not yet
determined whether it matters, see below.
**Java:** Corretto `1.8.0_412` · **Maven:** 3.9.11 · Test framework:
JUnit 5 (`JUnitPlatformProvider` auto-detected)

### Exact command line

```
mvn tsvd4j:clean
mvn tsvd4j:tsvd4j -Dapi -DreuseForks=false "-Dsurefire.timeout=600" "-Dmaven.test.failure.ignore=true" *> logs\stage-a.log
```

### What happened

- Log showed `Running org.apache.commons.dbcp2.cpdsadapter.TestDriverAdapterCPDS`
  and then nothing else for 19+ minutes.
- CPU check on the forked test JVM: **2326 seconds of CPU time in ~1140
  seconds of wall clock** — saturating roughly 2 cores continuously. Not
  blocked, genuinely busy — same profile as the original Java-WebSocket
  measurement in issue 2 (14,776 CPU-s in 79 min there).
- `.tsvd4j\` was still empty at the time of the check — this class had not
  finished even once, in a completely fresh JVM (`-DreuseForks=false`
  guarantees no state carried in from a prior class).

### Root cause, found in the test source itself

`TestDriverAdapterCPDS.java` contains an inner class `ThreadDbcp367`
(almost certainly named after a real historical Apache DBCP concurrency
bug ticket) whose `run()` method is:

```java
for (int j = 0; j < 5000; j++) {
    conn = dataSource.getConnection();
    conn.close();
}
```

...and the test method spawns **200 of these threads at once**:

```java
final ThreadDbcp367[] threads = new ThreadDbcp367[200];
```

**200 × 5000 = 1,000,000 connection get/close cycles**, each one exercising
the exact `pcMap`/`validatingSet` `ConcurrentHashMap` fields
([commons-dbcp_run.md](commons-dbcp_run.md)) this whole detour was set up to
test. This confirms issue 2's mechanism precisely: the bug isn't about
*how many test classes* have run, it's about *total interception-point
count* — one sufficiently intense test can trigger it immediately, in a
brand-new JVM, with zero history from anything else.

### What I did

Killed it (`Ctrl+C`) — this bug does not recover with time, it only gets
worse (issue 2's own "cheap early, catastrophic late" profile). Excluded the
class and resumed:

```
mvn tsvd4j:tsvd4j -Dapi -DreuseForks=false "-Dsurefire.timeout=600" "-Dmaven.test.failure.ignore=true" "-Dsurefire.excludes=**/TestDriverAdapterCPDS.java" *> logs\stage-a-part2.log
```

### Things I did not expect but did see

- **The quadratic bug can trigger on the very first class of a fresh JVM**,
  not just after accumulating history across dozens of classes. This
  refines issue 2: severity scales with *total operation count within the
  window TSVD4J is watching*, regardless of whether that count comes from
  many small classes or one single enormous one.
- **A missed opportunity, worth flagging honestly**: this exact test was
  the single best candidate seen so far for the `ConcurrentHashMap`
  false-positive question (issue 15 / Gap 1) — 200 threads hammering the
  precise fields we're watching, in real production test code, not
  something hand-written. Excluding it was the only practical choice (it
  would never finish), but it means the best evidence available got thrown
  away rather than captured.

### Improvement ideas (the gold)

- A scaled-down version of this exact test (e.g. 10 threads × 50 iterations
  instead of 200 × 5000) run as a small standalone project — same idea as
  `tsvd4j-sanity`, but modeled directly on real production code instead of
  hand-written from scratch — could recover this lost opportunity cheaply,
  without needing TSVD4J to survive a million-operation stress test.

### Next run — what I want to try

1. Finish Stage A with this one class excluded, then proceed to the Step 4
   timing check (still needed — the `argLine` collision risk is still
   unresolved).
2. Seriously consider building the scaled-down `ThreadDbcp367`-style test
   as a new, deliberate `tsvd4j-sanity`-style project — this could be the
   real breakthrough for the false-positive question that `marine-api`
   failed to deliver.

---

## Run 2026-09-06-11 — `commons-dbcp`, Stage A completes — the false positive is CONFIRMED on real, unmodified production code

**Headline: 6 distinct conflicting pairs found. 3 of them directly hit the
exact `ConcurrentHashMap`-backed fields (`validatingSet`, `pcMap`) this
whole detour was set up to test — via three different access patterns
(`contains`/`remove`, `get`/`put`, `remove`/`remove`). This is the result
`marine-api` failed to produce twice. Issue 15 is no longer "confirmed on a
hand-written test, unconfirmed on real code" — it is confirmed on real,
unmodified, third-party production code.**

**Project under test:** `apache/commons-dbcp`, release tag
`rel/commons-dbcp-2.14.0`
**Command:** `mvn tsvd4j:tsvd4j -Dapi -DreuseForks=false
"-Dsurefire.timeout=600" "-Dmaven.test.failure.ignore=true"
"-Dsurefire.excludes=**/TestDriverAdapterCPDS.java,**/TestSharedPoolDataSource.java"`
(the two classes excluded were the quadratic-slowdown and delay-induced-hang
casualties from earlier in this same run — see the two entries above)

### Timing (settles the Step 4 question from the guide)

| | |
| --- | --- |
| Baseline (`mvn clean test`, no TSVD4J) | 169.4 s (2m49s) |
| Stage A (API-only, 2 classes excluded) | 179 s (2m59s) |
| Overhead | **~6%** |

This is a much smaller overhead than field mode showed on `marine-api`
(185×), which at first looked like "the agent never attached" (the guide's
Step 4 heuristic assumed field-mode-sized overhead as the bar). **The pairs
themselves are the real proof** — TSVD4J cannot produce this specific,
structured output without genuinely running its instrumentation and delay
logic. The small overhead makes sense in hindsight: API mode only
intercepts ~260 whitelisted method calls, not every field access the way
field mode does, so its overhead is inherently much lighter. **Correction to
the guide's Step 4**: "no dramatic slowdown" does not mean "the agent didn't
attach" for API mode specifically — check for actual pairs/output before
concluding a silent failure. Field mode's overhead expectation still holds
for field mode.

### The 6 pairs, and what each one means

```
KeyedCPDSConnectionFactory|contains|94 : AbstractConnectionFactory|remove|141
GenericKeyedObjectPool|get|1594 : GenericKeyedObjectPool|put|909
KeyedCPDSConnectionFactory|get|95 : KeyedCPDSConnectionFactory|put|204
KeyedCPDSConnectionFactory|remove|144 : KeyedCPDSConnectionFactory|remove|144
GenericKeyedObjectPool|get|1594 : GenericKeyedObjectPool|remove|982
GenericKeyedObjectPool|remove|982 : GenericKeyedObjectPool|remove|982
```

| Pair | Field involved | Verified as | Verdict |
| --- | --- | --- | --- |
| `KeyedCPDSConnectionFactory:94` × `AbstractConnectionFactory:141` | `validatingSet` (`Collections.newSetFromMap(new ConcurrentHashMap<>())`) | `validatingSet.contains(pc)` (line 94, inherited field) racing `validatingSet.remove(pooledConn)` (line 141) | **False positive** — `ConcurrentHashMap`-backed set, safe by construction |
| `KeyedCPDSConnectionFactory:95` × `:204` | `pcMap` (`ConcurrentHashMap`) | `pcMap.get(pc)` racing `pcMap.put(pooledConnection, pci)` | **False positive** — same reasoning |
| `KeyedCPDSConnectionFactory:144` (self) | `pcMap` | Two threads both calling `pcMap.remove(pooledConnection)` | **False positive** — same reasoning |
| `GenericKeyedObjectPool:1594` × `:909` | `allObjects` (`ConcurrentHashMap`, in `commons-pool2`) | `allObjects.get(...)` racing `allObjects.put(...)` | **False positive** — same reasoning, different library |
| `GenericKeyedObjectPool:1594` × `:982` | `allObjects` (`commons-pool2`) | `allObjects.get(...)` racing `allObjects.remove(...)` | **False positive** — same reasoning |
| `GenericKeyedObjectPool:982` (self) | `allObjects` (`commons-pool2`) | Two threads both calling `allObjects.remove(...)` | **False positive** — same reasoning |

### Verified directly in source (not just inferred from the pair format)

```java
// KeyedCPDSConnectionFactory.java:94
if (!validatingSet.contains(pc)) {
// KeyedCPDSConnectionFactory.java:95
    final PooledConnectionAndInfo pci = pcMap.get(pc);
// KeyedCPDSConnectionFactory.java:204
pcMap.put(pooledConnection, pci);
// KeyedCPDSConnectionFactory.java:144
pcMap.remove(pooledConnection);
// AbstractConnectionFactory.java:141
validatingSet.remove(pooledConn);
```

Both `validatingSet` and `pcMap` are declared in `AbstractConnectionFactory`
(lines 48/53, per [commons-dbcp_run.md](commons-dbcp_run.md)) and inherited
by `KeyedCPDSConnectionFactory`. Every operation TSVD4J flagged
(`contains`, `get`, `put`, `remove`) is one of the exact operations
`ConcurrentHashMap` (and `Collections.newSetFromMap` over one) is
specifically designed and documented to make safe under concurrent access
from multiple threads with no external locking. None of this code was
written by us, modified by us, or hand-picked to trigger a bug — it is
Apache Commons' own production connection-pooling logic, doing exactly what
it was designed to do.

### Why this is the strongest version of this finding so far

- **`tsvd4j-sanity` (issue 15, original)**: proved the bug is *possible*,
  using code written specifically to test it.
- **`marine-api`**: an attempt at real-world evidence — inconclusive, 0
  pairs found in every mode, twice.
- **`commons-dbcp` (this run)**: real-world evidence, **positive, and total**
  — **all 6 pairs found were confirmed false positives**, spanning 2
  completely separate libraries (`commons-dbcp` itself and its
  `commons-pool2` dependency), 3 different container fields, and every
  basic map/set operation (`get`, `put`, `remove`, `contains`). Confirmed by
  cloning `commons-pool2`'s exact matching version (`rel/commons-pool-2.13.0`)
  to check the 3 pairs in that library directly — its `allObjects` field
  (`GenericKeyedObjectPool.java:115`) is also a `ConcurrentHashMap`. Full
  code walkthrough for all 6: [six_pairs_explained.md](six_pairs_explained.md).

### Improvement ideas (the gold)

- This is now solid enough to be the centerpiece of a write-up: **TSVD4J's
  own paper never measures false positives, and this shows real
  production code — the kind any of the paper's 12 evaluated projects
  could plausibly contain — triggers them, across multiple independent
  codebases.** Any of the paper's own 55 reported pairs that touch a
  `java.util.concurrent` class should be treated as suspect until
  individually verified, not counted as confirmed bugs.
- **A 100% false-positive rate on this run's 6 pairs is itself a headline
  number** — worth stating plainly in any write-up, with the caveat that
  this is one run on one project, not a claim about TSVD4J's overall rate
  across all possible code.

### Next run — what I want to try

1. Run Stage C (field mode) and Stage D (both) on `commons-dbcp` — now that
   the agent is confirmed working, these should be run for completeness
   and might catch even more false positives (field mode watches
   `validatingSet`/`pcMap` even more thoroughly than API mode does).
2. Update [tsvd4j_known_issues.md](tsvd4j_known_issues.md) issue 15 and
   [research_gaps.md](research_gaps.md) Gap 1 to reflect this as answered,
   not just theorized.

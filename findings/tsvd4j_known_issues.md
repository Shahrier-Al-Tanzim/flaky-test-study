# TSVD4J — known issues found by reading the source

Everything here was found by reading the artifact at
`flaky-study\TSVD4J` (master, commit `4958a7f`) against the ICSE 2023 paper.
None of it is documented in the paper or the README.

This file matters for two reasons: it explains why runs stall, and several
entries are publishable observations of the kind the advisor asked for
("limitations you identify, potential opportunities for improving existing
techniques").

Severity key: **B** = blocks a run, **C** = corrupts results, **L** =
limitation worth writing up.

---

## 1. (B) The delay is hard-coded at 100 ms

`Utility.java`:

```java
// TODO: Make it configurable amount of delay (currently constant 100ms)
public static void delay() {
    try { Thread.sleep(100); }
```

The authors flag this themselves. Because `ClassTracer.visitFieldInsn`
instruments **every** `putfield`/`putstatic`/`getfield`/`getstatic` in every
non-blacklisted class, and `Utility.shouldDelay` returns true for essentially
every write, a normal suite becomes unrunnable. A proposed (unapplied) fix is
[M1 in tsvd4j_run.md](tsvd4j_run.md#m1-make-the-injected-delay-configurable).

**Write-up angle:** the delay is the single knob that trades detection power
against runtime, and the tool exposes no way to set it. Measuring the
pairs-found-vs-delay curve on P1–P6 is a small, self-contained study.

---

## 2. (B) `Helper.threadCountList` grows without bound

`Helper.createInstance`, both overloads:

```java
long currentThreadId = Thread.currentThread().getId();
String uniqueThread = String.valueOf(currentThreadId) + Thread.currentThread().getName();
if (!threadCountList.contains(currentThreadId)) {   // Long tested against List<String>
    threadCountList.add(uniqueThread);
}
```

`contains(currentThreadId)` autoboxes a `long` to `Long` and compares it to
`String` elements, so it is **always false**. A new string is appended on every
interception point — millions of them — and never removed. The list is a plain
`ArrayList` mutated from many threads, so it is also itself thread-unsafe.

### The real mechanism: quadratic slowdown, not heap exhaustion

**Corrected 2026-09-04 after measuring a live run.** An earlier version of this
note said the stall was heap filling up and GC thrashing. That was wrong. The
actual mechanism is worse and more specific:

`.contains()` on an `ArrayList` is a **linear scan**. Since the list grows by
one entry on *every* interception point and is never pruned, each new
interception point scans the entire history of every previous one. Cost per
operation grows linearly with operations already done, so total cost is
**quadratic** — O(n²). The tool does not slow down gradually; it falls off a
cliff.

The same pattern appears in at least three more places, all `ArrayList` +
`.contains()` + never pruned:

| Location | List | Scanned on |
| --- | --- | --- |
| `Helper.createInstance` | `threadCountList` | every interception point |
| `Utility.findRacingTP` | `dangerousTPPairs` | every racing pair check |
| `TestListener.testFinished` | `conflictingListPair` | every pair, every test |

**Measured evidence** (Stage A, `-Dapi`, Java-WebSocket, JDK 8, single reused
fork):

- Forked test JVM accumulated **14,776 seconds of CPU time in ~79 minutes of
  wall clock** — i.e. it was saturating roughly 3 cores continuously. The
  process was *not* blocked or parked; it was busy.
- First ~30 test classes (simple, single-threaded: `framing`, `exceptions`,
  `drafts`, `extensions`) finished in **34 seconds total**.
- Then `issues.AllIssueTests` alone took **15 minutes**.
- By class ~55 it was spending **25+ minutes on a single class** with no
  forward progress, still burning CPU the whole time.

That profile — cheap early, catastrophic late, CPU-saturated throughout — is
the signature of the quadratic scan, not of memory pressure.

Proposed (unapplied) fix:
[M2 in tsvd4j_run.md](tsvd4j_run.md#m2-fix-the-unbounded-threadcountlist-growth).
The no-code-change mitigation is `-DreuseForks=false` (W2), which is more
valuable than first assumed: a fresh JVM per test class **resets every one of
these lists**, removing the quadratic growth at its source rather than merely
capping the damage.

**Write-up angle:** a thread-safety violation *inside* a thread-safety
violation detector, on the exact data structure class the tool is built to
watch. Also: `Agent.java` prints `Total # Thread Count = <size>`, so every
reported thread count in any TSVD4J run is wrong. And the quadratic profile
means the paper's 6-hour-per-application timeout is not a generous safety
margin — it is a hard ceiling the tool hits by design on any suite large
enough.

**Second confirmed instance, on a different project — refines the trigger
condition.** On `commons-dbcp`, this bug fired on the *very first* test
class of a completely fresh JVM (`-DreuseForks=false`, so no state carried
over from anything prior) — not after ~55 classes like on Java-WebSocket.
Root cause: that one test (`TestDriverAdapterCPDS`) spins up 200 real
threads each doing 5000 connection-pool operations — 1,000,000 total
operations in one test method. Measured: 2326 CPU-seconds burned in ~19
minutes of wall clock (saturating ~2 cores) with zero progress. This
confirms the bug's real trigger is **total interception-point count**, not
"how many classes have run" — a single sufficiently intense test can
trigger it immediately, with no accumulated history required. See
[tsvd4j_findings.md](tsvd4j_findings.md) run 2026-09-06-10.

---

## 3. (B) `Utility.lastInterceptionPointForOBJ` is never pruned

`findRacingTP` inserts one entry per object/field identity hash and only ever
trims the *inner* list to `lastTPWindow = 5`. The outer map keeps one entry per
distinct object ever touched. Combined with `planDistance = 10000000` ms
(~2.8 h), effectively nothing ever ages out, so `dangerousTPPairs` grows too.

No clean patch — the workaround in the run guide is `-DreuseForks=false`, which
gives each test class a fresh JVM and resets all static state.

**Write-up angle:** the memory profile is unbounded in the number of distinct
objects, which is why the paper's projects are all ≤24 kLOC. Ask whether the
approach scales at all to a large application.

---

## 4. (C) `ClassTracer.loadFile` skips the first API and appends `null`

```java
String line = reader.readLine();
while (line != null) {
    line = reader.readLine();
    listAPI.add(line);
}
```

The first `readLine()` result is discarded before the loop body ever uses it,
and the final `null` is added to the list. `API.txt` has 260 entries and its
first line is:

```
java/util/Collection/add(Ljava/lang/Object;)Z
```

So **`Collection.add` is never instrumented**, and the tracked API list is
259 entries with a `null` in it. Every API-mode number in Table II was produced
with this bug active.

This is a plausible partial explanation for API-only finding 0 pairs on P1 and
only 12 across all 12 applications, versus 43 for field tracking — the paper
attributes that gap entirely to field tracking being more powerful.

**Write-up angle:** re-run the API-only column with the off-by-one fixed and
see whether the API/field split in the paper's central claim still holds. This
is a direct, cheap, checkable challenge to a published result.

---

## 5. (C) `TSVD4JMojo` silently discards the project's existing `argLine`

`AbstractTSVD4JMojo.execute` carefully reads it:

```java
this.originalArgLine = localProperties.getProperty("argLine", "");
```

…and `applyConfig` then never uses it, instead adding a fresh `<argLine>` child
and overwriting the project property with only the `-javaagent` flag. Any
`--add-opens`, `-Xmx`, or JaCoCo agent the project needed is dropped. If the
project already configured `<argLine>` inside surefire, the config gains a
duplicate child and surefire may take the wrong one — in which case the agent
never attaches and `.tsvd4j/` is empty **with no error**.

---

## 6. (L) The test listener is JUnit 4 only

`TSVD4JMojo` injects `edu.utexas.ece.tsvd4j.listener.TestListener` through
surefire's `listener` property, and the class `extends
org.junit.runner.notification.RunListener` — JUnit 4. On a JUnit 5 project the
property is ignored, losing both per-test attribution and the incremental
output that makes an interrupted run salvageable.

Since `Conflicting-Pairs.txt` is written only from a shutdown hook, a JUnit 5
project that times out yields **nothing at all**.

**Write-up angle:** IDoFT and most currently-maintained Maven projects have
moved to JUnit 5. The tool's applicability to today's ecosystem is narrower
than the paper implies.

---

## 7. (L) `isTrapActive` is written outside synchronization

`Utility.onCall` is not synchronized but starts with `isTrapActive = false;`,
while every reader (`shouldDelay`) and the other writers (`setTrap`,
`clearTrap`) are `static synchronized`. The authors' own comment notes this.
Practical effect: `!isTrapActive` is nearly always true when `shouldDelay`
runs, so the "only delay when no trap is active" heuristic barely applies and
almost every write delays. That is both a correctness question about the
reimplementation of TSVD's heuristics and a large part of the runtime cost.

---

## 8. (L) Suite classes cause double execution

Java-WebSocket ships `AllTests.java`, `AllClientTests.java`, etc. Surefire
matches both the suite classes and the individual test classes, so each test
runs twice. The paper's "641 tests" for P1 is therefore not 641 distinct
tests. Whether the same holds for P2–P6 has not been checked, which would
need verifying before trusting Table I's counts.

---

## 9. (L) Instrumentation blacklist is a hard-coded string array

`Agent.blackListContains` holds a fixed list (`java.`, `javax.`, `sun.`,
`jdk.`, `com.google.`, `org.eclipse.jetty.`, `org.slf4j.`, `org.junit.`,
`org.mockito.`, …). It is not configurable, so an application package
causing trouble cannot be excluded, and any modern framework not on
the list (Netty, Spring, Jackson, JUnit 5's `org.junit.jupiter` is covered by
`org.junit.` but its `platform` engine internals are too) gets fully
instrumented. This is a large part of why runtime explodes on real projects.

---

## 10. (L) Dependency versions pin the tool to ≤ Java 16

`tsvd4j-core/pom.xml`: ASM **9.0** (class files ≤ Java 16), `asm-commons`
**7.3.1**, `javassist` **3.14.0-GA** (2011). The parent pom compiles with
`<source>1.8</source>` and passes `-noverify`, removed-in-spirit since JDK 13.
The paper says "Java 8 and up", which is true only up to Java 16.

**Write-up angle:** this is the Tier 4 experiment in
[next_steps.md](next_steps.md) — quantify exactly where the tool stops working
and what it would take to support current LTS JDKs.

---

## 11. (B) Quote marks around the agent path make the tool unrunnable on Windows

`TSVD4JMojo.getPathToTSVD4JJar` (line 79) returns the jar path wrapped in
**literal** quote characters:

```java
return "\"" + result + "\"";
```

That value is used in two places — the `-javaagent` argument and an
`additionalClasspathElement`. A quote mark is an **illegal character in a
Windows file path**, so as soon as Surefire treats the string as a real file
location, it fails. Observed in `mvn -X` output as a stray trailing quote
inside the classpath list:

```
... json-20180813.jar  tsvd4j-core-0.1-SNAPSHOT.jar"  surefire-junit4-3.2.5.jar ...
```

Immediately after that line the log jumps to `Tests run: 0` with no fork
attempt at all. Every mode (`-Dapi`, `-Dfield`, default) produces zero output,
in ~4 seconds, forever. **Unlike issues 1–3, there is no command-line
workaround** — the string is built unconditionally in Java code with no
property to override it.

Made much harder to diagnose by issue 12 below. Fix and step-by-step
instructions: [TSVD4Jfix.md](TSVD4Jfix.md).

**Write-up angle:** the published artifact cannot run at all on Windows out of
the box. Worth checking whether the authors only ever ran it on Linux/macOS,
where `"` is a legal filename character. This is a reproducibility finding in
its own right.

---

## 12. (C) `TSVD4JMojo` reports BUILD SUCCESS when Surefire fails

`TSVD4JMojo.execute`:

```java
} catch (MojoExecutionException mojoException) {
    Logger.getGlobal().log(Level.INFO, "Surefire failed when running tests");
}
```

The exception is swallowed, logged at **INFO** level as a single vague line,
and the build then reports `BUILD SUCCESS`. The underlying cause — the actual
message and stack trace — is discarded entirely and is **not** recovered even
with `-X`.

Practical effect: issue 11 presented as "the build succeeded, 0 tests ran, no
errors." Nothing in the normal output indicates a failure occurred. Finding
the real cause required inspecting `-X` debug output line by line and testing
the agent jar outside Maven.

**Write-up angle:** silent failure with a success exit code is worse than a
crash — a CI pipeline using this tool would report green while collecting no
data at all.

---

## 13. (L) The tool's delays convert latent test bugs into permanent hangs

Observed directly in a Stage A run on Java-WebSocket. `Issue941Test` calls
`pingLatch.await()` with no timeout, relying on a network ping arriving
promptly. Under instrumentation the run reached that class and made no
progress for 25+ minutes while saturating CPU.

Related: `Issue825Test` sleeps 10 s inside a 15 s limit — injected delays push
it over. And a `BindException: Address already in use` cascade appears in
server tests when a port is not released before the next test binds it.

**Write-up angle:** this is the invasiveness question the paper never
addresses. TSVD4J changes the timing of the program it measures, and that
change is large enough to break tests that pass without it. Any pair count it
reports comes from a program behaving differently than it does in production —
so how much of what it finds is reachable in the un-instrumented program?
Quantify by diffing the baseline `target\surefire-reports\` against the
instrumented one.

---

## 14. (L) `-DreuseForks=false` cannot reset state *inside* a suite class

Observed directly during Stage D on Java-WebSocket. Surefire only starts a
fresh fork **between top-level test classes** — but `AllTests.java` (and
`AllClientTests`, `AllIssueTests`, etc.) is itself just *one* top-level class
that internally runs dozens of other test classes via JUnit's
`@Suite.SuiteClasses`. Surefire has no visibility into that internal list, so
`-DreuseForks=false` cannot reset TSVD4J's leaking static state (issue 2)
partway through a suite — only once the *entire* suite class finishes and its
fork exits.

Practical effect: because `AllTests` runs first (alphabetical) and is left in
the run (per the guide's own advice — excluding suite classes "risks missing
whatever cross-class state a suite run might exercise differently"), the
quadratic-slowdown bug in issue 2 gets a much longer, uninterrupted window to
compound inside `AllTests` than it does for any of the many standalone
classes that follow it. This didn't fatally stall Stage A or C, but it is the
same underlying risk waiting to resurface on a larger suite or a slower
machine — `-DreuseForks=false` is a **per-Surefire-class** mitigation, not a
per-JUnit-class one, and this project's own suite classes are exactly the
case that falls through that gap.

**Write-up angle:** combined with issue 8 (suite classes cause double
execution), this means the workaround guide already recommends for the
quadratic bug (W2) provides *no protection at all* for the portion of the
suite that runs through `AllTests` and friends — a fork-level fix cannot help
with a problem that exists below the fork's own granularity. The only
no-code mitigation is excluding suite classes outright
(`-Dsurefire.excludes=**/All*Tests.java`), which trades this risk for losing
whatever cross-class state the suite might have exercised.

---

## 15. (C) TSVD4J does not know which collection classes are already thread-safe

Confirmed directly with a controlled test in `tsvd4j-sanity` (`UnsafeTest.java`,
`twoWritersConcurrentHashMap`): two threads calling `.put()` on a
`java.util.concurrent.ConcurrentHashMap` — a class from Java's own standard
library, specifically designed and documented to be safe for exactly this
pattern — was reported as a conflicting pair:

```
Conflicting pairs found: com/example/UnsafeTest|put|92:com/example/UnsafeTest|put|92
```

Meanwhile, two other genuinely-safe patterns tested at the same time were
correctly left silent: writes protected by `synchronized` on a shared lock,
and two threads that never actually overlap in time (`t1.join()` called
before `t2.start()`). So this isn't TSVD4J being universally over-eager — it
specifically fails to special-case thread-safe collection classes. It tracks
`Map.put()` (and presumably the rest of `API.txt`'s ~260 methods) by method
signature alone, with no awareness that `ConcurrentHashMap`, `Vector`,
`Hashtable`, `CopyOnWriteArrayList`, and other `java.util.concurrent`/legacy
synchronized classes already guarantee the exact safety property the tool is
checking for.

**Write-up angle:** the paper reports pairs found but never checks how many
are real bugs vs. false alarms — this is a direct, reproducible answer: at
least 1 of 3 tested "should be safe" patterns produced a false positive, a
33% false-positive rate on this tiny sample. Any of TSVD4J's 55
paper-reported pairs that involve a `java.util.concurrent` class deserves a
second look before being counted as a real bug. A cheap, high-value fix
would be adding the `java.util.concurrent` package (or a specific
already-synchronized-classes list) to `Agent.blackListContains` (see issue
9) — same mechanism already used to skip `java.`/`javax.`/`org.junit.` etc.

**Confirmed on real, unmodified production code — no longer just a
hand-written test.** Ran API-only mode on `apache/commons-dbcp` (a real
connection-pooling library, not written or modified for this study) and
got 6 conflicting pairs. **All 6 confirmed false positives** — 3 hit
`ConcurrentHashMap`-backed fields in `commons-dbcp` itself (`validatingSet`
and `pcMap` in `AbstractConnectionFactory`/`KeyedCPDSConnectionFactory`),
and the other 3 hit a `ConcurrentHashMap`-backed field
(`allObjects`) in `commons-pool2` — a completely separate library that
`commons-dbcp` depends on, confirmed by cloning that library's exact
matching version. Across both libraries, every basic map/set operation was
represented: `contains`×`remove`, `get`×`put`, `get`×`remove`, and two
`remove`×`remove` self-pairs. Every one of these is exactly the access
pattern `ConcurrentHashMap` is built to make safe. A prior attempt on
`marine-api` (also chosen for genuine `ConcurrentHashMap` usage) found
nothing in any mode, twice — this is the result that attempt was looking
for, on a different real project, and then some. Full code walkthrough for
all 6: [six_pairs_explained.md](six_pairs_explained.md). Run
detail: [tsvd4j_findings.md](tsvd4j_findings.md) run 2026-09-06-11.

---

## 16. (L) The tool reproduces zero of the paper's own results on some projects, for reasons that differ each time

Confirmed directly on `ktuukkan/marine-api` (paper's commit `af00038`): ran
all three tracking modes exactly as prescribed — API-only, field-only, and
default (both) — and got **0 conflicting pairs every time**, against the
paper's own reported 4, 1, and 5 respectively. Each run was confirmed
genuinely active, not a silent failure like issue 11/12: field-only alone
took 185× longer than the untouched baseline, and default mode took 36.5
minutes with 71/71 (or near-71/71) classes completing normally. The agent
was demonstrably running and injecting delays the whole time; it just never
caught anything. **Repeated a second time, independently, with the same
result** — 6 for 6 across two full runs, with nearly identical timing both
times, ruling out "one unlucky run" as the explanation. Full detail:
[tsvd4j_findings.md](tsvd4j_findings.md) run 2026-09-05-09.

**Correction (2026-09-06): re-checked this against the paper's actual
Table II directly, and the `openpojo` comparison below was stated too
strongly — fixing it here.** `openpojo` (P6) is reported as API-only=2,
field-only=**0**, total=2 — only field mode is zero, not "every tracking
mode." The project genuinely reported as 0 across *every* technique
(RV-Predict, API, field, and total) in the paper's own data is **J5
(JaConTeBe-lucene)**, not `openpojo`.

That said, the real point stands on its own without needing the `openpojo`
comparison: **`marine-api`'s own row in the paper reports 4/1/5
(API/field/total) — and our repeated, confirmed-active runs got 0/0/0,
directly contradicting the paper's specific numbers for this exact
project**, which is arguably a stronger reproducibility concern than a
same-project partial zero would be. `openpojo`'s field-only=0 and J5's
total=0 are both worth keeping in mind as separate, paper-acknowledged data
points about where the tool struggles — [next_steps.md](next_steps.md)
already flags `openpojo`'s case correctly (reflection defeating the
instrumenter, field-only specifically) — but they are not the same claim as
what `marine-api` shows here.

**Write-up angle:** if 2 of the paper's 12 evaluated projects are this
unreliable to reproduce, that is a direct, quantifiable reproducibility
concern about Table II as a whole — not just "the tool is non-deterministic
by a few pairs" (the caution already noted in Step 8), but "the tool can
silently reproduce nothing at all" on a meaningful fraction of the paper's
own benchmark. Worth checking the remaining paper projects specifically for
this pattern, to see whether it's 2-of-12 or something larger.

---

## Suggested order to investigate

1. **Issue 11 + 12** (Windows blocker + silent failure) — already encountered
   directly during this study; the fastest write-up and directly about
   reproducibility.
2. **Issue 4** (API off-by-one) — cheap, and directly touches a published
   claim.
3. **Issue 2** (quadratic slowdown) — now backed by a CPU measurement; pairs
   naturally with issue 1 (delay curve) as a scalability study.
4. **Issue 13** (invasiveness) — the most interesting scientific question of
   the set.
5. **Issue 6** (JUnit 5) — establishes how much of today's ecosystem the tool
   can actually reach.

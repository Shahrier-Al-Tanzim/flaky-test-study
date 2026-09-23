# RankF - Findings log

> Observations from replicating the RankF artifact. Organised by category.
> Every entry gives: the exact command, the wall-clock, what was expected (from
> the paper), what happened, and why the difference matters. Entries are never
> deleted.

## Run-block template

    ### YYYY-MM-DD - <one-line title> `[TAG]` `[TAG]`
    **Subject:** <project> module <module>, SHA <sha>
    **OD test:** <fully qualified name>, kind: victim / brittle
    **Paper says:** <the exact number or claim, with table/section>
    **Command:**
    ```
    <the full command, every flag>
    ```
    **Wall-clock:** <time>
    **Observed:** <what actually happened>
    **Gap:** <what is different, and why that is interesting>
    **Log:** findings/logs/rankf/<file>.log

---

## Primary subject decision (Step 9)

**`marine-api` is the primary subject for Modules 3–6.** The Wei et al.
ground-truth CSV (`flaky-study/RankF/wei-dataset/wei-od-dataset.csv`) contains
exactly **12 unique OD tests** for `marine-api` at SHA
`af0003847db9ba822f67d4f1dceb8de3fe63250a` - the **same SHA and the same 12
test names** already confirmed by this study's own iDFlakies run (see
`idflakies_findings.md`, "12/12 flaky tests found - exact match" against
IDoFT). This is the ideal case the methodology described here calls for: ground truth and our own
already-collected test-order/outcome data exist for the same project at the
same commit, so Module 4's `RankF_O` corpus (Step 15) can draw directly on
`findings/reports/idflakies/` rather than needing fresh runs for the core
result.

**`apache/dubbo` known-answer pair confirmed available.** The dataset
contains the paper's own Figure 1/2 worked example at SHA
`737f7a7ea67832d7f17517326fb2491d0a086dd7`, module `dubbo-rpc/dubbo-rpc-dubbo`:
brittle `DubboProtocolTest.testDubboProtocolWithMina` with state-setter
`RpcFilterTest.testRpcFilter` (one of 3 recorded candidate polluters for that
brittle; the other two are `testDubboProtocol` and
`testDubboProtocolMultiService` from the same class - plausible same-class
false-candidates, useful for testing whether `RankF_O` can tell a same-class
"pass-by-side-effect-of-running" candidate from the true cross-class
state-setter). 10 unique dubbo OD tests total in the dataset. This module
differs from FlakeSync's dubbo modules (`dubbo-config-api` etc., M7–M11) - no direct module overlap, but the project overlap itself is relevant to
Module 8 Step 30.

Use `dubbo` as Step 16's known-answer validation before trusting any
`RankF_O` number on `marine-api`.

**2026-09-23 - attempted, then deliberately stopped.** Shallow-cloned
`apache/dubbo` at `737f7a7` to run this validation; stopped and deleted the
clone before any Maven build ran, on the user's report that running this on
this machine hangs it - not worth the resource cost for a sanity check on a
result already cross-checked multiple other ways in Module 8. No `[STALENESS]`
or `[RESOURCE-GAP]` claim is made here since the clone never got far enough
to demonstrate an actual limit; this is a `[NULL]` - a known-answer check
this reproduction chose not to run, not one that failed. **The Module 4
`marine-api` ranking therefore still rests on the hand-verified ground truth
(Module 3) alone, without an independent known-answer confirmation.**

---

## Paper's claims, before measurement

Transcribed 2026-09-22, before running anything in Modules 2–7, so later
numbers cannot be read as confirmation of numbers already half-remembered.

**Vocabulary (Step 6):**

| Term | Meaning |
| --- | --- |
| Victim | An OD test that passes alone but fails when some other test runs before it |
| Polluter | The test that, run before a victim, makes it fail |
| Cleaner | A test that, run between a polluter and its victim, resets state so the victim passes again |
| Brittle | An OD test that fails alone and only passes when some other test runs before it |
| State-setter | The test that, run before a brittle, sets up the state it needs |

Pairings: victim ↔ polluter ↔ cleaner; brittle ↔ state-setter (no cleaner for
a brittle). Maps to IDoFT: `OD-Vic` = victim, `OD-Brit` = brittle, plain `OD`
= unspecified (the crux of Module 8).

**The subject funnel (Section IV-A):**

| Stage | Count | Stated reason for the drop |
| --- | --- | --- |
| OD tests in the Wei et al. dataset | 249, from 44 modules across 25 projects | starting point |
| Reproducible with Maven Surefire | 155, from 34 modules across 24 projects | "some OD tests in the dataset could not be reproduced" - 94 lost, 37.8% |
| Tests in those 34 modules, excluding Maven-skipped | 16,166 | - |
| Test-method bodies parseable by srcML | 13,219 | 2,947 excluded (18.2%) - inherit code from parent test classes outside the module |

**The efficiency result (RQ1):** median time to find the first OD-relevant
test - RankF 9.4–14.1 s, best baseline 34.2–118.5 s. For state-setters
specifically (Table III medians): `RankF_L` 59.5 s, `RankF_O` 13.3 s,
`OBO_avg` 489.5 s, delta-debugging 118.5 s.

**The configuration admission (RQ2):** `RankF_O` evaluated with 20
test-orders. Stable Rank-1 needs, on average, 206.0 (polluters), 86.2
(state-setters), 171.5 (cleaners) orders. Ties never needed at 20 orders;
ties disappear at 19.0 / 17.5 / 18.2 orders for the Distance, #Methods and
Plus One heuristics respectively.

**The best configurations (RQ3):** `RankF_L` → negative class strategy.
`RankF_O` → combined class strategy, Plus One heuristic.

**The metric footnote (Section VI), MAP for ranking polluters:**
`RankF_L` 0.007, `RankF_O` 0.251, `OBO_avg` 0.000 - `RankF_L` (the GPU-dependent
half) scores 36× worse than the GPU-free `RankF_O` on this metric, a
comparison the paper never draws explicitly.

---

## `RankF_O` algorithm, restated in own words (Module 4, Step 14)

For each test-order in the corpus, look at whether the OD test passed or failed
*in that specific order*, then look at every test that ran *before* it in that
same order. A failing order casts a "this might be the cause" vote (positive
score) for each test before it; a passing order casts a "probably not the
cause" vote (negative score) for each test before it. A test that shows up
before the OD test again and again in the failing orders, and rarely or never
in the passing ones, accumulates a high positive score and a low negative
score - that's the signal the ranking is built on. The five heuristics differ
only in how big each vote is (flat +1, weighted by method count, weighted by
proximity to the OD test, or one of the two "score by one thing, break ties by
another" combinations); the three strategies differ only in which of
(positive, negative, positive−negative) gets sorted and in which direction.
Matches the earlier restatement - no disagreement with the paper found here.

## Module 4 corpus - reused vs. self-generated (Step 15)

**Source 1 (reuse the earlier iDFlakies output) is a documented null.** The
plan expected `findings/reports/idflakies/` and
`flaky-study/marine-api/.dtfixingtools/{detection-results,test-runs/output}`
to hold the per-round order-plus-outcome data behind the earlier 12/12 match
against IDoFT. Checked directly - both directories exist but are **empty** on
this Windows clone. The reason, cross-referenced against
`idflakies_findings.md`: the run that actually found the 12 flaky tests
(`marine-api-oldsha-run1.log`, 5 rounds) executed inside a **WSL-side** clone
(`~/flaky-study/marine-api-oldsha`), and the fuller 7-detector confirmation ran
inside a **Docker container** - neither location's `detection-results/` was
ever copied out to the Windows-visible `findings/` tree. The Windows-side
`iDFlakies` run against the same SHA crashed before producing results (the
already-documented `TempFiles.withTempFile` Windows/POSIX bug). Net effect:
there is no surviving per-round order file to reuse - Module 4 falls back to
Source 2 (self-generated corpus) for its entire corpus, not just the Module 6
sensitivity sweep the plan anticipated needing fresh generation for.
**Log:** n/a - confirmed by directory listing, cross-referenced against
`findings/idflakies_findings.md` lines 196–356.

### 2026-09-23 - Class-level random ordering can never reproduce a same-class polluter/cleaner pair `[UNEXPECTED]` `[LIMITATION]`
**Subject:** `marine-api` @ `af0003847db9ba822f67d4f1dceb8de3fe63250a`, corpus
generation for `AbstractAISMessageListenerTest.testBasicListenerWithUnexpectedMessage`
(Module 4, Step 15)
**Command:**
```
findings/reports/rankf/gen_corpus.py --project ... --seeds 1-20 \
  --od-class net.sf.marineapi.ais.event.AbstractAISMessageListenerTest \
  --od-method testBasicListenerWithUnexpectedMessage --out corpus-20.csv
# internally: mvn -q test -Dsurefire.runOrder=random -Dsurefire.runOrder.random.seed=<seed>
```
**Observed:** 20 different random seeds, 20 genuinely different class-level
orders (confirmed distinct via `before_od` in `findings/reports/rankf/corpus-20.csv` - some runs had 1 class before the victim, others 64), **but the victim passed
in all 20 of 20**, even in orders where the polluter's class
(`SentenceFactoryTest`) ran before it. Root cause, cross-checked against
Module 3: the recorded cleaner (`testCreateCustomParser`) lives in the **same
class** as the recorded polluter (`testRegisterParserWithAlternativeBeginChar`).
Maven Surefire's `runOrder=random` shuffles **class** execution order only - it never reorders **methods within a class** (JUnit4's own default method
order, which Module 3 showed puts the polluter method before the cleaner
method by default, applies unchanged every time). So whenever
`SentenceFactoryTest` runs as a whole class, the polluter always runs
immediately followed by its own cleaner, before the victim ever gets a chance
to observe the polluted state - the class self-cleans on every single run,
by construction, regardless of where the class falls in the suite order.
**Gap:** This is a real limitation of using vanilla Surefire `runOrder=random`
to build a `RankF_O` corpus: **it cannot generate a single failing order for
any OD test whose recorded polluter and cleaner share a class** - exactly the
case for every row of this victim in the Wei dataset (all of its recorded
cleaners are `SentenceFactoryTest` methods too). iDFlakies' own
`random-class-method` detector name implies it shuffles at *both* granularities
for exactly this reason; plain Surefire's `random` only does the first half.
Confirms and generalizes the `-Dtest`-ordering trap already logged for `unix4j`
and Module 3's `marine-api` pair-run - the pattern now has three independent
confirmations, all rooted in Surefire's coarse-grained sense of "order."
**Fix attempted, and what it actually revealed:** rebuilt the corpus generator
to explode `SentenceFactoryTest` into its 16 individual `Class#method`
selectors (mixed alongside 70 whole-class selectors). This did **not** fix the
problem - 90 further seeds (70 + a 5-seed and another 5-seed probe, all
recorded) produced **0 failing orders out of 90**. Checking *why*: the
intra-class method order inside `SentenceFactoryTest`'s own surefire report is
**byte-for-byte identical across every seed tried** (`testCreateParser`,
`testRegisterParserWithAlternativeBeginChar`, `testListParsers`, ... - same
16-method sequence at seeds 1, 5, 10, 101–105, 201–205, and all of 1–70).
**This is not bad luck at a ~1/16 rate - it is deterministic.**
`-Dsurefire.runOrder`/`.random.seed` governs the order of *classes* (or of
`Class#method` selectors that resolve to *different* classes); it has no
effect on the order JUnit4 invokes multiple selected methods **within the
same class**, which follows JUnit4's own default `MethodSorters` (a fixed
hash of method names, unrelated to Surefire's seed). The polluter method is
therefore permanently fixed at position 2 of 16 inside its class's execution
block, for every random-order corpus Surefire can generate this way - the
cleaner-equivalent methods after it always run before the block ends, no
matter how many seeds are tried. **Conclusion: for any OD pair whose polluter
and cleaner share a class, vanilla Surefire `runOrder=random` cannot generate
a single failing test-order, ever** - not a probability, a hard architectural
ceiling. Checked the Wei dataset for marine-api's other 11 confirmed OD
tests: every one of them has its polluter *and* every recorded cleaner in
`SentenceFactoryTest` too, so this ceiling applies to the entire subject, not
just this one victim.
**Consequence for Module 4:** the corpus actually scored in Step 16/17 mixes
90 auto-generated whole-suite random orders (all genuine, all passing) with
two hand-crafted orders carried over from Module 3's Step 12 (the "alone" run
and the pinned polluter→victim run) to supply the one known-failing example a
corpus needs to be scoreable at all. This is disclosed explicitly in the
corpus's own provenance column rather than presented as a normal random
sample.
**Log:** findings/logs/rankf/gen-corpus-20.log, gen-corpus-70.log,
findings/reports/rankf/corpus-20.csv, corpus-70.csv, corpus-test5.csv,
corpus-test5b.csv (all all-pass, kept as evidence rather than deleted)

---

## Module 4 - `RankF_O` result (Steps 16–17)

**Corpus:** `findings/reports/rankf/final-corpus.csv` - 92 orders: 90
auto-generated random whole-suite orders (all passing, real class-level
variation) plus the two hand-verified orders from Module 3 Step 12 (alone:
pass; polluter-then-victim: fail). **91 pass / 1 fail** - see the entry above
for why a balanced corpus wasn't obtainable here. Candidate granularity is
test **class** (71 candidates, `AbstractAISMessageListenerTest` itself
excluded), not method - see `rankfo.py`'s own docstring for why.

**Implementation:** `findings/reports/rankf/rankfo.py`, matching the Step 14
restatement - five heuristics × three strategies, run against the corpus with
`findings/reports/rankf/ranked/ranked-<heuristic>-<strategy>.csv` as output.

**Known-answer check (Step 16 Verify):** true answer = `SentenceFactoryTest`
(the class holding both the recorded polluter and every recorded cleaner for
this victim, per Module 2 Step 9/Module 3).

| Heuristic | Positive rank | Negative rank | Combined rank |
| --- | --- | --- | --- |
| Plus One | **1** | 57 | 51 |
| #Methods | **1** | 55 | 53 |
| Distance | **1** | 37 | 18 |
| Combined (+1, D) | **1** | 53 | 50 |
| Combined (#M, D) | **1** | 55 | 53 |

**Observed:** the **positive-class strategy ranks the true polluter at rank 1
under all five heuristics** - trivially so, since `SentenceFactoryTest` is the
*only* candidate with a nonzero positive score (it's the only test that
appears in the corpus's single failing order). The **negative-class and
combined-class strategies - including the paper's own stated best
configuration for `RankF_O`, Plus One + combined class - rank it 18th to 57th
out of ~70**, because `SentenceFactoryTest` also shows up in a large fraction
of the 90 passing orders (it's a big class that runs often), accumulating a
negative score large enough to bury the one real signal.
**Gap - read carefully before treating this as a paper disagreement:** this
is very likely an artifact of the corpus's 91:1 pass/fail imbalance, which is
itself a direct downstream consequence of the same-class self-cancellation
limit above, not a fair like-for-like test of the paper's evaluated
configuration (the paper's own corpora, built from `sequentially-generated
+random-class-method` iDFlakies runs the authors don't disclose in this level
of pass/fail-ratio detail, are presumably far more balanced). Logged as
`[CONFIG-DEPENDENT]` rather than `[DISAGREEMENT]` for that reason: it
demonstrates that `RankF_O`'s recommended strategy is sensitive to a corpus
property (fail/pass balance) the paper's RQ2 configuration discussion never
addresses, which is a genuine, reportable gap in the paper's own robustness
story - but it does not show the paper's claimed strategy is wrong in
general, only that it degrades under a corpus imbalance this reproduction was
forced into by a subject-specific limitation.
**Log:** findings/logs/rankf/rankfo-run.log (n/a, ran instantly - output is
the 15 CSVs under `findings/reports/rankf/ranked/`)

---

## Module 5 - Baselines (Step 18: OBO)

**Per-pair Maven cost, measured directly:** 9 real `mvn -q test
"-Dtest=<CandidateClass>,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage"`
invocations (8 different candidate classes plus a repeat), each one an actual
OBO-style single-candidate pairing. Wall-clock: **7.4s–49.1s, median 8.6s,
mean 15.6s** (one 49.1s outlier, likely background contention on this
machine, not a Maven/JVM property - median is the more representative
figure). This lines up with the earlier warning and the paper's own
"Surefire overhead time" caveat: **the great majority of every OBO step is
Maven/JVM startup, not test execution** - the actual test bodies run in
milliseconds (see any `surefire-reports/*.txt` `Time elapsed`).
**Log:** findings/logs/rankf/obo-single-pair-timing.log

**Whether OBO can succeed here at all, checked directly rather than assumed:**
paired the *whole* `SentenceFactoryTest` class (not just the recorded
polluter method) against the victim, in isolation - the natural granularity
OBO would use if walking a real Surefire-generated test-order one **class** at
a time, same as `RankF_O`'s corpus in Module 4.
```
mvn -q test "-Dtest=SentenceFactoryTest,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage" "-Dsurefire.runOrder=reversealphabetical"
```
**Observed:** passes (`Tests run: 1, Failures: 0`) - confirmed the victim does
not fail even when its one true polluter class is the *only* other class in
the run. This is the same self-cancellation as Module 4, now shown to be a
property of the **class**, not an artifact of full-suite shuffling: whenever
`SentenceFactoryTest` runs as a whole (any context, any position), its own
later methods reset the registry state before control ever passes to another
class.
**Gap - a genuine finding about the OBO baseline itself, not about our
reproduction:** **OBO walking at class granularity can never find this
subject's true culprit, for the identical structural reason `RankF_O`'s
class-granularity corpus could never contain a failing order.** The paper
describes OBO as testing "each candidate test" one by one - if a real
implementation (like iFixFlakies, or the paper's own) operates at whole-class
granularity rather than isolating individual methods, it would **silently
report no culprit found** for this exact ground-truth pair, a false negative
neither this reproduction nor (as far as could be checked) the paper's own
text addresses. Only method-level isolation - exactly what Module 3's Step 12
Run B already did by hand (`-Dtest=SentenceFactoryTest#testRegisterParserWithAlternativeBeginChar,...`) - finds it, in the minimum possible one step, because that hand-picked pairing
already *is* the one-candidate OBO comparison that succeeds.
**OBO_avg estimate:** since the true culprit is a single specific method
requiring individual-method-level candidate selection to isolate (never a
whole-class pairing), and Module 4 already established Surefire cannot
generate a corpus of "failing test-orders" for this ground truth to seed 10
independent OBO walks from (the paper's own methodology, Section IV-B),
`OBO_avg` cannot be measured the way the paper defines it here - recorded as
`[RESOURCE-GAP]` rather than guessed at. What **is** measurable and reported
above is the real per-pair Maven cost, which is the dominant term in whatever
`OBO_avg` would be: at the paper's own baseline of "34.2 to 118.5s" for the
best baseline median, our median single-pair cost of 8.6s implies the paper's
own OBO runs needed on the order of **4–14 sequential pair-invocations** per
victim/brittle to reach that median - consistent with OBO being a genuinely
expensive linear search, the exact comparison RankF's efficiency claim rests
on.
**Log:** findings/logs/rankf/obo-wholeclass-pair.log, obo-single-pair-timing.log

---

## Module 5 - Baselines (Step 19: delta-debugging)

**iFixFlakies built cleanly on JDK 8** - `mvn -q clean install -DskipTests`
produced `target/ifixflakies-1.0.0-SNAPSHOT.jar` and installed it to the local
`.m2` repo, no output because of `-q` (confirmed via the jar's presence, not
assumed from a silent exit code). **No JDK 16+ reflection crash this time**,
unlike iDFlakies' first attempt - but that's because JDK 8 was used
pre-emptively from the start here, having already learned that trap from the
`idflakies_findings.md` history; not a contradiction of the earlier prediction,
just this reproduction skipping straight past it.
**Gap - chose not to wire up the real plugin, and why:** `MinimizerPlugin`
(iFixFlakies' actual delta-debugging entry point) requires a `flaky-list.json`
file whose schema is defined by a separate, undocumented dependency
(`testrunner-maven-plugin`, a different repo not vendored here) plus a pom.xml
modification via `pom-modify/modify-project.sh`. Neither the README nor the
repo itself documents the JSON schema, and chasing it through the
`testrunner` project's own source was judged not worth the time for one
baseline number. **Used the pre-agreed, explicitly sanctioned fallback
instead:** "Implement the split-and-recurse loop yourself... simpler than it
sounds - the algorithm is five lines." Implementation:
`findings/reports/rankf/dd.py` - genuinely five lines of actual logic (split
candidates in half, test the first half + OD test, recurse into whichever
half fails, stop at one element), calling real `mvn` invocations, not
simulated.
**Starting point, verified before delta-debugging it:** delta-debugging needs
a real *failing* test-order to recurse from, which Module 4's corpus could
never produce (see above) - so one was hand-constructed: 7 classes known to be
unrelated to the AIS sentence-parser registry, plus the real polluter method
last, confirmed to still fail exactly like Module 3's minimal case:
```
mvn -q test "-Dtest=WPLTest,VLWTest,SentenceFactoryTest#testRegisterParserWithAlternativeBeginChar,RTETest,MTATest,HDTTest,GSATest,DPTTest,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage" "-Dsurefire.runOrder=reversealphabetical"
```
→ fails with the same `UnsupportedSentenceException: Parser for type 'VDM' not found`, execution order confirmed via surefire XML timestamps:
`WPLTest, VLWTest, SentenceFactoryTest, RTETest, MTATest, HDTTest, GSATest, DPTTest`, victim last.
**Delta-debugging run, real invocations:**
| Step | Candidates tested | Outcome | Wall-clock |
| --- | --- | --- | --- |
| 1 | `[WPLTest, VLWTest, SentenceFactoryTest#..., RTETest]` (first half of 8) | FAIL | 14.5s |
| 2 | `[WPLTest, VLWTest]` (first half of 4) | pass | 12.6s |
| 3 | `[SentenceFactoryTest#..., RTETest]` (second half of 4) | FAIL | 11.3s |
| 4 | `[SentenceFactoryTest#...]` (first half of 2) | FAIL | 12.2s |
**Converged to the correct single culprit in 4 Maven invocations, 50.6s
total** (mean 12.65s/invocation - consistent with Step 18's measured per-pair
cost, confirming the dominant cost really is JVM/Maven startup, not test
execution, for both baselines). This matches the theoretical minimum: `⌈log₂
8⌉ = 3` levels of recursion, realized here in 4 real invocations (one "wasted"
test on the first, passing half at level 2) - a textbook, correctly-behaving
delta-debug run, and unlike Step 18's OBO, this one **worked without needing
to construct an artificial corpus first**, because delta-debugging only ever
needs *one* real failing order to start from, not ten.
**Comparison to OBO (Step 18) on the same starting prefix:** OBO would walk
this same 8-element prefix one at a time; at worst it inspects all 8 before
finding the culprit (last position), giving up to 8 Maven invocations, versus
delta-debugging's 4 here (`⌈log₂ n⌉`-ish scaling vs. `n` scaling) - reproducing, on a genuinely tiny scale, the qualitative reason the paper
prefers delta-debugging over plain one-by-one search as its stronger
baseline.
**Log:** findings/logs/rankf/ifixflakies-clone.log, ifixflakies-build.log,
dd-verify-8prefix.log, dd-run.log

---

### 2026-09-23 - Step 20: the comparison table

| Approach | Tests run before first hit | Wall-clock (total) | Wall-clock (minus JVM startup ~8.6s median) | Paper's median (state-setters) |
| --- | --- | --- | --- | --- |
| `RankF_O` (positive-class, any heuristic) | n/a - ranks from a pre-built corpus, no incremental Maven runs at search time | instant once the corpus exists (corpus itself cost 92 Maven runs, ~15–20 min) | instant | 13.3 s |
| `RankF_L` | *Module 7* | - | - | 59.5 s |
| `OBO` | not measurable end-to-end here (class-granularity walk never converges - see Step 18); per-pair cost only | median 8.6s **per candidate tested** | ~0s/candidate | 489.5 s |
| Delta-debugging (own implementation) | 4 invocations to converge on an 8-candidate failing prefix | 50.6s | ~50.6 − 4×8.6 ≈ 16.2s | 118.5 s |

**Compared as shapes, not absolutes, as a matter of standard practice:** the
paper's own ordering - `RankF` fastest, delta-debugging next, OBO slowest - is
**not fully reproduced here**, but not because the ordering is wrong: `RankF_O`
"wins" trivially in this table because its cost was paid up front building the
92-order corpus (not shown as a per-search cost the way the paper frames its
number), and `OBO`'s number is genuinely unmeasurable end-to-end for this
subject rather than merely slow - both are consequences of the same
class/method-granularity limitation documented throughout Modules 4–5, not
evidence against the paper's relative-speed claim. The one clean,
apples-to-apples number obtained - **delta-debugging's 4 invocations / 50.6s
to find a single known culprit in an 8-candidate prefix** - is consistent in
shape with the paper's claim that delta-debugging beats OBO's linear search;
it just could not be raced directly against OBO here because OBO could not
finish at all at the granularity available.
**Log:** synthesized from the Step 18/19 entries above; no new commands run.

---

## Module 6 - Sensitivity to test-order count (Steps 21–22)

**Method:** swept **prefixes of one shuffled
corpus**, repeated across **3 independent shuffles**, rather than drawing
fresh random samples per point (which would mix "more data" with "different
data"). Corpus is the same 92-order `final-corpus.csv` from Module 4 (91
pass, 1 fail). `findings/reports/rankf/sweep.py`, Plus One heuristic, all
three strategies, sizes 5/10/20/30/50/75/92 (92 replaces the originally targeted 100 - that's the whole corpus, since generating more would hit the same
self-cancellation ceiling documented in Module 4).

**Positive-class strategy - rank of `SentenceFactoryTest`, by shuffle and corpus size:**

| Orders | Shuffle 0 | Shuffle 1 | Shuffle 2 |
| --- | --- | --- | --- |
| 5 | 49 (not found) | 49 | 49 |
| 10 | 49 | 49 | 49 |
| **20** | **49** | **49** | **49** |
| 30 | **1** | 49 | 49 |
| 50 | 1 | **1** | **1** |
| 75 | 1 | 1 | 1 |
| 92 | 1 | 1 | 1 |

("49" = tied last among the 70 zero-positive-score candidates, alphabetically
sorted - i.e., not found at all; `AbstractAISMessageListenerTest` excluded
from the 71-candidate pool.)

**Observed - matches the anticipated "interesting outcome #1" exactly:**
the corpus contains exactly one failing order (from Module 3's hand-verified
run), so under the positive-class strategy, rank is either "not found" or "1"
depending purely on whether that single order has been drawn into the prefix
yet - a step function, not a curve. **At the paper's own evaluated
configuration of 20 orders, all three independent shuffles fail to find the
true polluter at all** (rank 49/71, tied-last) - 0 out of 3. The transition
happens at 30 orders in one shuffle and not until 50 in the other two - pure
variance from where one random draw happened to land, not signal. Given the
corpus has 1 relevant order in 92, the expected fraction present in a
20-order prefix is `20/92 ≈ 21.7%` per order, so missing it in a single
20-draw sample is unsurprising on its own (~78% chance); **missing it in all
three independent tries is the more telling number** - under this reproduction's
own (admittedly degenerate, 91:1-imbalanced) corpus, 20 orders is not a safe
default, it is closer to a coin that usually lands wrong.
**Negative and combined strategies never reach rank 1 at any corpus size
tried** (observed range 4–68, no visible trend toward convergence even at 92
orders) - consistent with the Module 4 finding that these strategies are
structurally hurt by this corpus's imbalance regardless of how much of it is
used.
**Honest caveat on generalizability:** this curve's shape (a step function at
"whichever order the one useful order lands") is a direct artifact of having
exactly one informative order in a heavily auto-generated corpus - it is not
the same experiment as the paper's own sweep (which presumably has many
naturally-occurring failing orders per OD test from a properly diverse
iDFlakies-style corpus). What *is* comparable is the qualitative point: **the
paper's own admission that 20 orders is far short of what stable Rank-1 needs
(206/86.2/171.5) is corroborated here, independently, on a different subject,
by a different mechanism** - logged as `[CONFIG-DEPENDENT]`.
**Log:** findings/logs/rankf/sensitivity-sweep.log, sweep output above

### Step 22 - cost of reaching a stable ranking, on this machine

**Measured full-suite runtime on this subject:** 12.9s (`mvn -q test`, timed
directly - dominated by Maven/JVM startup, same pattern as every other timing
in this study).

| Orders | Cost on this machine | vs. delta-debugging's 50.6s (Module 5) |
| --- | --- | --- |
| 20 (paper's evaluated config) | 20 × 12.9s = **4.3 min** | 5.1× slower |
| 86.2 (state-setter stability) | **18.5 min** | 22× slower |
| 171.5 (cleaner stability) | **36.9 min** | 44× slower |
| 206.0 (polluter stability) | **44.3 min** | 52× slower |

**Gap - the decision the paper leaves on the table, worked out:** at the
paper's own *evaluated* 20-order configuration, `RankF_O`'s corpus-building
cost (4.3 min) already exceeds delta-debugging's real measured cost here
(50.6s) by 5×, before even reaching the 86–206 orders the paper says are
actually needed for a *stable* answer - at which point the gap widens to
22–52×. **This directly contradicts the framing of `RankF_O` as the cheap,
GPU-free alternative to delta-debugging**, at least for a single OD test on
this subject.
**The one honest mitigating factor, stated for balance:** a test-order corpus
is a **shared, reusable asset** - once 206 random orders have been run and
recorded, they can score *every* OD test in the project, not just one,
whereas delta-debugging restarts from scratch per OD test. For a project with
many OD tests to diagnose (this reproduction only had one usable victim), the
amortized cost could favor `RankF_O` again. The paper does not make this
amortization argument either - it is left implicit - but it is the strongest
honest counter to the finding above, and belongs in the same paragraph as the
finding, not omitted.
**Log:** findings/logs/rankf/suite-runtime-timed.log

---

## Module 8 - Cross-check and write-up (Steps 28–30)

### Step 28 - Do iDFlakies and RankF actually compose?

**What the earlier work already established** (`idflakies_findings.md`, "The
classification gap, quantified"): iDFlakies detected all 12 of `marine-api`'s
confirmed OD tests, but every single one - 12/12, 100% - carries only the
generic `"OD"` type in `flaky-lists.json`, never `OD-Vic` or `OD-Brit`.
RankF's own algorithm (Section III-B, restated in Module 4 Step 14) branches
on exactly that distinction: a victim ranks against *failing* orders looking
for a polluter, a brittle ranks against *passing* orders looking for a
state-setter. **iDFlakies' raw output alone does not contain the one bit of
information `RankF_O` needs to know which branch to take.** The only place
that distinction exists in this whole toolchain is IDoFT's own labels - a
third, separate artifact neither tool produces.
**Concrete demonstration, not just an inference:** ran `RankF_O`
(`rankfo.py`, now with `--kind victim|brittle`) on the *identical* 92-order
corpus twice - once correctly assuming victim, once incorrectly assuming
brittle (i.e., flipping which orders count as positive evidence):
```
python rankfo.py --corpus final-corpus.csv ... --kind victim   # correct
python rankfo.py --corpus final-corpus.csv ... --kind brittle  # wrong guess
```
| Assumption | Rank of true polluter (`SentenceFactoryTest`, positive/plusone) | Rank-1 candidate instead |
| --- | --- | --- |
| victim (correct) | **1** | - |
| brittle (wrong guess) | **17** | `TTMTest` (a completely unrelated class) |
**Gap:** a wrong victim/brittle guess doesn't just degrade the ranking, it
**replaces the entire top of the list with noise** - the wrong assumption's
rank-1–5 candidates (`TTMTest`, `PositionProviderTest`,
`AISMessageParserTest`, `DTMTest`, `GSVTest`) have no relationship to the
real polluter at all; they're simply whichever classes happen to run often in
passing orders, which is meaningless once "passing" is (wrongly) treated as
the informative signal. **This is a concrete, reproducible
`[DISAGREEMENT]`/`[LIMITATION]` between two tools from the same research
group**: RankF's own paper names iDFlakies as its expected upstream source of
test-orders ("we choose 20 orders to match the number suggested by
iDFlakies"), but iDFlakies' actual output cannot supply the one label RankF
needs to run correctly - a user has to consult IDoFT by hand, for every OD
test, before the pipeline the two papers imply actually works.
**Log:** findings/reports/rankf/ranked-assume-victim/, ranked-assume-brittle/

### Step 29 - RankF against IDoFT's labels

| Test (marine-api) | IDoFT category | iDFlakies said | `RankF_O` rank-1 candidate | True OD-relevant test | Agree? |
| --- | --- | --- | --- | --- | --- |
| `AbstractAISMessageListenerTest.testBasicListenerWithUnexpectedMessage` | `OD-Vic` (victim) | generic `OD` (no sub-label) | `SentenceFactoryTest` (positive-class strategy, any heuristic) | `SentenceFactoryTest.testRegisterParserWithAlternativeBeginChar` | **Yes, at class granularity** - the true polluter's class ranks #1. Candidate granularity could not go to method level for the reasons documented in Module 4, so this is class-level agreement, not method-level |

Only one of the 12 confirmed `marine-api` OD tests was carried all the way
through to a scored ranking (Modules 3–6's chosen subject); the other 11 share
the same `SentenceFactoryTest` polluter/cleaner structure (Module 4's
availability entry), so scoring them individually would be expected to
produce the same class-level answer, not new information - not repeated here
for that reason. **No case of "RankF ranks a candidate #1 that turns out to
be a real, previously-unrecorded OD-relevant test"** was found - the single
scored case's rank-1 answer matches IDoFT/the hand-verified ground truth
exactly, so there is no candidate new IDoFT entry to report from this
reproduction.

### Step 30 - RankF against FlakeSync (dubbo overlap)

**Correction, made while writing this section:** an earlier draft of this
entry claimed no module-level overlap existed between the two datasets'
dubbo coverage. That was wrong, caught by checking
`planning/flakesync_explore.md`'s own Table 1 CSV directly instead of relying
on a paraphrase - **FlakeSync's M9 is `apache/dubbo`, module
`dubbo-rpc/dubbo-rpc-dubbo` (nested path confirmed in
`flakesync_findings.md`), at SHA `737f7a7...`** - the exact same repo, module,
and commit as RankF's Wei-dataset dubbo entry (Module 2, Step 9) and its own
Figure 1/2 worked example. Real overlap exists; corrected below.

**What overlaps, checked precisely:** the Wei/RankF dataset records exactly
**one** OD test from this module - `DubboProtocolTest.testDubboProtocolWithMina`
(brittle) - with `testRpcFilter` as its state-setter and `testDubboProtocol`/
`testDubboProtocolMultiService` (same class) as other candidate polluters
(Module 2, Step 9). FlakeSync's own expected-results fixtures for this module
(`findings/reports/flakesync/expected_results/`) show it tested **the same
class**, `DubboProtocolTest`, but **different specific methods** - `testDemoProtocol`, `testNonSerializedParameter`, `testPerm`,
`testReturnNonSerialized` - as its async-flaky (NOD) targets.
**Gap:** **not** a direct same-test contradiction (the specific method names
don't collide), so this falls short of "one dataset mislabelled the exact
same test" - but it is a genuine, closer-than-expected near-miss: **both
techniques independently flagged the identical test class, in the identical
module, at the identical commit, as containing flaky behaviour, while
disagreeing on which specific methods in that class are the interesting
ones and by what mechanism** (order-dependence vs. asynchronous timing).
Neither paper cites the other or appears aware of this overlap. Worth a
follow-up this reproduction didn't have time for: running
`testDemoProtocol`/`testNonSerializedParameter`/`testPerm`/
`testReturnNonSerialized` under RankF's OD framing (are any of them
secretly order-dependent too, mislabelled as purely async by FlakeSync?) - recorded as an open question, not run.
**The higher-level point still holds, now with real (if partial) evidence
rather than a null result:** both plans independently arrived at the same
meta-finding from opposite directions - FlakeSync's Step 32 found 54% of a
sampled sample of IDoFT's NOD entries are not really async flaky; this plan's
Modules 2 and 3 found the Wei OD dataset's own counts don't match the
paper's published funnel, and that a `-Dtest`-order "non-reproduction" can be
an ordering-tool artifact rather than a real fix (the `unix4j` entry). Two
different research pipelines, converging on the same test class in the same
project, is a stronger version of the same underlying conclusion: **the
category labels these flaky-test techniques are evaluated against are less
reliable, and less mutually exclusive, than either evaluation assumes.**
**Log:** n/a - cross-referenced from `planning/flakesync_explore.md` (Table 1
CSV, line for M9), `findings/flakesync_findings.md` (nested-path
confirmation), `findings/reports/flakesync/expected_results/` (actual tested
method names), and `flaky-study/RankF/wei-dataset/` (Module 2 inventory); no
new commands run.

---

## [AVAILABILITY] - artifacts, datasets or links that are gone, moved, or gated

### 2026-09-22 - Fine-tuned BigBird models are gone; no permanent mirror exists `[AVAILABILITY]` `[RESOURCE-GAP]`
**Subject:** RankF artifact hub, Box link
**Paper says:** the hub links out to fine-tuned `RankF_L` models on Box
(`https://utexas.box.com/s/adfk1run5mcae984pbpd9p0b6b0vszt1`), intended as the
primary inference path for Module 7 since training needs a 48 GB GPU.
**Command:**
```
curl -s -L -D - -o box.html "https://utexas.box.com/s/adfk1run5mcae984pbpd9p0b6b0vszt1"
```
**Observed:** 301 redirect to `utexas.app.box.com`, then a genuine HTTP 404
from Box's own backend (real `box-request-id`/session cookies, not a cached
CDN error) - i.e. Box itself says the shared link no longer exists, not a
client-side JS-shell failure. Searched `github.com/UT-SE-Research` (13 repos)
for a mirror; none of them holds RankF code or model weights.
**Gap:** The paper's own stated mitigation for the 6 GB VRAM gap - "use the
published fine-tuned models for inference" - is unavailable. Module 7's
primary path collapses to the stretch-goal path (train from scratch on a
48 GB-designed model, on 6 GB), which was expected not to fit.
**Log:** findings/logs/rankf/link-status.log

### 2026-09-22 - Wei et al.'s "original dataset" link is dead; the Drive mirror works `[AVAILABILITY]` `[STALENESS]`
**Subject:** Ground-truth hub, `sites.google.com/view/tuscan-squares-probabilities`
**Paper says:** the ground-truth OD/OD-relevant test dataset (249 OD tests, 44
modules, 25 projects) is hosted at `cs.gmu.edu/~winglam/publications/2021/WeiETAL21TACAS.zip`.
**Command:**
```
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" -L \
  "https://cs.gmu.edu/~winglam/publications/2021/WeiETAL21TACAS.zip"
```
**Observed:** HTTP 200 but `Content-Type: text/html`; the body is GMU CS
department's Drupal-based homepage, not the zip. GMU appears to have retired
the old personal-faculty-page URL structure. The second link on the same
page - a Google Drive file (`id=13oGvRlGbg8upaK75q2VTZZwUsxWy4i2P`), labelled
"Dataset Confirmed with Maven Surefire" - downloaded successfully via plain
`curl` (no browser/cookie needed): 808,411 bytes, real CSV.
**Gap:** The paper's primary citation for its own ground truth is a dead link;
only the secondary, already-filtered "confirmed" version survives. This
secondary version has a different scope than the paper's headline numbers - see the STALENESS entry below.
**Log:** findings/logs/rankf/link-status.log

### 2026-09-22 - The anonymous code repo needed the raw API, not the browser URL `[AVAILABILITY]`
**Subject:** `anonymous.4open.science/r/RankF-DDED`
**Observed:** `WebFetch` on the browser URL returned only the page's JS-shell
header ("Anonymous Github") with no content - exactly the anticipated trap.
Hitting the underlying API directly (`/api/repo/RankF-DDED/file/README.md`,
`/api/repo/RankF-DDED/zip`) returned real content: full setup README and a
valid 11.8 MB zip (`PK` header confirmed).
**Gap:** None - repository is genuinely alive. Recorded because it demonstrates
the earlier warning was necessary and correct, not because anything is
missing.
**Log:** findings/logs/rankf/link-status.log

## [UNEXPECTED] - behaved differently from the paper or the docs

### 2026-09-22 - The Wei dataset's own column names collide with the established vocabulary `[UNEXPECTED]`
**Subject:** `flaky-study/RankF/wei-dataset/wei-od-dataset.csv`
**Command:**
```
python -c "csv.DictReader over the file; print sample brittle row, sample victim-with-cleaner row"
```
**Observed:** Columns are `gitURL, sha, module, victim, polluter, cleaner,
type`. For `type == brittle` rows, the OD test itself is still stored under
the column literally named `victim`, and the state-setter is stored under
the column literally named `polluter` - the file re-uses the victim/polluter
column pair for both pairings rather than having distinct `oc_test` /
`relevant_test` columns. `cleaner` is blank for every brittle row (521/521),
consistent with brittles having no cleaner. 1,635/2,352 rows have a
`cleaner` value; the rest (victim rows with only a polluter recorded) are
blank. `module` is blank on 715/2,352 rows (mostly single-module projects
where the repo root doubles as the module). `sha` is filled on every row
(2,352/2,352).
**Gap:** Not a defect in the dataset - but any script consuming this CSV
must branch on the `type` column before trusting what `victim`/`polluter`
mean, exactly the "confusing cleaner with state-setter" trap already
already warns about in Step 6/Trap #6. Recorded so Module 4's `rankfo.py`
reads `type` first and never assumes column-name = role.
**Log:** n/a - verified directly from the CSV, see Step 8/9 inventory below.

## [LIMITATION] - demonstrated boundaries of the technique

Entries under this tag ended up filed inline under their owning module
section rather than repeated here (this file drifted from strictly
category-first to module-first organization partway through - noted rather
than silently left inconsistent). Tagged entries: "Class-level random
ordering can never reproduce a same-class polluter/cleaner pair" and "Corpus
construction ceiling generalizes to the whole subject" (Module 4); "Class-
level random ordering... " and the OBO whole-class-pair result (Module 5,
Step 18); the iDFlakies/RankF label-dependency demonstration (Module 8, Step
28).

## [DISAGREEMENT] - contradictions between tools, datasets, or papers

See Module 4's `RankF_O` result (paper's own best configuration ranks the
true polluter 51st, not 1st, on this corpus - filed as `[CONFIG-DEPENDENT]`
rather than a clean disagreement, with the reasoning for that choice spelled
out there) and Module 8 Step 30 (the FlakeSync/RankF `DubboProtocolTest`
overlap - same class and commit, different specific methods, not a direct
same-test contradiction but close).

## [FALSE-POSITIVE] - claimed results that do not hold up

Nothing found under this tag. Every ranking and baseline result produced in
this reproduction (Modules 4–6) was checked against a hand-verified ground
truth before being trusted (Module 3's three-run demonstration), so no case
arose of this reproduction's own tooling claiming a result that didn't hold
up under scrutiny. This is different from the paper's own claims, several of
which *were* found not to hold up under this corpus's conditions - those are
filed as `[CONFIG-DEPENDENT]`/`[DISAGREEMENT]` instead, since the paper's
claim itself wasn't fabricated, just sensitive to a configuration this
reproduction was forced into.

## [FALSE-NEGATIVE] - real cases the tool missed

Nothing found under this tag, for the same reason `RankF_O` never had a
chance to miss a real case here: the only case scored (Module 4) it got
right (rank 1, positive-class strategy). The negative/combined strategies'
poor ranks are better described as scores swamped by corpus imbalance than
as the technique "missing" a case it could see - see Module 4's `[CONFIG-
DEPENDENT]` entry for that distinction.

## [CONFIG-DEPENDENT] - results that move with configuration

See Module 4 (positive-class strategy finds the answer, the paper's own
preferred combined-class strategy does not, on the same corpus) and Module 6
(rank at the paper's evaluated 20 orders is 0-for-3 across independent
shufflings; the paper's own admitted 86–206-order stability requirement
costs 22–52× delta-debugging's real measured time).

## [RESOURCE-GAP] - hardware or time beyond what is stated

See the Module 7 GPU gap noted at the top of this file (48 GB-designed model,
6 GB available, and the fine-tuned models needed to route around that gap are
gone - filed under AVAILABILITY, cross-tagged here) and Module 5 Step 18
(`OBO_avg` as the paper defines it - averaged over 10 failing/passing orders - could not be measured for the same corpus-generation reason Module 4
documents, filed as a resource/measurability gap rather than guessed at).

## [STALENESS] - benchmark entries that no longer reproduce

### 2026-09-22 - "Confirmed" Wei dataset has 197 OD tests / 39 modules, not the paper's 249 / 44 `[STALENESS]`
**Subject:** `flaky-study/RankF/wei-dataset/wei-od-dataset.csv` (the Google
Drive "Dataset Confirmed with Maven Surefire" file - the only surviving
download for the ground truth; see the AVAILABILITY entry above).
**Paper says:** Section IV-A - 249 OD tests, 44 modules, 25 projects as the
starting point before the paper's own Maven-reproduction filter drops it to
155 OD tests / 34 modules / 24 projects.
**Command:**
```
python -c "... csv.DictReader over wei-od-dataset.csv, dedupe by
  (gitURL, sha, module, victim/brittle test) ..."
```
**Observed:** 2,352 data rows (one row per victim–polluter–cleaner
combination), collapsing to 197 unique OD tests across 39 modules and 25
projects. Type split: 1,831 victim rows, 521 brittle rows (row-level, not
deduplicated to unique tests yet).
**Gap:** 197/39/25 matches neither the paper's starting point (249/44/25) nor
its post-reproduction figure (155/34/24). Projects match (25), but OD-test and
module counts sit between the two published numbers. The file's own label
("Dataset Confirmed with Maven Surefire") strongly suggests **this already is
the paper's post-reproduction cut**, not the raw starting set - but even under
that reading it doesn't match (155/34/24 expected vs 197/39/25 observed).
Two explanations remain open: (a) the file is a partially-filtered
intermediate that doesn't correspond to either published number, or (b) the
dataset was revised after publication and silently drifted. Either way,
**Step 10's planned reproduction sample cannot be compared directly against
the paper's stated 155-of-249 rate** without treating this file's own count
(197) as the new baseline, not 249.
**Answers to Step 8's four questions:**
1. Columns: `gitURL, sha, module, victim, polluter, cleaner, type` (7 named +
   one trailing blank column from a trailing comma in the source). The
   victim/brittle distinction is explicit via `type` (`victim` or `brittle`),
   but see the [UNEXPECTED] entry above - the `victim`/`polluter` column names
   are reused for both pairings rather than having role-neutral column names.
2. Gives **both**: `polluter` is filled on all 2,352 rows; `cleaner` is filled
   on 1,635/2,352 (only for `victim`-type rows that have a recorded cleaner - 0/521 brittle rows have one, as expected since brittles have no cleaner).
3. Yes - `sha` is filled on every row (2,352/2,352).
4. Row count is 2,352 (one row per victim/brittle × polluter/state-setter ×
   optional-cleaner combination), which collapses to 197 unique OD tests - **not** 249. See STALENESS gap above.
**Log:** findings/logs/rankf/link-status.log (initial discovery); analysis
via ad-hoc `python -c` commands, not yet scripted into a committed tool.

### 2026-09-23 - `marine-api` needs JDK 8 (`tools.jar` system dependency), fails outright on JDK 21 `[PLATFORM]`
**Subject:** `marine-api` @ `af0003847db9ba822f67d4f1dceb8de3fe63250a` (Module 3, Step 11/12)
**Command:**
```
mvn -q test "-Dtest=AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage"
```
**Observed:** With the system default JDK (21, active per the machine survey), the
build fails before any test runs: `Could not resolve dependencies for project
net.sf.marineapi:marineapi:bundle:0.11.0-SNAPSHOT - dependency: com.sun:tools:jar:0
(system) - Could not find artifact ... at specified path
...\.jdks\ms-21.0.7/../lib/tools.jar`. `tools.jar` was removed from the JDK in
Java 9. Switching `JAVA_HOME` to the Corretto 8 install
(`C:\Users\Tanzim\.jdks\corretto-1.8.0_412`) fixes it immediately - no source or
pom edit needed.
**Gap:** Not a RankF-specific finding, but a real reproducibility trap for anyone
running this reproduction on a modern JDK-default machine: the earlier iDFlakies module
must have picked up JDK 8 implicitly (WSL's system-wide JDK 8, per the machine
survey), which masked this. Every future `mvn` invocation against `marine-api` in
this reproduction needs `JAVA_HOME` pinned to JDK 8 explicitly on Windows/PowerShell - worth adding to the per-shell setup so it isn't rediscovered per module.
**Log:** findings/logs/rankf/gt-alone.log (first attempt, JDK 21, failing)

### 2026-09-23 - Ground truth for `marine-api`'s primary victim/polluter/cleaner triple fully reproduces `[NULL]`
**Subject:** `marine-api` @ `af0003847db9ba822f67d4f1dceb8de3fe63250a`, module root
(single-module project)
**OD test:** `net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testBasicListenerWithUnexpectedMessage`,
kind: victim. Polluter: `net.sf.marineapi.nmea.parser.SentenceFactoryTest.testRegisterParserWithAlternativeBeginChar`.
Cleaner: `net.sf.marineapi.nmea.parser.SentenceFactoryTest.testCreateCustomParser`.
**Paper says:** n/a - this is Module 3 Step 12, the documented ground-truth
demonstration before trusting anything from Module 4 onward.
**Command:**
```
# Run A
mvn -q test "-Dtest=AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage"
# Run B
mvn -q test "-Dtest=SentenceFactoryTest#testRegisterParserWithAlternativeBeginChar,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage" "-Dsurefire.runOrder=reversealphabetical"
# Run C
mvn -q test "-Dtest=SentenceFactoryTest#testRegisterParserWithAlternativeBeginChar+testCreateCustomParser,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage" "-Dsurefire.runOrder=reversealphabetical"
```
**Wall-clock:** each run well under a second (small suite).
**Observed:** Run A - passes alone (`Tests run: 1, Failures: 0, Errors: 0`).
Run B - fails: `net.sf.marineapi.nmea.parser.UnsupportedSentenceException: Parser
for type 'VDM' not found`, thrown from the victim's constructor, confirmed from
`AbstractAISMessageListenerTest`'s own surefire report plus XML write-order
(`SentenceFactoryTest`'s report timestamped before `AbstractAISMessageListenerTest`'s).
Run C - passes again once the cleaner runs between polluter and victim
(`<testcase>` order inside `SentenceFactoryTest`'s XML confirms
`testRegisterParserWithAlternativeBeginChar` executed before
`testCreateCustomParser`, i.e. polluter before cleaner as intended).
**Gap:** None - all three outcomes match the Step 12 expectations exactly.
Recorded as a `[NULL]` (deliberate positive result) because it establishes that
Modules 4–6 have a trustworthy, hand-verified ground truth to score against,
and because the mechanism of the pollution is now known precisely: the polluter
unregisters/changes the AIS sentence-type parser registry that the victim's
constructor depends on.
**Log:** findings/logs/rankf/gt-alone.log, gt-pair.log, gt-cleaner.log

### 2026-09-23 - `-Dtest` order is not just unreliable, it's alphabetical-by-package regardless of the list order given `[UNEXPECTED]`
**Subject:** `marine-api` @ `af0003847db9ba822f67d4f1dceb8de3fe63250a` (Module 3, Step 12, Run B first attempt)
**Command:**
```
mvn -q test "-Dtest=SentenceFactoryTest#testRegisterParserWithAlternativeBeginChar,AbstractAISMessageListenerTest#testBasicListenerWithUnexpectedMessage" "-Dsurefire.runOrder=filesystem"
```
**Observed:** Requested order was polluter (`nmea.parser.SentenceFactoryTest`)
then victim (`ais.event.AbstractAISMessageListenerTest`). Actual order, confirmed
from the surefire XML write-timestamps, was the reverse: the victim's report was
written first. Both tests passed - i.e. this run silently failed to demonstrate
the pollution, and looked like a clean (non-reproducing) result rather than an
ordering bug, until the timestamps were checked. Switching
`-Dsurefire.runOrder=reversealphabetical` fixed it, because `ais.*` sorts before
`nmea.*` alphabetically and `filesystem` here behaved identically to
`alphabetical` (not, as its name implies, actual on-disk file order) - `reversealphabetical` was the only setting that put the `nmea.*` class first for
this particular pair.
**Gap:** This is the same class of trap already logged for `unix4j` (see below),
now confirmed on a second, unrelated project. `-Dtest`'s comma-separated order is
purely a *selection* filter, never an execution-order guarantee - `runOrder`
governs the actual sequence, and `filesystem` is not literally filesystem order,
it tracks package/class alphabetical order in practice on this Maven/Surefire
version (3.6.0). Anyone reproducing a polluter→victim pair must check the
package names of the two classes first and pick `alphabetical` or
`reversealphabetical` accordingly - or, when polluter and victim share a class
(as with `unix4j`), fall back to a mechanism not yet available (see the
unix4j entry's open gap).
**Log:** findings/logs/rankf/gt-pair.log (first, ignored attempt's timestamps are
overwritten by the retry - see the surefire XML mtimes captured in the session
transcript; the committed log is the successful reversealphabetical retry)

### 2026-09-22 - Surefire's `-Dtest` order does not reliably honor the requested sequence, confirmed in practice `[UNEXPECTED]`
**Subject:** `tools4j/unix4j` @ `367da7d262e682a08577cdf19ebbbdd8a46870fe`, module
`unix4j-core/unix4j-command` (Step 10, reproduction sample entry 3/10)
**OD test:** `org.unix4j.unix.FindFileTimeDependentTest.find_fileCreatedBeforeNow`,
victim; recorded polluter `find_fileCreatedAfterTime` (same class)
**Paper says:** n/a - this is a documented trap (#10), verified
here rather than just taken on faith.
**Command:**
```
mvn -q -pl unix4j-core/unix4j-command -am test \
  "-Dtest=FindFileTimeDependentTest#find_fileCreatedAfterTime+find_fileCreatedBeforeNow" \
  "-Dsurefire.runOrder=filesystem"   # then repeated with runOrder=alphabetical
```
**Observed:** With `runOrder=filesystem`, the surefire XML shows execution
order `find_fileCreatedBeforeNow` then `find_fileCreatedAfterTime` - the
*reverse* of the `-Dtest` list, both passed. With `runOrder=alphabetical`,
the XML showed the **same** order (`BeforeNow` first) despite "After" <
"Before" alphabetically - and this time the second test
(`find_fileCreatedAfterTime`) failed, the first still passed. Two runs with
apparently the same actual order produced different outcomes, meaning the
failure here is not a clean order-triggered pollution but something more
timing-sensitive (test name is literally `FindFileTimeDependentTest`).
**Gap:** Neither `filesystem` nor `alphabetical` runOrder gave reliable
control over test sequence within a class - confirming the plan's stated
trap in practice, not just in principle. The pair could not be verified as a
clean polluter→victim relationship with vanilla Surefire flags alone; doing
so would need iDFlakies' own order-specification mechanism (already used
successfully elsewhere in this study) or a custom JUnit runner outside the
subject's source tree. Recorded as a methodology finding rather than spending
the reproduction-sample's time budget forcing exact order on every one of
the 10 sampled entries - see Step 10 summary for how this shaped the rest of
the sample.
**Log:** findings/logs/rankf/repro-01-unix4j-*.log

## [PLATFORM] - OS-specific breaks

See Module 3 ("`marine-api` needs JDK 8 (`tools.jar` system dependency), fails
outright on JDK 21") - every command in Modules 3–6 had to pin `JAVA_HOME` to
the Corretto 8 install for this reason.

## [NULL] - deliberate negative results

See Module 3 (the full hand-verified victim/polluter/cleaner demonstration - all three runs matched expectation exactly, a positive result recorded
deliberately as a `[NULL]`-style baseline before anything downstream could be
trusted) and Module 8 Step 30 (no module-level overlap in an earlier, since-
corrected draft - see the correction note there for why that draft claim was
wrong and what replaced it).

## [IMPROVEMENT] - concrete changes that would fix something observed

Nothing filed under this exact tag inline, but three concrete improvements
are written up in `findings/reports/rankf/rankf_report.md` under "Opportunities
to improve the technique": (1) `RankF_O`'s corpus-generation step should
detect/warn about the same-class polluter/cleaner case rather than silently
producing an unusable corpus; (2) a compatibility shim or documented step
between iDFlakies' output and RankF's victim/brittle input requirement, since
the two tools are named as a pipeline by RankF's own paper but don't actually
compose; (3) the paper's RQ2 order-count admission should be paired with its
real-minutes cost, the way Module 6 worked out here, rather than left as a
single disclosure sentence that reads as cheaper than it is.

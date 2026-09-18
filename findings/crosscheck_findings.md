# Cross-check — Findings log (Module 6)

> Formal comparisons across NonDex, iDFlakies, IDoFT, and TSVD4J — the
> section this research specifically targets ("disagreements between
> tools or datasets"). Read [comparative_report.md](comparative_report.md)
> for the earlier synthesis across Modules 2–4; this file adds the
> Module 6 same-project runs that made a real comparison possible.

---

## Step 21 — NonDex vs iDFlakies, same project

Before this module, NonDex and iDFlakies had never been run on the same
project. Filled that gap directly.

| Test | NonDex flagged? | iDFlakies flagged? | Notes |
| --- | --- | --- | --- |
| `marine-api` (current commit), all 926 tests | No — 0 hits, clean 3-run pass | No — 0 hits across 20 rounds | **Both tools agree: clean.** Neither `ID` nor `OD` issues on current code |
| `Java-WebSocket` (`aad6654`), all tests | **Could not complete** — crashed on its own baseline before any shuffling | 7 candidates in round 1 (5 pre-existing, 2 new); killed by timeout before completing all 3 rounds | **A real capability gap**, not a disagreement — see below |

**The one genuine finding here:** NonDex has no equivalent to iDFlakies'
`all_must_pass=false` flag. On a project with real pre-existing
flakiness, NonDex can't even establish a baseline and produces **no
result at all** — not a null result, a non-result. iDFlakies tolerates
the same flakiness and still produces partial, useful signal. This is a
concrete, reportable capability difference between the two tools.

---

## Step 22 — Both tools vs IDoFT's labels

| Test | IDoFT category | NonDex says | iDFlakies says | Agree? |
| --- | --- | --- | --- | --- |
| `marine-api` — all 12 `OD-Vic` tests (Module 2) | `OD-Vic` | Not tested against this specific commit | **12/12 exact match**, at IDoFT's exact recorded SHA (Module 4) | ✅ Full agreement |
| `marine-api` — same 12, current commit | (fix expected, PR #109 `Accepted`) | 0 hits, current commit | 0 hits, 20 rounds, current commit | ✅ Both confirm the fix holds |
| `Java-WebSocket` — `Issue598Test` (`NDOD;TD` in IDoFT) | `NDOD;TD` | Not directly tested (baseline crashed first) | Not in the 7 tests round 1 caught (process killed before rounds 2–3 could re-check) | Inconclusive — see gaps below |
| `Java-WebSocket` — `Issue677Test.testIssue` (`NDOD;OD-Vic;TD` in IDoFT) | `NDOD;OD-Vic;TD` | Not tested | Not in round 1's 7 tests | Inconclusive |

**The interesting cell:** `marine-api` is the one case with a complete
picture, and it's full agreement in both directions — a real success
story for cross-validation, not a gap.

---

## Step 23 — Both tools vs TSVD4J (`Java-WebSocket`, exact commit `aad6654`)

TSVD4J's own Stage D found **18 unique conflicting source-line pairs**
(source-code thread-safety violations, not test names — a different
format than NonDex/iDFlakies report). One TSVD4J pair location,
`Issue598Test|164`, is in a test class also flagged `NDOD;TD` by IDoFT —
a real independent overlap noted in Module 2, though neither NonDex nor
iDFlakies confirmed or denied it directly this round (see gaps below).

**NonDex result:** could not complete — crashed on `Issue825Test` and
`Issue1142Test` (both SSL/timeout-related) before any shuffling began.

**iDFlakies result (round 1 of 3, process killed by timeout before
completing):**

| Test flagged | Already failing in clean baseline? |
| --- | --- |
| `Issue997Test.test_localServer_ServerLocalhost_Client127_CheckInactive` | **Yes** — pre-existing |
| `Issue997Test.test_localServer_ServerLocalhost_ClientLocalhost_CheckActive` | **Yes** — pre-existing |
| `Issue997Test.test_localServer_ServerLocalhost_ClientLocalhost_CheckInactive` | **Yes** — pre-existing |
| `Issue825Test.testIssue` | **Yes** — pre-existing (15s timeout) |
| `Issue890Test.testWithSSLSession` | **Yes** — pre-existing (4s timeout) |
| `Issue1142Test.testWithSSLSession` | **No** — new candidate |
| `Issue764Test.testIssue` | **No** — new candidate |

**The false-positive count the plan's Step 23 explicitly asks for:
5 of iDFlakies' 7 round-1 hits (71%) are pre-existing environmental
flakiness, not genuine order-dependence.** Only 2 of 7 are real new
candidates — and both are `testWithSSLSession`-pattern tests, suggesting
a shared SSL/timing root cause across `Issue890Test` and `Issue1142Test`,
not necessarily true order-dependence either.

**The hang, confirmed:** the plan's own upstream note says Java-WebSocket
has a test that "hangs forever" under iDFlakies. This run hit exactly
that — round 2 took noticeably longer (204s cumulative vs. round 1's
75.6s), and the process never reached round 3 or a final summary,
requiring a hard kill after the full 10-minute safety timeout. This is
the first time in this whole study that a hang was directly reproduced
and timed, rather than just documented as a risk.

**Cross-referencing against TSVD4J:** none of iDFlakies' 7 flagged tests
match TSVD4J's 18 conflicting-pair classes (`WebSocketImpl`,
`WebSocketClient`, `Draft_6455`, `Issue598Test`, `Issue621Test`) by name.
**No overlap found in the data actually collected** — but the run never
completed all 3 rounds, so this is not a confident "no overlap exists,"
only "no overlap found in what round 1 caught before the hang."

---

## Step 24 — How stale is IDoFT? (10-entry random sample, seed 42)

| Project @ SHA | Result |
| --- | --- |
| `alibaba/alibabacloud-tairjedis-sdk` | ✅ Builds clean |
| `abel533/Mapper` | ✅ Builds clean |
| `rest-assured/rest-assured` | ❌ **Genuine build failure** — cascading `cannot find symbol` errors in `json-schema-validator` module, consistent with a dependency-resolution or JDK-version mismatch |
| `apolloconfig/apollo` | ⏱️ Timed out (180s budget) — large project, inconclusive |
| `swagger-api/swagger-core` | ⏱️ Timed out — inconclusive |
| `winder/Universal-G-Code-Sender` | ⏱️ Timed out — inconclusive |
| `apache/ignite-3` | ⏱️ Timed out — inconclusive |
| `apache/iotdb` | ⏱️ Clone itself timed out (90s) — inconclusive |
| `apache/pulsar` | ⏱️ Clone itself timed out — inconclusive |

**Honest result: 2 of 9 confirmed still building, 1 of 9 confirmed
genuinely broken, 6 of 9 inconclusive** — not because they're stale, but
because several sampled projects (Apache IoTDB, Pulsar, Ignite;
Apollo) are large, well-resourced codebases that legitimately need more
than the 90–180 second budget this quick check allowed. **This is a
methodology limitation of this specific check, not a finding about
IDoFT's staleness** — a fair staleness measurement would need per-project
budgets sized to project scale, not a flat timeout.

**What this small sample does support:** at least 1 of 9 (11%) sampled
IDoFT entries genuinely fails to build at its recorded commit today —
a real, if small, confirmed-stale data point, consistent with
FlakeSync's own admission (cited in `research_gaps.md`) that its subject
funnel decays hard for exactly these reasons (deleted tests, no-longer-
building projects). No claim beyond that 1-in-9 number is safe to make
from this sample size and timeout budget.

---

## Step 25 — Summary

**What I did:** ran NonDex and iDFlakies on the same projects for the
first time (`marine-api`, `Java-WebSocket`), compared both against
IDoFT's published labels and TSVD4J's earlier thread-safety findings,
and sampled 9 further IDoFT entries to check how many still build.

**What each tool found (this module's new runs):**

| Tool | Target | Result |
| --- | --- | --- |
| NonDex | `marine-api` | Clean — 0 hits |
| NonDex | `Java-WebSocket` | Could not complete — no tolerance for pre-existing failures |
| iDFlakies | `Java-WebSocket` | 7 candidates, 5 pre-existing, 2 new, hung and was killed before finishing |

**The disagreements section (this study's central research question):**

1. **NonDex vs. iDFlakies capability gap** — NonDex has no equivalent to
   `all_must_pass=false`; on a project with pre-existing flakiness it
   produces no result at all, where iDFlakies still produces partial
   signal.
2. **Docker's official 7-detector pipeline vs. our manual run**
   (Module 5) — found 9/12 of the same known-flaky `marine-api` tests,
   an exact subset, not a contradiction, but a real difference in
   detection power by strategy and round count.
3. **The false-success pattern**, now confirmed across **three
   independent tools** (TSVD4J, iDFlakies, NonDex's `debug` goal) —
   the strongest, most generalizable finding in the whole study.

**What I'd do next:** re-run the Step 24 staleness sample with
per-project timeouts sized to project scale, and re-run `Java-WebSocket`'s
iDFlakies test with the hanging test explicitly excluded (via
`detector.filter` or similar) to get a complete 3-round result instead of
a partial, killed one.

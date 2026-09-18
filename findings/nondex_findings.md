# NonDex — Findings log

> Findings from Module 3. Keep entries concise, dated, with the exact
> command that produced them. Old entries are never deleted.

---

## 2026-09-16 — Baseline build check (Module 3, Step 8)

**Target:** `delight-nashorn-sandbox` (primary target, 79 tests, JUnit 4.13.1)

**Command:**
```powershell
Measure-Command { mvn -q clean test } *> ..\..\findings\logs\nondex\baseline.log
```

**Result:** `BUILD SUCCESS` (`$LASTEXITCODE` = 0), no pre-existing test
failures (`surefire-reports` search for `FAILURE!` returned nothing).
Wall-clock baseline: **1 minute 43.65 seconds**. Despite the known risk
that Nashorn was removed from the JDK at 15+ and this project targets
source level 11, the build ran cleanly on the active JDK — no
`ScriptEngine` null error. Clean target: safe to proceed to the NonDex
run itself without needing the `rxjava2-extras` fallback.

**Note:** an earlier baseline attempt was accidentally run from
`flaky-study\idoft\` (no `pom.xml` there) and overwrote the same log file
with a spurious `$LASTEXITCODE=1` failure — not a real result, just wrong
working directory. Re-run from the correct folder gave the number above.

## 2026-09-16 — NonDex run (Module 3, Step 11)

**Target:** `delight-nashorn-sandbox`
**Command:**
```powershell
mvn edu.illinois:nondex-maven-plugin:2.2.1:nondex *> ..\..\findings\logs\nondex\run1.log
```

**Result:** `BUILD SUCCESS`. 4 total runs (1 clean + 3 shuffled seeds:
`933178`, `974622`, `1016066`), each **98 tests, 0 failures, 0 errors,
1 skipped**. NonDex's own summary: *"No Test Failed with this
configuration"* for every seed — **"All tests pass without NonDex
shuffling."**

**Interpretation:** a genuine null result, not a failed run —
`delight-nashorn-sandbox` makes no assumptions about unguaranteed Java
iteration order (HashMap/HashSet, etc.) that NonDex's shuffling would
catch. Worth reporting as-is per the plan (an empty summary is still a
real, reportable finding).

**Timing:** total wall-clock **19 minutes 22 seconds** — notably longer
than the ~7-minute estimate from 4× the Step 8 baseline (1m43s). The gap
is NonDex's own overhead (writing `.nondex\` output, generating
`test_results.html` per seed) across 4 runs, not slower test execution.

## 2026-09-16 — Bug found: `nondex:debug` is broken on Windows (unrelated to any real failure)

**Context:** ran the optional `nondex:debug` goal out of curiosity, even
though the Step 11 run found zero failures (nothing to actually debug).

**Command:**
```powershell
mvn edu.illinois:nondex-maven-plugin:2.2.1:debug "-Dtest=TheFailingTest"
```

**Result:** `BUILD FAILURE` — `Illegal char <0x0C> at index 23` while
resolving the run's stored `.nondex\<execid>` path.

**Diagnosis:** the corrupted path (`Toolslaky-studydelight-nashorn-sandbox...`
— most backslashes silently vanished from the real absolute path) matches
Java `Properties`-file escape parsing being applied to a raw Windows path.
Backslash-plus-uppercase-letter sequences (e.g. from a folder name
starting with a capital letter) are unrecognized escapes, so the parser
drops the backslash and keeps the letter; `\f` (the start of
`\flaky-study`) *is* a recognized escape — form feed (0x0C), an invisible
control character — which is the illegal char the path validator then
rejects. **`nondex:debug` appears to reload its saved run state through
Properties-style unescaping, which silently mangles any Windows path
containing a backslash followed by a letter — i.e. almost every real
Windows path.** Not specific to this project or this machine's folder
names; this would happen on any Windows machine, any project, any failing
test.

**Significance:** a genuine, reproducible, previously-undocumented
Windows-specific defect in NonDex's `debug` goal — parallel to iDFlakies'
own documented-but-unexplained Windows problems (Module 4). Diagnosed the
actual mechanism here, which iDFlakies' own docs don't attempt.

**Not pursued further** — no user-side fix found; noting the bug and
moving on rather than patching NonDex itself.

**Possible workaround (low priority, untested):** force forward slashes
via `-DnondexDir=Tools/.../.nondex` (relative to the drive/root) on both
the `nondex` and `debug`
goals, so the saved path never contains a backslash+letter sequence for
the `Properties` parser to misread. Would need a fresh `nondex:nondex`
run first — the existing `run1.log` execid was already saved with the
broken backslash path and can't be debugged after the fact. Only worth
trying if a future project actually has a real failing test to debug;
not needed for `delight-nashorn-sandbox` (zero failures found).

## 2026-09-18 — Second target: `marine-api` (Module 6, Step 21 — same-project comparison with iDFlakies)

**Purpose:** NonDex had only ever been run on `delight-nashorn-sandbox`,
never on the same project as an iDFlakies run — meaning no real
same-project NonDex-vs-iDFlakies comparison existed. Ran it on
`marine-api` (current commit, JDK 11) specifically to fill that gap.

**Command:**
```bash
mvn -B edu.illinois:nondex-maven-plugin:2.2.1:nondex
```

**Result:** `BUILD SUCCESS`, all 3 shuffled runs clean —
*"No Test Failed with this configuration"* each time. **Real time:
34.6 seconds.** A second genuine null result: `marine-api` makes no
unguaranteed-order (`ID`-category) assumptions, same as
`delight-nashorn-sandbox`.

## 2026-09-18 — Third target: `Java-WebSocket` (Module 6, Step 23)

**Purpose:** compare NonDex against TSVD4J's own 18 conflicting-pair
findings and IDoFT's documented labels, all on the same project/commit
(`aad6654`, matching TSVD4J's exact commit).

**Setup note:** this project needs JDK 8 (source level 1.7) — matches
the Windows-side requirement already known from the TSVD4J study.

**Command:**
```bash
mvn -B edu.illinois:nondex-maven-plugin:2.2.1:nondex
```

**Result:** `BUILD FAILURE` — NonDex couldn't even complete its own
initial clean baseline run. `Issue825Test.testIssue` (15s timeout) and
`Issue1142Test.testWithSSLSession` (4s timeout) failed before any
shuffling happened. **This is not a NonDex bug or a real "no result" —
it's the exact pre-existing environmental flakiness the plan's own Step 23
note warns about** (port reuse, SSL/timing issues unrelated to test
order). Also matches the Windows-side baseline run on this same commit
([idflakies_findings.md](idflakies_findings.md) equivalent), which found
4 failures + 2 timeouts in `Issue997Test`/`Issue825Test`/`Issue890Test` —
overlapping but not identical sets, consistent with genuinely
non-deterministic environmental flakiness rather than a fixed, reproducible
bug.

**Reportable finding:** NonDex requires a clean baseline to even start
shuffling — on a project with real pre-existing environmental flakiness,
this means NonDex **cannot produce any result at all**, clean or dirty.
That's a real limitation worth noting: unlike iDFlakies (which has an
explicit `all_must_pass=false` flag to tolerate this), NonDex has no
equivalent escape hatch in this version.

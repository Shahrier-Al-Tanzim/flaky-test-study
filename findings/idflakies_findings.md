# iDFlakies — Findings log

> Findings from Modules 4 (WSL) and 5 (Docker + Windows break). Keep entries
> concise, dated, with the exact command that produced them. Old entries are
> never deleted.

---

## 2026-09-18 — Linux-side baseline build (Module 4, Step 16)

**Target:** `rxjava2-extras`, cloned fresh inside WSL at
`~/flaky-study/rxjava2-extras` (not `/mnt/c` — avoided the crawl trap).

**JDK used:** OpenJDK 8 (`1.8.0_502`), switched via
`update-alternatives --config java` / `--config javac` — Ubuntu shipped
17 and 25 as defaults; 8 had to be selected explicitly. This is a
system-wide change (not per-terminal), confirmed persistent.

**Command:**
```bash
{ time mvn -q clean test ; } > /mnt/c/Tools/findings/logs/idflakies/idflakies-baseline.log 2>&1
```

**Result:** `EXIT CODE: 0` (pass), no matches for `FAILURE!` in
`target/surefire-reports/*.txt`. **Real time: 1m 3.473s** (user 43.7s,
sys 5.4s).

**Note on the log's content:** `-q` suppresses Maven's own
`BUILD SUCCESS`/`BUILD FAILURE` banner entirely — the log only contains
the test code's own console output (`System.out`/`System.err`), which
includes large `UndeliverableException` stack traces and repeated
`WARN: boo` lines. These are **intentional test noise** (the suite
deliberately throws errors with messages like `"boo"` to exercise
error-handling paths), not real failures — confirmed by the clean exit
code and empty failure search, not by assumption.

**Trap hit along the way:** `time cmd > file 2>&1` only redirects `cmd`'s
output — `time`'s own real/user/sys summary prints to the terminal, not
the file, unless grouped as `{ time cmd ; } > file 2>&1`. First attempt
lost the timing info to the screen; second attempt (shown above) captured
it correctly.

## 2026-09-18 — iDFlakies ran but executed zero tests (Module 4, Step 17)

**Target:** `rxjava2-extras`, same project as the clean Step 16 baseline
(176 compiled test classes confirmed present).

**Command (attempt 1):**
```bash
{ time mvn edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect \
  -Ddetector.detector_type=random-class-method \
  -Ddt.randomize.rounds=3 \
  -Ddt.detector.original_order.all_must_pass=false ; } \
  > /mnt/c/Tools/findings/logs/idflakies/idflakies-run1.log 2>&1
```

**Result:** `BUILD SUCCESS`, but `[INFO] Found 0 tests` — and a direct
`grep -c "Running "` on the log confirmed **0 matches**: no test actually
executed, despite 176 compiled `.class` files sitting in
`target/test-classes`. `flaky-lists.json` came back `{"dts":[]}` — an
empty result that looks identical to a clean "no flakiness found" run,
but isn't one.

**Diagnosis:** `pom.xml` line 225 has
`<argLine>@{argLine}</argLine>` — a placeholder normally filled in by
JaCoCo during a full `mvn test` lifecycle run. Invoking the iDFlakies
plugin goal directly skips that normal lifecycle, so the placeholder
likely never gets filled, and Surefire silently launches zero tests.
**This is the same class of bug as TSVD4J issue 5** (argLine collision
producing a false "success" with zero tests run) — now confirmed on a
second, independent tool.

**Attempted fix (command 2):** ran JaCoCo's own setup goal first in the
same invocation, hoping it would populate the placeholder before
iDFlakies ran:
```bash
mvn -B jacoco:prepare-agent edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect \
  -Ddetector.detector_type=random-class-method \
  -Ddt.randomize.rounds=3 \
  -Ddt.detector.original_order.all_must_pass=false \
  > /mnt/c/Tools/findings/logs/idflakies/idflakies-run2.log 2>&1
```
**Did not fix it** — `Found 0 tests` in all 3 rounds again, confirmed by
a direct log check (`-B` did clean up the ANSI color-code pollution from
attempt 1, confirmed separately — 0 escape-code matches — but had no
effect on the zero-tests problem).

**Conclusion:** `rxjava2-extras`'s specific JaCoCo/`argLine` pom setup is
incompatible with iDFlakies' direct-goal invocation, at least with the
fixes tried so far. Not pursuing further workarounds on this project —
switching target to `marine-api` instead, which has the added benefit of
already-confirmed real `OD-Vic` tests in IDoFT (Module 2 finding) to
compare against.

## 2026-09-18 — Baseline build, new target `marine-api` (Module 4, Step 16 redo)

**First attempt failed for a real reason:** `marine-api` targets Java
**11**, but WSL's active JDK was still set to 8 (switched earlier for
`rxjava2-extras`/iDFlakies-era projects). An older JDK cannot compile
code targeting a newer release — `Fatal error compiling: invalid target
release: 11`. Switched WSL's default back to JDK 17 via
`update-alternatives --config java` / `--config javac` (17 is newer than
11, so it can target it; 8 could not). **Lesson: the "use Java 8 for
iDFlakies" default from Step 15 doesn't hold for every project — match
the JDK per-project, same as the Windows side of this whole study.**

**Also fixed:** the first attempt's log was polluted with raw ANSI color
codes (`[1;31mERROR[m]` etc.) because `-B` (batch mode) was left off.
Added `-B` to the command below and confirmed 0 escape-code matches
afterward — `-B` should be included in every `mvn` command from here on.

**Command (JDK 17, with `-B`):**
```bash
{ time mvn -B -q clean test ; } > /mnt/c/Tools/findings/logs/idflakies/marine-api-baseline.log 2>&1
echo "EXIT CODE: $?"
```

**Result:** `EXIT CODE: 0` (pass), 0 `FAILURE` mentions, 0 leftover
escape codes. **Real time: 16.8 seconds** — much faster than
`rxjava2-extras`'s ~1m baseline, consistent with `marine-api` being a
smaller project.

## 2026-09-18 — Second bug: iDFlakies crashes on JDK 16+ (Module 4, Step 17, `marine-api`)

**First iDFlakies attempt on `marine-api` (JDK 17) crashed instantly:**
```
java.lang.reflect.InaccessibleObjectException: Unable to make private
java.lang.StackTraceElement() accessible: module java.base does not
"opens java.lang" to unnamed module
```
Root cause, confirmed by reading the actual crash file
(`failing-test-output-...`): iDFlakies bundles Google's **Gson** library
internally to serialize test results, and Gson uses reflection to access
a private JDK constructor (`StackTraceElement`). **Java 16 changed the
default from "allow with a warning" to "deny outright"** (JEP 396) for
exactly this kind of access — so an older tool like iDFlakies (built
before this became a hard error) breaks on JDK 16+ by default. Different
bug class from the `rxjava2-extras` `argLine` issue — this one is
iDFlakies itself colliding with a newer JDK, not a project's pom.

**Workaround attempts, in order:**
1. `export JAVA_TOOL_OPTIONS="--add-opens java.base/java.lang=ALL-UNNAMED"`
   — **failed differently**: `java -version` itself then errored with
   `Unrecognized option: --add-opens`, even though that flag is valid on
   JDK 9+. Cause unconfirmed, but reproducible: the flag works fine typed
   directly (`java --add-opens ... -version` succeeds), just not via this
   specific env var on this JDK/Maven combination.
2. `export JDK_JAVA_OPTIONS="--add-opens java.base/java.lang=ALL-UNNAMED"`
   (unset `JAVA_TOOL_OPTIONS` first) — **worked**. `mvn -version` picked
   it up cleanly (`NOTE: Picked up JDK_JAVA_OPTIONS: ...`), and the
   subsequent iDFlakies run no longer crashed at the reflection step.
3. **Switched to JDK 11 instead** (avoids the problem entirely — JDK 16's
   default change doesn't apply below 16, so no flag is needed at all).
   Confirmed via `apt-cache search openjdk` that `openjdk-11-jdk` was
   available; installed and set as default via `update-alternatives`.

**Result after switching to JDK 11:** iDFlakies ran without crashing —
`Located 1084 tests`, `Getting original results (1084 tests)` completed
(no exception), 3 rounds finished in ~13s, `flaky-lists.json` came back
`{"dts":[]}` (empty — zero flaky tests found). A `COPY_FAILING_TEST_OUTPUT`
line still appears in the log, but the referenced file's timestamp
(`Sep 18 18:35`) is **stale** — from the original JDK-17 crash, never
regenerated by later runs — confirmed this is leftover boilerplate
text, not a fresh failure.

**Open question this result raised:** `marine-api` has 12 confirmed
`OD-Vic` tests in IDoFT (Module 2 finding), tied to a real accepted PR.
iDFlakies found zero. Two possible explanations: (a) the clone is on a
newer commit than IDoFT's recorded SHA, so the fix is already merged, or
(b) 3–5 rounds is too few (the plan explicitly warns against trusting a
0-result from a short run). Checked via
`git merge-base --is-ancestor <idoft-sha> HEAD`: **confirmed the current
clone is newer** — the IDoFT-recorded commit is an ancestor of HEAD, so
explanation (a) is the more likely one.

**Verifying directly:** cloned a second copy
(`~/flaky-study/marine-api-oldsha`), checked out IDoFT's exact recorded
SHA (`af0003847db9ba822f67d4f1dceb8de3fe63250a`). This *old* pom has a
`system`-scoped dependency on `com.sun:tools:jar:0` (the old `tools.jar`
mechanism) — **removed entirely from the JDK starting Java 9**. So this
old commit needs **JDK 8 specifically**; neither 11 nor 17 can build it
(`Could not find artifact com.sun:tools:jar:0 ... tools.jar`). Worked
around by setting `JAVA_HOME` directly on the command (no `sudo`/system
default change needed) — baseline passed clean on JDK 8, then ran
iDFlakies with 5 rounds (in progress / see next entry for the result).

**Running total of environment problems this one project has produced:**
wrong JDK for compiling (needs 11+), iDFlakies' own JDK-16+ reflection
bug, and the old commit needing a JDK version that no longer even ships
a required file. All three are genuine, reportable observations about
how fragile cross-JDK reproduction is for older research tools — exactly
the kind of "limitations" and "unexpected behavior" this research aims
to surface, independent of whatever the actual flaky-test result turns
out to be.

## 2026-09-18 — Full result: iDFlakies exactly reproduces IDoFT's 12 tests (Module 4, Step 17/18)

**Target:** `marine-api`, checked out at IDoFT's exact recorded commit
`af0003847db9ba822f67d4f1dceb8de3fe63250a`, in a second clone
(`~/flaky-study/marine-api-oldsha`), using **JDK 8** (required — see the
`tools.jar` note above).

**Command:**
```bash
{ time mvn -B edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect \
  -Ddetector.detector_type=random-class-method \
  -Ddt.randomize.rounds=5 \
  -Ddt.detector.original_order.all_must_pass=false ; } \
  > /mnt/c/Tools/findings/logs/idflakies/marine-api-oldsha-run1.log 2>&1
```

**Result:** `BUILD SUCCESS`, real time **56.7 seconds**. `Located 926
tests`. Rounds 1, 2, 4, 5 each found 0 flaky tests; **round 3 found
exactly 12** — matching IDoFT's recorded count precisely. The 12 detected
test names, pulled from `detection-results/list.txt`:

```
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testBasicListenerWithUnexpectedMessage
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testConstructor
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testGenericsListener
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testGenericsListenerDefaultConstructorThrows
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testOnMessageWithExpectedMessage
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testParametrizedConstructor
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListener
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListenerWithIncorrectOrder
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListenerWithMixedOrder
net.sf.marineapi.ais.parser.AISMessageFactoryTest.testCreate
net.sf.marineapi.ais.parser.AISMessageFactoryTest.testCreateWithIncorrectOrder
net.sf.marineapi.ais.parser.AISMessageFactoryTest.testCreateWithTwo
```

**This is an exact match** — all 12 identical to the 12 `OD-Vic` tests
IDoFT recorded for `marine-api` (Module 2 finding), same test names, same
count.

**The classification gap, quantified:** checked `flaky-lists.json`'s
per-test `"type"` field — **all 12 of 12 (100%) are labeled generic
`"OD"`, with no victim/polluter sub-classification at all.** IDoFT's own
data calls these `OD-Vic` specifically (it identified which side of the
pair is the victim); iDFlakies detected the exact same 12 tests but
couldn't determine which are victims vs. polluters for any of them. This
is precisely the documented "partial classification" weakness — this
run is a clean, complete demonstration of it: iDFlakies can reliably
**detect** order-dependence here, but not **diagnose** it.

**Full picture across both commits:**

| Clone | Commit | iDFlakies result |
| --- | --- | --- |
| `marine-api` (current) | `6224ad6`, newer than IDoFT's recorded SHA | 0 flaky tests found |
| `marine-api-oldsha` | `af00038`, IDoFT's exact recorded SHA | **12/12 flaky tests found — exact match** |

**Conclusion — a genuine cross-tool/cross-dataset finding:** iDFlakies
independently reproduces IDoFT's exact recorded result when run at the
matching commit, using a completely different detection method (random
reordering vs. whatever IDoFT's own pipeline used). On the current,
newer commit, iDFlakies correctly finds nothing — consistent with PR #109
(the fix IDoFT's own row links to) having already been merged. This is
not a disagreement between tool and dataset; it's a **successful
independent confirmation of a historical, already-fixed bug**, plus
confirmation the fix holds on current code. A different, complementary
kind of result to the `rxjava2-extras`/`argLine` disagreement above —
one shows a real tool-vs-project incompatibility, this one shows a real
tool-vs-dataset agreement.

## 2026-09-18 — Full 20-round confirmation on current commit (Module 4, Step 18 Verify)

Per the plan's own rule — *"Do not report '0 OD tests' from a 3-round
run. Three shuffles is a smoke test, not a search."* — the 3-round `run1`
result above was not yet trustworthy on its own. Re-ran at the paper's
full default of 20 rounds to settle it properly.

**Command:**
```bash
{ time mvn -B edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect \
  -Ddetector.detector_type=random-class-method \
  -Ddt.randomize.rounds=20 \
  -Ddt.detector.original_order.all_must_pass=false ; } \
  > /mnt/c/Tools/findings/logs/idflakies/marine-api-run-20rounds.log 2>&1
```

**Result:** `BUILD SUCCESS`, real time **1m 26.8s**. `Located 1084
tests`. **All 20 rounds found 0 flaky tests** — the 3-round result was
not a false negative; it agrees fully with the full 20-round search.

**Verify — satisfied.** Combined with the old-commit result (12/12 match
at 5 rounds — not a null result, so round count matters less there), the
full picture is now backed by the proper rigor level the plan calls for,
not just a quick smoke test.

## 2026-09-18 — Genuine Windows-specific bug, precisely diagnosed (Module 5, Step 20)

**Target:** `marine-api`, Windows-side clone (`C:\...\flaky-study\marine-api`)
— discovered mid-test that this clone happens to already sit at
`af00038`, the exact same old commit tested in WSL, not the current one.

**Honesty caveat (found 2026-09-19, in retrospect):** this clone's
`pom.xml` is not pristine — it has a `tsvd4j-maven-plugin` declaration
added during the earlier TSVD4J study (permitted under the plan's own
ground rules: "add a plugin block the tool itself requires"). Checked
the diff: it's a bare `<plugin>` declaration with no `<execution>`
binding shown, so it shouldn't auto-run during a direct goal invocation
like `idflakies:detect`, and it doesn't explain the `FileSystemException`
below (that's clearly internal to iDFlakies' own `TempFiles.scala`, not
project-specific). Still, this run was not against a fully clean clone —
worth knowing if anyone tries to reproduce this exactly.

**First attempt (JDK 21, Windows default):** failed with
`Could not find artifact com.sun:tools:jar:0` — the **same already-known**
`tools.jar` issue from the old-commit section above (this clone needs
JDK 8, unrelated to Windows itself). Not a new finding — re-ran with the
right JDK to isolate anything genuinely Windows-specific underneath.

**Second attempt (JDK 8, matching what worked in WSL):**
```powershell
$env:JAVA_HOME = "C:\Users\Tanzim\.jdks\corretto-1.8.0_412"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
mvn -B edu.illinois.cs:idflakies-maven-plugin:2.0.0:detect "-Ddetector.detector_type=random-class-method" "-Ddt.randomize.rounds=3" "-Ddt.detector.original_order.all_must_pass=false" *> ..\..\findings\logs\idflakies\idflakies-windows-attempt-jdk8.log
```

**Result:** `Located 926 tests` (test discovery worked fine — same as
WSL). Then, right at `Getting original results`, a real crash:

```
java.nio.file.FileSystemException: C:\Users\...\Temp\temp....tmp: The
process cannot access the file because it is being used by another
process.
  at sun.nio.fs.WindowsFileSystemProvider.implDelete(...)
  at java.nio.file.Files.deleteIfExists(Files.java:1165)
  at edu.illinois.cs.testrunner.util.TempFiles$.withTempFile(TempFiles.scala:19)
  at edu.illinois.cs.dt.tools.runner.InstrumentingSmartRunner.runWithCp(InstrumentingSmartRunner.java:54)
  ...
```
(full trace also saved by iDFlakies itself to `.dtfixingtools/error`)
**`BUILD SUCCESS` printed anyway** — the now-familiar false-success
pattern, a fourth confirmed instance of it in this study.

**Diagnosis — a real Windows/Linux filesystem semantics difference:**
`TempFiles.withTempFile` (Scala, line 19) deletes a temp file right after
a forked test-runner subprocess finishes using it. **On Linux, a process
can delete a file while another process still has it open** — completely
normal POSIX behavior, which is why this never breaks in WSL. **On
Windows, a file locked open by one process cannot be deleted by another
until the OS releases the lock** — if the forked subprocess's file handle
hasn't fully released by the time the parent tries to delete it, Windows
throws `FileSystemException` instead of just succeeding. iDFlakies'
temp-file cleanup code was written assuming POSIX delete semantics and
doesn't account for this.

**This is exactly what upstream's undocumented "Windows has some
problems" warning refers to** — now precisely identified: not a vague
compatibility issue, but one specific method (`TempFiles.withTempFile`)
making an assumption that only holds on POSIX filesystems. First
documented, reproducible, root-caused account of this — upstream's own
docs never explain it.

## 2026-09-18 — Docker route, official multi-detector pipeline (Module 5, Step 19)

**Setup:** Docker Desktop was not running initially — started it, confirmed
WSL integration works (`docker ps` succeeds from inside Ubuntu). Cloned
the iDFlakies *tool* repo itself (separate from test-subject clones):
```bash
git clone https://github.com/UT-SE-Research/iDFlakies.git
```

**Read `create_and_run_dockers.sh` before running it**, per the plan's
own instruction. Input format: a CSV of `owner/repo,sha` lines, plus
`rounds` and `timeout` (seconds) as positional args. Also read
`baseDockerfile` first — worth noting it pins **Ubuntu 16.04** and
**JDK 8 hardcoded**, meaning this route can only test commits that build
on JDK 8. Used `marine-api`'s exact IDoFT-recorded SHA (matches the JDK 8
requirement already established for that commit).

**Command:**
```bash
echo "ktuukkan/marine-api,af0003847db9ba822f67d4f1dceb8de3fe63250a" > projects.csv
./create_and_run_dockers.sh projects.csv 3 300 > /mnt/c/Tools/findings/logs/idflakies/docker-run1.log 2>&1
```

**Result:** Building the base image worked cleanly — despite Ubuntu
16.04 being long past end-of-life, its package mirrors (including
`xenial-security`) were still reachable and every `apt-get` step
succeeded. **Not the broken-infrastructure finding expected going in.**

The official `run_project.sh`/`run_experiment.sh` pipeline runs **7
separate detector modes automatically** in one invocation — far more
thorough than a single manual `mvn idflakies:detect` call:

| Detector | Rounds | Result |
| --- | --- | --- |
| `random` | **20** | **Found 9 tests** |
| `reverse` | 3 | 0 |
| `reverse-class` | 3 | 0 |
| `original` | 3 | 0 |
| `random` (again) | 3 | 0 |
| `random-class` | 3 | 0 |
| `smart-shuffle` | 3 | 0 |

**The 9 tests found**, all from one class:
```
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListenerWithIncorrectOrder
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testGenericsListenerDefaultConstructorThrows
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testGenericsListener
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListenerWithMixedOrder
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testConstructor
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testOnMessageWithExpectedMessage
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testSequenceListener
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testParametrizedConstructor
net.sf.marineapi.ais.event.AbstractAISMessageListenerTest.testBasicListenerWithUnexpectedMessage
```

**Compared to our own WSL result (12/12, exact IDoFT match, above):**
these 9 are an **exact subset** — the same 9 `AbstractAISMessageListenerTest`
tests, but missing all 3 `AISMessageFactoryTest` tests
(`testCreate`, `testCreateWithIncorrectOrder`, `testCreateWithTwo`) our
own `random-class-method` run (5 rounds) caught.

**Reading this correctly:** not a contradiction between the two routes —
a genuine methodological difference. Different detector strategies
(`random` vs `random-class-method`) and round counts have different
power to catch different flaky tests, even on the exact same commit.
Docker's own official pipeline, using its own default `random` detector
at 20 rounds, only caught 9 of the 12 known-flaky tests; our manually
chosen detector/round combination caught all 12. **This is itself a
useful finding**: even the paper's own reference detection method,
run at its own default settings, doesn't reliably catch every known
flaky test in one pass — reinforcing why the plan warns against trusting
a single run's "0 found" result at face value.

**Verify — satisfied.** Docker route confirmed working (WSL integration,
image builds, container run all succeeded), and its result was directly
compared against the manual WSL run rather than taken at face value.

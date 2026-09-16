# IDoFT — Findings log

> Findings from Module 2 (dataset exploration) and the Module 6 staleness
> check, which reuses this same dataset. Keep entries concise, dated, with
> the exact command that produced them. Old entries are never deleted.

---

## 2026-09-16 — Dataset overlap search (Module 2, Step 7)

**Command:**
```powershell
Select-String -Path pr-data.csv -Pattern "Java-WebSocket|marine-api|rxjava2-extras|delight-nashorn-sandbox|openpojo|fluent-logger-java|commons-dbcp|commons-pool"
```

**Result:** 6 of 8 cloned projects appear in IDoFT.

| Project | Hits | Notes |
| --- | --- | --- |
| Java-WebSocket | ~40+ | Includes `Issue677Test.testIssue` = `NDOD;OD-Vic;TD` — check against TSVD4J's pairs in Module 6 |
| marine-api | 12 | All `OD-Vic`, all `Accepted`, all from one real PR ([#109](https://github.com/ktuukkan/marine-api/pull/109)) |
| openpojo | 20 | Mix of ID / OD-Vic / UD, many `Unmaintained` |
| fluent-logger-java | 7 | Several `Unmaintained` (last commit 2019-06-12) |
| rxjava2-extras | 6 | Mostly NDOD/TD/UD |
| delight-nashorn-sandbox | 3 | Includes `NDOD;OD-Brit;TD` |
| **commons-dbcp** | **0** | Not in the dataset |
| **commons-pool** | **0** | Not in the dataset |

## 2026-09-16 — Category distribution + a parsing gotcha

**Command (naive, wrong):**
```powershell
Get-Content pr-data.csv | ForEach-Object { ($_ -split ',')[4] } | Group-Object | Sort-Object Count -Descending
```

**Command (correct):**
```powershell
Import-Csv pr-data.csv | Group-Object Category | Sort-Object Count -Descending
```

**Result:** the naive `-split ','` undercounted `ID` by 37 (5,154 vs. the
correct 5,191) and produced two fake "categories" (`[])`, `[])@[a]`,
13 + 11 rows) — caused by commas embedded inside free-text fields (likely
Notes) that a plain split doesn't respect. `Import-Csv` parses quoting
correctly and is the trustworthy source for exact counts.

**Real distribution (top categories, `Import-Csv`):** ID 5,191 · OD 1,074 ·
NOD 664 · OD-Vic 470 · NIO 198 · UD 158 · TD 129. **ID dominates the dataset
by ~5×** — relevant since ID is exactly what NonDex targets.

# RankF - quick-reference summary

> Condensed from [rankf_findings.md](rankf_findings.md) and [reports/rankf/rankf_report.md](reports/rankf/rankf_report.md). One line per point.

## Limitations found
- Maven Surefire's `runOrder=random` only shuffles test *classes*, never methods within one class - if a polluter and its cleaner share a class (true for all 12 `marine-api` OD tests), no random-seed corpus can ever produce a failing order.
- The same class-level ceiling breaks OBO too - pairing the whole polluter class with the victim still passes, so `OBO_avg` couldn't be measured end-to-end either.
- `RankF_O` could only be scored at test-*class* granularity here, not method-level, because of the corpus ceiling above.
- srcML (needed for `RankF_L`) fails to parse ~18% of test bodies (inherited code) by the paper's own numbers - a chunk of candidates invisible to the LLM half by construction.
- Module 7 (`RankF_L`, GPU) never ran: fine-tuned model weights on Box are gone (404), and training needs ~8x this machine's VRAM.
- The dubbo known-answer validation (Step 16, `testDubboProtocolWithMina`/`testRpcFilter`) was started then abandoned - running it hung the user's machine - so the one scored `marine-api` result has no independent known-answer cross-check.

## Gaps / disagreements
- iDFlakies labels all 12 confirmed `marine-api` OD tests as generic `"OD"`, never `OD-Vic`/`OD-Brit` - but `RankF_O`'s algorithm needs that distinction to pick the right scoring branch. iDFlakies output alone cannot drive RankF; a third artifact (IDoFT) has to supply the label by hand.
- Guessing the wrong victim/brittle label doesn't just degrade the ranking - it drops the true polluter from rank 1 to rank 17 and replaces the top of the list with unrelated classes.
- The paper evaluates `RankF_O` at 20 test-orders but admits stable Rank-1 needs 86–206 orders on average; this reproduction's own 3-shuffle sweep found the true polluter missed 3/3 times at 20 orders on its subject.
- Costing that 86–206-order requirement against measured baseline times gives 18.5–44.3 minutes - 22–52x delta-debugging's real measured cost, undercutting RankF_O's "cheap alternative" framing (partially offset by corpus reuse across multiple OD tests, an amortization the paper never states either).
- Paper's own MAP table: `RankF_L` 0.007 vs `RankF_O` 0.251 for ranking polluters - the GPU-dependent half scores 36x worse by that metric despite being the headline result; paper never draws this conclusion itself.
- `apache/dubbo` module `dubbo-rpc/dubbo-rpc-dubbo` @ SHA `737f7a7` is flagged by both RankF (OD, via `DubboProtocolTest`) and FlakeSync (NOD, same class, different methods) - same class/commit, disagreeing failure mechanisms, neither paper aware of the other.
- Two of RankF's four artifact pieces are effectively gone: fine-tuned model weights (Box, 404) and the paper's primary ground-truth dataset citation (dead GMU link; a secondary Drive mirror still works but is scoped differently).

## Opportunities to improve the technique
- RankF (or a wrapper around it) should consume IDoFT's victim/brittle labels directly instead of assuming iDFlakies' output already carries that information - closes the exact handoff gap found in Module 8.
- A corpus-generation step should detect same-class polluter/cleaner pairs up front and fall back to a different randomization strategy (e.g. explicit method-level shuffling within a class) instead of silently producing a useless all-passing corpus.
- The paper's own order-count admission (86–206 needed vs. 20 evaluated) should be turned into an adaptive stopping rule - keep generating orders until the ranking stabilizes, rather than a fixed count - which would also make the real cost visible rather than hidden in one sentence.
- Publish checksums alongside the Box/Drive artifact links so re-downloads (or their absence) can be verified/detected, matching what FlakeSync's Zenodo record already does.
- Given `RankF_L`'s much worse MAP score for a large GPU/setup cost, the practical recommendation is to default to `RankF_O` and treat `RankF_L` as optional/experimental rather than the headline method.

## General findings
- Module 4's one scored case (`marine-api`, `SentenceFactoryTest` polluter) ranked correctly at #1 under the positive-class strategy, using a hand-assembled corpus (90 auto passing orders + 2 hand-verified) rather than the intended pure-random corpus.
- Surefire's `-Dtest` argument order is not honored by `runOrder=filesystem` - execution ends up alphabetical by package regardless of the requested sequence, confirmed on two unrelated projects.
- This reproduction's own module-9/dubbo cross-check with FlakeSync, plus the RankF-vs-iDFlakies label gap, both land on the same broader point already seen elsewhere in this study: category labels (OD vs NOD, victim vs brittle) are less reliable and less mutually exclusive than the papers evaluating against them assume.
- `apache/dubbo` known-answer validation remains undone; the `marine-api` result stands on hand-verified ground truth (Module 3) alone.

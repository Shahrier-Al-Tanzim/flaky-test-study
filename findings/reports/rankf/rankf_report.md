# RankF: Findings Summary

RankF ranks candidate tests by how often they appear before an
order-dependent (OD) test in orders where it failed versus orders where it
passed - the goal is to find the polluter (for a victim) or state-setter (for
a brittle) without running every candidate one by one. Testing covered
`RankF_O` (the CPU-only, model-free half) end to end on `marine-api`, plus
both classical baselines (OBO, delta-debugging) measured the same way. The
GPU half, `RankF_L`, was not run - its published fine-tuned models are gone
(the Box link 404s) and training from scratch would need 8× the VRAM this
machine has, so Module 7 was skipped rather than attempted and abandoned.

## What I did

Reproduced `RankF_O` from the paper's own algorithm description (Section
III-B) against `marine-api`, the same subject an earlier module in this study
already confirmed has 12 exact-match order-dependent tests against IDoFT.
Hand-verified one victim/polluter/cleaner triple by running it directly
(alone, polluted, cleaned) before trusting anything downstream. Built a test-
order corpus, scored it under all 5 heuristics × 3 strategies the paper
defines, measured both classical baselines (OBO, delta-debugging) for real on
the same machine, swept corpus size against ranking accuracy, and cross-
checked the whole pipeline against iDFlakies' actual output format and
FlakeSync's overlapping dubbo data. Skipped: `RankF_L` (Module 7, GPU - documented dead end, not attempted) and the `dubbo` known-answer validation
(deferred - would need cloning and building `apache/dubbo` separately).

## Limitations identified

**The central one, found while trying to generate a test-order corpus:**
Maven Surefire's `runOrder=random` only ever shuffles the order of test
*classes* - it cannot reorder methods *within* one class, which follows a
fixed JUnit4 hash unrelated to the seed. `marine-api`'s real polluter and its
recorded cleaner both live in the same test class. The result: **no amount of
random-seed corpus generation can ever produce a single failing test-order
for this subject's ground truth** - confirmed empirically across 90 seeds (0
failures) and then proven directly (identical intra-class method order at
every seed tried). This isn't specific to `marine-api` either - checking the
Wei dataset showed all 12 of the subject's confirmed OD tests share this same
structure. A corpus had to be hand-assembled instead (90 auto-generated
passing orders + 2 hand-verified orders) to make scoring possible at all.

**The same limitation reaches OBO, not just `RankF_O`'s corpus.** Pairing the
whole polluter class (not just the specific method) with the victim, in
isolation, still passes - meaning a real OBO implementation walking at class
granularity would never find this subject's culprit either. `OBO_avg` as the
paper defines it (average over 10 failing/passing orders) could not be
measured end-to-end for the same structural reason.

**iDFlakies' output cannot feed `RankF_O` directly**, despite RankF naming it
as the expected upstream source. iDFlakies labels all 12 of `marine-api`'s
confirmed OD tests with a generic `"OD"` type - never `OD-Vic` or `OD-Brit` - but `RankF_O`'s algorithm branches on exactly that distinction (failing
orders vs. passing orders are positive evidence, depending on which). Ran
both assumptions on the identical corpus to make this concrete: guessing
wrong drops the true polluter from rank 1 to rank 17, and replaces the top of
the ranked list with unrelated classes. The only place the needed label
exists is IDoFT - a third artifact neither paper's tool produces.

## Unexpected behavior

Surefire's `-Dtest` argument order is not honored at all by `runOrder`
settings like `filesystem` - it turned out to just be alphabetical-by-package
in practice, ignoring the requested sequence entirely, confirmed independently
on two unrelated projects (`unix4j` and `marine-api`). A run that looked like
a clean non-reproduction (both tests passed) was actually running the tests
in the reverse of the intended order - caught only by checking surefire XML
write-timestamps rather than trusting the exit code.

Two of the RankF artifact's own hosted pieces are gone: the fine-tuned
`RankF_L` model weights (Box link, genuine 404) and the paper's primary
citation for its ground-truth dataset (a dead GMU faculty-page URL - a
secondary Google Drive mirror still works, but scoped differently than the
paper's headline 249/155 numbers).

## Disagreements between these results and the paper's

The paper's own admission that `RankF_O`'s evaluated 20-order configuration
falls far short of the 86–206 orders needed for a *stable* ranking was
independently corroborated here, on a different subject: swept 3 independent
shufflings of the corpus, and **none of the three found the true polluter at
20 orders** - 0 for 3, not a coin-flip in this reproduction's favor, worse.

The paper's stated best configuration for `RankF_O` - Plus One heuristic,
combined-class strategy - **ranked the true polluter 51st of ~70** on this
subject's corpus; only the positive-class strategy (not the paper's
recommendation) found it at rank 1. Flagged as `[CONFIG-DEPENDENT]` rather
than a clean contradiction, since the cause is very likely this
reproduction's forced 91:1 pass/fail corpus imbalance rather than a flaw in
the paper's claim in general.

Costed the paper's own admitted 86–206-order requirement in real minutes on
this machine: 18.5–44.3 minutes, versus delta-debugging's real measured 50.6
seconds for the same job - a 22–52× gap that directly undercuts the "cheap,
GPU-free alternative" framing, with the honest counterpoint that a corpus is
reusable across every OD test in a project, unlike delta-debugging.

FlakeSync's M9 (`apache/dubbo`, module `dubbo-rpc/dubbo-rpc-dubbo`, same SHA
RankF's own dataset uses) and RankF's dubbo ground truth both flag the same
test class, `DubboProtocolTest`, as containing flaky behavior - but disagree
on which specific methods matter and by what mechanism (order-dependence vs.
async timing). Not a direct same-test contradiction, but a closer overlap
than either paper's authors appear to know about.

## Opportunities to improve the technique

`RankF_O`'s corpus-generation step should document (or detect) the same-class
polluter/cleaner case explicitly - right now a user relying on vanilla
Surefire `runOrder=random` would silently get a corpus that can never contain
the failing order they need, with no warning.

The victim/brittle label dependency is a real integration gap between RankF
and its own named upstream tool (iDFlakies). A small compatibility shim that
consumes IDoFT's labels directly, or a documented manual step, would close
the loop RankF's own paper implies exists but doesn't.

The paper's RQ2 order-count admission (206.0/86.2/171.5 orders needed) should
be paired with the real-minutes cost that follows from it, the way Module 6
worked out here - as written, the paper's own text makes `RankF_O` look
strictly cheaper than the baselines, which this reproduction's arithmetic
does not support once the full order count is priced in.

## Next steps

- Clone and build `apache/dubbo` to run the Figure 1/2 known-answer
  validation (`testDubboProtocolWithMina` / `testRpcFilter`) that Module 4
  deferred - the strongest available cross-check against the paper's own
  worked example, not yet done.
- Follow up on the FlakeSync/RankF `DubboProtocolTest` overlap: run
  FlakeSync's four NOD-labeled methods (`testDemoProtocol`,
  `testNonSerializedParameter`, `testPerm`, `testReturnNonSerialized`) under
  RankF's OD framing to check whether any are secretly order-dependent too.
- If a project with a genuinely diverse (non-same-class) polluter/cleaner
  relationship turns up, re-run Module 4's sweep there to get a smooth
  convergence curve rather than this reproduction's step function, and see
  whether the 20-orders-is-unstable finding holds at a less degenerate
  imbalance ratio.

# RankF vs. FlakeSync - comparison findings

> Condensed, single-line points. Full detail: [rankf_findings.md](rankf_findings.md) Module 8 Step 30, [flakesync_findings.md](flakesync_findings.md), [comparative_report.md](comparative_report.md) §11.

## What they even target (different by design)
- RankF ranks OD (order-dependent) tests' polluters/state-setters; FlakeSync repairs NOD (asynchronous/timing) flaky tests - disjoint categories by definition, not competing techniques.
- Neither paper cites the other, despite coming from research groups working the same benchmark ecosystem (IDoFT).
- RankF is diagnosis-only (produces a ranked list, doesn't fix anything); FlakeSync attempts an actual repair.

## The concrete overlap found
- Both plans independently hit `apache/dubbo`, module `dubbo-rpc/dubbo-rpc-dubbo`, at the exact same SHA (`737f7a7`) - RankF via the Wei dataset, FlakeSync as its own subject M9.
- Both flag the same test class, `DubboProtocolTest`, as flaky - but by different mechanisms: RankF calls `testDubboProtocolWithMina` order-dependent (brittle), FlakeSync calls `testDemoProtocol`/`testNonSerializedParameter`/`testPerm`/`testReturnNonSerialized` asynchronous (NOD).
- Specific method names don't collide - so it's not a direct same-test contradiction, just an unexpectedly close near-miss: same class, same commit, different specific methods, different claimed root cause.
- Open question left unrun: whether FlakeSync's four "async" methods in that class are secretly order-dependent too (mislabelled), or vice versa - neither this reproduction nor either paper checked.

## Shared meta-finding, reached from opposite directions
- FlakeSync's own Step 32 found 54% of a sampled IDoFT NOD-labelled set aren't really async-flaky.
- RankF's Module 2/3 found the Wei OD dataset's published counts don't match the paper's own funnel, and a "non-reproducing" OD test can be a test-ordering-tool artifact rather than a real fix.
- Conclusion both point at: the category labels (OD vs. NOD) that these techniques are evaluated against are less reliable, and less mutually exclusive, than either evaluation assumes.

## Methodological parallels noticed while running both
- Both papers report a single "headline" configuration while admitting (in one line) that it isn't the one needed for stability - RankF: 20 orders evaluated vs. 86–206 needed for stable Rank-1; FlakeSync: its shipped delay schedule vs. a stress-tested one.
- Both showed non-deterministic/config-dependent behavior under repetition - FlakeSync's critical-point search gave two different answers across 6 repeated runs on one machine; RankF's ranking moved with which 20-order sample was drawn.
- Both artifacts have an availability gap not disclosed by the papers - RankF's fine-tuned models (Box, gone) and primary dataset citation (dead GMU link); FlakeSync's own evaluation-input row for `elastic-job-lite` uses an unpinned `master` ref instead of a SHA and broke during this study.

## Net takeaway
- Running both on the same repo ecosystem strengthens the same conclusion twice, independently: OD/NOD classification in the underlying benchmarks (IDoFT, Wei dataset) is shakier than downstream tools assume, and both tools' headline numbers are more configuration-dependent than their papers admit.

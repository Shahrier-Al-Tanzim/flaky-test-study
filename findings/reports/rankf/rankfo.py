"""RankF_O reimplementation, from the paper's Section III-B description
(Module 4, Step 16). Reads a corpus of test-orders with pass/fail outcomes for
one OD test, scores every candidate test by five heuristics, ranks by three
strategies, and writes one CSV per (heuristic, strategy) combination.

Candidate granularity in this run is test CLASS (see the findings log for why
method-level granularity could not be corpus-generated for this subject).
"method count" (#Methods heuristic) is therefore each class's method count
from suite-tests.txt, and "distance" is measured in classes, not methods.
"""
import argparse
import csv
import glob
from collections import defaultdict

HEURISTICS = ["plusone", "nummethods", "distance", "combined_1d", "combined_md"]
STRATEGIES = ["positive", "negative", "combined"]


def load_corpus(path):
    orders = []
    with open(path) as f:
        for r in csv.DictReader(f):
            before = [c for c in r["before"].split("|") if c]
            orders.append({"outcome": r["outcome"], "before": before})
    return orders


def load_method_counts(suite_file):
    counts = defaultdict(int)
    with open(suite_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cls, _ = line.split("#")
            counts[cls.rsplit(".", 1)[-1]] += 1
    return counts


def score_orders(orders, heuristic, method_counts, kind="victim"):
    # victim: failing orders vote positive (looking for a polluter).
    # brittle: passing orders vote positive instead (looking for a state-setter) -
    # the paper's own distinction (Section III-B); getting this backwards inverts
    # the whole ranking, which is exactly what Module 8 Step 28 tests.
    positive_outcome = "fail" if kind == "victim" else "pass"
    pos = defaultdict(float)
    neg = defaultdict(float)
    last_distance = {}  # tie-break source: distance in the LAST order processed
    for order in orders:
        before = order["before"]
        n = len(before)
        for i, test in enumerate(before):
            distance = n - i  # 1 = immediately before the OD test
            if heuristic == "plusone":
                weight = 1.0
            elif heuristic == "nummethods":
                weight = float(method_counts.get(test, 1))
            elif heuristic == "distance":
                weight = 1.0 / distance
            elif heuristic == "combined_1d":
                weight = 1.0
            elif heuristic == "combined_md":
                weight = float(method_counts.get(test, 1))
            else:
                raise ValueError(heuristic)

            if order["outcome"] == positive_outcome:
                pos[test] += weight
            else:
                neg[test] += weight
            last_distance[test] = distance
    return pos, neg, last_distance


def rank(candidates, pos, neg, last_distance, strategy, heuristic):
    def tie_break(test):
        # Combined heuristics break ties by distance-to-OD-test in the last order;
        # the three simple heuristics break ties alphabetically.
        if heuristic in ("combined_1d", "combined_md"):
            return last_distance.get(test, float("inf"))
        return test

    if strategy == "positive":
        key = lambda t: (-pos.get(t, 0.0), tie_break(t))
    elif strategy == "negative":
        key = lambda t: (neg.get(t, 0.0), tie_break(t))
    elif strategy == "combined":
        key = lambda t: (-(pos.get(t, 0.0) - neg.get(t, 0.0)), tie_break(t))
    else:
        raise ValueError(strategy)
    return sorted(candidates, key=key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--suite-file", required=True)
    ap.add_argument("--od-class", required=True, help="simple class name, excluded from candidates")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--kind", default="victim", choices=["victim", "brittle"])
    args = ap.parse_args()

    orders = load_corpus(args.corpus)
    method_counts = load_method_counts(args.suite_file)
    candidates = sorted(c for c in method_counts if c != args.od_class)

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    for heuristic in HEURISTICS:
        pos, neg, last_distance = score_orders(orders, heuristic, method_counts, args.kind)
        for strategy in STRATEGIES:
            ranked = rank(candidates, pos, neg, last_distance, strategy, heuristic)
            out_path = f"{args.out_dir}/ranked-{heuristic}-{strategy}.csv"
            with open(out_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["rank", "test", "positive_score", "negative_score", "combined_score"])
                for i, t in enumerate(ranked, start=1):
                    p, n = pos.get(t, 0.0), neg.get(t, 0.0)
                    w.writerow([i, t, p, n, p - n])
    print(f"{len(HEURISTICS) * len(STRATEGIES)} ranked lists written to {args.out_dir}")


if __name__ == "__main__":
    main()

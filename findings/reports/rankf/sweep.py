"""Module 6, Step 21: sweep rank-of-true-polluter against corpus size, using
prefixes of the SAME (shuffled) corpus so each point is a superset of the
last, repeated across 3 independent shuffles per the plan's instruction.
"""
import argparse
import csv
import random
import sys

sys.path.insert(0, ".")
from rankfo import score_orders, rank, HEURISTICS, STRATEGIES, load_method_counts  # noqa: E402


def load_corpus(path):
    orders = []
    with open(path) as f:
        for r in csv.DictReader(f):
            before = [c for c in r["before"].split("|") if c]
            orders.append({"outcome": r["outcome"], "before": before})
    return orders


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--suite-file", required=True)
    ap.add_argument("--od-class", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--sizes", default="5,10,20,30,50,75,92")
    ap.add_argument("--shuffles", type=int, default=3)
    ap.add_argument("--heuristic", default="plusone")
    args = ap.parse_args()

    orders = load_corpus(args.corpus)
    method_counts = load_method_counts(args.suite_file)
    candidates = sorted(c for c in method_counts if c != args.od_class)
    sizes = [int(x) for x in args.sizes.split(",")]

    print("shuffle,n_orders,n_fail_included,strategy,rank_of_truth")
    for shuffle_i in range(args.shuffles):
        rng = random.Random(1000 + shuffle_i)
        shuffled = orders[:]
        rng.shuffle(shuffled)
        for n in sizes:
            prefix = shuffled[:n]
            n_fail = sum(1 for o in prefix if o["outcome"] == "fail")
            pos, neg, last_distance = score_orders(prefix, args.heuristic, method_counts)
            for strategy in STRATEGIES:
                ranked = rank(candidates, pos, neg, last_distance, strategy, args.heuristic)
                r = ranked.index(args.truth) + 1 if args.truth in ranked else -1
                print(f"{shuffle_i},{n},{n_fail},{strategy},{r}")


if __name__ == "__main__":
    main()

"""Generate a RankF_O test-order corpus for marine-api by running the full
suite under many random Surefire seeds and recording, per seed: the class
execution order (from surefire report write-times) and the OD test's outcome.

Usage:
    python gen_corpus.py --project <path-to-marine-api-rankf> --seeds 1-20 \
        --od-class net.sf.marineapi.ais.event.AbstractAISMessageListenerTest \
        --od-method testBasicListenerWithUnexpectedMessage \
        --out corpus.csv --java-home <path>
"""
import argparse
import csv
import glob
import os
import subprocess
import sys
import xml.etree.ElementTree as ET


def run_one_seed(project, java_home, seed, test_selector):
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env["PATH"]
    # clear old reports so this seed's mtimes aren't polluted by stale files
    for f in glob.glob(os.path.join(project, "target", "surefire-reports", "*")):
        os.remove(f)
    cmd = (
        "mvn -q test "
        f'"-Dtest={test_selector}" '
        "-Dsurefire.runOrder=random "
        f"-Dsurefire.runOrder.random.seed={seed}"
    )
    subprocess.run(cmd, cwd=project, env=env, capture_output=True, shell=True)


def read_order_and_outcome(project, od_class, od_method):
    reports_dir = os.path.join(project, "target", "surefire-reports")
    xmls = glob.glob(os.path.join(reports_dir, "TEST-*.xml"))
    entries = []
    for f in xmls:
        classname = os.path.basename(f)[len("TEST-"):-len(".xml")]
        mtime = os.path.getmtime(f)
        entries.append((mtime, classname, f))
    entries.sort(key=lambda e: e[0])
    order = [classname for _, classname, _ in entries]

    outcome = None
    for _, classname, f in entries:
        if classname == od_class:
            tree = ET.parse(f)
            for tc in tree.getroot().findall("testcase"):
                if tc.get("name") == od_method:
                    failed = tc.find("failure") is not None or tc.find("error") is not None
                    outcome = "fail" if failed else "pass"
    return order, outcome


def parse_seeds(spec):
    if "-" in spec:
        lo, hi = spec.split("-")
        return list(range(int(lo), int(hi) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--java-home", required=True)
    ap.add_argument("--seeds", required=True, help="e.g. 1-20 or 1,2,3")
    ap.add_argument("--od-class", required=True)
    ap.add_argument("--od-method", required=True)
    ap.add_argument("--suite-file", required=True, help="suite-tests.txt, one Class#method per line")
    ap.add_argument("--split-classes", default="", help="comma-separated simple class names to explode into individual methods")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    split = set(args.split_classes.split(",")) if args.split_classes else set()
    with open(args.suite_file) as f:
        all_tests = [line.strip() for line in f if line.strip()]

    by_class = {}
    for t in all_tests:
        cls, method = t.split("#")
        by_class.setdefault(cls, []).append(method)

    selectors = []
    for cls, methods in by_class.items():
        simple = cls.rsplit(".", 1)[-1]
        if simple in split:
            for m in methods:
                selectors.append(f"{simple}#{m}")
        else:
            selectors.append(simple)
    test_selector = ",".join(selectors)
    print(f"{len(selectors)} selectors, {sum(len(m) for m in by_class.values())} total methods", file=sys.stderr)

    seeds = parse_seeds(args.seeds)
    rows = []
    for seed in seeds:
        run_one_seed(args.project, args.java_home, seed, test_selector)
        order, outcome = read_order_and_outcome(args.project, args.od_class, args.od_method)
        before = order[: order.index(args.od_class)] if args.od_class in order else order
        rows.append({
            "seed": seed,
            "outcome": outcome,
            "n_classes_total": len(order),
            "n_before_od": len(before),
            "before_od": "|".join(before),
        })
        print(f"seed {seed}: outcome={outcome}, {len(before)} classes before OD test", file=sys.stderr)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["seed", "outcome", "n_classes_total", "n_before_od", "before_od"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()

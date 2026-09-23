"""Delta-debugging baseline (Module 5, Step 19), our own implementation per
the plan's fallback since iFixFlakies' MinimizerPlugin needs an undocumented
JSON schema from a separate dependency not worth chasing. Classic split-in-half,
test, recurse-into-the-failing-half search, run for real against marine-api.
"""
import argparse
import os
import subprocess
import time


def run_pair(project, java_home, candidates, od_selector, run_order="reversealphabetical"):
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env["PATH"]
    selector = ",".join(candidates + [od_selector])
    cmd = f'mvn -q test "-Dtest={selector}" "-Dsurefire.runOrder={run_order}"'
    t0 = time.time()
    result = subprocess.run(cmd, cwd=project, env=env, capture_output=True, shell=True)
    elapsed = time.time() - t0
    return result.returncode != 0, elapsed  # non-zero exit = a test failed


def delta_debug(project, java_home, prefix, od_selector, log):
    invocations = 0
    total_time = 0.0
    candidates = list(prefix)
    while len(candidates) > 1:
        mid = len(candidates) // 2
        half_a, half_b = candidates[:mid], candidates[mid:]
        failed, elapsed = run_pair(project, java_home, half_a, od_selector)
        invocations += 1
        total_time += elapsed
        log.append((list(half_a), failed, elapsed))
        if failed:
            candidates = half_a
            continue
        failed, elapsed = run_pair(project, java_home, half_b, od_selector)
        invocations += 1
        total_time += elapsed
        log.append((list(half_b), failed, elapsed))
        if failed:
            candidates = half_b
            continue
        # neither half alone reproduces: the paper's simplified version
        # (and the plan's own description) stops here rather than trying
        # complement sets; report the last-known-failing full prefix.
        return candidates, invocations, total_time, "neither-half-failed"
    return candidates, invocations, total_time, "converged"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--java-home", required=True)
    ap.add_argument("--prefix", required=True, help="comma-separated Class or Class#method selectors, execution order")
    ap.add_argument("--od-selector", required=True)
    args = ap.parse_args()

    prefix = args.prefix.split(",")
    log = []
    result, n, total_time, status = delta_debug(args.project, args.java_home, prefix, args.od_selector, log)

    print(f"starting prefix ({len(prefix)}): {prefix}")
    for candidates, failed, elapsed in log:
        print(f"  tested {candidates} -> {'FAIL' if failed else 'pass'} ({elapsed:.1f}s)")
    print(f"result: {result}, status={status}")
    print(f"invocations={n}, total_time={total_time:.1f}s")


if __name__ == "__main__":
    main()

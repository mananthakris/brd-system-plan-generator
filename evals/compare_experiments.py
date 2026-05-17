"""Compare two experiment score snapshots side-by-side.

Each snapshot is a JSON file saved by run_experiments.py to evals/results/.
The comparison shows per-agent score deltas and which prompt versions changed.

Usage:
    venv/bin/python -m evals.compare_experiments \\
        --baseline  evals/results/experiment_20240101_100000.json \\
        --candidate evals/results/experiment_20240101_110000.json

    # Or compare the two most recent snapshots automatically:
    venv/bin/python -m evals.compare_experiments --latest

Improvement workflow:
    1. Run baseline:   venv/bin/python -m evals.run_experiments
    2. Edit a prompt in prompts/registry.py and bump its version
    3. Re-run:         venv/bin/python -m evals.run_golden_brds && venv/bin/python -m evals.run_experiments
    4. Compare:        venv/bin/python -m evals.compare_experiments --latest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

PASS_THRESHOLD = 0.70
COL_AGENT = 28
COL_EVAL = 24


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        # Allow passing just the filename stem
        p = RESULTS_DIR / path
        if not p.exists():
            p = RESULTS_DIR / f"{path}.json"
    if not p.exists():
        print(f"ERROR: snapshot not found: {path}")
        sys.exit(1)
    return json.loads(p.read_text())


def _two_latest() -> tuple[Path, Path]:
    snapshots = sorted(RESULTS_DIR.glob("experiment_*.json"))
    if len(snapshots) < 2:
        print(f"ERROR: need at least 2 snapshots in {RESULTS_DIR}. Run venv/bin/python -m evals.run_experiments twice.")
        sys.exit(1)
    return snapshots[-2], snapshots[-1]


def _fmt_delta(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.4f}"


def _marker(delta: float) -> str:
    if delta > 0.01:
        return "✓"
    if delta < -0.01:
        return "✗"
    return "~"


def compare(baseline: dict, candidate: dict) -> None:
    b_name = baseline["experiment_name"]
    c_name = candidate["experiment_name"]
    b_ts = baseline["timestamp"][:16]
    c_ts = candidate["timestamp"][:16]

    print()
    print("=" * 80)
    print("  EXPERIMENT COMPARISON")
    print("=" * 80)
    print(f"  Baseline:  {b_name}  ({b_ts})")
    print(f"  Candidate: {c_name}  ({c_ts})")

    # Prompt version diff
    b_versions = baseline.get("prompt_versions", {})
    c_versions = candidate.get("prompt_versions", {})
    all_agents = sorted(set(b_versions) | set(c_versions))
    changed = [a for a in all_agents if b_versions.get(a) != c_versions.get(a)]

    print()
    print("  Prompt versions:")
    for agent in all_agents:
        bv = b_versions.get(agent, "—")
        cv = c_versions.get(agent, "—")
        tag = "  ← changed" if agent in changed else ""
        print(f"    {agent:<30} {bv:>7}  →  {cv:<7}{tag}")

    if not changed:
        print("    (no prompt version changes between these two runs)")

    # Score comparison table
    b_scores = baseline.get("scores", {})
    c_scores = candidate.get("scores", {})
    score_agents = sorted(set(b_scores) | set(c_scores))

    print()
    header = (
        f"  {'Agent':<{COL_AGENT}} {'Evaluator':<{COL_EVAL}} "
        f"{'Baseline':>9} {'Candidate':>9} {'Delta':>8}   "
    )
    print(header)
    print("  " + "─" * (len(header) - 2))

    total_delta = 0.0
    total_count = 0

    for agent in score_agents:
        bs = b_scores.get(agent, {})
        cs = c_scores.get(agent, {})
        all_evals = sorted(set(bs) | set(cs))
        for ev in all_evals:
            bval = bs.get(ev)
            cval = cs.get(ev)
            if bval is None or cval is None:
                continue
            delta = cval - bval
            total_delta += delta
            total_count += 1
            marker = _marker(delta)
            print(
                f"  {agent:<{COL_AGENT}} {ev:<{COL_EVAL}} "
                f"{bval:>9.4f} {cval:>9.4f} {_fmt_delta(delta):>8}  {marker}"
            )

    print("  " + "─" * (len(header) - 2))
    if total_count:
        avg_delta = total_delta / total_count
        overall_marker = _marker(avg_delta)
        print(
            f"  {'OVERALL AVERAGE':<{COL_AGENT + COL_EVAL + 1}} "
            f"{'':>9} {'':>9} {_fmt_delta(avg_delta):>8}  {overall_marker}"
        )

    print()

    # Verdict
    if changed:
        if total_count and total_delta > 0:
            print("  VERDICT: Scores improved after prompt change(s). Safe to ship.")
        elif total_count and total_delta < -0.02:
            print("  VERDICT: Scores regressed. Review the changes before shipping.")
        else:
            print("  VERDICT: Negligible score change. Consider whether the prompt edit was meaningful.")
    else:
        print("  VERDICT: No prompt version changes detected. This comparison shows run-to-run variance.")

    print(f"\n  LLM quality scores (llm_quality evaluator): see Phoenix UI → {RESULTS_DIR.parent.parent.name}")
    print("  → Datasets & Experiments → golden_brd_evals → Experiments tab")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two experiment score snapshots from evals/results/."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="Compare the two most recent snapshots")
    group.add_argument("--baseline", metavar="FILE", help="Path or filename of the baseline snapshot")
    parser.add_argument("--candidate", metavar="FILE", help="Path or filename of the candidate snapshot (required with --baseline)")
    args = parser.parse_args()

    if args.latest:
        b_path, c_path = _two_latest()
        baseline = json.loads(b_path.read_text())
        candidate = json.loads(c_path.read_text())
        print(f"Comparing:\n  baseline:  {b_path.name}\n  candidate: {c_path.name}")
    else:
        if not args.candidate:
            parser.error("--candidate is required when using --baseline")
        baseline = _load(args.baseline)
        candidate = _load(args.candidate)

    compare(baseline, candidate)


if __name__ == "__main__":
    main()

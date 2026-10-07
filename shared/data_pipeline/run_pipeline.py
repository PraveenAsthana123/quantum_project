"""
run_pipeline.py — Master Orchestrator
=======================================
Runs all 7 steps in sequence with progress reporting,
timing per step, and a final comparison table.

Usage:
    python run_pipeline.py              # run all steps
    python run_pipeline.py --steps 1,2  # run specific steps only
    python run_pipeline.py --skip 6     # skip heavy quantum step
"""

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
PIPELINE_DIR = os.path.dirname(__file__)

STEPS = [
    (1, "step1_generate_data",    "Generate 1000×1000 synthetic dataset"),
    (2, "step2_clean",            "Data cleaning (dedup, nulls, outliers, encode)"),
    (3, "step3_normalize",        "Normalize / scale features"),
    (4, "step4_feature_reduction","Feature reduction (corr, var, kbest, PCA)"),
    (5, "step5_classical_ml",     "Classical ML baseline (LR, RF, XGB, SVC, Stack)"),
    (6, "step6_quantum_vqc",      "Quantum VQC (4-qubit PennyLane)"),
    (7, "step7_compare",          "Classical vs. Quantum comparison"),
]


# ── Progress bar ──────────────────────────────────────────────────────────────

def progress_bar(current: int, total: int, width: int = 30) -> str:
    filled = int(width * current / max(total, 1))
    bar    = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{total}"


# ── Dynamic module loader ─────────────────────────────────────────────────────

def load_module(module_name: str):
    """Load a pipeline step module from the same directory."""
    path = os.path.join(PIPELINE_DIR, f"{module_name}.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Step script not found: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Final summary ─────────────────────────────────────────────────────────────

def print_final_summary(step_timings: list, step_errors: list):
    """Print a concise pipeline summary with timings and errors."""
    comparison_path = os.path.join(DATA_DIR, "comparison_report.json")

    print("\n" + "=" * 62)
    print("  PIPELINE RUN SUMMARY")
    print("=" * 62)
    fmt = "{:<5} {:<42} {:>6} {:>6}"
    print(fmt.format("Step", "Description", "Time", "Status"))
    print("-" * 62)

    total_time = 0.0
    for step_num, desc, elapsed, error in step_timings:
        status = "OK" if error is None else "FAIL"
        print(fmt.format(
            f"#{step_num}",
            desc[:42],
            f"{elapsed:.1f}s",
            status
        ))
        total_time += elapsed

    print("-" * 62)
    print(fmt.format("", "TOTAL", f"{total_time:.1f}s", ""))

    # Errors
    errors = [(s, e) for (s, _, _, e) in step_timings if e is not None]
    if errors:
        print(f"\n  {len(errors)} step(s) failed:")
        for step_num, err in errors:
            print(f"    Step #{step_num}: {err}")

    # Comparison table (if step 7 ran)
    if os.path.exists(comparison_path):
        try:
            with open(comparison_path) as f:
                rep = json.load(f)
            print("\n" + "=" * 62)
            print("  CLASSICAL vs. QUANTUM RESULTS")
            print("=" * 62)
            print(f"  Classical best  : {rep['classical_best_model']}")
            print(f"    Accuracy: {rep['classical_best_accuracy']:.4f}  "
                  f"AUC: {rep['classical_best_auc']:.4f}  "
                  f"F1: {rep['classical_best_f1']:.4f}")
            print(f"  Quantum VQC     : {rep['quantum_model']}")
            print(f"    Accuracy: {rep['quantum_accuracy']:.4f}  "
                  f"AUC: {rep['quantum_auc']:.4f}  "
                  f"F1: {rep['quantum_f1']:.4f}")
            print(f"  Accuracy gap    : {rep['gap_pct']:+.2f}%")
            print(f"  Quantum advantage? {rep['quantum_advantage']}")
            print(f"  Recommended     : {rep['recommended_approach'].upper()}")

            print("\n  Top quantum advantage use cases:")
            for i, s in enumerate(rep.get("quantum_advantage_scenarios", [])[:3], 1):
                print(f"    {i}. {s['scenario']}")
        except Exception as e:
            print(f"  (Could not load comparison report: {e})")

    print("=" * 62 + "\n")


# ── Run a single step ─────────────────────────────────────────────────────────

def run_step(step_num: int, module_name: str, description: str,
             step_index: int, total_steps: int) -> tuple[float, Exception | None]:
    """Load and execute a step's main() function."""
    bar = progress_bar(step_index, total_steps)
    print(f"\n{bar}")
    print(f"Step #{step_num}: {description}")
    print("-" * 60)

    t0 = time.time()
    error = None
    try:
        mod = load_module(module_name)
        mod.main()
    except Exception as e:
        error = e
        print(f"\n  ERROR in step #{step_num}: {e}")
        traceback.print_exc()

    elapsed = time.time() - t0
    status = "COMPLETE" if error is None else "FAILED"
    print(f"  Step #{step_num} {status} in {elapsed:.1f}s")
    return elapsed, error


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Quantum Data Pipeline — Master Orchestrator"
    )
    parser.add_argument(
        "--steps", type=str, default=None,
        help="Comma-separated list of step numbers to run (e.g. '1,2,3'). "
             "Default: all steps."
    )
    parser.add_argument(
        "--skip", type=str, default=None,
        help="Comma-separated list of step numbers to skip (e.g. '6')."
    )
    parser.add_argument(
        "--stop-on-error", action="store_true",
        help="Halt pipeline on first step failure (default: continue)."
    )
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    os.makedirs(DATA_DIR, exist_ok=True)

    # Determine which steps to run
    all_step_nums = [s[0] for s in STEPS]
    if args.steps:
        run_nums = {int(x.strip()) for x in args.steps.split(",")}
    else:
        run_nums = set(all_step_nums)
    if args.skip:
        skip_nums = {int(x.strip()) for x in args.skip.split(",")}
        run_nums -= skip_nums

    steps_to_run = [s for s in STEPS if s[0] in run_nums]
    total = len(steps_to_run)

    print("\n" + "=" * 62)
    print("  QUANTUM DATA PIPELINE — CLASSICAL → QUANTUM ML")
    print("=" * 62)
    print(f"  Steps to run: {sorted(run_nums)}")
    print(f"  Data directory: {DATA_DIR}")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    step_timings = []
    for idx, (step_num, module_name, description) in enumerate(steps_to_run, start=1):
        elapsed, error = run_step(step_num, module_name, description, idx, total)
        step_timings.append((step_num, description, elapsed, error))

        if error is not None and args.stop_on_error:
            print(f"\n  --stop-on-error set; halting after step #{step_num}.")
            break

    # Final progress bar (complete)
    bar = progress_bar(total, total)
    print(f"\n{bar}")

    print_final_summary(step_timings, step_timings)
    return 0 if all(e is None for _, _, _, e in step_timings) else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Step 5: Classical ML Baseline
==============================
Loads features_8.csv (8 features matching 8-qubit quantum comparison).

Models trained:
  a) LogisticRegression
  b) RandomForestClassifier (n_estimators=200, class_weight='balanced')
  c) XGBClassifier  (or GradientBoostingClassifier as fallback)
  d) SVC (kernel='rbf', probability=True)
  e) StackingClassifier (a+b+c+d → LogisticRegression meta-learner)

Outputs:
  data/classical_results.json
"""

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import (GradientBoostingClassifier, RandomForestClassifier,
                               StackingClassifier)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                              precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE  = os.path.join(DATA_DIR, "features_8.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "classical_results.json")

LABEL_COL  = "label"
RANDOM_SEED = 42
TEST_SIZE   = 0.15
VAL_SIZE    = 0.15   # fraction of total


# ── Metrics helper ────────────────────────────────────────────────────────────

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """Return a metrics dict given true labels, predictions, and probabilities."""
    cm = confusion_matrix(y_true, y_pred).tolist()
    return {
        "accuracy"        : round(float(accuracy_score(y_true, y_pred)), 4),
        "auc"             : round(float(roc_auc_score(y_true, y_prob)), 4),
        "f1"              : round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision"       : round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall"          : round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "confusion_matrix": cm,
    }


def train_and_evaluate(name: str, model, X_train, y_train,
                       X_val, y_val, X_test, y_test) -> dict:
    """Fit model, evaluate on val and test, return results dict."""
    print(f"  Training {name}...")
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - t0

    results = {"model": name, "training_time_s": round(train_time, 2)}

    for split_name, X_s, y_s in [("val", X_val, y_val), ("test", X_test, y_test)]:
        y_pred = model.predict(X_s)
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_s)[:, 1]
        else:
            y_prob = model.decision_function(X_s)
            # Normalise to [0,1] for AUC
            y_prob = (y_prob - y_prob.min()) / (y_prob.max() - y_prob.min() + 1e-9)

        metrics = compute_metrics(y_s, y_pred, y_prob)
        results[split_name] = metrics
        print(f"    [{split_name}] acc={metrics['accuracy']:.4f}  "
              f"auc={metrics['auc']:.4f}  f1={metrics['f1']:.4f}")

    results["training_time_s"] = round(train_time, 2)
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0_total = time.time()
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 5: Classical ML Baseline")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run step4_feature_reduction.py first."
        )

    print(f"  Loading {INPUT_FILE} ...")
    df = pd.read_csv(INPUT_FILE)
    print(f"  Loaded: {df.shape[0]} rows × {df.shape[1]} cols")

    X = df.drop(columns=[LABEL_COL]).values
    y = df[LABEL_COL].values
    feature_names = df.drop(columns=[LABEL_COL]).columns.tolist()

    # ── Stratified split: 70 / 15 / 15 ────────────────────────────────────
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
    )
    val_fraction = VAL_SIZE / (1 - TEST_SIZE)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val,
        test_size=val_fraction, random_state=RANDOM_SEED, stratify=y_train_val
    )
    print(f"  Split → train={len(X_train)}  val={len(X_val)}  test={len(X_test)}")
    print(f"  Class balance (train) → 0:{(y_train==0).sum()}  1:{(y_train==1).sum()}")

    # ── Build models ────────────────────────────────────────────────────────
    lr  = LogisticRegression(max_iter=1000, class_weight="balanced",
                             random_state=RANDOM_SEED, solver="lbfgs")
    rf  = RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                 random_state=RANDOM_SEED, n_jobs=-1)

    try:
        from xgboost import XGBClassifier
        scale_pos = int((y_train == 0).sum()) / max(int((y_train == 1).sum()), 1)
        boost = XGBClassifier(n_estimators=200, scale_pos_weight=scale_pos,
                              random_state=RANDOM_SEED, eval_metric="logloss",
                              use_label_encoder=False, verbosity=0)
        boost_name = "XGBClassifier"
    except ImportError:
        boost = GradientBoostingClassifier(n_estimators=200, random_state=RANDOM_SEED)
        boost_name = "GradientBoostingClassifier"
        print(f"  XGBoost not installed; using {boost_name}.")

    svc = SVC(kernel="rbf", probability=True, class_weight="balanced",
              random_state=RANDOM_SEED)

    stack = StackingClassifier(
        estimators=[
            ("lr",    LogisticRegression(max_iter=500, class_weight="balanced",
                                         random_state=RANDOM_SEED)),
            ("rf",    RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                              random_state=RANDOM_SEED, n_jobs=-1)),
            ("boost", GradientBoostingClassifier(n_estimators=100,
                                                  random_state=RANDOM_SEED)),
            ("svc",   SVC(kernel="rbf", probability=True, class_weight="balanced",
                          random_state=RANDOM_SEED)),
        ],
        final_estimator=LogisticRegression(max_iter=500, random_state=RANDOM_SEED),
        cv=3,
        n_jobs=-1,
    )

    model_defs = [
        ("LogisticRegression", lr),
        ("RandomForestClassifier", rf),
        (boost_name, boost),
        ("SVC_rbf", svc),
        ("StackingClassifier", stack),
    ]

    # ── Train & evaluate ────────────────────────────────────────────────────
    all_results = []
    for name, model in model_defs:
        res = train_and_evaluate(name, model,
                                 X_train, y_train,
                                 X_val,   y_val,
                                 X_test,  y_test)
        all_results.append(res)

    # ── Find best model by test AUC ─────────────────────────────────────────
    best = max(all_results, key=lambda r: r["test"]["auc"])
    print(f"\n  Best model (test AUC): {best['model']}  "
          f"AUC={best['test']['auc']:.4f}  "
          f"acc={best['test']['accuracy']:.4f}")

    # ── Save ────────────────────────────────────────────────────────────────
    output = {
        "dataset"         : "features_8.csv",
        "n_features"      : len(feature_names),
        "feature_names"   : feature_names,
        "n_train"         : len(X_train),
        "n_val"           : len(X_val),
        "n_test"          : len(X_test),
        "best_model"      : best["model"],
        "best_test_auc"   : best["test"]["auc"],
        "best_test_accuracy": best["test"]["accuracy"],
        "models"          : all_results,
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    elapsed = time.time() - t0_total
    print(f"  Results saved → {OUTPUT_JSON}")
    print(f"  Total elapsed: {elapsed:.1f}s")
    print("  STEP 5 COMPLETE\n")


if __name__ == "__main__":
    main()

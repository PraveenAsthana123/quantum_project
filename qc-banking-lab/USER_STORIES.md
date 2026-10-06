# QC Banking Lab — User Stories

Version: 1.0.0 | Date: 2026-10-06 | Lab: qc-banking-lab

---

## US-001: Real-Time Fraud Screening

**As a** fraud analyst
**I want** to score incoming credit card transactions against a pre-trained quantum-enhanced fraud model
**so that** I can flag suspicious transactions before settlement and reduce false-negative write-offs.

**Acceptance criteria:**
- Model inference completes within 200 ms per transaction on lab hardware.
- Fraud recall (sensitivity) is at least 0.80 on the held-out test set.
- Every decision includes a confidence score and the top-3 feature contributions.
- All predictions are logged with timestamp, transaction ID, and model version.

**Demo:**
1. Run `python src/demo.py` — observe Step 5 quantum inference on 100-sample subset completing in under 60 s.
2. Inspect the comparison table in Step 6 to confirm quantum recall is competitive with classical RandomForest.

---

## US-002: Classical vs Quantum Accuracy Benchmark

**As a** quant researcher
**I want** to compare LogisticRegression, RandomForest, XGBoost, and VQC side-by-side on the same fraud dataset
**so that** I can quantify where quantum advantage appears and publish reproducible benchmark numbers.

**Acceptance criteria:**
- All four models are evaluated on the identical 80/20 stratified split.
- Metrics reported: accuracy, F1, ROC-AUC, and inference time in ms.
- Seed 42 is used throughout so results are bit-for-bit reproducible.
- Results are emitted as a formatted comparison table to stdout.

**Demo:**
1. Run `python src/demo.py` — Step 4 trains all classical models, Step 5 runs VQC.
2. Step 6 prints the aligned comparison table; copy to a notebook for further analysis.

---

## US-003: Synthetic Dataset Generation

**As a** data scientist
**I want** to generate a privacy-safe synthetic credit card fraud dataset that matches Kaggle statistics
**so that** I can run experiments in environments where real cardholder data cannot be used.

**Acceptance criteria:**
- Generated CSV has exactly 10,000 rows with columns Time, V1–V28, Amount, Class.
- Fraud rate is 1.5 %–2.0 % (matching Kaggle ~1.7 %).
- V-features for fraud class have statistically significant shifts in V1, V4, V11, V14, V17 (verified by t-test, p < 0.01).
- File is reproducible: re-running with seed=42 produces a byte-identical CSV.
- Output printed to console: rows generated, fraud count, fraud rate, file size.

**Demo:**
1. Run `python src/generate_data.py`.
2. Check `data/creditcard_synthetic.csv` — open in pandas and confirm `df["Class"].mean() ≈ 0.017`.

---

## US-004: CISO Risk Dashboard Input

**As a** CISO
**I want** the demo pipeline to export a JSON result file with model performance, fraud rate, and threshold metadata
**so that** I can feed it into the enterprise risk dashboard without manual transcription.

**Acceptance criteria:**
- `data/quantum_results.json` and `data/classical_results.json` are both populated after a full run.
- JSON schema is consistent across runs (no missing keys on partial failures).
- Results include model name, accuracy, F1, ROC-AUC, train time, and prediction time.
- Any model failure is logged as `{"status": "error", "message": "..."}` rather than crashing the pipeline.

**Demo:**
1. Run `python src/quantum_fraud.py` — observe `data/quantum_results.json` written.
2. Run `python src/classical_baseline.py` — observe `data/classical_results.json` written.
3. Inspect both files with `python -c "import json; print(json.load(open('data/quantum_results.json')).keys())"`.

---

## US-005: Compliance Audit Trail

**As a** compliance officer
**I want** every model training run to record the data source, preprocessing steps, model hyperparameters, and evaluation date
**so that** I can reconstruct any historical fraud decision for regulatory audit.

**Acceptance criteria:**
- Result JSON files include a `generated_at` ISO-8601 timestamp.
- Hyperparameters (n_qubits, n_layers, epochs, random_state) are stored alongside metrics.
- The preprocessing pipeline (scaler type, PCA components) is documented in the result file.
- Re-running with the same seed reproduces identical metrics (± floating-point tolerance).

**Demo:**
1. Run `python src/quantum_fraud.py` twice; diff the two `quantum_results.json` files — metrics are identical, only `generated_at` differs.

---

## US-006: Risk Manager Threshold Tuning

**As a** risk manager
**I want** to adjust the classification threshold (default 0.5) to trade off precision and recall
**so that** I can tune the fraud catch rate against the customer false-positive complaint rate.

**Acceptance criteria:**
- `quantum_fraud.py` exposes a `predict(weights, X, threshold=0.5)` signature.
- Lowering the threshold to 0.3 increases recall by at least 5 percentage points on the test set.
- The comparison table in `demo.py` shows metrics at the default threshold (0.5).
- A `--threshold` CLI argument will be implemented in a future sprint (documented as backlog item).

**Demo:**
1. In a Python shell: `from src.quantum_fraud import predict, train, load_balanced_subset`.
2. Compare `predict(weights, X_test, threshold=0.5)` vs `predict(weights, X_test, threshold=0.3)` on held-out set.

---

## US-007: Portfolio Optimisation Comparison

**As a** quant researcher
**I want** to benchmark quantum portfolio optimisation (QAOA/VQE) against classical mean-variance optimisation
**so that** I can demonstrate where quantum algorithms offer Sharpe-ratio improvements in a portfolio context.

**Acceptance criteria:**
- `quantum_portfolio.py` completes without error for an 8-asset portfolio on the default device.
- Sharpe ratio and expected return are reported for both classical and quantum solutions.
- `portfolio_results.json` is written with both result sets.
- The quantum circuit depth is printed so hardware feasibility can be evaluated.

**Demo:**
1. Run `python src/quantum_portfolio.py`.
2. Inspect `data/portfolio_results.json` for `classical.sharpe` vs `quantum.sharpe`.

---

## US-008: Fraud Benchmark Regression Suite

**As a** data scientist
**I want** an automated benchmark script that re-runs all models and fails loudly if any metric regresses
**so that** I can gate model deployments on objective performance thresholds in CI.

**Acceptance criteria:**
- `src/fraud_benchmark.py` runs all models and exits with code 0 if all metrics pass and code 1 if any fail.
- PASS thresholds: accuracy > 0.85, F1 > 0.70, ROC-AUC > 0.90 for RandomForest and XGBoost.
- Thresholds are configurable via environment variables (`FRAUD_BENCH_ACC_THRESHOLD`, etc.).
- Results are saved to `data/benchmark_results.json` for CI artefact archiving.

**Demo:**
1. Run `python src/fraud_benchmark.py`.
2. Confirm exit code 0: `echo $?`.
3. Observe PASS/FAIL lines per model in stdout.

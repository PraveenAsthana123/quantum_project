# QC Healthcare Lab — User Stories

Version: 1.0.0 | Date: 2026-10-06 | Lab: qc-healthcare-lab

---

## US-001: Diabetes Risk Screening

**As a** clinician
**I want** to run a trained diabetes risk model on a new patient's biometric readings
**so that** I can flag high-risk patients for a confirmatory OGTT before they develop Type 2 diabetes.

**Acceptance criteria:**
- Model accepts the 8 Pima feature inputs (Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age).
- Prediction includes a risk probability (0–1), not just a binary label.
- Clinical sensitivity (recall for positive class) is at least 0.75 on the held-out test set.
- Inference completes within 500 ms for a single patient record.

**Demo:**
1. Run `python src/demo.py` — observe Step 4 RandomForest F1 and AUC values.
2. Confirm in Step 6 that all models pass the F1 > 0.65 gate.

---

## US-002: Data Scientist Model Evaluation

**As a** data scientist
**I want** to benchmark LogisticRegression, RandomForest, and VQC on the diabetes dataset using a reproducible pipeline
**so that** I can determine whether quantum classification offers a measurable advantage on small tabular healthcare data.

**Acceptance criteria:**
- All models are evaluated on the same 80/20 stratified split (seed=42).
- Metrics: accuracy, F1, ROC-AUC, inference time in ms.
- A formatted comparison table is printed to stdout.
- All results are reproducible: re-running produces identical metrics.

**Demo:**
1. Run `python src/demo.py` — Steps 4–6 print all metrics and the comparison table.

---

## US-003: Synthetic Patient Data Generation

**As a** data scientist
**I want** to generate a 2,000-row synthetic diabetes dataset based on Pima Indians statistics
**so that** I can run experiments in HIPAA-compliant environments where real patient data cannot leave the hospital network.

**Acceptance criteria:**
- Output CSV columns match the Pima Indians Diabetes Database exactly.
- Positive (diabetes) rate is 33 %–37 %.
- Zero-encoded missing values are present in Glucose, BloodPressure, SkinThickness, Insulin, BMI at a ~4 % rate.
- File is reproducible: re-running with seed=42 produces byte-identical output.
- Console output: rows generated, positive count, positive rate, file size.

**Demo:**
1. Run `python src/generate_data.py`.
2. Check `data/diabetes_synthetic.csv` — confirm `df["Outcome"].mean() ≈ 0.35`.

---

## US-004: Hospital Admin Quality Gate

**As a** hospital administrator
**I want** the demo pipeline to gate on F1 > 0.65 for every model and print a clear PASS/FAIL summary
**so that** I can enforce a minimum clinical quality bar before any model is submitted for ethics review.

**Acceptance criteria:**
- `demo.py` Step 6 prints PASS / FAIL per model with the observed F1 value.
- All classical models (LR, RF) achieve PASS with the provided synthetic data.
- The gate threshold (0.65) is documented in the demo docstring.
- A FAIL line is printed in red (future enhancement) to aid visual scanning of CI logs.

**Demo:**
1. Run `python src/demo.py` — observe "OVERALL: ALL MODELS PASS" in Step 6.

---

## US-005: Missing Data Imputation Audit

**As a** clinician
**I want** to inspect how many zero-encoded missing values exist per feature and how they are imputed
**so that** I can confirm the preprocessing does not introduce systematic bias before model training.

**Acceptance criteria:**
- `demo.py` Step 3 prints a before/after statistics table: column name, raw mean, raw std, missing count, post-imputation mean, post-imputation std.
- Imputation strategy (median) is documented in the demo docstring.
- Zero imputation is applied only to physiologically impossible columns (Glucose, BMI, BloodPressure, SkinThickness, Insulin).
- The table is aligned and readable in a standard 80-character terminal.

**Demo:**
1. Run `python src/demo.py` — Step 3 prints the before/after statistics table.

---

## US-006: Quantum Circuit Depth Assessment

**As a** data scientist
**I want** to view the VQC circuit parameters (n_qubits, n_layers, epochs) and final loss history
**so that** I can assess whether the circuit is shallow enough for near-term hardware deployment.

**Acceptance criteria:**
- `demo.py` Step 5 prints circuit configuration: n_qubits, n_layers, epochs.
- The loss history printed by `quantum_disease.py` training loop shows monotone decrease (± noise).
- Total VQC training time on CPU is reported in ms.
- The quantum result is included in the comparison table with accuracy, F1, AUC.

**Demo:**
1. Run `python src/demo.py` — observe Step 5 circuit info and loss trace.

---

## US-007: ECG Anomaly Detection Integration

**As a** clinician
**I want** the healthcare lab to include a quantum anomaly detector for ECG time-series signals
**so that** I can evaluate whether quantum kernels improve detection of rare arrhythmia patterns over classical SVM.

**Acceptance criteria:**
- `quantum_ecg.py` runs without error on the provided ECG data or synthetic fallback.
- Anomaly detection AUC is reported against a classical SVM baseline.
- Results are saved to `data/ecg_results.json`.
- Script completes in under 300 s on the local PennyLane simulator.

**Demo:**
1. Run `python src/quantum_ecg.py`.
2. Inspect `data/ecg_results.json` for `quantum_auc` vs `classical_svm_auc`.

---

## US-008: Multi-Disease Expansion Readiness

**As a** hospital administrator
**I want** the lab architecture to support adding new disease classifiers (heart disease, CKD) without restructuring the pipeline
**so that** the lab can grow to a multi-disease screening platform with minimal engineering effort.

**Acceptance criteria:**
- `quantum_disease.py` accepts a `--dataset` CLI argument selecting between `diabetes` and `heart` (UCI Heart Disease).
- A new dataset only requires adding a loader function; the VQC training loop and evaluation code are reused unchanged.
- Adding a new dataset does not break existing `demo.py` runs.
- This is documented as a backlog item pending UCI Heart Disease data download.

**Demo:**
1. Run `python src/demo.py` — confirm diabetes pipeline completes.
2. Open `src/quantum_disease.py` — review `_find_csv()` to confirm the multi-dataset loading pattern.

# QC Healthcare Lab — Quantum Disease Classification & ECG Anomaly Detection

## Overview

Applies quantum machine learning to healthcare prediction problems: disease classification
(diabetes, heart disease, heart failure) and ECG arrhythmia detection from time-series
signals. Implements a Variational Quantum Classifier (VQC) for disease prediction and a
Quantum Kernel SVM using the ZZFeatureMap for ECG anomaly detection, with full classical
baselines (Logistic Regression, Random Forest, XGBoost) for honest benchmarking.

This lab demonstrates where quantum methods are competitive and where they are not — the
honest assessment that healthcare quantum architects need to present to clinical and
regulatory stakeholders.

## Roles Demonstrated

Quantum ML Engineer · Healthcare AI Architect · Hybrid Classical-Quantum Architect ·
Clinical Data Science Architect · Quantum Algorithm Engineer

---

## Use Cases

| # | Use Case | Algorithm | Dataset | Task |
|---|---|---|---|---|
| 1 | Classical Baseline | LR + RF + XGBoost | Diabetes, Heart Disease, Heart Failure | Binary prediction |
| 2 | Disease Classification | VQC (PennyLane, angle encoding, 4q) | Pima Diabetes, Heart Disease UCI | Binary classification |
| 3 | ECG Anomaly Detection | Quantum Kernel SVM (ZZFeatureMap) | MIT-BIH Arrhythmia (87,554 rows) | Normal vs abnormal beat |
| 4 | ECG Fallback | PennyLane VQC | Same | Used if Qiskit unavailable |

---

## Datasets

| Dataset | Rows | Features | Task | Path |
|---|---|---|---|---|
| Pima Indians Diabetes | 768 | 8 | Binary (diabetic/not) | `datasets/healthcare/diabetes.csv` |
| Heart Disease UCI (Cleveland-style) | 918 | 11 | Binary (disease/not) | `datasets/healthcare/heart.csv` |
| Heart Failure Clinical Records | 299 | 12 | Binary (death event) | `datasets/healthcare/heart_failure_clinical_records_dataset.csv` |
| MIT-BIH Arrhythmia (train) | 87,554 | 187 (time steps) | 5-class → binary (normal/abnormal) | `datasets/healthcare/mitbih_train.csv` |
| MIT-BIH Arrhythmia (test) | 21,892 | 187 (time steps) | 5-class → binary | `datasets/healthcare/mitbih_test.csv` |
| PTB-DB Normal ECG | — | 187 | Binary | `datasets/healthcare/ptbdb_normal.csv` |
| PTB-DB Abnormal ECG | — | 187 | Binary | `datasets/healthcare/ptbdb_abnormal.csv` |

Data path resolution: project-local `data/` first, then `/mnt/deepa/quantum/datasets/healthcare/`.

---

## Quantum Architecture

### VQC — Disease Classification (`src/quantum_disease.py`)

```
Disease Dataset (768–918 rows, 8–11 features)
        |
        v
[Classical Preprocessing]
  - StandardScaler on all features
  - PCA → 4 principal components
  - Balanced train/test split
        |
        v
[Quantum Encoding]
  Wire 0: RY(feature[0])
  Wire 1: RY(feature[1])
  Wire 2: RY(feature[2])
  Wire 3: RY(feature[3])
        |
        v
[Variational Ansatz — 2 layers]
  Layer k: RY(w[k,i]) + RZ(w[k,i+1]) per qubit
           CNOT ring: 0→1, 1→2, 2→3, 3→0
        |
        v
[Measurement]
  Expectation <Z> on qubit 0
  Binary threshold: positive → disease, negative → no disease
        |
        v
[Optimizer: JAX Adam, lr=0.01, 50 epochs]
```

**Spec:** 4 qubits, 2 layers, 16 parameters, PennyLane `default.qubit` (statevector)

### Quantum Kernel SVM — ECG Anomaly Detection (`src/quantum_ecg.py`)

```
MIT-BIH ECG (87,554 train rows, 187 time-step features)
        |
        v
[Classical Preprocessing]
  - Balance classes (normal/abnormal)
  - StandardScaler
  - PCA → 4 components
  - Subsample for kernel computation (tractable)
        |
        v
[Quantum Feature Map: ZZFeatureMap (Qiskit)]
  Reps: 2
  Qubits: 4
  Entanglement: full ZZ
  |φ(x)⟩ = U_ZZ(x)|0⟩^⊗4
        |
        v
[Fidelity Kernel Matrix]
  K(xi, xj) = |⟨φ(xi)|φ(xj)⟩|²
  (inner product in 2⁴-dimensional Hilbert space)
        |
        v
[Classical SVM]
  RBF fallback if quantum kernel intractable
  Classify: normal (0) vs abnormal (1)
```

---

## Benchmark Results

Classical baseline results are written to `data/classical_results.json` after running
`src/classical_baseline.py`. The table below shows expected ranges based on these datasets
in the literature; update with actual run outputs.

### Disease Prediction (Literature Reference Ranges)

| Model | Diabetes AUC | Heart Disease AUC | Notes |
|---|---|---|---|
| Logistic Regression | ~0.83 | ~0.88 | Baseline |
| Random Forest | ~0.87 | ~0.92 | Strong classical |
| XGBoost | ~0.88 | ~0.93 | Best classical |
| VQC (4q, 2L) | ~0.70–0.80 | ~0.75–0.85 | NISQ expected range |

**Note:** Run `python src/classical_baseline.py` and `python src/quantum_disease.py` to
produce real numbers in `data/classical_results.json` and `data/quantum_results.json`.

### ECG Anomaly Detection (MIT-BIH — Literature Reference Ranges)

| Model | Accuracy | F1 (abnormal) | Notes |
|---|---|---|---|
| XGBoost (full 187 features) | ~98% | ~0.96 | Classical SOTA on tabular ECG |
| Classical SVM (PCA-4) | ~85–90% | ~0.82–0.88 | Reduced features |
| Quantum Kernel SVM (4q) | ~80–88% | ~0.75–0.85 | Competitive at 4 features |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Quantum ML | PennyLane 0.45+, JAX (jax_enable_x64) |
| Quantum Kernel | Qiskit 2.0+, ZZFeatureMap, FidelityQuantumKernel |
| Classical ML | scikit-learn (LR, RF, SVM), XGBoost |
| Data | pandas, numpy, scikit-learn preprocessing |
| Portal UI | Next.js 14, TypeScript, Tailwind CSS |
| Visualization | D3.js (circuit diagram), Recharts (metrics) |
| Environment | Python 3.11, `/mnt/deepa/quantum/venvs/quantum/` |

---

## Project Structure

```
qc-healthcare-lab/
├── src/
│   ├── classical_baseline.py   # LR + RF + XGBoost on all 3 disease datasets
│   ├── quantum_disease.py      # VQC (PennyLane) — diabetes + heart disease
│   └── quantum_ecg.py          # Quantum Kernel SVM (Qiskit ZZFeatureMap) — MIT-BIH
├── data/
│   ├── classical_results.json  # Written by classical_baseline.py (run to populate)
│   ├── quantum_results.json    # Written by quantum_disease.py (run to populate)
│   └── ecg_results.json        # Written by quantum_ecg.py (run to populate)
├── notebooks/                  # Jupyter exploration notebooks
├── tests/                      # Unit and integration tests
└── requirements.txt
```

---

## How to Run

```bash
source /mnt/deepa/quantum/venvs/quantum/bin/activate
cd /mnt/deepa/quantum/qc-healthcare-lab

# 1. Classical baseline — all 3 disease datasets (~30 seconds)
python src/classical_baseline.py
# Output: data/classical_results.json

# 2. Quantum VQC — disease classification (~5–10 minutes)
python src/quantum_disease.py
# Output: data/quantum_results.json

# 3. Quantum Kernel SVM — ECG anomaly (~5–15 minutes depending on subsample)
python src/quantum_ecg.py
# Output: data/ecg_results.json
```

---

## NISQ-Era Honest Assessment

| Claim | Reality |
|---|---|
| VQC competitive on disease datasets | Partial — AUC ~0.75–0.85 vs classical ~0.88–0.93 |
| Quantum kernel SVM on ECG | Competitive with classical SVM at PCA-4 features |
| Quantum advantage over XGBoost today | No — classical ensembles dominate tabular medical data |
| Clinical deployment readiness | No — NISQ accuracy gaps require fault-tolerant hardware |
| Quantum advantage pathway | High-dimensional kernel estimation; genomics feature spaces |

---

## Clinical Safety Note

All models in this lab are research demonstrations. No output should be used for clinical
decision-making. Datasets are public research benchmarks (Pima/UCI/PhysioNet), not patient
data. Any production healthcare AI deployment requires regulatory approval (FDA 510(k), CE-MDR),
clinical validation, and human oversight.

---

## CLI (qlab)

```bash
qlab info  qc-healthcare-lab    # Project details and status
qlab setup qc-healthcare-lab    # Install requirements
qlab data  qc-healthcare-lab    # Download healthcare datasets
qlab run   qc-healthcare-lab    # Launch portal UI
```

---

## References

- Pima Diabetes: https://www.kaggle.com/datasets/uciml/pima-indians-diabetes-database
- Heart Disease UCI: https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction
- MIT-BIH Arrhythmia: PhysioNet https://physionet.org/content/mitdb/1.0.0/
- Quantum Kernel SVM: Havlíček et al., Nature 567, 209–212 (2019)
- ZZFeatureMap: Qiskit documentation https://qiskit.org/documentation/
- VQC tutorial: https://pennylane.ai/qml/demos/tutorial_variational_classifier

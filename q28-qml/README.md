# Q28 — Quantum Machine Learning (QML) Lab

Part of the 30-project Quantum Portal research workspace.

## Overview

This lab benchmarks Quantum Machine Learning algorithms against classical
baselines using real datasets. The four modules cover the three most practical
near-term QML primitives: **Variational Quantum Classifiers (VQC)**,
**Quantum Support Vector Machines (QSVM)**, and **Quantum Kernel Estimation**.

All quantum circuits are implemented with **PennyLane** and trained via **JAX**
autodiff. Sample sizes are kept small (150–400 rows) so every script runs on a
laptop CPU simulator in under ~10 minutes.

---

## Datasets

| Dataset | Location | Used by |
|---------|----------|---------|
| Wine Quality (6498 rows, 12 features) | `datasets/qml/winequalityN.csv` | classical_baseline, qsvm, quantum_kernel |
| MNIST digits 0 & 1 subset | `datasets/qml/mnist_train.csv` + `mnist_test.csv` | vqc_classifier |

---

## Modules

### 1. `src/classical_baseline.py`
**Wine quality binary classification: SVM (RBF) + RandomForest**

- Loads `winequalityN.csv`, binarises quality (≥6 = "good")
- Trains SVM (RBF kernel, C=10) and RandomForest (200 trees)
- 5-fold cross-validation for each model
- Reports accuracy, F1, ROC-AUC, confusion matrix
- Saves → `data/classical_results.json`

```bash
python src/classical_baseline.py
```

---

### 2. `src/qsvm.py`
**Quantum Support Vector Machine with ZZFeatureMap quantum kernel**

- PCA reduces 11 wine features → 4, scaled to [0, π]
- **Quantum kernel**: `K(x_i, x_j) = |⟨0|U†(x_j)U(x_i)|0⟩|²`
  where `U` is a ZZFeatureMap-style circuit (Hadamard + RZ + CNOT + ZZ interactions)
- SVM trained with `kernel="precomputed"` on 200 train / 80 test samples
- Comparison against classical RBF-SVM on the same reduced features
- Saves → `data/qsvm_results.json`

```bash
python src/qsvm.py
```

Expected runtime: ~5–15 min (200×200 + 80×200 kernel evaluations on CPU sim).

---

### 3. `src/vqc_classifier.py`
**Variational Quantum Classifier on MNIST (digits 0 vs 1)**

- Loads `mnist_train.csv` / `mnist_test.csv`, filters digits 0 and 1
- PCA: 784 → 4 features, scaled to [0, π]
- **Circuit**: 4 qubits, 2 entangling layers
  - Angle embedding: `RY(x_i)` per qubit
  - Each layer: `RY`, `RZ` per qubit → CNOT ring entanglement
- **Training**: JAX + Adam (40 epochs, batch=16, lr=0.05)
- MSE loss with ±1 labels; inference threshold at 0
- Saves → `data/vqc_results.json`

```bash
python src/vqc_classifier.py
```

Expected runtime: ~5–20 min (JAX JIT compilation + 40 × 19 circuit evals).

---

### 4. `src/quantum_kernel.py`
**Quantum kernel estimation: ZZFeatureMap vs PennyLane fidelity kernel vs classical RBF**

Three-way comparison on wine quality (150 train, 60 test):

| Kernel | Implementation |
|--------|---------------|
| Classical RBF | `sklearn.svm.SVC(kernel="rbf")` |
| ZZFeatureMap | Manual PennyLane `@qml.qnode` (adjoint trick) |
| PennyLane fidelity | `qml.kernels.kernel_matrix` + `AngleEmbedding` |

- Saves → `data/kernel_results.json`

```bash
python src/quantum_kernel.py
```

Expected runtime: ~5–10 min (150×150 + 60×150 kernel evaluations × 2 quantum methods).

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run all scripts in order (classical first, then quantum)
python src/classical_baseline.py   # fast  (~10s)
python src/vqc_classifier.py       # ~5–20 min
python src/qsvm.py                 # ~5–15 min
python src/quantum_kernel.py       # ~5–10 min

# 3. Results are in data/
ls data/
# classical_results.json
# vqc_results.json
# qsvm_results.json
# kernel_results.json
```

---

## Circuit Architecture

### VQC (4-qubit, 2-layer)
```
q0: ─RY(x₀)─RY(w₀₀)─RZ(w₀₁)─●──────────X─
q1: ─RY(x₁)─RY(w₁₀)─RZ(w₁₁)─X─●─────────│─
q2: ─RY(x₂)─RY(w₂₀)─RZ(w₂₁)───X─●────── │─
q3: ─RY(x₃)─RY(w₃₀)─RZ(w₃₁)─────X─●─────●─
              [ repeated × N_LAYERS ]
measurement: expval(PauliZ(q0))
```

### ZZFeatureMap Kernel Circuit (4-qubit)
```
q_i: ─H─RZ(2x_i)─●─────────RZ(2(π-x_i)(π-x_{i+1}))─●─
                  └────────────────────────────────────┘
Output: P(|0000⟩) after U†(x_j) U(x_i) |0⟩
```

---

## Expected Results (indicative, CPU sim)

| Model | Dataset | Accuracy | F1 | AUC |
|-------|---------|----------|----|-----|
| SVM-RBF (classical) | Wine | ~0.78 | ~0.85 | ~0.82 |
| RandomForest | Wine | ~0.82 | ~0.88 | ~0.88 |
| QSVM (ZZ kernel) | Wine subset | ~0.70–0.78 | ~0.78–0.85 | ~0.72–0.82 |
| VQC | MNIST 0v1 | ~0.88–0.96 | ~0.88–0.96 | ~0.92–0.98 |
| Quantum RBF kernel | Wine subset | ~0.70–0.78 | — | — |

Note: quantum results on small subsets show high variance; classical models
trained on the full dataset will generally outperform quantum methods at this scale.

---

## File Structure

```
q28-qml/
├── src/
│   ├── classical_baseline.py   # SVM + RF baseline
│   ├── qsvm.py                 # Quantum SVM
│   ├── vqc_classifier.py       # Variational Quantum Classifier
│   └── quantum_kernel.py       # Quantum kernel estimation
├── data/                       # Output JSON results (auto-created)
├── requirements.txt
└── README.md
```

---

## Quantum Backend

All scripts use `pennylane.device("default.qubit")` — PennyLane's exact
state-vector simulator. No QPU credentials required. To run on real hardware,
replace the device with:

```python
dev = qml.device("qiskit.ibmq", wires=N_QUBITS, backend="ibm_nairobi")
```

---

## References

- Havlíček et al., "Supervised learning with quantum-enhanced feature spaces," *Nature* 567 (2019)
- Schuld & Killoran, "Quantum machine learning in feature Hilbert spaces," *PRL* 122 (2019)
- PennyLane documentation: https://pennylane.ai/qml/

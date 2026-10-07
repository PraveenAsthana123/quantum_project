#!/usr/bin/env python3
"""Quantum Machine Learning — Data generator."""
import csv, json, math, random
import numpy as np
from pathlib import Path

random.seed(42)
np.random.seed(42)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# qml_benchmark.csv
with open(DATA_DIR / "qml_benchmark.csv", "w", newline="") as _f:
    _f.writelines(['dataset,n_samples,n_features,classical_acc,qml_acc,qubits,params,epochs\n', 'XOR,20,2,0.95,0.90,2,4,50\n', 'Iris-2class,100,4,0.97,0.95,4,8,100\n', 'MNIST-binary,1000,16,0.99,0.94,4,16,200\n', 'Circles,200,2,0.96,0.92,2,6,100\n'])
print(f"  Saved → {DATA_DIR / "qml_benchmark.csv"}")

# training_curve.csv
with open(DATA_DIR / "training_curve.csv", "w", newline="") as _f:
    _f.writelines(['epoch,loss,accuracy\n', '0,0.5000,0.5000\n', '5,0.3869,0.6018\n', '10,0.2994,0.6806\n', '15,0.2316,0.7415\n', '20,0.1792,0.7887\n', '25,0.1387,0.8252\n', '30,0.1073,0.8534\n', '35,0.0830,0.8753\n', '40,0.0643,0.8922\n', '45,0.0500,0.9053\n', '50,0.0500,0.9154\n'])
print(f"  Saved → {DATA_DIR / "training_curve.csv"}")

print("Data generation complete.")

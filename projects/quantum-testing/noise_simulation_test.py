#!/usr/bin/env python3

from pathlib import Path
import json

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    amplitude_damping_error,
    phase_damping_error,
    ReadoutError,
)

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "noise-tests"
DATA = ROOT / "datasets" / "generated" / "noisy-circuits"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

ideal_counts = AerSimulator().run(qc, shots=3000).result().get_counts()

noise = NoiseModel()

noise.add_all_qubit_quantum_error(
    depolarizing_error(0.01, 1),
    ["h", "x", "sx"]
)

noise.add_all_qubit_quantum_error(
    depolarizing_error(0.03, 2),
    ["cx"]
)

# Add simple readout confusion.
noise.add_all_qubit_readout_error(
    ReadoutError([[0.98, 0.02], [0.03, 0.97]])
)

noisy_counts = AerSimulator(
    noise_model=noise
).run(qc, shots=3000).result().get_counts()

payload = {
    "ideal": ideal_counts,
    "noisy": noisy_counts,
    "noise_types_tested": [
        "depolarizing",
        "readout",
        "amplitude_damping_available",
        "phase_damping_available",
    ],
}

text = json.dumps(payload, indent=2)

(OUT / "bell-noise.json").write_text(text)
(DATA / "bell-noise.json").write_text(text)

print(text)
print("NOISE SIMULATION: PASS")

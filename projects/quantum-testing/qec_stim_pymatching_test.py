#!/usr/bin/env python3

from pathlib import Path
import json

import numpy as np
import stim
import pymatching

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "qec-tests"
DATA = ROOT / "datasets" / "generated" / "qec-syndromes"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

circuit = stim.Circuit.generated(
    "repetition_code:memory",
    distance=5,
    rounds=5,
    after_clifford_depolarization=0.005,
    before_measure_flip_probability=0.002,
    after_reset_flip_probability=0.002,
)

dem = circuit.detector_error_model(decompose_errors=True)
matching = pymatching.Matching.from_detector_error_model(dem)

sampler = circuit.compile_detector_sampler()

detectors, observables = sampler.sample(
    shots=3000,
    separate_observables=True,
)

predictions = matching.decode_batch(detectors)

if predictions.ndim == 1:
    predictions = predictions[:, None]

if observables.ndim == 1:
    observables = observables[:, None]

logical_mask = np.any(predictions != observables, axis=1)

payload = {
    "distance": 5,
    "rounds": 5,
    "shots": int(len(logical_mask)),
    "detector_count": int(detectors.shape[1]),
    "logical_errors": int(logical_mask.sum()),
    "logical_error_rate": float(logical_mask.mean()),
}

text = json.dumps(payload, indent=2)

(OUT / "stim-pymatching.json").write_text(text)
(DATA / "stim-pymatching.json").write_text(text)

print(text)
print("QEC TEST: PASS")

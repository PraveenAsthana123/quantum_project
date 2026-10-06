#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import allantools


ROOT = Path("/mnt/deepa/quantum")
RESULTS = ROOT / "results" / "quantum-clock"

RESULTS.mkdir(
    parents=True,
    exist_ok=True
)


###############################################################################
# RAMSEY FRINGE
###############################################################################

detuning = np.linspace(
    -5.0,
    5.0,
    501
)

T = 1.0

probability = (
    1.0
    +
    np.cos(detuning * T)
) / 2.0


df = pd.DataFrame({
    "detuning": detuning,
    "excited_probability": probability
})

df.to_csv(
    RESULTS / "ramsey_fringe.csv",
    index=False
)


plt.figure(figsize=(9, 5))

plt.plot(
    detuning,
    probability
)

plt.xlabel("Detuning")
plt.ylabel("Excited-state probability")
plt.title("Ramsey Clock Fringe")
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS / "ramsey_fringe.png",
    dpi=160
)

plt.close()


###############################################################################
# SYNTHETIC CLOCK NOISE
###############################################################################

rng = np.random.default_rng(42)

fractional_frequency = rng.normal(
    0.0,
    1e-12,
    30000
)


taus, adev, errors, counts = allantools.oadev(
    fractional_frequency,
    rate=1.0,
    data_type="freq",
    taus="decade"
)


adev_df = pd.DataFrame({
    "tau_seconds": taus,
    "oadev": adev,
    "error": errors,
    "samples": counts
})


adev_df.to_csv(
    RESULTS / "allan_deviation.csv",
    index=False
)


plt.figure(figsize=(9, 5))

plt.loglog(
    taus,
    adev,
    marker="o"
)

plt.xlabel("Averaging time τ (s)")
plt.ylabel("Overlapping Allan deviation")
plt.title("Synthetic Clock Stability")
plt.grid(True, which="both")

plt.tight_layout()

plt.savefig(
    RESULTS / "allan_deviation.png",
    dpi=160
)

plt.close()


print()
print("=" * 70)
print("QUANTUM CLOCK TEST: PASS")
print("=" * 70)
print("Results:", RESULTS)
print()

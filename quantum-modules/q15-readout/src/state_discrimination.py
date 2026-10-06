"""
Optimal State Discrimination
==============================
Implements Helstrom measurement for binary quantum state discrimination.
Compares: simple threshold / maximum likelihood / Bayesian methods.
Shows IQ plane readout blob separation.

Setup: discriminate between |0⟩ and |1⟩ in the IQ plane.
  - |0⟩ → IQ blob centered at (I₀, Q₀) with width σ
  - |1⟩ → IQ blob centered at (I₁, Q₁) with width σ

Helstrom bound: minimum error probability for binary discrimination.

Saves results to data/discrimination_results.json.
"""

import json
import numpy as np
from pathlib import Path
from scipy import stats


# ---------------------------------------------------------------------------
# IQ readout model
# ---------------------------------------------------------------------------

class IQReadout:
    """
    Simulate IQ quadrature readout for a superconducting qubit.

    State |0⟩: IQ blob at (I₀, Q₀) = (1.0, 0.0) with noise σ
    State |1⟩: IQ blob at (I₁, Q₁) = (-1.0, 0.0) with noise σ
    """

    def __init__(self, I0: float = 1.0, Q0: float = 0.0,
                 I1: float = -1.0, Q1: float = 0.0,
                 sigma: float = 0.4, seed: int = 42):
        self.center0 = np.array([I0, Q0])
        self.center1 = np.array([I1, Q1])
        self.sigma = sigma
        self.rng = np.random.default_rng(seed)
        self.separation = np.linalg.norm(self.center0 - self.center1)
        self.snr_db = float(20 * np.log10(self.separation / (2 * sigma)))

    def sample(self, state: int, n_shots: int = 1000) -> np.ndarray:
        """Sample n_shots IQ points for state |0⟩ or |1⟩."""
        center = self.center0 if state == 0 else self.center1
        noise = self.rng.normal(0, self.sigma, (n_shots, 2))
        return center + noise

    def sample_mixed(self, p0: float = 0.5, n_shots: int = 2000) -> tuple:
        """Sample from a mixture of |0⟩ and |1⟩ with prior p0."""
        n0 = int(n_shots * p0)
        n1 = n_shots - n0
        samples_0 = self.sample(0, n0)
        samples_1 = self.sample(1, n1)
        labels = np.concatenate([np.zeros(n0, dtype=int), np.ones(n1, dtype=int)])
        samples = np.vstack([samples_0, samples_1])

        # Shuffle
        idx = self.rng.permutation(len(labels))
        return samples[idx], labels[idx]


# ---------------------------------------------------------------------------
# Discrimination methods
# ---------------------------------------------------------------------------

def threshold_discrimination(iq_points: np.ndarray, threshold: float = 0.0,
                               axis: int = 0) -> np.ndarray:
    """
    Simple threshold on I quadrature.
    Predict 0 if I > threshold, else 1.
    """
    return (iq_points[:, axis] <= threshold).astype(int)


def maximum_likelihood_discrimination(iq_points: np.ndarray,
                                       center0: np.ndarray,
                                       center1: np.ndarray,
                                       sigma: float) -> np.ndarray:
    """
    Maximum likelihood (ML) discrimination.
    Predict 0 if P(IQ | |0⟩) > P(IQ | |1⟩).
    For Gaussian blobs: equivalent to nearest-centroid.
    """
    d0 = np.sum((iq_points - center0) ** 2, axis=1)
    d1 = np.sum((iq_points - center1) ** 2, axis=1)
    return (d0 >= d1).astype(int)


def bayesian_discrimination(iq_points: np.ndarray,
                              center0: np.ndarray, center1: np.ndarray,
                              sigma: float, prior0: float = 0.5) -> np.ndarray:
    """
    Bayesian (MAP) discrimination.
    Predict argmax of P(state|IQ) = P(IQ|state) * P(state).
    """
    prior1 = 1.0 - prior0

    # Log likelihoods
    log_p_iq_0 = -np.sum((iq_points - center0) ** 2, axis=1) / (2 * sigma ** 2)
    log_p_iq_1 = -np.sum((iq_points - center1) ** 2, axis=1) / (2 * sigma ** 2)

    log_posterior_0 = log_p_iq_0 + np.log(prior0 + 1e-15)
    log_posterior_1 = log_p_iq_1 + np.log(prior1 + 1e-15)

    return (log_posterior_0 < log_posterior_1).astype(int)


# ---------------------------------------------------------------------------
# Error probability
# ---------------------------------------------------------------------------

def error_probability(predictions: np.ndarray, true_labels: np.ndarray) -> float:
    """Compute classification error probability."""
    return float(np.mean(predictions != true_labels))


def helstrom_bound(center0: np.ndarray, center1: np.ndarray,
                    sigma: float, prior0: float = 0.5) -> float:
    """
    Helstrom bound for binary state discrimination.
    For two Gaussian distributions with equal covariance:
    P_err = Q(d / (2σ))  where Q is the Q-function, d = |μ₁ - μ₀|

    Q(x) = 0.5 * erfc(x / √2)
    """
    d = np.linalg.norm(center1 - center0)
    # SNR in linear units
    snr_linear = d / (2 * sigma)
    p_err = 0.5 * stats.norm.sf(snr_linear)  # Q(d/2σ) = 1 - Φ(d/2σ)
    return float(p_err)


# ---------------------------------------------------------------------------
# IQ blob statistics
# ---------------------------------------------------------------------------

def compute_iq_statistics(iq_0: np.ndarray, iq_1: np.ndarray) -> dict:
    """Compute IQ plane statistics for readout blobs."""
    mean0 = np.mean(iq_0, axis=0)
    mean1 = np.mean(iq_1, axis=0)
    std0 = np.std(iq_0, axis=0)
    std1 = np.std(iq_1, axis=0)
    separation = float(np.linalg.norm(mean0 - mean1))
    snr = separation / (np.mean([std0, std1]))
    snr_dB = float(20 * np.log10(snr + 1e-10))

    return {
        "mean_state0": mean0.tolist(),
        "mean_state1": mean1.tolist(),
        "std_state0": std0.tolist(),
        "std_state1": std1.tolist(),
        "iq_separation": round(separation, 6),
        "snr_linear": round(snr, 4),
        "snr_dB": round(snr_dB, 2),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Optimal State Discrimination — IQ Plane Analysis")
    print("=" * 60)

    sigma_values = [0.2, 0.3, 0.4, 0.5, 0.6]
    n_shots = 3000
    prior0 = 0.5

    print(f"\nShots per sigma : {n_shots}")
    print(f"IQ centers: |0⟩ = (1.0, 0.0), |1⟩ = (-1.0, 0.0)")
    print(f"Prior P(|0⟩) = {prior0}\n")

    print(f"{'σ':>6} | {'SNR(dB)':>9} | {'Threshold':>12} | {'ML':>10} | {'Bayesian':>10} | {'Helstrom':>10}")
    print("-" * 72)

    all_results = []
    for sigma in sigma_values:
        readout = IQReadout(sigma=sigma)
        iq_samples, true_labels = readout.sample_mixed(p0=prior0, n_shots=n_shots)

        # Methods
        pred_thresh = threshold_discrimination(iq_samples)
        pred_ml = maximum_likelihood_discrimination(iq_samples,
                                                     readout.center0, readout.center1, sigma)
        pred_bayes = bayesian_discrimination(iq_samples,
                                              readout.center0, readout.center1, sigma, prior0)

        err_thresh = error_probability(pred_thresh, true_labels)
        err_ml = error_probability(pred_ml, true_labels)
        err_bayes = error_probability(pred_bayes, true_labels)
        helstrom = helstrom_bound(readout.center0, readout.center1, sigma, prior0)

        snr_db = readout.snr_db
        print(f"{sigma:>6.2f} | {snr_db:>9.2f} | {err_thresh:>12.6f} | {err_ml:>10.6f} | "
              f"{err_bayes:>10.6f} | {helstrom:>10.6f}")

        # IQ statistics
        iq_0 = iq_samples[true_labels == 0]
        iq_1 = iq_samples[true_labels == 1]
        iq_stats = compute_iq_statistics(iq_0, iq_1)

        all_results.append({
            "sigma": sigma,
            "snr_dB": round(snr_db, 2),
            "method": "comparison",
            "error_threshold": round(err_thresh, 6),
            "error_ml": round(err_ml, 6),
            "error_bayesian": round(err_bayes, 6),
            "error_helstrom_bound": round(helstrom, 6),
            "iq_statistics": iq_stats,
        })

    # Primary result for default sigma=0.4
    primary = all_results[2]

    print(f"\nAt σ=0.4:")
    print(f"  Threshold error : {primary['error_threshold']:.4f}")
    print(f"  ML error        : {primary['error_ml']:.4f}")
    print(f"  Bayesian error  : {primary['error_bayesian']:.4f}")
    print(f"  Helstrom bound  : {primary['error_helstrom_bound']:.4f}")

    results = {
        "method": "comparison: threshold, ML, Bayesian, Helstrom",
        "error_probability": primary["error_bayesian"],
        "snr_dB": primary["snr_dB"],
        "iq_separation": primary["iq_statistics"]["iq_separation"],
        "helstrom_bound": primary["error_helstrom_bound"],
        "methods_compared": {
            "threshold": primary["error_threshold"],
            "maximum_likelihood": primary["error_ml"],
            "bayesian_map": primary["error_bayesian"],
            "helstrom_optimal": primary["error_helstrom_bound"],
        },
        "iq_blob_stats": primary["iq_statistics"],
        "all_sigma_results": all_results,
        "notes": (
            "For equal-variance Gaussian blobs, ML == Bayesian (with equal priors) "
            "and both achieve the Helstrom bound. The threshold method achieves the "
            "Helstrom bound only when the threshold is optimally placed."
        ),
    }

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "discrimination_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_path}")
    print("\nState discrimination simulation complete.")


if __name__ == "__main__":
    main()

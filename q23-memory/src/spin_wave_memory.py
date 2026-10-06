"""
Q23 — Quantum Memory
spin_wave_memory.py

Atomic Frequency Comb (AFC) quantum memory.
Creates a comb structure in the absorption spectrum, calculates
multimode storage capacity, and shows revival efficiency vs comb finesse.

Reference: Afzelius et al., PRA 79, 052329 (2009);
           de Riedmatten et al., Nature 456, 773 (2008).

Outputs: data/afc_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# AFC physics
# ---------------------------------------------------------------------------

def afc_efficiency(finesse: float, optical_depth_background: float = 0.1) -> float:
    """
    AFC storage and re-emission efficiency.

    η_AFC ≈ (d_comb / (d_comb + d_bg))^2  *  sinc²(Δ/Γ)
    Simplified for ideal comb (Δ/Γ → 0):
       η = exp(-d_comb / finesse) * (1 - exp(-d_comb))^2

    Practical formula from Afzelius 2009:
       η = (F-1)^2 / F^2 * exp(-d_0/F)
    where F = finesse, d_0 = peak optical depth per tooth.
    """
    F = max(finesse, 1.01)
    # Typical peak optical depth per tooth
    d0 = 2.0  # typical value for Tm:YAG or Pr:YSO
    eta = ((F - 1.0) / F) ** 2 * math.exp(-d0 / F)
    return min(1.0, max(0.0, eta))


def storage_time_from_comb(comb_spacing_MHz: float) -> float:
    """
    AFC storage time = 1 / Δ_comb  (Fourier relationship).
    Storage time in µs for comb spacing in MHz.
    """
    if comb_spacing_MHz <= 0:
        return float("inf")
    return 1.0 / comb_spacing_MHz  # µs


def multimode_capacity(bandwidth_MHz: float, comb_spacing_MHz: float) -> int:
    """
    Number of temporal modes stored = bandwidth / comb_spacing.
    This equals the number of comb teeth in the absorption window.
    """
    if comb_spacing_MHz <= 0:
        return 0
    return max(1, int(bandwidth_MHz / comb_spacing_MHz))


def retrieval_decoherence(storage_time_us: float, t2_us: float) -> float:
    """Fidelity reduction during storage: exp(-t_store/T2)."""
    return math.exp(-storage_time_us / t2_us)


# ---------------------------------------------------------------------------
# AFC spectrum model
# ---------------------------------------------------------------------------

class AFCSpectrum:
    """
    Model the absorption comb structure in frequency space.
    Comb: N teeth equally spaced by Δ, each of width γ.
    """

    def __init__(self,
                 n_teeth: int = 10,
                 comb_spacing_MHz: float = 1.0,
                 tooth_width_MHz: float = 0.1,
                 peak_absorption: float = 3.0,
                 background_absorption: float = 0.1):
        self.n_teeth = n_teeth
        self.delta = comb_spacing_MHz          # Δ — tooth separation [MHz]
        self.gamma = tooth_width_MHz           # γ — tooth width [MHz]
        self.alpha_peak = peak_absorption      # peak optical depth
        self.alpha_bg = background_absorption  # background OD

        self.finesse = comb_spacing_MHz / tooth_width_MHz

    def absorption_at(self, freq_offset_MHz: float) -> float:
        """Absorption at a given frequency offset from line centre."""
        alpha = self.alpha_bg
        for k in range(-self.n_teeth // 2, self.n_teeth // 2 + 1):
            tooth_center = k * self.delta
            lorentzian = (self.gamma / 2.0) ** 2 / (
                (freq_offset_MHz - tooth_center) ** 2
                + (self.gamma / 2.0) ** 2)
            alpha += self.alpha_peak * lorentzian
        return alpha

    def efficiency(self) -> float:
        return afc_efficiency(self.finesse)

    def storage_time_us(self) -> float:
        return storage_time_from_comb(self.delta)

    def capacity(self, bandwidth_MHz: float = None) -> int:
        if bandwidth_MHz is None:
            bandwidth_MHz = self.n_teeth * self.delta
        return multimode_capacity(bandwidth_MHz, self.delta)


# ---------------------------------------------------------------------------
# Finesse sweep
# ---------------------------------------------------------------------------

def finesse_sweep(finesse_values=None, t2_us: float = 100.0) -> list:
    """Revival efficiency vs comb finesse."""
    if finesse_values is None:
        finesse_values = [2, 3, 5, 7, 10, 15, 20]
    rows = []
    for F in finesse_values:
        eta = afc_efficiency(F)
        spacing_MHz = 1.0  # fixed spacing
        tooth_width = spacing_MHz / F
        t_store = storage_time_from_comb(spacing_MHz)
        decoher = retrieval_decoherence(t_store, t2_us)
        rows.append({
            "finesse": F,
            "efficiency_ideal": round(eta, 4),
            "efficiency_with_decoherence": round(eta * decoher, 4),
            "storage_time_us": round(t_store, 4),
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Atomic Frequency Comb (AFC) Quantum Memory ===\n")

    # Representative parameters: Tm:YAG crystal at 4K
    n_teeth = 10
    comb_spacing_MHz = 1.0      # 1 MHz spacing → 1 µs storage time
    tooth_width_MHz = 0.1       # finesse = 10
    t2_us = 100.0               # spin coherence time

    comb = AFCSpectrum(
        n_teeth=n_teeth,
        comb_spacing_MHz=comb_spacing_MHz,
        tooth_width_MHz=tooth_width_MHz,
    )

    eta = comb.efficiency()
    t_store = comb.storage_time_us()
    capacity = comb.capacity()
    decoher = retrieval_decoherence(t_store, t2_us)

    print(f"Comb teeth            : {n_teeth}")
    print(f"Comb spacing          : {comb_spacing_MHz} MHz")
    print(f"Tooth width           : {tooth_width_MHz} MHz")
    print(f"Finesse               : {comb.finesse:.1f}")
    print(f"Storage time          : {t_store:.2f} µs")
    print(f"Multimode capacity    : {capacity}")
    print(f"Efficiency (ideal)    : {eta:.4f}")
    print(f"Decoherence factor    : {decoher:.4f}")
    print(f"Efficiency (real)     : {eta*decoher:.4f}")

    print("\n--- Finesse sweep ---")
    sweep = finesse_sweep(t2_us=t2_us)
    for row in sweep:
        print(f"  F={row['finesse']:3d}  η={row['efficiency_ideal']:.4f}  "
              f"η(decoher)={row['efficiency_with_decoherence']:.4f}  "
              f"t_store={row['storage_time_us']:.3f}µs")

    results = {
        "comb_teeth": n_teeth,
        "finesse": comb.finesse,
        "storage_time_us": round(t_store, 4),
        "multimode_capacity": capacity,
        "efficiency": round(eta * decoher, 4),
        "efficiency_ideal": round(eta, 4),
        "t2_us": t2_us,
        "finesse_sweep": sweep,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/afc_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()

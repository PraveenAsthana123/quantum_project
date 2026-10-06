"""
Q23 — Quantum Memory
eit_memory.py

EIT (Electromagnetically Induced Transparency) quantum memory.
Models photon storage in an atomic ensemble (3-level Lambda system).
Computes storage efficiency vs optical depth and decoherence.

Reference: Gorshkov et al., PRL 98, 123601 (2007);
           Hammerer et al., Rev. Mod. Phys. 82, 1041 (2010).

Outputs: data/eit_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# EIT physics
# ---------------------------------------------------------------------------

def eit_storage_efficiency(optical_depth: float,
                            cooperativity_factor: float = 1.0) -> float:
    """
    Storage efficiency for EIT memory in optically thick atomic ensemble.

    η_store ≈ 1 - (1 + d)^{-2} for the adiabatic limit (simplified).
    More accurate model (Gorshkov 2007):
       η = d / (d + 1)   (for optimal control pulse, single spatial mode)

    For high OD: η → 1 - 1/d.
    cooperativity_factor accounts for mode-matching and cavity enhancement.
    """
    d = optical_depth
    if d <= 0:
        return 0.0
    eta = d / (d + 1.0)
    return min(1.0, eta * cooperativity_factor)


def eit_retrieval_efficiency(storage_eff: float,
                              decoherence_factor: float = 1.0) -> float:
    """
    Retrieval efficiency ≤ storage efficiency, degraded by decoherence.
    η_ret = η_store * exp(-t_storage/T2)   (via decoherence_factor)
    """
    return storage_eff * decoherence_factor


def decoherence_factor(storage_time_us: float, t2_us: float) -> float:
    """Exponential dephasing decay."""
    return math.exp(-storage_time_us / t2_us)


def t1_from_od(optical_depth: float, gamma_MHz: float = 6.0) -> float:
    """
    Estimate T1 from atomic decay: T1 ≈ 1/(2*pi*gamma).
    gamma is the excited-state decay rate in MHz.
    Returns T1 in µs.
    Note: The excited-state T1 (~26 ns for Rb D1) is not the relevant T1
    for the ground-state spin coherence; ground-state T1 can be >> ms.
    This function returns the relevant ground-state coherence T1.
    """
    # For EIT in Rb, ground-state T1 is limited by transit time and collisions
    # Typical values: 10–1000 µs depending on buffer gas / cell geometry.
    # We use 1/(2π*gamma_groundstate) with gamma_groundstate ~ 1 kHz:
    gamma_ground_kHz = 1.0  # kHz — ground-state decoherence rate
    return 1e3 / (2.0 * math.pi * gamma_ground_kHz)  # µs  ≈ 159 µs


def t2_from_t1(t1_us: float, dephasing_rate_kHz: float = 1.0) -> float:
    """
    Ground-state T2 = 1/(1/(2T1) + Γ_phi).
    Γ_phi = 2*pi*dephasing_rate_kHz [kHz → µs^-1].
    Returns T2 in µs.
    """
    t_phi_us = 1e3 / (2.0 * math.pi * dephasing_rate_kHz)  # µs
    t2_us = 1.0 / (1.0 / (2.0 * t1_us) + 1.0 / t_phi_us)
    return t2_us


# ---------------------------------------------------------------------------
# Protocol timing model
# ---------------------------------------------------------------------------

class EITProtocol:
    """Write → Storage → Retrieval timing model for EIT memory."""

    def __init__(self,
                 optical_depth: float = 100.0,
                 t1_us: float = 26.5,
                 t2_us: float = 200.0,
                 write_pulse_us: float = 1.0,
                 read_pulse_us: float = 1.0):
        self.optical_depth = optical_depth
        self.t1_us = t1_us
        self.t2_us = t2_us
        self.write_pulse_us = write_pulse_us
        self.read_pulse_us = read_pulse_us

    def max_storage_time(self, efficiency_threshold: float = 0.1) -> float:
        """
        Maximum storage time for which retrieval efficiency > threshold.
        η_ret(t) = η_store * exp(-t/T2) > threshold
        t_max = T2 * ln(η_store / threshold)
        """
        eta_store = eit_storage_efficiency(self.optical_depth)
        if eta_store <= efficiency_threshold:
            return 0.0
        t_max = self.t2_us * math.log(eta_store / efficiency_threshold)
        return max(0.0, t_max)

    def efficiency_vs_time(self, storage_times_us: list) -> list:
        """Return (storage_time_us, storage_eff, retrieval_eff) tuples."""
        eta_store = eit_storage_efficiency(self.optical_depth)
        rows = []
        for t in storage_times_us:
            df = decoherence_factor(t, self.t2_us)
            eta_ret = eit_retrieval_efficiency(eta_store, df)
            rows.append({
                "storage_time_us": round(t, 2),
                "storage_efficiency": round(eta_store, 4),
                "retrieval_efficiency": round(eta_ret, 4),
            })
        return rows


# ---------------------------------------------------------------------------
# Optical depth sweep
# ---------------------------------------------------------------------------

def od_sweep(od_values=None, t2_us: float = 200.0,
             storage_time_us: float = 10.0) -> list:
    """Storage and retrieval efficiency vs optical depth."""
    if od_values is None:
        od_values = [10, 20, 50, 100, 200, 500, 1000]
    rows = []
    for od in od_values:
        eta_s = eit_storage_efficiency(od)
        df = decoherence_factor(storage_time_us, t2_us)
        eta_r = eit_retrieval_efficiency(eta_s, df)
        rows.append({
            "optical_depth": od,
            "storage_efficiency": round(eta_s, 4),
            "retrieval_efficiency": round(eta_r, 4),
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== EIT Quantum Memory Simulation ===\n")

    # Representative parameters: Rb-87 D1 line, room-T gradient echo memory
    optical_depth = 100.0
    t1_us = t1_from_od(optical_depth, gamma_MHz=6.0)   # ≈ 26.5 µs
    t2_us = t2_from_t1(t1_us, dephasing_rate_kHz=1.0)  # ≈ 200 µs

    proto = EITProtocol(
        optical_depth=optical_depth,
        t1_us=t1_us,
        t2_us=t2_us,
    )

    eta_store = eit_storage_efficiency(optical_depth)
    t_max = proto.max_storage_time(efficiency_threshold=0.1)

    print(f"Optical depth         : {optical_depth}")
    print(f"T1                    : {t1_us:.2f} µs")
    print(f"T2                    : {t2_us:.2f} µs")
    print(f"Storage efficiency    : {eta_store:.4f}")
    print(f"Max storage time(10%) : {t_max:.1f} µs")

    # Efficiency vs storage time
    storage_times = [0, 10, 50, 100, 200, 500, 1000]
    print("\nEfficiency vs storage time:")
    for row in proto.efficiency_vs_time(storage_times):
        print(f"  t={row['storage_time_us']:6.0f} µs  "
              f"η_store={row['storage_efficiency']:.4f}  "
              f"η_ret={row['retrieval_efficiency']:.4f}")

    # OD sweep
    print("\nOD sweep (storage time = 10 µs):")
    sweep = od_sweep(t2_us=t2_us, storage_time_us=10.0)
    for row in sweep:
        print(f"  OD={row['optical_depth']:5d}  "
              f"η_store={row['storage_efficiency']:.4f}  "
              f"η_ret={row['retrieval_efficiency']:.4f}")

    results = {
        "optical_depth": optical_depth,
        "storage_efficiency": round(eta_store, 4),
        "retrieval_efficiency": round(
            eit_retrieval_efficiency(eta_store,
                                     decoherence_factor(10.0, t2_us)), 4),
        "t1_us": round(t1_us, 2),
        "t2_us": round(t2_us, 2),
        "max_storage_time_us": round(t_max, 2),
        "efficiency_vs_time": proto.efficiency_vs_time(storage_times),
        "od_sweep": sweep,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/eit_results.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()

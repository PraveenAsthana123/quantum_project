"""
Q26 — Quantum Metrology
optical_clock.py

Optical lattice clock simulation.
Models Al+ (267nm / ~1.1 PHz) and Sr (698nm / ~429 THz) transitions.
Calculates: systematic shifts (BBR, micromotion, Stark shift),
statistical uncertainty, and fractional frequency uncertainty δf/f.
Compares Cs fountain → optical clock hierarchy.

Reference: Ludlow et al., Rev. Mod. Phys. 87, 637 (2015);
           Bloom et al., Nature 506, 71 (2014).

Outputs: data/clock_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

KB = 1.380649e-23      # Boltzmann constant [J/K]
HBAR = 1.0546e-34      # reduced Planck constant [J·s]
C = 2.998e8            # speed of light [m/s]
ALPHA = 7.297e-3       # fine structure constant


# ---------------------------------------------------------------------------
# Clock species definitions
# ---------------------------------------------------------------------------

CLOCKS = {
    "Cs_fountain": {
        "species": "133Cs",
        "wavelength_nm": 32.6e6,    # 9.19 GHz microwave → effective λ
        "frequency_Hz": 9.192631770e9,
        "Q_factor": 1e10,
        "type": "microwave",
        "bbr_shift_frac": -1.7e-14,
        "stark_shift_frac": 0.0,
        "micromotion_shift_frac": 0.0,
        "gravitational_uncertainty": 1e-16,
        "instability_1s": 3e-14,   # σ_y at 1s
        "accuracy": 2e-16,
    },
    "Sr_optical": {
        "species": "87Sr",
        "wavelength_nm": 698.0,
        "frequency_Hz": 429.228e12,
        "Q_factor": 2.4e17,
        "type": "optical",
        "bbr_shift_frac": -5.1e-17,
        "stark_shift_frac": -2.0e-18,
        "micromotion_shift_frac": 0.0,     # lattice clock, no micromotion
        "gravitational_uncertainty": 2e-18,
        "instability_1s": 4e-16,
        "accuracy": 2e-18,
    },
    "Al_plus": {
        "species": "27Al+",
        "wavelength_nm": 267.4,
        "frequency_Hz": 1.121e15,
        "Q_factor": 6.7e17,
        "type": "optical_ion",
        "bbr_shift_frac": -9.0e-20,     # Al+ is extremely BBR insensitive
        "stark_shift_frac": -1.4e-18,
        "micromotion_shift_frac": 3e-19,
        "gravitational_uncertainty": 1e-18,
        "instability_1s": 2.8e-15,
        "accuracy": 9.4e-19,
    },
    "Yb_optical": {
        "species": "171Yb",
        "wavelength_nm": 578.4,
        "frequency_Hz": 518.295e12,
        "Q_factor": 1.8e17,
        "type": "optical",
        "bbr_shift_frac": -2.7e-16,
        "stark_shift_frac": -5.0e-18,
        "micromotion_shift_frac": 0.0,
        "gravitational_uncertainty": 3e-18,
        "instability_1s": 1e-15,
        "accuracy": 1.4e-18,
    },
}


# ---------------------------------------------------------------------------
# Systematic shift calculations
# ---------------------------------------------------------------------------

def bbr_shift(T_K: float = 300.0, alpha4: float = -2.0e-37) -> float:
    """
    Blackbody radiation (BBR) frequency shift.
    Δf/f ≈ -β * (T/300K)^4
    α4 is the differential polarisability coefficient [Hz/(V/m)²].
    Simple scaling: Δf/f_BBR ∝ T^4.
    """
    return alpha4 * (T_K / 300.0) ** 4


def lattice_stark_shift(lattice_depth_Er: float = 200.0,
                         magic_detuning_Hz: float = 0.0) -> float:
    """
    AC Stark shift from the optical lattice.
    At the magic wavelength: Δf = 0 to first order.
    Residual: δf/f ≈ magic_detuning / ν_0 * lattice_depth_correction
    """
    return magic_detuning_Hz * 1e-15  # small residual in fractional units


def gravitational_redshift(height_m: float = 0.0) -> float:
    """
    Gravitational redshift: Δf/f = g * h / c²
    g ≈ 9.8 m/s², Δf/f ≈ 1.09e-16 per metre.
    """
    g = 9.8
    return g * height_m / C ** 2


def statistical_uncertainty(instability_1s: float,
                              averaging_time_s: float) -> float:
    """
    Allan deviation at averaging time τ:
    σ_y(τ) = σ_y(1s) / √τ  (white frequency noise)
    """
    return instability_1s / math.sqrt(averaging_time_s)


# ---------------------------------------------------------------------------
# Quality factor and line Q
# ---------------------------------------------------------------------------

def quality_factor(frequency_Hz: float, linewidth_Hz: float) -> float:
    """Q = ν / Δν"""
    return frequency_Hz / linewidth_Hz


def natural_linewidth(lifetime_s: float) -> float:
    """Natural linewidth Δν = 1/(2π τ) [Hz]."""
    return 1.0 / (2.0 * math.pi * lifetime_s)


# ---------------------------------------------------------------------------
# Clock hierarchy
# ---------------------------------------------------------------------------

def compute_clock_metrics(clock_name: str,
                            averaging_time_s: float = 1e4,
                            T_environment_K: float = 300.0) -> dict:
    """
    Compute full uncertainty budget for a given clock species.
    Returns dict with all relevant metrics.
    """
    clk = CLOCKS[clock_name]

    # Statistical
    stat = statistical_uncertainty(clk["instability_1s"], averaging_time_s)

    # Systematic
    bbr = clk["bbr_shift_frac"]
    stark = clk["stark_shift_frac"]
    micromotion = clk["micromotion_shift_frac"]
    grav = clk["gravitational_uncertainty"]

    # Total systematic in quadrature (simplified)
    systematic = math.sqrt(bbr ** 2 + stark ** 2 +
                            micromotion ** 2 + grav ** 2)

    # Total uncertainty
    total = math.sqrt(stat ** 2 + systematic ** 2)

    return {
        "species": clk["species"],
        "frequency_Hz": clk["frequency_Hz"],
        "wavelength_nm": clk["wavelength_nm"],
        "quality_factor": clk["Q_factor"],
        "systematic_shifts": {
            "bbr_fractional": bbr,
            "stark_fractional": stark,
            "micromotion_fractional": micromotion,
            "gravitational_fractional": grav,
        },
        "total_systematic": round(systematic, 22),
        "statistical_at_avg_time": round(stat, 22),
        "total_uncertainty": round(total, 22),
        "precision_s": round(total / clk["frequency_Hz"], 32),
        "instability_1s": clk["instability_1s"],
        "accuracy": clk["accuracy"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Optical Lattice Clock Simulation ===\n")

    averaging_time = 1e4  # 10,000 seconds averaging

    all_results = {}
    print(f"{'Clock':15s}  {'Frequency':15s}  {'Accuracy':12s}  "
          f"{'Instability(1s)':18s}")
    print("-" * 70)

    for name in CLOCKS:
        metrics = compute_clock_metrics(name, averaging_time_s=averaging_time)
        all_results[name] = metrics
        freq_str = f"{metrics['frequency_Hz']:.4e} Hz"
        acc_str = f"{metrics['accuracy']:.2e}"
        inst_str = f"{metrics['instability_1s']:.2e}"
        print(f"{name:15s}  {freq_str:15s}  {acc_str:12s}  {inst_str:18s}")

    # Focus: Sr optical clock (representative)
    sr = all_results["Sr_optical"]
    print(f"\n--- Sr Optical Clock Detail ---")
    print(f"  Wavelength     : {sr['wavelength_nm']} nm")
    print(f"  Q factor       : {sr['quality_factor']:.2e}")
    print(f"  Accuracy       : {sr['accuracy']:.2e}")
    print(f"  Statistical    : {sr['statistical_at_avg_time']:.2e}")
    print(f"  Total uncert.  : {sr['total_uncertainty']:.2e}")
    print(f"  Precision [s]  : {sr['precision_s']:.2e} s")

    # Clock hierarchy improvement
    cs_acc = all_results["Cs_fountain"]["accuracy"]
    sr_acc = all_results["Sr_optical"]["accuracy"]
    al_acc = all_results["Al_plus"]["accuracy"]
    print(f"\n--- Clock Hierarchy Improvement ---")
    print(f"  Cs fountain    → Sr optical: {cs_acc/sr_acc:.0f}x improvement")
    print(f"  Sr optical     → Al+ ion   : {sr_acc/al_acc:.0f}x improvement")

    output = {
        "species": "Sr / Al+",
        "wavelength_nm": {"Sr": 698.0, "Al+": 267.4},
        "quality_factor": {"Sr": CLOCKS["Sr_optical"]["Q_factor"],
                            "Al+": CLOCKS["Al_plus"]["Q_factor"]},
        "systematic_shifts": {
            k: all_results[k]["systematic_shifts"]
            for k in all_results
        },
        "total_uncertainty": {
            k: all_results[k]["total_uncertainty"]
            for k in all_results
        },
        "precision_s": {
            k: all_results[k]["precision_s"]
            for k in all_results
        },
        "clock_hierarchy": {
            "Cs_fountain": all_results["Cs_fountain"]["accuracy"],
            "Sr_optical": all_results["Sr_optical"]["accuracy"],
            "Al_plus": all_results["Al_plus"]["accuracy"],
        },
        "full_metrics": all_results,
    }

    os.makedirs("data", exist_ok=True)
    out_path = "data/clock_results.json"
    with open(out_path, "w") as fh:
        json.dump(output, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()

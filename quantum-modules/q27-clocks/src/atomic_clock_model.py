"""
Q27 — Quantum Clocks
atomic_clock_model.py

Atomic clock stability model using Allan deviation.
σ_y(τ) = σ_0 / √τ  (white frequency noise regime)

Models: Cs fountain, Rb clock, Optical lattice clock.
Shows improvement trajectory 10^-13 → 10^-18 over 50 years.

Reference: Audoin & Guinot, "The Measurement of Time" (CUP, 2001);
           Ludlow et al., Rev. Mod. Phys. 87, 637 (2015).

Outputs: data/clock_model_results.json
"""

import json
import math
import os


# ---------------------------------------------------------------------------
# Clock species definitions
# ---------------------------------------------------------------------------

CLOCK_TYPES = {
    "Cs_fountain": {
        "frequency_Hz": 9.192631770e9,
        "instability_1s": 3.0e-14,    # σ_y(1s) white freq noise floor
        "accuracy": 2.0e-16,
        "tau_floor_s": 1.0,            # minimum coherent averaging time
        "year_introduced": 1991,
        "description": "Cs-133 fountain primary standard",
    },
    "Rb_clock": {
        "frequency_Hz": 6.834682611e9,
        "instability_1s": 5.0e-13,
        "accuracy": 1.0e-14,
        "tau_floor_s": 1.0,
        "year_introduced": 1970,
        "description": "Rb-87 passive frequency standard",
    },
    "H_maser": {
        "frequency_Hz": 1.420405752e9,
        "instability_1s": 1.0e-13,
        "accuracy": 1.0e-15,
        "tau_floor_s": 100.0,          # flicker floor at ~100 s
        "year_introduced": 1960,
        "description": "Active hydrogen maser",
    },
    "Sr_optical": {
        "frequency_Hz": 429.228e12,
        "instability_1s": 4.0e-16,
        "accuracy": 2.0e-18,
        "tau_floor_s": 1.0,
        "year_introduced": 2003,
        "description": "Sr-87 optical lattice clock",
    },
    "Al_plus_optical": {
        "frequency_Hz": 1.121e15,
        "instability_1s": 2.8e-15,
        "accuracy": 9.4e-19,
        "tau_floor_s": 1.0,
        "year_introduced": 2008,
        "description": "Al+ optical ion clock",
    },
    "Yb_optical": {
        "frequency_Hz": 518.295e12,
        "instability_1s": 1.0e-15,
        "accuracy": 1.4e-18,
        "tau_floor_s": 1.0,
        "year_introduced": 2006,
        "description": "Yb-171 optical lattice clock",
    },
}


# ---------------------------------------------------------------------------
# Allan deviation model
# ---------------------------------------------------------------------------

def allan_deviation(sigma_1s: float, tau_s: float,
                     flicker_floor: float = None,
                     tau_floor_s: float = 1.0) -> float:
    """
    Fractional frequency Allan deviation.
    Dominant regimes:
      White FM:   σ_y(τ) = σ_0 / √τ            (τ < τ_floor)
      Flicker FM: σ_y(τ) = σ_flicker            (τ ~ 1/f crossover)
      Random walk: σ_y(τ) ∝ τ^{+1/2}           (long τ, environment)

    Simple white FM model: σ_y(τ) = σ_1s / √τ
    With flicker floor: σ_y(τ) = √(σ_1s²/τ + σ_flicker²)
    """
    white_fm = sigma_1s / math.sqrt(max(tau_s, 1e-30))
    if flicker_floor is not None:
        return math.sqrt(white_fm ** 2 + flicker_floor ** 2)
    return white_fm


def averaging_time_for_accuracy(sigma_1s: float, accuracy: float) -> float:
    """
    Averaging time needed to reach a given accuracy:
    τ = (σ_1s / accuracy)²
    """
    if accuracy <= 0:
        return float("inf")
    return (sigma_1s / accuracy) ** 2


def stability_at_tau(clock_name: str, tau_s: float) -> float:
    """Allan deviation at averaging time τ for a named clock."""
    clk = CLOCK_TYPES[clock_name]
    return allan_deviation(clk["instability_1s"], tau_s)


# ---------------------------------------------------------------------------
# Historical improvement trajectory
# ---------------------------------------------------------------------------

def historical_trajectory() -> list:
    """
    Approximate historical accuracy improvement from 1955 to 2020.
    Values from Ludlow et al. 2015 + extensions.
    """
    trajectory = [
        {"year": 1955, "stability": 1e-9,  "type": "Cs_beam"},
        {"year": 1960, "stability": 1e-11, "type": "Cs_beam_improved"},
        {"year": 1970, "stability": 1e-12, "type": "Rb_standard"},
        {"year": 1975, "stability": 5e-13, "type": "H_maser"},
        {"year": 1991, "stability": 2e-14, "type": "Cs_fountain"},
        {"year": 1999, "stability": 2e-15, "type": "Cs_fountain_improved"},
        {"year": 2005, "stability": 5e-16, "type": "Cs_fountain_best"},
        {"year": 2008, "stability": 5e-17, "type": "Optical_early"},
        {"year": 2012, "stability": 2e-17, "type": "Sr_optical"},
        {"year": 2015, "stability": 2e-18, "type": "Sr_optical_best"},
        {"year": 2018, "stability": 1e-18, "type": "Al_plus"},
        {"year": 2021, "stability": 3e-19, "type": "Optical_projected"},
    ]
    return trajectory


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def simulate_clock_model(
        tau_values_s=None,
        averaging_time_s: float = 1e4) -> dict:
    """
    Compute Allan deviations for all clock types and historical trajectory.
    """
    if tau_values_s is None:
        tau_values_s = [1, 10, 100, 1000, 1e4, 1e5]

    results = {
        "clock_types": list(CLOCK_TYPES.keys()),
        "stabilities_at_1s": {
            name: CLOCK_TYPES[name]["instability_1s"]
            for name in CLOCK_TYPES
        },
        "tau_values_s": tau_values_s,
        "allan_deviations": {},
        "fractional_frequency_uncertainty": {},
        "averaging_time_to_accuracy_s": {},
        "historical_trajectory": historical_trajectory(),
    }

    print(f"\n{'Clock':20s}  {'σ_y(1s)':12s}  {'Accuracy':12s}  "
          f"{'τ to acc [s]':14s}")
    print("-" * 65)

    for name, clk in CLOCK_TYPES.items():
        sigmas = [round(allan_deviation(clk["instability_1s"], t), 22)
                  for t in tau_values_s]
        results["allan_deviations"][name] = sigmas

        # FFU at the accuracy limit
        results["fractional_frequency_uncertainty"][name] = clk["accuracy"]

        tau_acc = averaging_time_for_accuracy(
            clk["instability_1s"], clk["accuracy"])
        results["averaging_time_to_accuracy_s"][name] = round(tau_acc, 2)

        print(f"{name:20s}  {clk['instability_1s']:.2e}  "
              f"{clk['accuracy']:.2e}  {tau_acc:.2e}")

    # Show improvement span
    oldest = CLOCK_TYPES["Cs_fountain"]["accuracy"]
    newest = CLOCK_TYPES["Al_plus_optical"]["accuracy"]
    improvement = oldest / newest
    print(f"\nImprovement Cs→Al+: {improvement:.0e}x  "
          f"({math.log10(improvement):.1f} decades)")

    results["total_improvement_factor"] = improvement
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== Atomic Clock Stability Model ===")

    data = simulate_clock_model(
        tau_values_s=[1, 10, 100, 1000, 1e4, 1e5, 1e6],
    )

    os.makedirs("data", exist_ok=True)
    out_path = "data/clock_model_results.json"
    with open(out_path, "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    main()

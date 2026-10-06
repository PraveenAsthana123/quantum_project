"""
FPGA Real-Time Control Timing Simulation
Models FPGA control loop: measure → decode → feedback in <1μs
ADC sampling → threshold comparison → DAC output with full latency budget
"""
import numpy as np
import json
import os
from typing import Dict, List


# Latency budget constants (nanoseconds)
ADC_LATENCY_NS = 100      # ADC conversion time
PROCESSING_LATENCY_NS = 200   # FPGA logic: threshold decode + classical feedback
DAC_LATENCY_NS = 100      # DAC settling time
PROPAGATION_LATENCY_NS = 100  # Signal propagation delay (coax cables ~20 cm)
TOTAL_LATENCY_NS = ADC_LATENCY_NS + PROCESSING_LATENCY_NS + DAC_LATENCY_NS + PROPAGATION_LATENCY_NS


def simulate_adc_sampling(
    signal_amplitude: float,
    noise_amplitude: float,
    n_bits: int = 14,
    sample_rate_gsps: float = 1.0,
    n_samples: int = 1000,
    seed: int = 42,
) -> Dict:
    """
    Simulate ADC sampling of a qubit readout signal.
    Returns digitized samples and SNR.
    """
    rng = np.random.default_rng(seed)
    # Readout signal: IQ heterodyne measurement at IF ~250 MHz
    t = np.arange(n_samples) / (sample_rate_gsps * 1e9)
    if_freq = 250e6
    signal = signal_amplitude * np.cos(2 * np.pi * if_freq * t)
    noise = rng.normal(0, noise_amplitude, n_samples)
    measured = signal + noise

    # Quantize to n_bits
    v_max = 1.0
    lsb = 2 * v_max / (2 ** n_bits)
    quantized = np.round(measured / lsb).astype(int)
    quantized_v = quantized * lsb

    snr_db = 20 * np.log10(signal_amplitude / noise_amplitude) if noise_amplitude > 0 else 100.0
    return {
        "n_samples": n_samples,
        "sample_rate_gsps": sample_rate_gsps,
        "n_bits": n_bits,
        "snr_db": round(float(snr_db), 2),
        "signal_amplitude": signal_amplitude,
        "noise_amplitude": noise_amplitude,
        "rms_quantization_error": round(float(np.std(measured - quantized_v)), 6),
    }


def threshold_discrimination(
    iq_ground: np.ndarray,
    iq_excited: np.ndarray,
    threshold: float = 0.0,
) -> Dict:
    """
    Classify qubit state using threshold discrimination on I quadrature.
    Returns assignment fidelity.
    """
    ground_correct = np.sum(iq_ground < threshold)
    excited_correct = np.sum(iq_excited >= threshold)
    n = len(iq_ground)

    p_ground_correct = ground_correct / n
    p_excited_correct = excited_correct / n
    assignment_fidelity = (p_ground_correct + p_excited_correct) / 2.0

    return {
        "threshold": threshold,
        "p_ground_correct": round(float(p_ground_correct), 4),
        "p_excited_correct": round(float(p_excited_correct), 4),
        "assignment_fidelity": round(float(assignment_fidelity), 4),
    }


def simulate_dac_output(
    correction_angle_rad: float,
    dac_bits: int = 16,
    update_rate_msps: float = 1000.0,
) -> Dict:
    """
    Simulate DAC output for feedback correction pulse.
    Returns quantization noise and output fidelity.
    """
    lsb = 2.0 / (2 ** dac_bits)
    quantized = round(correction_angle_rad / lsb) * lsb
    quantization_error = abs(correction_angle_rad - quantized)
    update_period_ns = 1e3 / update_rate_msps  # ns

    return {
        "dac_bits": dac_bits,
        "update_rate_msps": update_rate_msps,
        "update_period_ns": round(update_period_ns, 2),
        "correction_angle_rad": round(correction_angle_rad, 6),
        "quantized_output": round(quantized, 8),
        "quantization_error_rad": round(quantization_error, 8),
        "lsb_rad": round(lsb, 8),
    }


def compute_feedback_fidelity(
    total_latency_ns: float,
    t2_us: float = 100.0,
    t1_us: float = 200.0,
    n_rounds: int = 100,
) -> float:
    """
    Estimate feedback fidelity considering decoherence during latency.
    F ≈ exp(-t_latency / T2) for phase-sensitive correction.
    """
    t_latency_us = total_latency_ns * 1e-3
    decay_per_round = np.exp(-t_latency_us / t2_us)
    cumulative_fidelity = decay_per_round ** n_rounds
    return round(float(cumulative_fidelity), 6)


def run_latency_budget_analysis() -> List[Dict]:
    """
    Full latency budget breakdown with Monte Carlo variation.
    """
    rng = np.random.default_rng(0)
    n_trials = 1000

    # Model timing jitter at each stage (1-sigma values in ns)
    adc_jitter = 5.0
    proc_jitter = 10.0
    dac_jitter = 5.0
    prop_jitter = 2.0

    adc_samples = rng.normal(ADC_LATENCY_NS, adc_jitter, n_trials)
    proc_samples = rng.normal(PROCESSING_LATENCY_NS, proc_jitter, n_trials)
    dac_samples = rng.normal(DAC_LATENCY_NS, dac_jitter, n_trials)
    prop_samples = rng.normal(PROPAGATION_LATENCY_NS, prop_jitter, n_trials)
    total_samples = adc_samples + proc_samples + dac_samples + prop_samples

    results = []
    for trial in range(5):  # Report first 5 trials
        results.append({
            "trial": trial + 1,
            "adc_latency_ns": round(float(adc_samples[trial]), 2),
            "processing_latency_ns": round(float(proc_samples[trial]), 2),
            "dac_latency_ns": round(float(dac_samples[trial]), 2),
            "propagation_latency_ns": round(float(prop_samples[trial]), 2),
            "total_latency_ns": round(float(total_samples[trial]), 2),
        })

    # Summary across all trials
    summary = {
        "trial": "summary",
        "adc_latency_ns": ADC_LATENCY_NS,
        "processing_latency_ns": PROCESSING_LATENCY_NS,
        "dac_latency_ns": DAC_LATENCY_NS,
        "propagation_latency_ns": PROPAGATION_LATENCY_NS,
        "total_latency_ns": TOTAL_LATENCY_NS,
        "mean_total_ns": round(float(np.mean(total_samples)), 2),
        "std_total_ns": round(float(np.std(total_samples)), 2),
        "p99_total_ns": round(float(np.percentile(total_samples, 99)), 2),
        "below_1us_pct": round(float(np.mean(total_samples < 1000) * 100), 2),
        "feedback_fidelity": compute_feedback_fidelity(TOTAL_LATENCY_NS),
    }
    results.append(summary)
    return results


def main():
    print("=" * 60)
    print("FPGA Real-Time Control Timing Simulation")
    print("=" * 60)

    # ADC simulation
    print("\n[1] ADC Sampling Simulation")
    adc_result = simulate_adc_sampling(signal_amplitude=0.8, noise_amplitude=0.05)
    print(f"  SNR          : {adc_result['snr_db']} dB")
    print(f"  Quant error  : {adc_result['rms_quantization_error']:.6f} V")

    # Threshold discrimination
    print("\n[2] Threshold Discrimination")
    rng = np.random.default_rng(1)
    iq_g = rng.normal(-0.5, 0.1, 500)
    iq_e = rng.normal(+0.5, 0.1, 500)
    disc = threshold_discrimination(iq_g, iq_e, threshold=0.0)
    print(f"  Assignment fidelity: {disc['assignment_fidelity']:.4f}")

    # DAC output
    print("\n[3] DAC Correction Output")
    dac_result = simulate_dac_output(correction_angle_rad=0.05)
    print(f"  Quantization error: {dac_result['quantization_error_rad']:.2e} rad")

    # Latency budget
    print("\n[4] Latency Budget Analysis")
    print(f"  ADC        : {ADC_LATENCY_NS} ns")
    print(f"  Processing : {PROCESSING_LATENCY_NS} ns")
    print(f"  DAC        : {DAC_LATENCY_NS} ns")
    print(f"  Propagation: {PROPAGATION_LATENCY_NS} ns")
    print(f"  Total      : {TOTAL_LATENCY_NS} ns  (<1μs: {'YES' if TOTAL_LATENCY_NS < 1000 else 'NO'})")

    latency_results = run_latency_budget_analysis()
    summary = latency_results[-1]
    print(f"  Mean (MC)  : {summary['mean_total_ns']:.1f} ± {summary['std_total_ns']:.1f} ns")
    print(f"  <1μs rate  : {summary['below_1us_pct']:.1f}%")
    print(f"  Feedback fidelity: {summary['feedback_fidelity']:.6f}")

    # Build output record
    output = {
        "adc_latency_ns": ADC_LATENCY_NS,
        "processing_latency_ns": PROCESSING_LATENCY_NS,
        "dac_latency_ns": DAC_LATENCY_NS,
        "propagation_latency_ns": PROPAGATION_LATENCY_NS,
        "total_latency_ns": TOTAL_LATENCY_NS,
        "feedback_fidelity": summary["feedback_fidelity"],
        "adc_snr_db": adc_result["snr_db"],
        "assignment_fidelity": disc["assignment_fidelity"],
        "below_1us_pct": summary["below_1us_pct"],
        "monte_carlo_mean_ns": summary["mean_total_ns"],
        "monte_carlo_std_ns": summary["std_total_ns"],
        "latency_trials": latency_results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "fpga_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()

"""
AWG (Arbitrary Waveform Generator) Pulse Sequence Simulation
Models IQ pulse generation for qubit control: baseband I/Q → upconversion → microwave pulse
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple


def generate_gaussian_envelope(t: np.ndarray, sigma: float, amplitude: float = 1.0) -> np.ndarray:
    """Generate a Gaussian pulse envelope."""
    return amplitude * np.exp(-0.5 * (t / sigma) ** 2)


def generate_drag_pulse(
    t: np.ndarray, sigma: float, beta: float = 0.5, amplitude: float = 1.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate DRAG (Derivative Removal via Adiabatic Gate) pulse.
    DRAG suppresses leakage to non-computational states.
    Returns (I_quadrature, Q_quadrature).
    """
    envelope = generate_gaussian_envelope(t, sigma, amplitude)
    d_envelope = -envelope * t / sigma ** 2  # derivative
    i_quad = envelope
    q_quad = beta * d_envelope
    return i_quad, q_quad


def upconvert_iq(
    i_quad: np.ndarray,
    q_quad: np.ndarray,
    t: np.ndarray,
    lo_freq_ghz: float,
) -> np.ndarray:
    """
    Upconvert baseband IQ signal to microwave frequency.
    s(t) = I(t)*cos(2π*f_LO*t) - Q(t)*sin(2π*f_LO*t)
    """
    lo_rad = 2 * np.pi * lo_freq_ghz * 1e9
    return i_quad * np.cos(lo_rad * t) - q_quad * np.sin(lo_rad * t)


def compute_rotation_fidelity(i_quad: np.ndarray, q_quad: np.ndarray, target_angle_rad: float) -> float:
    """
    Compute approximate pulse fidelity based on area condition.
    Ideal rotation requires ∫Ω(t)dt = target_angle.
    """
    dt = 1e-9  # 1 ns timestep
    pulse_area = np.trapezoid(np.sqrt(i_quad ** 2 + q_quad ** 2), dx=dt) if hasattr(np, 'trapezoid') else np.trapz(np.sqrt(i_quad ** 2 + q_quad ** 2), dx=dt)
    omega_rabi = target_angle_rad  # normalized to target
    if omega_rabi == 0:
        return 1.0
    error = abs(pulse_area - omega_rabi) / abs(omega_rabi)
    fidelity = max(0.0, 1.0 - error)
    return round(float(fidelity), 6)


def compute_fft_spectrum(signal: np.ndarray, dt_ns: float) -> Dict:
    """Compute FFT power spectrum of the microwave pulse."""
    n = len(signal)
    if n < 2:
        return {"frequencies_GHz": [0.0], "power_spectrum": [0.0]}
    freqs = np.fft.rfftfreq(n, d=dt_ns * 1e-9) / 1e9  # GHz
    fft_vals = np.fft.rfft(signal)
    power = (np.abs(fft_vals) ** 2 / n).tolist()
    freqs_list = freqs.tolist()
    return {"frequencies_GHz": freqs_list[:50], "power_spectrum": power[:50]}


def simulate_pulse(
    pulse_type: str,
    duration_ns: float,
    qubit_freq_ghz: float,
    amplitude: float = 0.5,
    beta_drag: float = 0.5,
) -> Dict:
    """
    Simulate a single AWG pulse and return characterization data.
    pulse_type: 'X', 'Y', 'Z', 'X/2', 'Y/2'
    """
    dt_ns = 1.0
    n_samples = int(duration_ns / dt_ns)
    t_ns = np.linspace(-duration_ns / 2, duration_ns / 2, n_samples)
    t_s = t_ns * 1e-9
    sigma = duration_ns / 6.0  # sigma = duration/6 for Gaussian

    target_angles = {
        "X": np.pi,
        "Y": np.pi,
        "Z": np.pi,
        "X/2": np.pi / 2,
        "Y/2": np.pi / 2,
    }
    target_angle = target_angles.get(pulse_type, np.pi)

    if pulse_type in ("X", "X/2"):
        i_quad, q_quad = generate_drag_pulse(t_ns, sigma, beta=beta_drag, amplitude=amplitude)
    elif pulse_type in ("Y", "Y/2"):
        # Y pulse: swap I and Q vs X
        q_raw, i_raw = generate_drag_pulse(t_ns, sigma, beta=beta_drag, amplitude=amplitude)
        i_quad, q_quad = i_raw, q_raw
    elif pulse_type == "Z":
        # Virtual Z gate: no physical pulse needed, modeled as phase shift
        i_quad = np.zeros(n_samples)
        q_quad = np.zeros(n_samples)
    else:
        i_quad = generate_gaussian_envelope(t_ns, sigma, amplitude)
        q_quad = np.zeros(n_samples)

    # Upconversion to microwave
    microwave = upconvert_iq(i_quad, q_quad, t_s, qubit_freq_ghz)

    # Compute spectrum
    spectrum = compute_fft_spectrum(microwave, dt_ns)

    # Fidelity estimate
    fidelity = compute_rotation_fidelity(i_quad, q_quad, target_angle)

    iq_amplitude = float(np.max(np.sqrt(i_quad ** 2 + q_quad ** 2)))

    return {
        "pulse_type": pulse_type,
        "duration_ns": duration_ns,
        "frequency_GHz": qubit_freq_ghz,
        "iq_amplitude": round(iq_amplitude, 6),
        "fidelity": fidelity,
        "spectrum_data": spectrum,
        "n_samples": n_samples,
        "sigma_ns": round(sigma, 3),
        "beta_drag": beta_drag,
    }


def main():
    print("=" * 60)
    print("AWG Pulse Sequence Simulation")
    print("=" * 60)

    qubit_freq_ghz = 5.0  # Typical transmon qubit frequency
    results = []

    pulse_configs = [
        ("X", 40.0),    # Pi pulse ~40 ns
        ("Y", 40.0),
        ("Z", 4.0),     # Virtual Z (phase update, minimal physical pulse)
        ("X/2", 40.0),  # Half-pi pulse
        ("Y/2", 40.0),
    ]

    for pulse_type, duration in pulse_configs:
        print(f"\nSimulating {pulse_type} pulse ({duration} ns @ {qubit_freq_ghz} GHz) ...")
        result = simulate_pulse(
            pulse_type=pulse_type,
            duration_ns=duration,
            qubit_freq_ghz=qubit_freq_ghz,
            amplitude=0.5,
            beta_drag=0.5,
        )
        results.append(result)
        print(f"  IQ amplitude : {result['iq_amplitude']:.4f}")
        print(f"  Fidelity     : {result['fidelity']:.6f}")
        peak_freq_idx = int(np.argmax(result["spectrum_data"]["power_spectrum"]))
        peak_freq = result["spectrum_data"]["frequencies_GHz"][peak_freq_idx]
        print(f"  Peak spectral freq: {peak_freq:.3f} GHz")

    # Save results
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "awg_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    print(f"Total pulses simulated: {len(results)}")


if __name__ == "__main__":
    main()

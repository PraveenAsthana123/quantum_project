"""
Synthetic data generator for all 30 Quantum Portal projects.
Each dataset is saved to /mnt/deepa/quantum/data/{project_id}_dataset.csv
and registered in the SQLite DB via database.insert_dataset().
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path("/mnt/deepa/quantum/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(seed=42)


# ---------------------------------------------------------------------------
# Generator helpers
# ---------------------------------------------------------------------------

def _csv_path(project_id: str) -> Path:
    return DATA_DIR / f"{project_id}_dataset.csv"


def _save(df: pd.DataFrame, project_id: str) -> str:
    path = _csv_path(project_id)
    df.to_csv(path, index=False)
    return str(path)


def _float(lo: float, hi: float, n: int) -> np.ndarray:
    return RNG.uniform(lo, hi, n).astype(float)


def _int(lo: int, hi: int, n: int) -> np.ndarray:
    return RNG.integers(lo, hi + 1, n)


def _choice(options: list, n: int) -> np.ndarray:
    return RNG.choice(options, n)


# ---------------------------------------------------------------------------
# Per-project generators
# ---------------------------------------------------------------------------

GENERATORS: Dict[str, callable] = {}


def _reg(project_id: str):
    def decorator(fn):
        GENERATORS[project_id] = fn
        return fn
    return decorator


@_reg("q01-algorithms")
def gen_q01(n=1000):
    labels = _choice(["grover", "qft", "teleportation", "phase_estimation"], n)
    return pd.DataFrame({
        "circuit_depth":  _int(2, 40, n),
        "gate_count":     _int(5, 120, n),
        "fidelity":       _float(0.85, 1.0, n).round(4),
        "speedup":        _float(1.0, 16.0, n).round(3),
        "n_qubits":       _int(2, 8, n),
        "shots":          _choice([512, 1024, 2048, 4096], n),
        "algorithm_type": labels,
    })


@_reg("q02-error-mitigation")
def gen_q02(n=1000):
    mit_types = _choice(["ZNE", "PEC", "mthree", "readout"], n)
    fid_before = _float(0.60, 0.95, n)
    fid_after  = np.clip(fid_before + _float(0.01, 0.15, n), 0, 1)
    return pd.DataFrame({
        "noise_rate":       _float(0.001, 0.05, n).round(4),
        "mitigation_type":  mit_types,
        "fidelity_before":  fid_before.round(4),
        "fidelity_after":   fid_after.round(4),
        "overhead_factor":  _float(1.0, 5.0, n).round(2),
        "circuit_depth":    _int(3, 30, n),
        "improvement_pct":  ((fid_after - fid_before) / (fid_before + 1e-9) * 100).round(2),
    })


@_reg("q03-ftqc")
def gen_q03(n=500):
    code_dist = _choice([3, 5, 7, 9, 11], n)
    physical_q = code_dist ** 2
    logical_err = 10 ** _float(-8, -4, n)
    return pd.DataFrame({
        "code_distance":      code_dist,
        "logical_error_rate": logical_err.round(10),
        "physical_qubits":    physical_q,
        "logical_qubits":     np.ones(n, dtype=int),
        "syndrome_count":     code_dist ** 2 - 1,
        "overhead_ratio":     physical_q.astype(float),
        "threshold_pct":      _float(0.5, 1.1, n).round(3),
        "correction_code":    _choice(["surface", "steane", "reed_muller"], n),
    })


@_reg("q04-compiler")
def gen_q04(n=1000):
    in_gates = _int(20, 200, n)
    reduction = _float(0.05, 0.40, n)
    out_gates = (in_gates * (1 - reduction)).astype(int)
    return pd.DataFrame({
        "input_gates":        in_gates,
        "output_gates":       out_gates,
        "depth_before":       _int(10, 100, n),
        "depth_after":        _int(5, 80, n),
        "compilation_time_ms": _float(2.0, 500.0, n).round(2),
        "cnot_reduction_pct": _float(0.0, 35.0, n).round(2),
        "optimization_level": _choice([1, 2, 3], n),
        "tool":               _choice(["qiskit", "tket", "bqskit"], n),
    })


@_reg("q05-ir-interop")
def gen_q05(n=500):
    fmt_pairs = [("qasm2","qasm3"), ("qasm2","quil"), ("qasm3","cirq_json"),
                 ("openqasm","quil"), ("pytket_json","qasm2")]
    pairs = _choice(fmt_pairs, n)
    return pd.DataFrame({
        "source_format":       [p[0] for p in pairs],
        "target_format":       [p[1] for p in pairs],
        "translation_fidelity": _float(0.92, 1.0, n).round(4),
        "gate_count":          _int(5, 80, n),
        "translation_time_ms": _float(0.5, 50.0, n).round(2),
        "semantic_equivalence": _choice([True, True, True, False], n),
    })


@_reg("q06-transpilation")
def gen_q06(n=500):
    return pd.DataFrame({
        "circuit_equivalence_score": _float(0.90, 1.0, n).round(4),
        "optimization_level":        _choice([1, 2, 3], n),
        "swap_count":                _int(0, 20, n),
        "cx_count_before":           _int(5, 60, n),
        "cx_count_after":            _int(3, 50, n),
        "depth_before":              _int(10, 80, n),
        "depth_after":               _int(5, 70, n),
        "backend":                   _choice(["ibmq_lima","ibmq_quito","ibm_nairobi"], n),
    })


@_reg("q07-cloud-qpu")
def gen_q07(n=500):
    backends = _choice(["ibm_nairobi","ibm_brisbane","aws_sv1","ionq_aria","quantinuum_h2"], n)
    return pd.DataFrame({
        "backend":        backends,
        "queue_time_s":   _float(0, 3600, n).round(1),
        "execution_time_ms": _float(10, 5000, n).round(1),
        "success_rate":   _float(0.70, 0.995, n).round(4),
        "n_qubits":       _int(2, 27, n),
        "shots":          _choice([512, 1024, 4096, 8192], n),
        "job_status":     _choice(["completed","completed","completed","error","timeout"], n),
    })


@_reg("q08-distributed-qc")
def gen_q08(n=500):
    n_parts = _choice([2, 3, 4, 5], n)
    cut_q = n_parts - 1
    return pd.DataFrame({
        "n_partitions":           n_parts,
        "cut_qubits":             cut_q,
        "reconstruction_fidelity": _float(0.80, 0.99, n).round(4),
        "sampling_overhead":      (4.0 ** cut_q).astype(float).round(2),
        "total_qubits":           _int(6, 20, n),
        "classical_comm_bits":    _int(10, 1000, n),
        "latency_ms":             _float(50, 5000, n).round(1),
    })


@_reg("q09-circuit-cutting")
def gen_q09(n=500):
    cut_size = _int(1, 6, n)
    return pd.DataFrame({
        "cut_size":          cut_size,
        "sampling_overhead": (4.0 ** cut_size).round(2),
        "fidelity":          _float(0.85, 0.99, n).round(4),
        "speedup":           _float(1.0, 4.0, n).round(3),
        "n_subcircuits":     cut_size + 1,
        "shots_per_sub":     _choice([256, 512, 1024], n),
        "method":            _choice(["gate_cut","wire_cut","hybrid_cut"], n),
    })


@_reg("q10-silicon-spin")
def gen_q10(n=500):
    return pd.DataFrame({
        "exchange_coupling_mhz": _float(1.0, 100.0, n).round(3),
        "gate_fidelity":         _float(0.990, 0.9999, n).round(5),
        "coherence_time_us":     _float(10, 500, n).round(2),
        "T1_us":                 _float(100, 2000, n).round(2),
        "T2_us":                 _float(20, 500, n).round(2),
        "qubit_type":            _choice(["spin_up","spin_down"], n),
        "dot_count":             _int(2, 6, n),
        "temperature_mk":        _float(10, 50, n).round(1),
    })


@_reg("q11-topological")
def gen_q11(n=300):
    return pd.DataFrame({
        "anyon_type":               _choice(["fibonacci","ising","Z3_parafermion"], n),
        "braiding_sequence_length": _int(4, 50, n),
        "topological_protection":   _float(0.990, 0.99999, n).round(6),
        "gate_type":                _choice(["cnot","t","hadamard","phase"], n),
        "fusion_outcome":           _choice([0, 1], n),
        "braiding_fidelity":        _float(0.995, 1.0, n).round(5),
    })


@_reg("q12-analog-qc")
def gen_q12(n=500):
    return pd.DataFrame({
        "squeezing_db":           _float(3.0, 15.0, n).round(2),
        "entanglement_entropy":   _float(0.1, 2.0, n).round(4),
        "teleportation_fidelity": _float(0.75, 0.99, n).round(4),
        "mode_count":             _int(2, 20, n),
        "photon_loss_pct":        _float(0.5, 20.0, n).round(2),
        "detector_efficiency":    _float(0.7, 0.99, n).round(3),
        "platform":               _choice(["xanadu_borealis","gaussian_boson","twin_beam"], n),
    })


@_reg("q13-control")
def gen_q13(n=500):
    return pd.DataFrame({
        "control_fidelity":             _float(0.980, 0.9999, n).round(5),
        "feedback_delay_ns":            _float(50, 500, n).round(1),
        "state_discrimination_accuracy": _float(0.95, 0.9999, n).round(5),
        "pulse_duration_ns":            _float(10, 100, n).round(1),
        "bandwidth_mhz":                _float(50, 500, n).round(1),
        "crosstalk_pct":                _float(0.0, 2.0, n).round(3),
        "scheme":                       _choice(["pid","mpc","reinforcement_learning"], n),
    })


@_reg("q14-calibration")
def gen_q14(n=500):
    return pd.DataFrame({
        "gate_error_rate":    _float(1e-4, 5e-3, n).round(6),
        "readout_error_rate": _float(5e-4, 3e-2, n).round(6),
        "T1_us":              _float(50, 500, n).round(2),
        "T2_us":              _float(30, 300, n).round(2),
        "rb_fidelity":        _float(0.995, 0.9999, n).round(5),
        "method":             _choice(["rb","gst","qpt","xeb"], n),
        "qubit_id":           _int(0, 26, n),
    })


@_reg("q15-readout")
def gen_q15(n=500):
    return pd.DataFrame({
        "assignment_error":          _float(0.001, 0.05, n).round(4),
        "readout_frequency_ghz":     _float(6.0, 8.5, n).round(4),
        "SNR":                       _float(5, 50, n).round(2),
        "discrimination_fidelity":   _float(0.95, 0.9999, n).round(5),
        "integration_time_ns":       _float(200, 2000, n).round(0),
        "state_0_population":        _float(0.45, 0.55, n).round(4),
        "method":                    _choice(["heterodyne","homodyne","parametric_amplifier"], n),
    })


@_reg("q16-ctrl-electronics")
def gen_q16(n=300):
    return pd.DataFrame({
        "pulse_duration_ns": _float(10, 200, n).round(1),
        "amplitude":         _float(0.1, 1.0, n).round(4),
        "frequency_ghz":     _float(4.5, 8.5, n).round(4),
        "gate_fidelity":     _float(0.990, 0.9999, n).round(5),
        "DRAG_alpha":        _float(-0.5, 0.0, n).round(4),
        "leakage_pct":       _float(0.0, 0.5, n).round(4),
        "channel":           _int(0, 7, n),
        "waveform_type":     _choice(["gaussian","drag","square","cosine"], n),
    })


@_reg("q17-cryogenics")
def gen_q17(n=300):
    return pd.DataFrame({
        "temperature_mk":    _float(5, 20, n).round(1),
        "cooling_power_mw":  _float(0.1, 5.0, n).round(2),
        "qubit_count":       _int(4, 100, n),
        "coherence_time_us": _float(50, 1000, n).round(2),
        "stage":             _choice(["4K","still","cold_plate","mixing_chamber"], n),
        "heat_load_uw":      _float(1, 100, n).round(2),
        "cooldown_hours":    _float(8, 72, n).round(1),
    })


@_reg("q18-fabrication")
def gen_q18(n=300):
    return pd.DataFrame({
        "junction_resistance_ohm": _float(5e3, 15e3, n).round(0),
        "critical_current_na":     _float(10, 100, n).round(2),
        "capacitance_ff":          _float(50, 200, n).round(2),
        "Q_factor":                _float(1e5, 5e6, n).round(0),
        "frequency_ghz":           _float(4.0, 8.0, n).round(4),
        "anharmonicity_mhz":       _float(-350, -200, n).round(1),
        "wafer_id":                _int(1, 50, n),
        "yield_pct":               _float(60, 98, n).round(1),
    })


@_reg("q19-packaging")
def gen_q19(n=300):
    return pd.DataFrame({
        "bond_wire_length_um":   _float(200, 2000, n).round(0),
        "parasitic_inductance_ph": _float(0.1, 5.0, n).round(3),
        "thermal_resistance_k_w": _float(0.5, 10.0, n).round(3),
        "yield_pct":             _float(60, 99, n).round(1),
        "substrate_type":        _choice(["sapphire","silicon","fused_silica"], n),
        "flip_chip":             _choice([True, False], n),
        "bump_count":            _int(10, 200, n),
    })


@_reg("q20-chemistry")
def gen_q20(n=500):
    molecules = _choice(["H2","LiH","BeH2","H2O","NH3","N2","CH4"], n)
    fci_energy = _float(-75.0, -2.0, n)
    vqe_error  = _float(0.0001, 0.01, n)
    return pd.DataFrame({
        "molecule":     molecules,
        "n_electrons":  _int(2, 20, n),
        "n_orbitals":   _int(2, 16, n),
        "vqe_energy":   (fci_energy + vqe_error).round(6),
        "fci_energy":   fci_energy.round(6),
        "accuracy_mha": (vqe_error * 1000).round(4),
        "ansatz":       _choice(["UCCSD","k_UpCCGSD","hardware_efficient"], n),
        "iterations":   _int(20, 300, n),
    })


@_reg("q21-many-body")
def gen_q21(n=500):
    return pd.DataFrame({
        "system_size":          _int(4, 50, n),
        "filling_fraction":     _float(0.25, 0.75, n).round(3),
        "ground_energy":        _float(-50.0, -5.0, n).round(4),
        "entanglement_entropy": _float(0.1, 5.0, n).round(4),
        "model":                _choice(["ising_1d","heisenberg","hubbard","bose_hubbard"], n),
        "bond_dimension":       _choice([16, 32, 64, 128, 256], n),
        "trotter_steps":        _int(10, 200, n),
    })


@_reg("q22-repeaters")
def gen_q22(n=500):
    dist = _float(10, 1000, n)
    rate = 1e4 / (dist + 1) * _float(0.5, 1.5, n)
    return pd.DataFrame({
        "link_distance_km":   dist.round(1),
        "entanglement_rate_hz": rate.round(3),
        "fidelity":           _float(0.80, 0.99, n).round(4),
        "secret_key_rate_bps": (rate * 0.6).round(3),
        "n_repeaters":        _int(0, 10, n),
        "protocol":           _choice(["DLCZ","single_photon","two_photon"], n),
        "memory_time_ms":     _float(1, 1000, n).round(2),
    })


@_reg("q23-memory")
def gen_q23(n=300):
    return pd.DataFrame({
        "storage_time_us":     _float(1, 10000, n).round(2),
        "retrieval_efficiency": _float(0.50, 0.95, n).round(4),
        "fidelity":            _float(0.75, 0.99, n).round(4),
        "bandwidth_mhz":       _float(0.1, 100, n).round(3),
        "mode_count":          _int(1, 100, n),
        "material":            _choice(["praseodymium","rare_earth_crystal","atomic_vapor","nv_center"], n),
        "wavelength_nm":       _choice([606, 780, 852, 1310, 1550], n),
    })


@_reg("q24-internet")
def gen_q24(n=1000):
    key_sent = _int(100, 10000, n)
    qber     = _float(0.01, 0.12, n)
    sifted   = (key_sent * (1 - qber)).astype(int)
    return pd.DataFrame({
        "key_bits_sent":     key_sent,
        "key_bits_received": sifted,
        "QBER":              qber.round(4),
        "secret_key_rate_bps": (sifted * _float(0.5, 0.9, n)).astype(int),
        "eavesdrop_detected": (qber > 0.08).astype(int),
        "protocol":          _choice(["BB84","E91","B92","SARG04"], n),
        "channel_length_km": _float(1, 200, n).round(1),
    })


@_reg("q25-sensing")
def gen_q25(n=500):
    sql_ratio = _float(0.1, 1.0, n)
    hl_ratio  = sql_ratio * _float(0.5, 0.99, n)
    return pd.DataFrame({
        "sensitivity":            _float(1e-12, 1e-8, n),
        "SNR_improvement_dB":     _float(1, 15, n).round(2),
        "measurement_time_us":    _float(1, 1000, n).round(2),
        "SQL_ratio":              sql_ratio.round(4),
        "HL_ratio":               hl_ratio.round(4),
        "probe_state":            _choice(["GHZ","NOON","spin_squeezed","fock"], n),
        "n_probe_qubits":         _int(2, 20, n),
    })


@_reg("q26-metrology")
def gen_q26(n=500):
    return pd.DataFrame({
        "frequency_accuracy_hz":    _float(1e-5, 1.0, n),
        "stability_sigma":          _float(1e-16, 1e-13, n),
        "clock_type":               _choice(["optical_lattice","ion_trap","atomic_fountain"], n),
        "quantum_projection_noise":  _float(1e-10, 1e-8, n),
        "averaging_time_s":         _float(1, 1000, n).round(1),
        "atoms_count":              _int(100, 100000, n),
        "interrogation_time_ms":    _float(50, 1000, n).round(1),
    })


@_reg("q27-clocks")
def gen_q27(n=500):
    return pd.DataFrame({
        "tick_frequency_hz":      _float(1e9, 3e15, n),
        "drift_ppm":              _float(0.001, 50.0, n).round(4),
        "temperature_coefficient_ppb_k": _float(0.01, 5.0, n).round(4),
        "coherence_time_s":       _float(0.01, 100.0, n).round(3),
        "clock_type":             _choice(["TCXO","OCXO","atomic_Cs","optical","quantum_enhanced"], n),
        "power_mw":               _float(1, 5000, n).round(1),
        "allan_deviation_1s":     _float(1e-15, 1e-11, n),
    })


@_reg("q28-qml")
def gen_q28(n=1000):
    n_q = _choice([2, 4, 6, 8], n)
    n_l = _choice([1, 2, 3, 4], n)
    class_base = _float(0.85, 0.97, n)
    q_acc = class_base + _float(-0.05, 0.08, n)
    return pd.DataFrame({
        "n_qubits":          n_q,
        "n_layers":          n_l,
        "accuracy":          np.clip(q_acc, 0, 1).round(4),
        "f1_score":          np.clip(q_acc - _float(0, 0.05, n), 0, 1).round(4),
        "training_time_s":   _float(30, 3600, n).round(1),
        "classical_baseline": class_base.round(4),
        "quantum_advantage": (q_acc - class_base).round(4),
        "dataset":           _choice(["mnist_2class","fashion_mnist","iris","breast_cancer"], n),
        "optimizer":         _choice(["adam","spsa","rotosolve"], n),
    })


@_reg("qc-banking-lab")
def gen_banking(n=5000):
    amounts = np.exp(_float(1, 10, n))
    fraud = (
        (amounts > 1000) &
        (_choice([True, False, False, False], n)) |
        (_choice([True, False, False, False, False, False, False, False, False, False], n))
    ).astype(int)
    return pd.DataFrame({
        "amount":            amounts.round(2),
        "merchant_category": _choice(["grocery","travel","online","restaurant","atm","luxury"], n),
        "time_of_day_h":     _float(0, 24, n).round(2),
        "day_of_week":       _int(0, 6, n),
        "n_transactions_1h": _int(0, 20, n),
        "distance_from_home_km": _float(0, 5000, n).round(1),
        "card_present":      _choice([1, 0], n),
        "quantum_score":     _float(0.0, 1.0, n).round(4),
        "classical_score":   _float(0.0, 1.0, n).round(4),
        "fraud_label":       fraud,
    })


@_reg("qc-finance-lab")
def gen_finance(n=2000):
    n_assets = _choice([5, 10, 15, 20, 25, 30], n)
    returns  = _float(-0.05, 0.20, n)
    vol      = _float(0.05, 0.40, n)
    sharpe_q = returns / vol + _float(-0.1, 0.3, n)
    return pd.DataFrame({
        "n_assets":            n_assets,
        "expected_return":     returns.round(4),
        "volatility":          vol.round(4),
        "sharpe_ratio":        (returns / vol).round(4),
        "quantum_sharpe":      sharpe_q.round(4),
        "max_drawdown":        _float(-0.3, 0.0, n).round(4),
        "optimization_method": _choice(["QAOA","VQE","classical_qp","markowitz"], n),
        "quantum_optimized":   _choice([1, 1, 0], n),
        "improvement_pct":     _float(-2, 10, n).round(2),
    })


@_reg("qc-healthcare-lab")
def gen_healthcare(n=1000):
    eeg = {f"eeg_feature_{i}": _float(-2, 2, n).round(4) for i in range(10)}
    seizure_prob = 1 / (1 + np.exp(-(_float(-3, 3, n))))
    label = (seizure_prob > 0.5).astype(int)
    df = pd.DataFrame(eeg)
    df["seizure_label"]      = label
    df["seizure_probability"] = seizure_prob.round(4)
    df["quantum_prediction"] = np.clip(seizure_prob + _float(-0.1, 0.1, n), 0, 1).round(4)
    df["patient_age"]        = _int(5, 85, n)
    df["recording_minutes"]  = _float(10, 60, n).round(1)
    df["channel_count"]      = _choice([19, 32, 64, 128, 256], n)
    return df


@_reg("qc-logistics-lab")
def gen_logistics(n=500):
    n_nodes = _choice([5, 10, 15, 20, 25], n)
    n_veh   = _choice([2, 3, 4, 5], n)
    dist_c  = (n_nodes * _float(8, 20, n)).round(1)
    dist_q  = (dist_c * _float(0.85, 1.05, n)).round(1)
    return pd.DataFrame({
        "n_nodes":                 n_nodes,
        "n_vehicles":              n_veh,
        "total_distance_km":       dist_c,
        "quantum_distance_km":     dist_q,
        "improvement_pct":         ((dist_c - dist_q) / dist_c * 100).round(2),
        "time_window_tight":       _choice([True, False], n),
        "capacity_constraint":     _choice([True, True, False], n),
        "solver":                  _choice(["QAOA","VQE","D-Wave_BQM","classical_OR"], n),
        "solve_time_s":            _float(0.1, 120, n).round(2),
    })


@_reg("qc-security-lab")
def gen_security(n=1000):
    qber = _float(0.005, 0.15, n)
    return pd.DataFrame({
        "protocol":           _choice(["BB84","E91","Kyber1024","Dilithium3","SPHINCS+"], n),
        "key_rate_bps":       _float(100, 50000, n).round(0),
        "QBER":               qber.round(4),
        "eavesdrop_detected": (qber > 0.09).astype(int),
        "pqc_algorithm":      _choice(["Kyber1024","Dilithium3","SPHINCS+","Falcon512"], n),
        "key_length_bits":    _choice([128, 256, 512, 1024, 2048], n),
        "session_duration_s": _float(1, 3600, n).round(0),
        "security_level":     _choice([1, 3, 5], n),
    })


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def generate_all_datasets(db_register: bool = True) -> Dict[str, str]:
    """
    Generate all synthetic datasets, save CSVs, optionally register in DB.
    Returns {project_id: file_path}.
    """
    from database import insert_dataset  # avoid circular import at module level

    results: Dict[str, str] = {}
    for project_id, gen_fn in GENERATORS.items():
        try:
            path = _csv_path(project_id)
            if path.exists():
                logger.info("Dataset already exists: %s", path)
                results[project_id] = str(path)
                # Still register in DB (INSERT OR IGNORE is safe)
                if db_register:
                    df = pd.read_csv(path, nrows=1)
                    n_rows = sum(1 for _ in open(path)) - 1  # subtract header
                    await insert_dataset(
                        project_id=project_id,
                        name=f"{project_id}_synthetic",
                        source="synthetic",
                        n_samples=n_rows,
                        n_features=len(df.columns),
                        file_path=str(path),
                        description=f"Synthetic dataset for {project_id}",
                        is_synthetic=True,
                    )
                continue

            df = gen_fn()
            fpath = _save(df, project_id)
            results[project_id] = fpath
            logger.info("Generated %s: %d rows × %d cols → %s",
                        project_id, len(df), len(df.columns), fpath)

            if db_register:
                await insert_dataset(
                    project_id=project_id,
                    name=f"{project_id}_synthetic",
                    source="synthetic",
                    n_samples=len(df),
                    n_features=len(df.columns),
                    file_path=fpath,
                    description=f"Synthetic dataset for {project_id}",
                    is_synthetic=True,
                )
        except Exception as exc:
            logger.error("data_gen failed for %s: %s", project_id, exc)

    return results


def generate_all_datasets_sync() -> Dict[str, str]:
    """Synchronous wrapper — used during startup before the event loop runs."""
    results: Dict[str, str] = {}
    for project_id, gen_fn in GENERATORS.items():
        try:
            path = _csv_path(project_id)
            if path.exists():
                results[project_id] = str(path)
                continue
            df = gen_fn()
            fpath = _save(df, project_id)
            results[project_id] = fpath
            logger.info("Generated (sync) %s: %d rows", project_id, len(df))
        except Exception as exc:
            logger.error("data_gen (sync) failed for %s: %s", project_id, exc)
    return results

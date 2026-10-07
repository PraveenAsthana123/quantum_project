"""
Shared utilities and base classes for all quantum projects.
"""
from __future__ import annotations
import os
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

QUANTUM_ROOT = Path(__file__).parent.parent
DATA_ROOT = QUANTUM_ROOT / "data"


# ---------------------------------------------------------------------------
# Base project class
# ---------------------------------------------------------------------------

class QuantumProject:
    """
    Base class for every quantum project in this workspace.
    Provides consistent logging, timing, result storage, and data access.
    """

    name: str = "quantum-project"
    description: str = ""
    role_target: str = ""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path(".")
        self.data_dir = self.project_dir / "data"
        self.results: Dict[str, Any] = {}
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )
        self.log = logging.getLogger(self.name)

    def save_results(self, filename: str = "results.json"):
        out = self.project_dir / filename
        with open(out, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        self.log.info("Results saved to %s", out)

    def load_results(self, filename: str = "results.json") -> Dict:
        src = self.project_dir / filename
        if not src.exists():
            return {}
        with open(src) as f:
            return json.load(f)

    def timer(self, label: str):
        return _Timer(label, self.log)


class _Timer:
    def __init__(self, label: str, log):
        self.label = label
        self.log = log

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_):
        elapsed = time.perf_counter() - self.start
        self.log.info("%s completed in %.3fs", self.label, elapsed)
        self.elapsed = elapsed


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    name: str
    classical_time: float = 0.0
    quantum_time: float = 0.0
    classical_score: float = 0.0
    quantum_score: float = 0.0
    circuit_depth: int = 0
    num_qubits: int = 0
    shots: int = 1024
    notes: str = ""
    extra: Dict = field(default_factory=dict)

    def speedup(self) -> Optional[float]:
        if self.quantum_time and self.classical_time:
            return self.classical_time / self.quantum_time
        return None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "classical_time_s": self.classical_time,
            "quantum_time_s": self.quantum_time,
            "classical_score": self.classical_score,
            "quantum_score": self.quantum_score,
            "circuit_depth": self.circuit_depth,
            "num_qubits": self.num_qubits,
            "shots": self.shots,
            "speedup": self.speedup(),
            "notes": self.notes,
            **self.extra,
        }


# ---------------------------------------------------------------------------
# Circuit helpers
# ---------------------------------------------------------------------------

def build_bell_pair():
    """Return a Qiskit QuantumCircuit for a Bell state."""
    try:
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])
        return qc
    except ImportError:
        raise ImportError("qiskit is required: pip install qiskit")


def run_statevector(circuit):
    """Simulate circuit with Qiskit Aer statevector simulator."""
    try:
        from qiskit_aer import AerSimulator
        from qiskit import transpile
        sim = AerSimulator(method="statevector")
        tc = transpile(circuit, sim)
        result = sim.run(tc).result()
        return result
    except ImportError:
        raise ImportError("qiskit-aer is required: pip install qiskit-aer")


def circuit_stats(circuit) -> Dict:
    """Return basic circuit statistics."""
    try:
        return {
            "num_qubits": circuit.num_qubits,
            "depth": circuit.depth(),
            "gate_count": circuit.size(),
            "num_clbits": circuit.num_clbits,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Kaggle data helpers
# ---------------------------------------------------------------------------

KAGGLE_DATASETS: Dict[str, Dict] = {
    "creditcard-fraud": {
        "path": "mlg-ulb/creditcardfraud",
        "description": "Credit card fraud detection — 284,807 transactions",
        "projects": ["qc-banking-lab", "q01-algorithms", "q02-error-mitigation"],
    },
    "logistics-tsp": {
        "path": "gaborfodor/tsplib-benchmark",
        "description": "TSP/VRP benchmark instances",
        "projects": ["qc-logistics-lab", "q04-compiler", "q05-ir-interop", "q06-transpilation"],
    },
    "stock-market": {
        "path": "jacksoncrow/nasdaq-100-stock-price-data",
        "description": "NASDAQ-100 historical stock prices",
        "projects": ["qc-banking-lab", "q01-algorithms"],
    },
}


def kaggle_download(dataset_path: str, dest_dir: Path):
    """Download a Kaggle dataset to dest_dir."""
    import subprocess
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["kaggle", "datasets", "download", "-d", dataset_path, "-p", str(dest_dir), "--unzip"]
    logger.info("Downloading kaggle dataset %s → %s", dataset_path, dest_dir)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"kaggle download failed: {result.stderr}")
    logger.info("Download complete: %s", dest_dir)


# ---------------------------------------------------------------------------
# Quantum noise helpers
# ---------------------------------------------------------------------------

def depolarizing_noise_model(p_single: float = 0.001, p_two: float = 0.01):
    """Build a simple depolarizing noise model for Qiskit Aer."""
    try:
        from qiskit_aer.noise import NoiseModel, depolarizing_error
        nm = NoiseModel()
        nm.add_all_qubit_quantum_error(depolarizing_error(p_single, 1), ["u1", "u2", "u3", "h", "x"])
        nm.add_all_qubit_quantum_error(depolarizing_error(p_two, 2), ["cx", "cz"])
        return nm
    except ImportError:
        raise ImportError("qiskit-aer is required")


# ---------------------------------------------------------------------------
# Resource estimation
# ---------------------------------------------------------------------------

@dataclass
class ResourceEstimate:
    algorithm: str
    logical_qubits: int
    physical_qubits_estimate: int
    t_gates: int
    circuit_depth: int
    estimated_runtime_s: float
    qec_code: str = "surface"
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "algorithm": self.algorithm,
            "logical_qubits": self.logical_qubits,
            "physical_qubits_estimate": self.physical_qubits_estimate,
            "t_gates": self.t_gates,
            "circuit_depth": self.circuit_depth,
            "estimated_runtime_s": self.estimated_runtime_s,
            "qec_code": self.qec_code,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Simple observability helpers
# ---------------------------------------------------------------------------

class ExperimentTracker:
    """Lightweight experiment tracker — no external service required."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self._runs: List[Dict] = []
        if log_file.exists():
            with open(log_file) as f:
                self._runs = json.load(f)

    def log_run(self, name: str, params: Dict, metrics: Dict):
        entry = {
            "name": name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "params": params,
            "metrics": metrics,
        }
        self._runs.append(entry)
        self._save()
        return entry

    def _save(self):
        with open(self.log_file, "w") as f:
            json.dump(self._runs, f, indent=2, default=str)

    def latest(self, n: int = 5) -> List[Dict]:
        return self._runs[-n:]

    def all_runs(self) -> List[Dict]:
        return list(self._runs)

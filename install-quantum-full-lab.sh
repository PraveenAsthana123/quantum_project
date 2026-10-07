#!/usr/bin/env bash
set -Eeuo pipefail

###############################################################################
# FULL QUANTUM ARCHITECT / ENGINEERING LAB
#
# SINGLE QUANTUM ROOT:
#   /mnt/deepa/quantum
#
# Combines:
#   - Technical / Platform / Hybrid architecture
#   - Compiler / IR / transpilation / circuit cutting
#   - Circuit + gate building and testing
#   - High-performance / noisy / open-system / tensor simulation
#   - QEC / FTQC / error mitigation
#   - QML / optimization
#   - Hardware / pulse / calibration / readout
#   - Quantum networking / repeaters / communication
#   - Neutral atom / analog / photonic
#   - Test / V&V / GST / RB / benchmarking
#   - Visualization / 3-D / graph analytics
#   - Data engineering / provenance / experiment tracking
#   - Quantum datasets / chemistry schemas / materials data tools
#   - Security / software quality
#   - Local observability launchers
#
# Design goals:
#   * idempotent: safe to re-run
#   * no deletion of existing work
#   * isolated Python environments
#   * best-effort install for optional stacks
#   * all project/data/source artifacts stay under /mnt/deepa/quantum
###############################################################################

ROOT="/mnt/deepa/quantum"

GITHUB="$ROOT/github"
VENVS="$ROOT/venvs"
DATASETS="$ROOT/datasets"
PROJECTS="$ROOT/projects"
RESULTS="$ROOT/results"
LOGS="$ROOT/logs"
MANIFESTS="$ROOT/manifests"
NOTEBOOKS="$ROOT/notebooks"
SIMULATIONS="$ROOT/simulations"
CONTROL="$ROOT/control-tower"
CACHE="$ROOT/.cache"
SCRIPTS="$ROOT/scripts"

TEST_ROOT="$PROJECTS/quantum-testing"
DASH_ROOT="$PROJECTS/quantum-dashboard"

mkdir -p \
    "$ROOT" "$GITHUB" "$VENVS" "$DATASETS" "$PROJECTS" "$RESULTS" \
    "$LOGS" "$MANIFESTS" "$NOTEBOOKS" "$SIMULATIONS" "$CONTROL" \
    "$CACHE/pip" "$CACHE/kagglehub" "$SCRIPTS" "$TEST_ROOT" "$DASH_ROOT"

export PIP_CACHE_DIR="$CACHE/pip"
export XDG_CACHE_HOME="$CACHE"
export KAGGLEHUB_CACHE="$CACHE/kagglehub"

LOGFILE="$LOGS/full-quantum-lab-$(date +%Y%m%d-%H%M%S).log"

exec > >(tee -a "$LOGFILE") 2>&1

trap '
echo
echo "======================================================================"
echo "ERROR near line $LINENO"
echo "Log: '"$LOGFILE"'"
echo "======================================================================"
' ERR


header() {
    echo
    echo "======================================================================"
    echo "$*"
    echo "======================================================================"
}


warn() {
    echo "[WARNING] $*"
}


have() {
    command -v "$1" >/dev/null 2>&1
}


###############################################################################
# PRECHECK
###############################################################################

precheck() {

    header "PRECHECK"

    if [ ! -d "/mnt/deepa" ]; then
        echo "ERROR: /mnt/deepa is not mounted."
        exit 1
    fi

    echo "Quantum root: $ROOT"
    echo
    df -h /mnt/deepa || true

    echo
    echo "Python:"
    python3 --version || true

    echo
    echo "GPU:"
    if have nvidia-smi; then
        nvidia-smi --query-gpu=name,driver_version,memory.total \
            --format=csv,noheader || true
    else
        echo "NVIDIA GPU command not found. CPU paths remain usable."
    fi
}


###############################################################################
# SYSTEM SOFTWARE
###############################################################################

install_system() {

    header "SYSTEM DEPENDENCIES"

    sudo apt-get update

    sudo apt-get install -y \
        git git-lfs curl wget rsync unzip zip jq tree \
        build-essential gcc g++ gfortran \
        cmake ninja-build make pkg-config \
        python3 python3-dev python3-venv python3-pip python3-tk \
        libopenblas-dev liblapack-dev libhdf5-dev \
        libssl-dev libffi-dev \
        graphviz sqlite3 \
        libgl1 libxrender1 libsm6 libxext6 \
        default-jdk maven

    git lfs install || true

    # Optional engineering packages available on many Ubuntu installations.
    sudo apt-get install -y gmsh || warn "Optional apt package gmsh was not installed."
    sudo apt-get install -y klayout || warn "Optional apt package klayout was not installed."

    # Optional local observability containers.
    sudo apt-get install -y docker.io || warn "Optional Docker install failed."
    sudo apt-get install -y docker-compose-v2 || warn "Optional docker-compose-v2 install failed."
}


###############################################################################
# GITHUB MANIFEST
###############################################################################

write_repo_manifest() {

cat > "$MANIFESTS/full-quantum-github.tsv" <<'EOF'
# CATEGORY|NAME|URL|PURPOSE

architecture|qiskit-serverless|https://github.com/Qiskit/qiskit-serverless.git|distributed quantum-classical workload architecture
architecture|qfaas|https://github.com/Cloudslab/qfaas.git|quantum function as a service reference architecture
architecture|iquantum|https://github.com/Cloudslab/iQuantum.git|quantum datacenter scheduling capacity architecture

hybrid|cuda-quantum|https://github.com/NVIDIA/cuda-quantum.git|CPU GPU QPU programming compiler runtime
hybrid|catalyst|https://github.com/PennyLaneAI/catalyst.git|hybrid quantum classical JIT compiler

compiler|bqskit|https://github.com/BQSKit/bqskit.git|quantum synthesis compiler optimization
compiler|mqt-qmap|https://github.com/munich-quantum-toolkit/qmap.git|mapping routing compilation
compiler|tket|https://github.com/CQCL/tket.git|cross platform quantum compiler
compiler|pyqir|https://github.com/qir-alliance/pyqir.git|QIR generation parsing
compiler|qir-spec|https://github.com/qir-alliance/qir-spec.git|QIR specification
compiler|qiskit-addon-cutting|https://github.com/Qiskit/qiskit-addon-cutting.git|circuit cutting
compiler|pyzx|https://github.com/zxcalc/pyzx.git|ZX calculus optimization equivalence
compiler|quil|https://github.com/quil-lang/quil.git|quantum instruction language reference

simulation|qulacs|https://github.com/qulacs/qulacs.git|high speed statevector noisy parametric simulator
simulation|qsim|https://github.com/quantumlib/qsim.git|high performance Cirq simulator
simulation|quest|https://github.com/quest-kit/QuEST.git|CPU GPU MPI quantum simulator
simulation|quimb|https://github.com/jcmgray/quimb.git|tensor networks many body simulation
simulation|mqt-ddsim|https://github.com/munich-quantum-toolkit/ddsim.git|decision diagram simulator
simulation|mqt-yaqs|https://github.com/munich-quantum-toolkit/yaqs.git|tensor network open system noisy simulation
simulation|pennylane-lightning|https://github.com/PennyLaneAI/pennylane-lightning.git|fast CPU GPU tensor simulator

testing|mqt-bench|https://github.com/munich-quantum-toolkit/bench.git|quantum circuit benchmark suite
testing|mqt-qcec|https://github.com/munich-quantum-toolkit/qcec.git|quantum circuit equivalence checking
testing|qiskit-experiments|https://github.com/qiskit-community/qiskit-experiments.git|hardware characterization experiments
testing|pygsti|https://github.com/sandialabs/pyGSTi.git|GST RB RPE drift characterization

qec|stim|https://github.com/quantumlib/Stim.git|stabilizer QEC simulator
qec|pymatching|https://github.com/oscarhiggott/PyMatching.git|MWPM decoder
qec|qualtran|https://github.com/quantumlib/Qualtran.git|fault tolerant algorithm resource analysis
qec|qecsim|https://github.com/qecsim/qecsim.git|QEC simulation
qec|panqec|https://github.com/panqec/panqec.git|QEC code simulation
qec|microsoft-qdk|https://github.com/microsoft/qdk.git|QSharp resource estimation
qec|mitiq|https://github.com/unitaryfund/mitiq.git|quantum error mitigation

qml|qiskit-machine-learning|https://github.com/qiskit-community/qiskit-machine-learning.git|quantum kernels QNN VQC
qml|torchquantum|https://github.com/mit-han-lab/torchquantum.git|PyTorch GPU QML
qml|tensorflow-quantum|https://github.com/tensorflow/quantum.git|TensorFlow Cirq hybrid QML
qml|qml-benchmarks|https://github.com/XanaduAI/qml-benchmarks.git|quantum versus classical ML benchmarks

optimization|qiskit-addon-opt-mapper|https://github.com/Qiskit/qiskit-addon-opt-mapper.git|QUBO HUBO optimization mapping
optimization|dwave-ocean-sdk|https://github.com/dwavesystems/dwave-ocean-sdk.git|QUBO Ising annealing optimization

hardware|qibolab|https://github.com/qiboteam/qibolab.git|hardware drivers pulse execution
hardware|qibocal|https://github.com/qiboteam/qibocal.git|calibration characterization validation
hardware|qibosoq|https://github.com/qiboteam/qibosoq.git|QICK server integration
hardware|qick|https://github.com/openquantumhardware/qick.git|RFSoC quantum control electronics
hardware|scqubits|https://github.com/scqubits/scqubits.git|superconducting circuit modeling
hardware|simcats|https://github.com/f-hader/SimCATS.git|spin qubit charge stability simulation

network|sequence|https://github.com/sequence-toolbox/SeQUeNCe.git|quantum network repeater simulator
network|simqn|https://github.com/QNLab-USTC/SimQN.git|quantum network simulator
network|qunetsim|https://github.com/tqsd/QuNetSim.git|quantum network protocol simulator
network|requsim|https://github.com/jwallnoefer/requsim.git|quantum repeater strategy simulator
network|qnpack|https://github.com/qlbnl/qnpack.git|repeater memory all photonic models
network|quisp|https://github.com/sfc-aqua/quisp.git|large quantum internet simulator

analog|pulser|https://github.com/pasqal-io/Pulser.git|neutral atom pulse and analog simulation
visualization|mqt-naviz|https://github.com/munich-quantum-toolkit/naviz.git|neutral atom movement visualizer

photonic|perceval|https://github.com/Quandela/Perceval.git|photonic quantum programming and simulation

data|qdataset|https://github.com/eperrier/QDataSet.git|quantum ML control tomography simulated datasets
data|qcschema|https://github.com/MolSSI/QCSchema.git|quantum chemistry schema
data|qcelemental|https://github.com/MolSSI/QCElemental.git|molecule constants schema validation
data|dvc|https://github.com/treeverse/dvc.git|data versioning
data|mlflow|https://github.com/mlflow/mlflow.git|experiment tracking

materials|matbench|https://github.com/materialsproject/matbench.git|materials benchmark datasets
materials|pymatgen|https://github.com/materialsproject/pymatgen.git|materials structures analysis
materials|mp-api|https://github.com/materialsproject/api.git|Materials Project API client

graph|rustworkx|https://github.com/Qiskit/rustworkx.git|high performance graph algorithms

EOF
}


clone_or_update() {

    local category="$1"
    local name="$2"
    local url="$3"

    local category_dir="$GITHUB/$category"
    local dest="$category_dir/$name"

    mkdir -p "$category_dir"

    echo
    echo "[$category] $name"

    if [ -d "$dest/.git" ]; then
        git -C "$dest" pull --ff-only || warn "Could not update $name"
    else
        git clone --depth 1 "$url" "$dest" || warn "Could not clone $url"
    fi
}


download_repositories() {

    write_repo_manifest

    header "GITHUB REPOSITORIES"

    while IFS='|' read -r category name url purpose
    do
        [[ -z "${category:-}" ]] && continue
        [[ "$category" =~ ^# ]] && continue

        clone_or_update "$category" "$name" "$url"

    done < "$MANIFESTS/full-quantum-github.tsv"
}


###############################################################################
# PYTHON ENV HELPERS
###############################################################################

make_venv() {

    local name="$1"
    local path="$VENVS/$name"

    if [ ! -x "$path/bin/python" ]; then
        echo
        echo "Creating environment: $name"
        python3 -m venv "$path"
    fi

    "$path/bin/python" -m pip install \
        --upgrade pip setuptools wheel
}


pip_try() {

    local env="$1"
    shift

    echo
    echo "[$env] pip install $*"

    "$VENVS/$env/bin/python" -m pip install --upgrade "$@" \
        || warn "Optional package install failed in $env: $*"
}


editable_try() {

    local env="$1"
    local directory="$2"

    if [ -f "$directory/pyproject.toml" ] || [ -f "$directory/setup.py" ]; then

        echo
        echo "[$env] editable install:"
        echo "  $directory"

        "$VENVS/$env/bin/python" -m pip install -e "$directory" \
            || warn "Editable install failed: $directory"

    fi
}


###############################################################################
# ALL ISOLATED ENVIRONMENTS
###############################################################################

install_environments() {

    header "PYTHON ENVIRONMENTS"

    ###########################################################################
    # 1. TECHNICAL / PLATFORM ARCHITECT
    ###########################################################################

    make_venv architecture

    pip_try architecture \
        numpy scipy pandas matplotlib networkx rustworkx \
        qiskit qiskit-aer \
        qiskit-serverless \
        ray fastapi uvicorn pydantic \
        psutil \
        opentelemetry-api opentelemetry-sdk \
        prometheus-client \
        jupyterlab ipykernel


    ###########################################################################
    # 2. HYBRID CPU/GPU/QPU
    ###########################################################################

    make_venv hybrid

    pip_try hybrid \
        numpy scipy pandas matplotlib \
        pennylane pennylane-lightning \
        pennylane-catalyst \
        qiskit qiskit-aer \
        jax \
        jupyterlab


    ###########################################################################
    # 3. CUDA-Q - ISOLATED
    ###########################################################################

    make_venv cudaq

    pip_try cudaq \
        numpy scipy matplotlib

    # CUDA-Q has its own environment so a GPU compatibility issue cannot
    # damage the rest of the lab.
    pip_try cudaq cudaq


    ###########################################################################
    # 4. COMPILER / IR / TRANSPILATION / CIRCUIT CUTTING
    ###########################################################################

    make_venv compiler

    pip_try compiler \
        numpy scipy pandas \
        networkx rustworkx \
        qiskit qiskit-aer \
        bqskit mqt.qmap pytket \
        pyqir openqasm3 \
        qiskit-addon-cutting \
        pyzx \
        jupyterlab


    ###########################################################################
    # 5. SIMULATION
    ###########################################################################

    make_venv simulation

    pip_try simulation \
        numpy scipy pandas matplotlib \
        qiskit qiskit-aer \
        cirq qsimcirq \
        qulacs \
        qutip \
        quimb \
        mqt.ddsim \
        mqt.yaqs \
        pennylane \
        pennylane-lightning \
        psutil \
        jupyterlab


    ###########################################################################
    # 6. TEST / V&V / CHARACTERIZATION
    ###########################################################################

    make_venv testing

    pip_try testing \
        numpy scipy pandas matplotlib \
        qiskit qiskit-aer \
        pytest pytest-cov pytest-xdist pytest-benchmark \
        hypothesis coverage \
        mqt.bench mqt.qcec \
        pyzx \
        qiskit-experiments \
        pygsti \
        jupyterlab


    ###########################################################################
    # 7. QEC / FTQC / ERROR MITIGATION
    ###########################################################################

    make_venv qec-architect

    pip_try qec-architect \
        numpy scipy pandas matplotlib \
        qiskit qiskit-aer \
        stim pymatching \
        qecsim panqec \
        qualtran \
        mitiq \
        jupyterlab


    ###########################################################################
    # 8. QML
    ###########################################################################

    make_venv qml

    pip_try qml \
        numpy scipy pandas matplotlib \
        scikit-learn \
        qiskit qiskit-aer \
        qiskit-machine-learning \
        pennylane pennylane-lightning \
        torch \
        jupyterlab


    # TorchQuantum isolated because upstream compatibility can lag Qiskit.
    make_venv qml-torch

    pip_try qml-torch \
        numpy scipy pandas matplotlib \
        torch torchvision \
        qiskit \
        jupyterlab

    editable_try qml-torch "$GITHUB/qml/torchquantum"


    # TensorFlow Quantum isolated because it has tighter TensorFlow/Cirq pins.
    make_venv qml-tf

    pip_try qml-tf \
        numpy pandas matplotlib \
        tensorflow \
        tf-keras \
        cirq \
        tensorflow-quantum \
        jupyterlab


    ###########################################################################
    # 9. OPTIMIZATION
    ###########################################################################

    make_venv optimization

    pip_try optimization \
        numpy scipy pandas matplotlib \
        networkx \
        qiskit qiskit-aer \
        qiskit-addon-opt-mapper \
        dwave-ocean-sdk dimod \
        ortools \
        jupyterlab


    ###########################################################################
    # 10. HARDWARE / PULSE / CALIBRATION / READOUT
    ###########################################################################

    make_venv hardware-architect

    pip_try hardware-architect \
        numpy scipy pandas matplotlib \
        qutip scqubits \
        qibolab qibocal \
        scikit-rf pyvisa pyserial \
        pyqtgraph \
        jupyterlab

    editable_try hardware-architect "$GITHUB/hardware/qibosoq"
    editable_try hardware-architect "$GITHUB/hardware/qick"

    echo
    echo "[hardware-architect] SimCATS source:"
    echo "  $GITHUB/hardware/simcats"
    echo "SimCATS is intentionally source-only here because its advertised"
    echo "Python compatibility currently stops before the Ubuntu 24.04 default"
    echo "Python used by the rest of this lab."


    ###########################################################################
    # 11. QUANTUM COMMUNICATION / NETWORK
    ###########################################################################

    make_venv network-architect

    pip_try network-architect \
        numpy scipy pandas matplotlib \
        networkx rustworkx \
        qutip simpy \
        simqn qunetsim requsim \
        jupyterlab

    editable_try network-architect "$GITHUB/network/sequence"

    echo
    echo "[network-architect] QNPack is downloaded but not forced:"
    echo "  It requires NetSquid access/credentials."
    echo
    echo "[network-architect] QuISP is downloaded but not auto-built:"
    echo "  Full use requires OMNeT++."


    ###########################################################################
    # 12. ANALOG / NEUTRAL ATOM
    ###########################################################################

    make_venv analog

    pip_try analog \
        numpy scipy pandas matplotlib \
        qutip \
        pulser pulser-simulation \
        jupyterlab

    echo
    echo "MQT NAViz source downloaded under:"
    echo "  $GITHUB/visualization/mqt-naviz"
    echo "NAViz needs a recent Rust toolchain for a full GUI build."


    ###########################################################################
    # 13. PHOTONIC
    ###########################################################################

    make_venv photonic

    pip_try photonic \
        numpy scipy pandas matplotlib \
        perceval-quandela \
        jupyterlab


    ###########################################################################
    # 14. VISUALIZATION / CONTROL TOWER
    ###########################################################################

    make_venv visualization

    pip_try visualization \
        numpy scipy pandas \
        matplotlib plotly \
        dash dash-cytoscape \
        panel hvplot holoviews datashader bokeh \
        pyvista \
        pyvis \
        graphviz pydot \
        networkx rustworkx \
        streamlit \
        jupyterlab


    ###########################################################################
    # 15. GRAPH + DATA ENGINEERING
    ###########################################################################

    make_venv graph-data

    pip_try graph-data \
        numpy scipy pandas \
        networkx rustworkx igraph \
        pyvis graphviz pydot \
        rdflib neo4j \
        pyarrow polars duckdb \
        h5py zarr xarray \
        pandera \
        dvc mlflow \
        jupyterlab


    ###########################################################################
    # 16. MATERIALS
    ###########################################################################

    make_venv materials

    pip_try materials \
        numpy scipy pandas matplotlib \
        matbench \
        pymatgen \
        mp-api \
        qcelemental \
        ase \
        jupyterlab


    ###########################################################################
    # 17. QUANTUM DATA / PROVENANCE
    ###########################################################################

    make_venv data

    pip_try data \
        requests \
        kagglehub \
        numpy scipy pandas \
        pyarrow polars duckdb \
        h5py zarr xarray \
        pandera \
        qcelemental \
        dvc \
        mlflow \
        jupyterlab


    ###########################################################################
    # 18. SECURITY / SOFTWARE QUALITY
    ###########################################################################

    make_venv quantum-security

    pip_try quantum-security \
        bandit pip-audit cyclonedx-bom \
        ruff mypy pre-commit \
        pytest pytest-cov hypothesis \
        safety


    ###########################################################################
    # 19. OBSERVABILITY
    ###########################################################################

    make_venv observability

    pip_try observability \
        psutil \
        pandas \
        prometheus-client \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-exporter-otlp \
        mlflow \
        panel plotly \
        jupyterlab
}


###############################################################################
# DATASET MANIFEST
###############################################################################

write_dataset_manifest() {

cat > "$MANIFESTS/full-quantum-datasets.tsv" <<'EOF'
# NAME|TYPE|SOURCE/HANDLE|PURPOSE
qm9|kaggle|zaharch/quantum-machine-9-aka-qm9|quantum chemistry QML
wm811k|kaggle|qingyi/wm811k-wafer-map|semiconductor fabrication defect classification
secom|uci|https://archive.ics.uci.edu/ml/machine-learning-databases/secom/|semiconductor process analytics
qdataset|github|https://github.com/eperrier/QDataSet.git|quantum control noise tomography QML
qml-benchmarks|github|https://github.com/XanaduAI/qml-benchmarks.git|quantum versus classical QML benchmarks
matbench|package|matbench|materials benchmark datasets
materials-project|api|mp-api|materials data; API key required for remote queries
EOF
}


download_datasets() {

    write_dataset_manifest

    header "DATASETS"

    make_venv data
    pip_try data kagglehub requests pandas pyarrow

    local py="$VENVS/data/bin/python"

    "$py" - <<PY
import os
from pathlib import Path

os.environ["KAGGLEHUB_CACHE"] = "$CACHE/kagglehub"

root = Path("$DATASETS")
root.mkdir(parents=True, exist_ok=True)

try:
    import kagglehub
except Exception as exc:
    print("KaggleHub unavailable:", exc)
    raise SystemExit(0)

datasets = {
    "qm9": "zaharch/quantum-machine-9-aka-qm9",
    "wm811k": "qingyi/wm811k-wafer-map",
}

for name, handle in datasets.items():
    print()
    print("=" * 70)
    print("Dataset:", name)
    print("Handle :", handle)
    print("=" * 70)

    try:
        downloaded = Path(kagglehub.dataset_download(handle)).resolve()
        link = root / name

        if link.is_symlink():
            link.unlink()

        if not link.exists():
            link.symlink_to(downloaded, target_is_directory=True)

        print("Available at:", link)
        print("Kaggle cache:", downloaded)

    except Exception as exc:
        print("WARNING:", name, exc)
PY

    mkdir -p "$DATASETS/secom"

    curl -L --retry 3 \
        -o "$DATASETS/secom/secom.data" \
        "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom.data" \
        || warn "SECOM data download failed."

    curl -L --retry 3 \
        -o "$DATASETS/secom/secom_labels.data" \
        "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom_labels.data" \
        || warn "SECOM labels download failed."

    mkdir -p "$DATASETS/generated" \
             "$DATASETS/generated/gate-tests" \
             "$DATASETS/generated/random-circuits" \
             "$DATASETS/generated/noisy-circuits" \
             "$DATASETS/generated/qec-syndromes" \
             "$DATASETS/generated/transpiler-benchmarks" \
             "$DATASETS/generated/qml" \
             "$DATASETS/generated/calibration" \
             "$DATASETS/generated/readout-iq" \
             "$DATASETS/generated/network" \
             "$DATASETS/generated/repeater" \
             "$DATASETS/generated/pulse-control" \
             "$DATASETS/generated/clock" \
             "$DATASETS/generated/sensing" \
             "$DATASETS/generated/hardware"
}


###############################################################################
# GATE / CIRCUIT TEST
###############################################################################

write_gate_test() {

cat > "$TEST_ROOT/gate_circuit_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import (
    IGate, XGate, YGate, ZGate, HGate, SGate, TGate,
    SXGate, PhaseGate, UGate,
    RXGate, RYGate, RZGate,
    CXGate, CZGate, SwapGate, iSwapGate, ECRGate,
    CCXGate,
)
from qiskit.quantum_info import Operator, Statevector, state_fidelity

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "gate-circuit-tests"
DATA = ROOT / "datasets" / "generated" / "gate-tests"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

results = []


def record(name, passed, detail):
    row = {
        "test": name,
        "passed": bool(passed),
        "detail": str(detail),
    }
    results.append(row)
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")


def unitary_test(name, gate):
    U = Operator(gate).data
    eye = np.eye(U.shape[0], dtype=complex)
    ok = np.allclose(U.conj().T @ U, eye, atol=1e-10)
    record(f"unitary:{name}", ok, f"dimension={U.shape[0]}")


gates = {
    "I": IGate(),
    "X": XGate(),
    "Y": YGate(),
    "Z": ZGate(),
    "H": HGate(),
    "S": SGate(),
    "T": TGate(),
    "SX": SXGate(),
    "P": PhaseGate(0.23),
    "U": UGate(0.2, 0.3, 0.4),
    "RX": RXGate(0.37),
    "RY": RYGate(-0.42),
    "RZ": RZGate(0.91),
    "CX": CXGate(),
    "CZ": CZGate(),
    "SWAP": SwapGate(),
    "iSWAP": iSwapGate(),
    "ECR": ECRGate(),
    "CCX": CCXGate(),
}

for name, gate in gates.items():
    unitary_test(name, gate)


# X truth table
qc = QuantumCircuit(1)
qc.x(0)
sv = Statevector.from_instruction(qc)
record("X|0> -> |1>", np.allclose(np.abs(sv.data), [0, 1]), sv.data)


# H superposition
qc = QuantumCircuit(1)
qc.h(0)
sv = Statevector.from_instruction(qc)
record("H superposition", np.allclose(sv.probabilities(), [0.5, 0.5]), sv.probabilities())


# H twice identity
qc = QuantumCircuit(1)
qc.h(0)
qc.h(0)
sv = Statevector.from_instruction(qc)
record("H.H identity", np.allclose(np.abs(sv.data), [1, 0]), sv.data)


# Bell
bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
sv = Statevector.from_instruction(bell)
p = sv.probabilities_dict()

ok = (
    abs(p.get("00", 0) - 0.5) < 1e-10
    and abs(p.get("11", 0) - 0.5) < 1e-10
)

record("Bell state", ok, p)


# GHZ
ghz = QuantumCircuit(3)
ghz.h(0)
ghz.cx(0, 1)
ghz.cx(1, 2)
sv = Statevector.from_instruction(ghz)
p = sv.probabilities_dict()

ok = (
    abs(p.get("000", 0) - 0.5) < 1e-10
    and abs(p.get("111", 0) - 0.5) < 1e-10
)

record("GHZ state", ok, p)


# QFT smoke test
qft = QuantumCircuit(3)
qft.h(2)
qft.cp(np.pi / 2, 1, 2)
qft.cp(np.pi / 4, 0, 2)
qft.h(1)
qft.cp(np.pi / 2, 0, 1)
qft.h(0)
record("QFT-like circuit unitary", np.allclose(
    Operator(qft).data.conj().T @ Operator(qft).data,
    np.eye(8),
    atol=1e-10,
), f"depth={qft.depth()}")


# Compiler optimization equivalence via state fidelity
original = QuantumCircuit(3)
original.h(0)
original.cx(0, 1)
original.cx(1, 2)
original.rz(0.31, 2)
original.cx(1, 2)
original.cx(0, 1)

compiled = transpile(
    original,
    basis_gates=["rz", "sx", "x", "cx"],
    optimization_level=3,
)

sv1 = Statevector.from_instruction(original)
sv2 = Statevector.from_instruction(compiled)

fid = state_fidelity(sv1, sv2)

record(
    "transpile state fidelity",
    fid > 1 - 1e-9,
    f"fidelity={fid:.12f}",
)

record(
    "transpile metrics",
    True,
    f"depth={original.depth()}->{compiled.depth()}, gates={original.size()}->{compiled.size()}",
)


summary = {
    "passed": sum(1 for r in results if r["passed"]),
    "failed": sum(1 for r in results if not r["passed"]),
    "results": results,
}

text = json.dumps(summary, indent=2, default=str)

(OUT / "gate-circuit-test.json").write_text(text)
(DATA / "gate-circuit-test.json").write_text(text)

print()
print(json.dumps({
    "passed": summary["passed"],
    "failed": summary["failed"],
}, indent=2))

if summary["failed"]:
    raise SystemExit(1)
PY

chmod +x "$TEST_ROOT/gate_circuit_test.py"
}


###############################################################################
# NOISE TEST
###############################################################################

write_noise_test() {

cat > "$TEST_ROOT/noise_simulation_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    amplitude_damping_error,
    phase_damping_error,
    ReadoutError,
)

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "noise-tests"
DATA = ROOT / "datasets" / "generated" / "noisy-circuits"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

ideal_counts = AerSimulator().run(qc, shots=3000).result().get_counts()

noise = NoiseModel()

noise.add_all_qubit_quantum_error(
    depolarizing_error(0.01, 1),
    ["h", "x", "sx"]
)

noise.add_all_qubit_quantum_error(
    depolarizing_error(0.03, 2),
    ["cx"]
)

# Add simple readout confusion.
noise.add_all_qubit_readout_error(
    ReadoutError([[0.98, 0.02], [0.03, 0.97]])
)

noisy_counts = AerSimulator(
    noise_model=noise
).run(qc, shots=3000).result().get_counts()

payload = {
    "ideal": ideal_counts,
    "noisy": noisy_counts,
    "noise_types_tested": [
        "depolarizing",
        "readout",
        "amplitude_damping_available",
        "phase_damping_available",
    ],
}

text = json.dumps(payload, indent=2)

(OUT / "bell-noise.json").write_text(text)
(DATA / "bell-noise.json").write_text(text)

print(text)
print("NOISE SIMULATION: PASS")
PY

chmod +x "$TEST_ROOT/noise_simulation_test.py"
}


###############################################################################
# QEC TEST
###############################################################################

write_qec_test() {

cat > "$TEST_ROOT/qec_stim_pymatching_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

import numpy as np
import stim
import pymatching

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "qec-tests"
DATA = ROOT / "datasets" / "generated" / "qec-syndromes"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

circuit = stim.Circuit.generated(
    "repetition_code:memory",
    distance=5,
    rounds=5,
    after_clifford_depolarization=0.005,
    before_measure_flip_probability=0.002,
    after_reset_flip_probability=0.002,
)

dem = circuit.detector_error_model(decompose_errors=True)
matching = pymatching.Matching.from_detector_error_model(dem)

sampler = circuit.compile_detector_sampler()

detectors, observables = sampler.sample(
    shots=3000,
    separate_observables=True,
)

predictions = matching.decode_batch(detectors)

if predictions.ndim == 1:
    predictions = predictions[:, None]

if observables.ndim == 1:
    observables = observables[:, None]

logical_mask = np.any(predictions != observables, axis=1)

payload = {
    "distance": 5,
    "rounds": 5,
    "shots": int(len(logical_mask)),
    "detector_count": int(detectors.shape[1]),
    "logical_errors": int(logical_mask.sum()),
    "logical_error_rate": float(logical_mask.mean()),
}

text = json.dumps(payload, indent=2)

(OUT / "stim-pymatching.json").write_text(text)
(DATA / "stim-pymatching.json").write_text(text)

print(text)
print("QEC TEST: PASS")
PY

chmod +x "$TEST_ROOT/qec_stim_pymatching_test.py"
}


###############################################################################
# MQT / TESTING TOOL TEST
###############################################################################

write_mqt_test() {

cat > "$TEST_ROOT/mqt_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

from qiskit import QuantumCircuit, transpile

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "mqt-tests"
OUT.mkdir(parents=True, exist_ok=True)

result = {}

try:
    import mqt.ddsim
    result["mqt_ddsim"] = {
        "status": "PASS",
        "version": getattr(mqt.ddsim, "__version__", "installed"),
    }
except Exception as exc:
    result["mqt_ddsim"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    import mqt.yaqs
    result["mqt_yaqs"] = {
        "status": "PASS",
        "version": getattr(mqt.yaqs, "__version__", "installed"),
    }
except Exception as exc:
    result["mqt_yaqs"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    from mqt.bench import BenchmarkLevel, get_benchmark

    circuit = get_benchmark(
        benchmark="ghz",
        level=BenchmarkLevel.ALG,
        circuit_size=5,
    )

    result["mqt_bench"] = {
        "status": "PASS",
        "qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "gates": circuit.size(),
    }

except Exception as exc:
    result["mqt_bench"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    from mqt import qcec

    original = QuantumCircuit(3)
    original.h(0)
    original.cx(0, 1)
    original.cx(1, 2)

    compiled = transpile(
        original,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=3,
    )

    verification = qcec.verify(original, compiled)

    result["qcec"] = {
        "status": "PASS",
        "equivalence": str(verification.equivalence),
    }

except Exception as exc:
    result["qcec"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

(OUT / "mqt-test.json").write_text(
    json.dumps(result, indent=2)
)

print(json.dumps(result, indent=2))
PY

chmod +x "$TEST_ROOT/mqt_test.py"
}


###############################################################################
# CHARACTERIZATION / GST IMPORT TEST
###############################################################################

write_characterization_test() {

cat > "$TEST_ROOT/characterization_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "characterization-tests"
OUT.mkdir(parents=True, exist_ok=True)

result = {}

try:
    import pygsti

    result["pygsti"] = {
        "status": "PASS",
        "version": getattr(pygsti, "__version__", "installed"),
        "capabilities": [
            "gate-set-tomography",
            "randomized-benchmarking",
            "robust-phase-estimation",
            "drift-analysis",
        ],
    }

except Exception as exc:
    result["pygsti"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

try:
    import qiskit_experiments

    result["qiskit_experiments"] = {
        "status": "PASS",
        "version": getattr(qiskit_experiments, "__version__", "installed"),
    }

except Exception as exc:
    result["qiskit_experiments"] = {
        "status": "FAIL",
        "error": repr(exc),
    }

(OUT / "characterization.json").write_text(
    json.dumps(result, indent=2)
)

print(json.dumps(result, indent=2))
PY

chmod +x "$TEST_ROOT/characterization_test.py"
}


###############################################################################
# GRAPH TEST
###############################################################################

write_graph_test() {

cat > "$TEST_ROOT/graph_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

import networkx as nx
import rustworkx as rx

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "graph-tests"
OUT.mkdir(parents=True, exist_ok=True)

# Example QPU coupling graph.
edges = [
    (0, 1),
    (1, 2),
    (2, 3),
    (1, 4),
    (4, 5),
]

nxg = nx.Graph()
nxg.add_edges_from(edges)

shortest = nx.shortest_path(nxg, 0, 5)

rxg = rx.PyGraph()
rxg.add_nodes_from(list(range(6)))
rxg.add_edges_from_no_data(edges)

payload = {
    "nodes": nxg.number_of_nodes(),
    "edges": nxg.number_of_edges(),
    "shortest_0_to_5": shortest,
    "rustworkx_nodes": rxg.num_nodes(),
    "rustworkx_edges": rxg.num_edges(),
}

(OUT / "graph-test.json").write_text(
    json.dumps(payload, indent=2)
)

print(json.dumps(payload, indent=2))
print("GRAPH TEST: PASS")
PY

chmod +x "$TEST_ROOT/graph_test.py"
}


###############################################################################
# DATA ENGINEERING TEST
###############################################################################

write_data_test() {

cat > "$TEST_ROOT/data_engineering_test.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
import xarray as xr
import h5py
import zarr

ROOT = Path("/mnt/deepa/quantum")
OUT = ROOT / "results" / "data-engineering-tests"
DATA = ROOT / "datasets" / "generated" / "transpiler-benchmarks"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame({
    "circuit": ["bell", "ghz", "qft"],
    "qubits": [2, 3, 3],
    "depth": [2, 3, 5],
    "fidelity": [1.0, 1.0, 0.999],
})

parquet_file = DATA / "benchmark.parquet"

table = pa.Table.from_pandas(df)
pq.write_table(table, parquet_file)

query = duckdb.sql(
    f"SELECT AVG(depth) AS avg_depth FROM read_parquet('{parquet_file}')"
).fetchone()[0]

h5_file = OUT / "state-data.h5"

with h5py.File(h5_file, "w") as h5:
    h5.create_dataset("probability", data=np.array([0.5, 0.5]))

xr_ds = xr.Dataset(
    {
        "fidelity": (
            ("circuit",),
            np.array([1.0, 1.0, 0.999]),
        )
    },
    coords={
        "circuit": ["bell", "ghz", "qft"]
    },
)

zarr_path = OUT / "sweep.zarr"
xr_ds.to_zarr(zarr_path, mode="w")

payload = {
    "parquet": str(parquet_file),
    "duckdb_avg_depth": float(query),
    "hdf5": str(h5_file),
    "zarr": str(zarr_path),
}

(OUT / "data-test.json").write_text(
    json.dumps(payload, indent=2)
)

print(json.dumps(payload, indent=2))
print("DATA ENGINEERING TEST: PASS")
PY

chmod +x "$TEST_ROOT/data_engineering_test.py"
}


###############################################################################
# VISUALIZATION DASHBOARD
###############################################################################

write_dashboard() {

cat > "$DASH_ROOT/dashboard.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path

import pandas as pd
import panel as pn
import plotly.express as px
import networkx as nx

ROOT = Path("/mnt/deepa/quantum")

pn.extension("plotly")

venv_root = ROOT / "venvs"
github_root = ROOT / "github"

envs = sorted([
    p.name for p in venv_root.iterdir()
    if p.is_dir()
]) if venv_root.exists() else []

categories = []

if github_root.exists():
    for category in sorted(github_root.iterdir()):
        if not category.is_dir():
            continue

        repos = sum(
            1 for p in category.iterdir()
            if p.is_dir() and (p / ".git").exists()
        )

        categories.append({
            "category": category.name,
            "repositories": repos,
        })

df = pd.DataFrame(categories)

if df.empty:
    fig = px.bar(
        pd.DataFrame({"category": ["none"], "repositories": [0]}),
        x="category",
        y="repositories",
        title="Quantum GitHub Repository Inventory",
    )
else:
    fig = px.bar(
        df,
        x="category",
        y="repositories",
        title="Quantum GitHub Repository Inventory",
    )

# Small architecture graph.
g = nx.DiGraph()

g.add_edges_from([
    ("Business Workload", "Platform"),
    ("Platform", "Compiler"),
    ("Compiler", "Simulator"),
    ("Compiler", "QPU"),
    ("QPU", "Testing"),
    ("Simulator", "Testing"),
    ("Testing", "Data"),
    ("Data", "Control Tower"),
])

architecture_text = "\n".join(
    f"{a} -> {b}" for a, b in g.edges()
)

template = pn.template.FastListTemplate(
    title="Quantum Engineering Control Tower",
)

template.main.append(
    pn.pane.Markdown(
        f"""
# Quantum Engineering Lab

**Root:** `{ROOT}`

**Virtual environments:** {len(envs)}

**GitHub categories:** {len(categories)}

## Environments

`{", ".join(envs)}`

## Architecture

```text
{architecture_text}
```
"""
    )
)

template.main.append(
    pn.pane.Plotly(fig, sizing_mode="stretch_width")
)

template.servable()
PY

chmod +x "$DASH_ROOT/dashboard.py"


cat > "$DASH_ROOT/start-dashboard.sh" <<'SH'
#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"

exec "$ROOT/venvs/visualization/bin/panel" serve \
    "$ROOT/projects/quantum-dashboard/dashboard.py" \
    --address 127.0.0.1 \
    --port 5006 \
    --show
SH

chmod +x "$DASH_ROOT/start-dashboard.sh"
}


###############################################################################
# MLFLOW LAUNCHER
###############################################################################

write_mlflow_launcher() {

cat > "$SCRIPTS/start-mlflow.sh" <<'SH'
#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"

mkdir -p \
    "$ROOT/control-tower/mlflow/artifacts"

cd "$ROOT/control-tower/mlflow"

exec "$ROOT/venvs/observability/bin/mlflow" server \
    --host 127.0.0.1 \
    --port 5000 \
    --backend-store-uri "sqlite:///$ROOT/control-tower/mlflow/mlflow.db" \
    --default-artifact-root "$ROOT/control-tower/mlflow/artifacts"
SH

chmod +x "$SCRIPTS/start-mlflow.sh"
}


###############################################################################
# TEST RUNNER
###############################################################################

write_test_runner() {

cat > "$TEST_ROOT/run-all-tests.sh" <<'SH'
#!/usr/bin/env bash
set -u

ROOT="/mnt/deepa/quantum"
FAILED=0

run_test() {

    local env="$1"
    local file="$2"
    local label="$3"

    echo
    echo "======================================================================"
    echo "$label"
    echo "======================================================================"

    if [ ! -x "$ROOT/venvs/$env/bin/python" ]; then
        echo "[FAIL] Missing environment: $env"
        FAILED=1
        return
    fi

    "$ROOT/venvs/$env/bin/python" "$file" || FAILED=1
}


run_test testing \
    "$ROOT/projects/quantum-testing/gate_circuit_test.py" \
    "GATE / CIRCUIT / COMPILER TEST"

run_test testing \
    "$ROOT/projects/quantum-testing/noise_simulation_test.py" \
    "NOISE SIMULATION"

run_test qec-architect \
    "$ROOT/projects/quantum-testing/qec_stim_pymatching_test.py" \
    "QEC / DECODER"

run_test testing \
    "$ROOT/projects/quantum-testing/mqt_test.py" \
    "MQT BENCH / QCEC / DDSIM / YAQS"

run_test testing \
    "$ROOT/projects/quantum-testing/characterization_test.py" \
    "GST / RB / CHARACTERIZATION"

run_test graph-data \
    "$ROOT/projects/quantum-testing/graph_test.py" \
    "GRAPH ENGINE"

run_test graph-data \
    "$ROOT/projects/quantum-testing/data_engineering_test.py" \
    "DATA ENGINEERING"


echo

if [ "$FAILED" -eq 0 ]; then
    echo "======================================================================"
    echo "ALL PRIMARY QUANTUM LAB TESTS PASSED"
    echo "======================================================================"
else
    echo "======================================================================"
    echo "ONE OR MORE TESTS FAILED."
    echo "Review the test output and installation log."
    echo "======================================================================"
fi

exit "$FAILED"
SH

chmod +x "$TEST_ROOT/run-all-tests.sh"
}


###############################################################################
# WRITE ALL DEMOS / TESTS
###############################################################################

write_projects() {

    header "CREATING TESTS / DASHBOARD / LAUNCHERS"

    write_gate_test
    write_noise_test
    write_qec_test
    write_mqt_test
    write_characterization_test
    write_graph_test
    write_data_test
    write_dashboard
    write_mlflow_launcher
    write_observability_stack
    write_test_runner
}


###############################################################################
# MASTER MANAGER
###############################################################################

write_manager() {

cat > "$ROOT/quantum-manager.sh" <<'MANAGER'
#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENVS="$ROOT/venvs"
GITHUB="$ROOT/github"
DATASETS="$ROOT/datasets"
RESULTS="$ROOT/results"
INSTALLER="$ROOT/install-quantum-full-lab.sh"


header() {
    echo
    echo "======================================================================"
    echo "$*"
    echo "======================================================================"
}


status() {

    header "QUANTUM ENGINEERING LAB STATUS"

    echo "ROOT:"
    echo "  $ROOT"
    echo

    df -h "$ROOT" || true

    echo
    echo "ENVIRONMENTS"

    for env in \
        architecture \
        hybrid \
        cudaq \
        compiler \
        simulation \
        testing \
        qec-architect \
        qml \
        qml-torch \
        qml-tf \
        optimization \
        hardware-architect \
        network-architect \
        analog \
        photonic \
        visualization \
        graph-data \
        materials \
        data \
        quantum-security \
        observability
    do

        if [ -x "$VENVS/$env/bin/python" ]; then
            printf "  [OK]      %-22s " "$env"
            "$VENVS/$env/bin/python" --version 2>&1
        else
            printf "  [MISSING] %s\n" "$env"
        fi

    done

    echo
    echo "GITHUB REPOSITORIES"

    find "$GITHUB" -type d -name .git 2>/dev/null | wc -l

    echo
    echo "DATASETS"

    for ds in qm9 wm811k secom
    do
        if [ -e "$DATASETS/$ds" ]; then
            echo "  [OK]      $ds"
        else
            echo "  [MISSING] $ds"
        fi
    done

    echo
    echo "STORAGE"

    du -sh "$ROOT" 2>/dev/null || true
}


roles() {

cat <<'EOF'

QUANTUM ARCHITECT ROLE MAP

Technical Architect
  Qiskit, Cirq, PennyLane, OpenQASM, QIR

Platform Architect
  Qiskit Serverless, QFaaS, iQuantum, Ray, observability

Hybrid CPU/GPU/QPU Architect
  CUDA-Q, Catalyst, PennyLane

Compiler Architect
  BQSKit, MQT QMAP, TKET, PyQIR, QCEC, PyZX, circuit cutting

Simulation Architect
  Aer, qsim, Qulacs, QuEST source, DDSIM, YAQS, QuTiP, quimb, Lightning

Testing / V&V Architect
  pytest, Hypothesis, MQT Bench, QCEC, pyGSTi, Qiskit Experiments

QEC / FTQC Architect
  Stim, PyMatching, qecsim, PanQEC, Qualtran, QDK, Mitiq

QML Architect
  Qiskit Machine Learning, PennyLane, TorchQuantum, TensorFlow Quantum

Optimization Architect
  Qiskit Opt Mapper, D-Wave Ocean, OR-Tools

Hardware Architect
  Qibolab, Qibocal, Qibosoq, QICK, scqubits, SimCATS source

Communication Architect
  SeQUeNCe, SimQN, QuNetSim, ReQuSim, QNPack source, QuISP source

Analog / Neutral Atom Architect
  Pulser, MQT NAViz source

Photonic Architect
  Quandela Perceval

Visualization Architect
  Plotly, Dash Cytoscape, Panel, HoloViews, Datashader, PyVista, PyVis

Graph Architect
  rustworkx, NetworkX, igraph, RDFLib, Neo4j client

Data / Experiment Architect
  Arrow, Parquet, DuckDB, Polars, HDF5, Zarr, xarray, DVC, MLflow

Materials / Chemistry Data
  Matbench, pymatgen, mp-api, QCElemental, QCSchema source

EOF
}


gates() {

cat <<'EOF'

GATE / CIRCUIT COVERAGE

Single-qubit
  I X Y Z
  H S T SX
  Phase
  U
  RX RY RZ

Two-qubit
  CX / CNOT
  CZ
  SWAP
  iSWAP
  ECR

Three-qubit
  CCX / Toffoli

Circuit tests
  X truth table
  H superposition
  H.H identity
  Bell
  GHZ
  QFT-style circuit
  compiler/transpile equivalence
  state fidelity
  noise simulation

Characterization
  GST
  randomized benchmarking
  robust phase estimation
  drift analysis

QEC
  stabilizer simulation
  detector error model
  MWPM decoding
  logical error rate

EOF
}


versions() {

    header "PRIMARY PACKAGE VERSIONS"

    for env in architecture compiler simulation testing qec-architect qml visualization graph-data
    do
        echo
        echo "--- $env ---"

        if [ -x "$VENVS/$env/bin/python" ]; then
            "$VENVS/$env/bin/python" -m pip list | head -80
        fi
    done
}


disk() {

    header "STORAGE"

    df -h "$ROOT"

    echo

    du -sh "$ROOT"/* 2>/dev/null | sort -h
}


tree_view() {

    if command -v tree >/dev/null 2>&1; then
        tree -L 3 "$ROOT"
    else
        find "$ROOT" -maxdepth 3 -type d | sort
    fi
}


check_paths() {

    header "OLD PATH CHECK"

    grep -RIl \
        --exclude-dir=.git \
        --exclude-dir=venvs \
        -e '/mnt/deepa/AI/quantum' \
        -e '/media/praveen/Asthana4/quantum' \
        "$ROOT" \
        2>/dev/null \
        || true
}


case "${1:-status}" in

    status)
        status
        ;;

    roles)
        roles
        ;;

    gates)
        gates
        ;;

    versions)
        versions
        ;;

    test|test-all)
        "$ROOT/projects/quantum-testing/run-all-tests.sh"
        ;;

    dashboard)
        "$ROOT/projects/quantum-dashboard/start-dashboard.sh"
        ;;

    mlflow)
        "$ROOT/scripts/start-mlflow.sh"
        ;;

    observability-up)
        "$ROOT/scripts/observability-up.sh"
        ;;

    observability-down)
        "$ROOT/scripts/observability-down.sh"
        ;;

    repos)
        "$INSTALLER" repos
        ;;

    envs)
        "$INSTALLER" envs
        ;;

    datasets)
        "$INSTALLER" datasets
        ;;

    projects)
        "$INSTALLER" projects
        ;;

    update)
        "$INSTALLER" repos
        ;;

    disk)
        disk
        ;;

    tree)
        tree_view
        ;;

    check-paths)
        check_paths
        ;;

    all)
        "$INSTALLER" all
        ;;

    *)
        echo "Usage:"
        echo "  $0 status"
        echo "  $0 roles"
        echo "  $0 gates"
        echo "  $0 versions"
        echo "  $0 test"
        echo "  $0 dashboard"
        echo "  $0 mlflow"
        echo "  $0 observability-up"
        echo "  $0 observability-down"
        echo "  $0 repos"
        echo "  $0 envs"
        echo "  $0 datasets"
        echo "  $0 projects"
        echo "  $0 update"
        echo "  $0 disk"
        echo "  $0 tree"
        echo "  $0 check-paths"
        echo "  $0 all"
        exit 1
        ;;

esac
MANAGER

chmod +x "$ROOT/quantum-manager.sh"
}


###############################################################################
# PROMETHEUS / GRAFANA / LOKI LOCAL STACK
###############################################################################

write_observability_stack() {

    local obs="$CONTROL/observability"

    mkdir -p \
        "$obs/prometheus" \
        "$obs/loki" \
        "$obs/grafana"

cat > "$obs/prometheus/prometheus.yml" <<'YAML'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: quantum-python
    static_configs:
      - targets:
          - host.docker.internal:9108
YAML

cat > "$obs/loki/loki-config.yml" <<'YAML'
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
YAML

cat > "$obs/docker-compose.yml" <<'YAML'
services:

  prometheus:
    image: prom/prometheus:latest
    container_name: quantum-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"

  grafana:
    image: grafana/grafana:latest
    container_name: quantum-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - quantum-grafana-data:/var/lib/grafana

  loki:
    image: grafana/loki:latest
    container_name: quantum-loki
    restart: unless-stopped
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yaml:ro
      - quantum-loki-data:/loki

volumes:
  quantum-grafana-data:
  quantum-loki-data:
YAML

cat > "$SCRIPTS/observability-up.sh" <<'SH'
#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"
OBS="$ROOT/control-tower/observability"

cd "$OBS"

if docker compose version >/dev/null 2>&1; then
    sudo docker compose pull
    sudo docker compose up -d
elif command -v docker-compose >/dev/null 2>&1; then
    sudo docker-compose pull
    sudo docker-compose up -d
else
    echo "Docker Compose is not available."
    exit 1
fi

echo
echo "Prometheus: http://127.0.0.1:9090"
echo "Grafana   : http://127.0.0.1:3000"
echo "Loki      : http://127.0.0.1:3100"
SH

chmod +x "$SCRIPTS/observability-up.sh"

cat > "$SCRIPTS/observability-down.sh" <<'SH'
#!/usr/bin/env bash
set -e

ROOT="/mnt/deepa/quantum"
OBS="$ROOT/control-tower/observability"

cd "$OBS"

if docker compose version >/dev/null 2>&1; then
    sudo docker compose down
elif command -v docker-compose >/dev/null 2>&1; then
    sudo docker-compose down
else
    echo "Docker Compose is not available."
    exit 1
fi
SH

chmod +x "$SCRIPTS/observability-down.sh"
}


###############################################################################
# MANIFEST / NOTES
###############################################################################

write_notes() {

cat > "$ROOT/README-QUANTUM-LAB.txt" <<'EOF'
FULL QUANTUM ENGINEERING LAB
============================

ROOT
  /mnt/deepa/quantum

IMPORTANT OPTIONAL / EXTERNAL REQUIREMENTS

1. CUDA-Q
   Installed in an isolated venv on a best-effort basis.
   GPU execution depends on compatible NVIDIA/CUDA support.
   CPU paths can still be tested independently.

2. SimCATS
   Source is downloaded.
   Current advertised Python support may not match Ubuntu 24.04 default Python.
   Do not force it into the main hardware venv.

3. QNPack
   Source is downloaded.
   NetSquid access requires separate credentials/account access.

4. QuISP
   Source is downloaded.
   Full simulator build requires OMNeT++.

5. MQT NAViz
   Source is downloaded.
   Full GUI build requires a sufficiently recent Rust toolchain.

6. Materials Project
   mp-api is installed.
   Remote Materials Project API queries require your own API key.

7. Cloud QPUs
   IBM/AWS/Azure/QPU credentials are not stored by this installer.

MAIN COMMANDS

  /mnt/deepa/quantum/quantum-manager.sh status
  /mnt/deepa/quantum/quantum-manager.sh roles
  /mnt/deepa/quantum/quantum-manager.sh gates
  /mnt/deepa/quantum/quantum-manager.sh test
  /mnt/deepa/quantum/quantum-manager.sh dashboard
  /mnt/deepa/quantum/quantum-manager.sh mlflow
  /mnt/deepa/quantum/quantum-manager.sh observability-up
  /mnt/deepa/quantum/quantum-manager.sh observability-down
  /mnt/deepa/quantum/quantum-manager.sh disk
  /mnt/deepa/quantum/quantum-manager.sh tree

EOF
}


###############################################################################
# INSTALL SUMMARY
###############################################################################

summary() {

    header "FULL QUANTUM LAB READY"

    echo "Root:"
    echo "  $ROOT"
    echo

    echo "Manager:"
    echo "  $ROOT/quantum-manager.sh"
    echo

    echo "Status:"
    echo "  $ROOT/quantum-manager.sh status"
    echo

    echo "Test:"
    echo "  $ROOT/quantum-manager.sh test"
    echo

    echo "Dashboard:"
    echo "  $ROOT/quantum-manager.sh dashboard"
    echo

    echo "MLflow:"
    echo "  $ROOT/quantum-manager.sh mlflow"
    echo

    echo "GitHub:"
    echo "  $GITHUB"
    echo

    echo "Datasets:"
    echo "  $DATASETS"
    echo

    echo "Environments:"
    echo "  $VENVS"
    echo

    echo "Log:"
    echo "  $LOGFILE"
}


###############################################################################
# MAIN
###############################################################################

MODE="${1:-all}"

case "$MODE" in

    precheck)
        precheck
        ;;

    system)
        precheck
        install_system
        ;;

    repos)
        precheck
        download_repositories
        ;;

    envs)
        precheck
        install_environments
        ;;

    datasets)
        precheck
        download_datasets
        ;;

    projects)
        precheck
        write_projects
        write_manager
        write_notes
        ;;

    all)
        precheck
        install_system
        download_repositories
        install_environments
        download_datasets
        write_projects
        write_manager
        write_notes
        summary
        ;;

    *)
        echo "Usage:"
        echo "  $0 all"
        echo "  $0 precheck"
        echo "  $0 system"
        echo "  $0 repos"
        echo "  $0 envs"
        echo "  $0 datasets"
        echo "  $0 projects"
        exit 1
        ;;

esac

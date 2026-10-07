#!/usr/bin/env bash

set -Eeuo pipefail

###############################################################################
# QUANTUM MASTER PLATFORM
#
# SINGLE ROOT:
#   /mnt/deepa/quantum
#
# Everything created by this installer stays below this folder except
# normal Ubuntu system packages installed with apt.
###############################################################################

ROOT="/mnt/deepa/quantum"

GITHUB="$ROOT/github"
DATASETS="$ROOT/datasets"
VENVS="$ROOT/venvs"
PROJECTS="$ROOT/projects"
SCRIPTS="$ROOT/scripts"
LOGS="$ROOT/logs"
RESULTS="$ROOT/results"
NOTEBOOKS="$ROOT/notebooks"
SIMULATIONS="$ROOT/simulations"
CONTROL_TOWER="$ROOT/control-tower"
MANIFESTS="$ROOT/manifests"
CACHE="$ROOT/.cache"

mkdir -p \
    "$ROOT" \
    "$GITHUB" \
    "$DATASETS" \
    "$VENVS" \
    "$PROJECTS" \
    "$SCRIPTS" \
    "$LOGS" \
    "$RESULTS" \
    "$NOTEBOOKS" \
    "$SIMULATIONS" \
    "$CONTROL_TOWER" \
    "$MANIFESTS" \
    "$CACHE/pip" \
    "$CACHE/kagglehub"

###############################################################################
# FORCE CACHES INTO DEEPA QUANTUM
###############################################################################

export PIP_CACHE_DIR="$CACHE/pip"
export XDG_CACHE_HOME="$CACHE"
export KAGGLEHUB_CACHE="$CACHE/kagglehub"

LOGFILE="$LOGS/install-$(date +%Y%m%d-%H%M%S).log"

exec > >(tee -a "$LOGFILE") 2>&1

###############################################################################
# ERROR HANDLING
###############################################################################

trap '
echo
echo "================================================================"
echo "ERROR near line $LINENO"
echo "Check:"
echo "  '"$LOGFILE"'"
echo "================================================================"
' ERR


msg() {
    echo
    echo "================================================================"
    echo "$*"
    echo "================================================================"
}


warn() {
    echo
    echo "[WARNING] $*"
}


###############################################################################
# ROOT CHECK
###############################################################################

msg "QUANTUM MASTER INSTALLER"

echo "ROOT      : $ROOT"
echo "GITHUB    : $GITHUB"
echo "DATASETS  : $DATASETS"
echo "VENVS     : $VENVS"
echo "LOG       : $LOGFILE"

if [ ! -d "/mnt/deepa" ]; then
    echo "ERROR: /mnt/deepa is not mounted."
    exit 1
fi

df -h /mnt/deepa || true


###############################################################################
# UBUNTU PACKAGES
###############################################################################

install_system() {

    msg "INSTALLING UBUNTU DEPENDENCIES"

    sudo apt-get update

    sudo apt-get install -y \
        git \
        git-lfs \
        curl \
        wget \
        rsync \
        unzip \
        zip \
        jq \
        tree \
        build-essential \
        cmake \
        ninja-build \
        pkg-config \
        graphviz \
        python3 \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-tk \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        libhdf5-dev \
        libssl-dev \
        libffi-dev

    # Optional engineering packages.
    sudo apt-get install -y gmsh || warn "gmsh apt installation skipped."
    sudo apt-get install -y klayout || warn "KLayout apt installation skipped."

    git lfs install || true
}


###############################################################################
# GITHUB MANIFEST
###############################################################################

create_repo_manifest() {

cat > "$MANIFESTS/github.tsv" <<'EOF'
# CATEGORY|NAME|URL

core|qiskit|https://github.com/Qiskit/qiskit.git
core|qiskit-aer|https://github.com/Qiskit/qiskit-aer.git
core|cirq|https://github.com/quantumlib/Cirq.git
core|pennylane|https://github.com/PennyLaneAI/pennylane.git
core|cuda-quantum|https://github.com/NVIDIA/cuda-quantum.git
core|mitiq|https://github.com/unitaryfund/mitiq.git
core|dwave-ocean-sdk|https://github.com/dwavesystems/dwave-ocean-sdk.git

compiler|mqt-qmap|https://github.com/qu-tan-um/mqt-qmap.git
compiler|bqskit|https://github.com/BQSKit/bqskit.git
compiler|tket|https://github.com/CQCL/tket.git
compiler|pyqir|https://github.com/qir-alliance/pyqir.git
compiler|qir-spec|https://github.com/qir-alliance/qir-spec.git
compiler|qiskit-addon-cutting|https://github.com/Qiskit/qiskit-addon-cutting.git

qec|stim|https://github.com/quantumlib/Stim.git
qec|pymatching|https://github.com/oscarhiggott/PyMatching.git
qec|qualtran|https://github.com/quantumlib/Qualtran.git
qec|qecsim|https://github.com/qecsim/qecsim.git
qec|panqec|https://github.com/panqec/panqec.git

chemistry|pyscf|https://github.com/pyscf/pyscf.git
chemistry|openfermion|https://github.com/quantumlib/OpenFermion.git
chemistry|qiskit-nature|https://github.com/qiskit-community/qiskit-nature.git
chemistry|qiskit-nature-pyscf|https://github.com/qiskit-community/qiskit-nature-pyscf.git
chemistry|qdk-chemistry|https://github.com/microsoft/qdk-chemistry.git

manybody|quspin|https://github.com/QuSpin/QuSpin.git
manybody|tenpy|https://github.com/tenpy/tenpy.git
manybody|netket|https://github.com/netket/netket.git

network|sequence|https://github.com/sequence-toolbox/SeQUeNCe.git
network|simqn|https://github.com/QNLab-USTC/SimQN.git
network|qunetsim|https://github.com/tqsd/QuNetSim.git
network|requsim|https://github.com/jwallnoefer/requsim.git

hardware|qibolab|https://github.com/qiboteam/qibolab.git
hardware|qibocal|https://github.com/qiboteam/qibocal.git
hardware|qibosoq|https://github.com/qiboteam/qibosoq.git
hardware|qick|https://github.com/openquantumhardware/qick.git
hardware|scqubits|https://github.com/scqubits/scqubits.git

fabrication|gdsfactory|https://github.com/gdsfactory/gdsfactory.git
fabrication|quantum-rf-pdk|https://github.com/gdsfactory/quantum-rf-pdk.git
fabrication|sqdmetal|https://github.com/sqdlab/SQDMetal.git
fabrication|kqcircuits|https://github.com/iqm-finland/KQCircuits.git
fabrication|palace|https://github.com/awslabs/palace.git

sensing|qudi-core|https://github.com/Ulm-IQO/qudi-core.git
sensing|qudi-iqo-modules|https://github.com/Ulm-IQO/qudi-iqo-modules.git
sensing|uncutgem|https://github.com/QuantumVillage/UncutGem.git
sensing|ramsey-fpga|https://github.com/Kleven2k/ramsey.git
sensing|nvratemodel|https://github.com/sernstETH/nvratemodel.git

metrology|quanestimation|https://github.com/QuanEstimation/QuanEstimation.git
metrology|quanestimation-education|https://github.com/QuanEstimation/Education.git
metrology|allantools|https://github.com/aewallin/allantools.git
metrology|kshana|https://github.com/AshfordeOU/kshana.git
EOF

}


###############################################################################
# CLONE / UPDATE REPOSITORIES
###############################################################################

download_repositories() {

    create_repo_manifest

    msg "DOWNLOADING / UPDATING QUANTUM GITHUB REPOSITORIES"

    while IFS='|' read -r category name url
    do
        [[ -z "${category:-}" ]] && continue
        [[ "$category" =~ ^# ]] && continue

        CATEGORY_DIR="$GITHUB/$category"
        DEST="$CATEGORY_DIR/$name"

        mkdir -p "$CATEGORY_DIR"

        echo
        echo "[$category] $name"

        if [ -d "$DEST/.git" ]; then

            git -C "$DEST" pull --ff-only \
                || warn "Could not update $name"

        else

            git clone \
                --depth 1 \
                "$url" \
                "$DEST" \
                || warn "Could not clone $url"

        fi

    done < "$MANIFESTS/github.tsv"

}


###############################################################################
# VIRTUAL ENVIRONMENT FUNCTIONS
###############################################################################

create_venv() {

    ENV_NAME="$1"
    ENV_PATH="$VENVS/$ENV_NAME"

    if [ ! -x "$ENV_PATH/bin/python" ]; then

        echo
        echo "Creating environment: $ENV_NAME"

        python3 -m venv "$ENV_PATH"

    fi

    "$ENV_PATH/bin/python" -m pip install \
        --upgrade \
        pip \
        setuptools \
        wheel
}


pip_try() {

    ENV_NAME="$1"
    shift

    ENV_PATH="$VENVS/$ENV_NAME"

    echo
    echo "[$ENV_NAME] Installing:"
    echo "  $*"

    "$ENV_PATH/bin/python" -m pip install --upgrade "$@" \
        || warn "$ENV_NAME: optional package install failed: $*"
}


###############################################################################
# ENVIRONMENTS
###############################################################################

install_environments() {

    msg "CREATING ISOLATED QUANTUM ENVIRONMENTS"

    ###########################################################################
    # CORE
    ###########################################################################

    create_venv core

    pip_try core \
        numpy \
        scipy \
        pandas \
        matplotlib \
        sympy \
        networkx \
        jupyterlab \
        ipykernel \
        pytest \
        qiskit \
        qiskit-aer \
        qiskit-algorithms \
        qiskit-machine-learning \
        cirq \
        pennylane \
        mitiq \
        dwave-ocean-sdk \
        openqasm3 \
        pyqir


    ###########################################################################
    # COMPILER / IR / CIRCUIT CUTTING
    ###########################################################################

    create_venv compiler

    pip_try compiler \
        numpy \
        scipy \
        qiskit \
        mqt.qmap \
        bqskit \
        pytket \
        pyqir \
        openqasm3 \
        qiskit-addon-cutting


    ###########################################################################
    # QEC / FTQC
    ###########################################################################

    create_venv qec

    pip_try qec \
        numpy \
        scipy \
        matplotlib \
        networkx \
        stim \
        pymatching

    pip_try qec qecsim
    pip_try qec panqec
    pip_try qec qualtran


    ###########################################################################
    # CHEMISTRY
    ###########################################################################

    create_venv chemistry

    pip_try chemistry \
        numpy \
        scipy \
        pandas \
        matplotlib \
        jupyterlab \
        qiskit \
        qiskit-algorithms \
        qiskit-nature \
        qiskit-nature-pyscf \
        pyscf \
        openfermion \
        rdkit


    ###########################################################################
    # MANY-BODY
    ###########################################################################

    create_venv manybody

    pip_try manybody \
        numpy \
        scipy \
        pandas \
        matplotlib \
        jupyterlab \
        qutip

    pip_try manybody quspin
    pip_try manybody physics-tenpy
    pip_try manybody netket


    ###########################################################################
    # QUANTUM NETWORK
    ###########################################################################

    create_venv network

    pip_try network \
        numpy \
        scipy \
        pandas \
        matplotlib \
        networkx \
        qutip \
        simpy

    pip_try network simqn
    pip_try network qunetsim


    ###########################################################################
    # HARDWARE / CONTROL / READOUT
    ###########################################################################

    create_venv hardware

    pip_try hardware \
        numpy \
        scipy \
        pandas \
        matplotlib \
        qutip \
        scqubits \
        scikit-rf \
        pyvisa \
        pyserial \
        gmsh \
        pyvista

    pip_try hardware qibolab
    pip_try hardware qibocal


    ###########################################################################
    # SENSING
    ###########################################################################

    create_venv sensing

    pip_try sensing \
        numpy \
        scipy \
        pandas \
        matplotlib \
        qutip \
        scikit-learn \
        scikit-image \
        opencv-python \
        filterpy \
        jupyterlab


    ###########################################################################
    # METROLOGY / CLOCK / PNT
    ###########################################################################

    create_venv metrology

    pip_try metrology \
        numpy \
        scipy \
        pandas \
        matplotlib \
        qutip \
        pennylane \
        allantools \
        filterpy \
        jupyterlab

    pip_try metrology kshana
    pip_try metrology quanestimation


    ###########################################################################
    # DATA DOWNLOAD ENVIRONMENT
    ###########################################################################

    create_venv data

    pip_try data \
        kagglehub \
        requests \
        pandas \
        pyarrow

}


###############################################################################
# DATASET MANIFEST
###############################################################################

create_dataset_manifest() {

cat > "$MANIFESTS/datasets.tsv" <<'EOF'
# NAME|SOURCE|HANDLE
qm9|kaggle|zaharch/quantum-machine-9-aka-qm9
wm811k|kaggle|qingyi/wm811k-wafer-map
secom|uci|https://archive.ics.uci.edu/ml/machine-learning-databases/secom/
EOF

}


###############################################################################
# KAGGLE + UCI DATASETS
###############################################################################

download_datasets() {

    create_dataset_manifest

    msg "DOWNLOADING QUANTUM / FABRICATION DATASETS"

    DATA_PY="$VENVS/data/bin/python"

    if [ ! -x "$DATA_PY" ]; then
        create_venv data
        pip_try data kagglehub requests pandas pyarrow
    fi


    ###########################################################################
    # QM9 + WM811K VIA KAGGLEHUB
    ###########################################################################

    "$DATA_PY" - <<PY
import os
from pathlib import Path

os.environ["KAGGLEHUB_CACHE"] = "$CACHE/kagglehub"

import kagglehub

root = Path("$DATASETS")
root.mkdir(parents=True, exist_ok=True)

datasets = {
    "qm9": "zaharch/quantum-machine-9-aka-qm9",
    "wm811k": "qingyi/wm811k-wafer-map",
}

for name, handle in datasets.items():

    print()
    print("=" * 70)
    print("Downloading:", name)
    print("Handle     :", handle)
    print("=" * 70)

    try:
        downloaded = Path(
            kagglehub.dataset_download(handle)
        ).resolve()

        print("Kaggle cache:", downloaded)

        destination = root / name

        if destination.is_symlink():
            destination.unlink()

        if not destination.exists():
            destination.symlink_to(
                downloaded,
                target_is_directory=True
            )

        print("Dataset path:", destination)

    except Exception as exc:
        print("WARNING:", name, "download failed:", exc)

PY


    ###########################################################################
    # SECOM DIRECT FROM UCI
    ###########################################################################

    mkdir -p "$DATASETS/secom"

    curl -L \
        --retry 3 \
        -o "$DATASETS/secom/secom.data" \
        "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom.data" \
        || warn "SECOM data download failed."

    curl -L \
        --retry 3 \
        -o "$DATASETS/secom/secom_labels.data" \
        "https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom_labels.data" \
        || warn "SECOM labels download failed."


    echo
    echo "Dataset folders:"
    du -sh "$DATASETS"/* 2>/dev/null || true
}


###############################################################################
# CREATE QUANTUM CLOCK PROJECT USING CORRECT ROOT
###############################################################################

create_clock_project() {

    CLOCK_PROJECT="$PROJECTS/quantum-clock"

    mkdir -p "$CLOCK_PROJECT"

cat > "$CLOCK_PROJECT/quantum_clock_demo.py" <<'PY'
#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import allantools


ROOT = Path("/mnt/deepa/quantum")
RESULTS = ROOT / "results" / "quantum-clock"

RESULTS.mkdir(
    parents=True,
    exist_ok=True
)


###############################################################################
# RAMSEY FRINGE
###############################################################################

detuning = np.linspace(
    -5.0,
    5.0,
    501
)

T = 1.0

probability = (
    1.0
    +
    np.cos(detuning * T)
) / 2.0


df = pd.DataFrame({
    "detuning": detuning,
    "excited_probability": probability
})

df.to_csv(
    RESULTS / "ramsey_fringe.csv",
    index=False
)


plt.figure(figsize=(9, 5))

plt.plot(
    detuning,
    probability
)

plt.xlabel("Detuning")
plt.ylabel("Excited-state probability")
plt.title("Ramsey Clock Fringe")
plt.grid(True)

plt.tight_layout()

plt.savefig(
    RESULTS / "ramsey_fringe.png",
    dpi=160
)

plt.close()


###############################################################################
# SYNTHETIC CLOCK NOISE
###############################################################################

rng = np.random.default_rng(42)

fractional_frequency = rng.normal(
    0.0,
    1e-12,
    30000
)


taus, adev, errors, counts = allantools.oadev(
    fractional_frequency,
    rate=1.0,
    data_type="freq",
    taus="decade"
)


adev_df = pd.DataFrame({
    "tau_seconds": taus,
    "oadev": adev,
    "error": errors,
    "samples": counts
})


adev_df.to_csv(
    RESULTS / "allan_deviation.csv",
    index=False
)


plt.figure(figsize=(9, 5))

plt.loglog(
    taus,
    adev,
    marker="o"
)

plt.xlabel("Averaging time τ (s)")
plt.ylabel("Overlapping Allan deviation")
plt.title("Synthetic Clock Stability")
plt.grid(True, which="both")

plt.tight_layout()

plt.savefig(
    RESULTS / "allan_deviation.png",
    dpi=160
)

plt.close()


print()
print("=" * 70)
print("QUANTUM CLOCK TEST: PASS")
print("=" * 70)
print("Results:", RESULTS)
print()
PY

    chmod +x "$CLOCK_PROJECT/quantum_clock_demo.py"
}


###############################################################################
# MASTER MANAGER
###############################################################################

create_manager() {

cat > "$ROOT/quantum-manager.sh" <<'MANAGER'
#!/usr/bin/env bash

set -Eeuo pipefail

###############################################################################
# SELF-DETECT ROOT
#
# This avoids hard-coding /mnt/deepa/AI/quantum or another old path.
###############################################################################

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENVS="$ROOT/venvs"
GITHUB="$ROOT/github"
DATASETS="$ROOT/datasets"
PROJECTS="$ROOT/projects"
RESULTS="$ROOT/results"
INSTALLER="$ROOT/install-quantum-master.sh"


header() {
    echo
    echo "============================================================"
    echo "$*"
    echo "============================================================"
}


status() {

    header "QUANTUM PLATFORM STATUS"

    echo "ROOT:"
    echo "  $ROOT"

    echo
    df -h "$ROOT" || true

    echo
    echo "VIRTUAL ENVIRONMENTS"

    for env in \
        core \
        compiler \
        qec \
        chemistry \
        manybody \
        network \
        hardware \
        sensing \
        metrology \
        data
    do

        if [ -x "$VENVS/$env/bin/python" ]; then

            printf "  [OK]      %-15s " "$env"

            "$VENVS/$env/bin/python" \
                --version 2>&1

        else

            printf "  [MISSING] %s\n" "$env"

        fi

    done


    echo
    echo "GITHUB"

    REPO_COUNT=$(
        find "$GITHUB" \
            -type d \
            -name .git \
            2>/dev/null \
            | wc -l
    )

    echo "  repositories: $REPO_COUNT"


    echo
    echo "DATASETS"

    for ds in qm9 wm811k secom
    do

        if [ -e "$DATASETS/$ds" ]; then
            echo "  [OK] $ds"
        else
            echo "  [MISSING] $ds"
        fi

    done


    echo
    echo "STORAGE"

    du -sh "$ROOT" 2>/dev/null || true
}


repos() {
    "$INSTALLER" repos
}


datasets() {
    "$INSTALLER" datasets
}


envs() {
    "$INSTALLER" envs
}


update() {
    "$INSTALLER" repos
}


clock() {

    PY="$VENVS/metrology/bin/python"

    APP="$PROJECTS/quantum-clock/quantum_clock_demo.py"

    if [ ! -x "$PY" ]; then
        echo "Metrology environment missing."
        exit 1
    fi

    if [ ! -f "$APP" ]; then
        echo "Clock demo missing."
        exit 1
    fi

    "$PY" "$APP"

    echo
    echo "Clock results:"
    ls -lh "$RESULTS/quantum-clock" || true
}


jupyter() {

    ENV="${1:-core}"

    if [ ! -x "$VENVS/$ENV/bin/jupyter" ]; then

        echo "Jupyter is not installed in environment: $ENV"
        exit 1

    fi

    cd "$ROOT"

    exec "$VENVS/$ENV/bin/jupyter" lab \
        --notebook-dir="$ROOT" \
        --ip=127.0.0.1 \
        --port=8888 \
        --no-browser
}


test_core() {

    header "CORE TEST"

    "$VENVS/core/bin/python" - <<'PY'
import numpy
import scipy
import qiskit
import cirq
import pennylane

print("NumPy     :", numpy.__version__)
print("SciPy     :", scipy.__version__)
print("Qiskit    :", qiskit.__version__)
print("Cirq      :", cirq.__version__)
print("PennyLane :", pennylane.__version__)

print()
print("CORE TEST: PASS")
PY
}


test_qec() {

    header "QEC TEST"

    "$VENVS/qec/bin/python" - <<'PY'
import stim
import pymatching

print("Stim       :", stim.__version__)
print("PyMatching :", pymatching.__version__)

c = stim.Circuit("""
H 0
M 0
""")

print("Stim circuit:")
print(c)

print()
print("QEC TEST: PASS")
PY
}


test_chemistry() {

    header "CHEMISTRY TEST"

    "$VENVS/chemistry/bin/python" - <<'PY'
import pyscf
import openfermion
import qiskit_nature

print("PySCF       :", pyscf.__version__)
print("OpenFermion :", openfermion.__version__)
print("QiskitNature:", qiskit_nature.__version__)

print()
print("CHEMISTRY TEST: PASS")
PY
}


test_metrology() {

    header "METROLOGY TEST"

    "$VENVS/metrology/bin/python" - <<'PY'
import qutip
import allantools
import pennylane

print("QuTiP      :", qutip.__version__)
print("AllanTools : installed")
print("PennyLane  :", pennylane.__version__)

try:
    import kshana
    print("Kshana     : installed")
except Exception as e:
    print("Kshana     : optional import issue:", e)

print()
print("METROLOGY TEST: PASS")
PY
}


test_all() {

    FAILED=0

    test_core || FAILED=1
    test_qec || FAILED=1
    test_chemistry || FAILED=1
    test_metrology || FAILED=1

    echo

    if [ "$FAILED" -eq 0 ]; then

        echo "============================================================"
        echo "ALL PRIMARY TESTS PASSED"
        echo "============================================================"

    else

        echo "============================================================"
        echo "ONE OR MORE OPTIONAL TESTS FAILED."
        echo "Review the install log."
        echo "============================================================"

        return 1

    fi
}


tree_view() {

    if command -v tree >/dev/null 2>&1; then

        tree \
            -L 3 \
            "$ROOT"

    else

        find \
            "$ROOT" \
            -maxdepth 3 \
            -type d \
            | sort

    fi
}


disk() {

    header "QUANTUM STORAGE"

    df -h "$ROOT"

    echo

    du -sh "$ROOT"/* 2>/dev/null \
        | sort -h
}


check_paths() {

    header "CHECKING FOR OLD HARDCODED PATHS"

    grep -RIl \
        --exclude-dir=.git \
        --exclude-dir=venvs \
        -e '/mnt/deepa/AI/quantum' \
        -e '/media/praveen/Asthana4/quantum' \
        "$ROOT" \
        2>/dev/null \
        || true

    echo
    echo "If no files appeared above, active scripts are clean."
}


usage() {

cat <<EOF

Quantum Manager

ROOT:
  $ROOT

Commands:

  ./quantum-manager.sh status
  ./quantum-manager.sh repos
  ./quantum-manager.sh datasets
  ./quantum-manager.sh envs
  ./quantum-manager.sh update

  ./quantum-manager.sh test
  ./quantum-manager.sh test-core
  ./quantum-manager.sh test-qec
  ./quantum-manager.sh test-chemistry
  ./quantum-manager.sh test-metrology

  ./quantum-manager.sh clock

  ./quantum-manager.sh jupyter
  ./quantum-manager.sh jupyter chemistry
  ./quantum-manager.sh jupyter metrology

  ./quantum-manager.sh disk
  ./quantum-manager.sh tree
  ./quantum-manager.sh check-paths

EOF
}


case "${1:-status}" in

    status)
        status
        ;;

    repos)
        repos
        ;;

    datasets)
        datasets
        ;;

    envs)
        envs
        ;;

    update)
        update
        ;;

    test)
        test_all
        ;;

    test-core)
        test_core
        ;;

    test-qec)
        test_qec
        ;;

    test-chemistry)
        test_chemistry
        ;;

    test-metrology)
        test_metrology
        ;;

    clock)
        clock
        ;;

    jupyter)
        jupyter "${2:-core}"
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

    help|-h|--help)
        usage
        ;;

    *)
        echo "Unknown command: $1"
        usage
        exit 1
        ;;

esac

MANAGER

    chmod +x "$ROOT/quantum-manager.sh"
}


###############################################################################
# OLD INSTALLATION INFORMATION
###############################################################################

check_old_locations() {

    msg "CHECKING PREVIOUS QUANTUM LOCATIONS"

    OLD1="/mnt/deepa/AI/quantum"
    OLD2="/media/praveen/Asthana4/quantum"

    for OLD in "$OLD1" "$OLD2"
    do

        if [ -d "$OLD" ]; then

            echo
            echo "Found old location:"
            echo "  $OLD"

            echo
            echo "It is NOT being used by the new platform."
            echo "Do not move its old Python venv directly."
            echo

        fi

    done
}


###############################################################################
# MAIN
###############################################################################

MODE="${1:-all}"

case "$MODE" in

    system)
        install_system
        ;;

    repos)
        download_repositories
        ;;

    envs)
        install_environments
        ;;

    datasets)

        if [ ! -x "$VENVS/data/bin/python" ]; then
            create_venv data
            pip_try data kagglehub requests pandas pyarrow
        fi

        download_datasets
        ;;

    manager)
        create_clock_project
        create_manager
        ;;

    all)

        install_system

        check_old_locations

        download_repositories

        install_environments

        download_datasets

        create_clock_project

        create_manager

        ;;

    *)

        echo "Usage:"
        echo
        echo "  $0 all"
        echo "  $0 system"
        echo "  $0 repos"
        echo "  $0 envs"
        echo "  $0 datasets"
        echo "  $0 manager"

        exit 1
        ;;

esac


###############################################################################
# FINISH
###############################################################################

msg "QUANTUM INSTALLER FINISHED"

echo
echo "ROOT:"
echo "  $ROOT"

echo
echo "Manager:"
echo "  $ROOT/quantum-manager.sh"

echo
echo "Status:"
echo "  $ROOT/quantum-manager.sh status"

echo
echo "Tests:"
echo "  $ROOT/quantum-manager.sh test"

echo
echo "Clock demo:"
echo "  $ROOT/quantum-manager.sh clock"

echo
echo "Datasets:"
echo "  $DATASETS"

echo
echo "GitHub:"
echo "  $GITHUB"

echo
echo "Environments:"
echo "  $VENVS"

echo
echo "Install log:"
echo "  $LOGFILE"

echo
echo "Check old hardcoded paths:"
echo "  $ROOT/quantum-manager.sh check-paths"


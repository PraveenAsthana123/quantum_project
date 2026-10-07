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

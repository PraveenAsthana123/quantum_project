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

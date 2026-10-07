#!/usr/bin/env bash
# =============================================================================
# Quantum Portal — Weekly Benchmark Runner
# Runs all 30 quantum projects, collects accuracy/fidelity/time metrics,
# saves results to benchmarks/YYYY-MM-DD.json, sends summary email.
#
# Usage:
#   ./benchmark_all.sh                   # run all 30 projects
#   ./benchmark_all.sh --projects q01,q05  # run specific projects
#   ./benchmark_all.sh --dry-run           # validate config, no execution
#
# Schedule (crontab):
#   0 2 * * 0 /path/to/benchmark_all.sh >> /var/log/quantum-benchmark.log 2>&1
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BENCHMARK_DIR="${REPO_ROOT}/benchmarks"
DATE="$(date +%Y-%m-%d)"
TIMESTAMP="$(date +%Y-%m-%dT%H:%M:%SZ)"
OUTPUT_FILE="${BENCHMARK_DIR}/${DATE}.json"
LOG_FILE="${BENCHMARK_DIR}/${DATE}.log"
ALERT_EMAIL="${BENCHMARK_ALERT_EMAIL:-temp.genai18@gmail.com}"
API_BASE_URL="${QUANTUM_API_URL:-http://localhost:8000}"
TIMEOUT_SECONDS="${BENCHMARK_TIMEOUT:-300}"   # 5 min per project max
MAX_PARALLEL="${BENCHMARK_PARALLEL:-4}"        # concurrent projects

# All 30 quantum project IDs
ALL_PROJECTS=(
  "q01-algorithms"     "q02-error-mitigation"  "q03-ftqc"
  "q04-compiler"       "q05-ir-interop"        "q06-transpilation"
  "q07-cloud-qpu"      "q08-distributed-qc"    "q09-circuit-cutting"
  "q10-silicon-spin"   "q11-topological"       "q12-analog-qc"
  "q13-control"        "q14-calibration"       "q15-readout"
  "q16-ctrl-electronics" "q17-cryogenics"      "q18-fabrication"
  "q19-packaging"      "q20-chemistry"         "q21-many-body"
  "q22-repeaters"      "q23-memory"            "q24-internet"
  "q25-sensing"        "q26-metrology"         "q27-clocks"
  "qc-banking-lab"     "qc-logistics-lab"      "qc-security"
)

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DRY_RUN=false
SELECTED_PROJECTS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift ;;
    --projects)
      IFS=',' read -ra SELECTED_PROJECTS <<< "$2"
      shift 2 ;;
    *)
      echo "Unknown argument: $1"
      exit 1 ;;
  esac
done

PROJECTS=("${SELECTED_PROJECTS[@]:-${ALL_PROJECTS[@]}}")

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
mkdir -p "${BENCHMARK_DIR}"

log() {
  echo "[$(date +%H:%M:%S)] $*" | tee -a "${LOG_FILE}"
}

log "=== Quantum Benchmark Runner ==="
log "Date: ${DATE}"
log "Projects: ${#PROJECTS[@]}"
log "Output: ${OUTPUT_FILE}"
log "Dry run: ${DRY_RUN}"

if [[ "${DRY_RUN}" == "true" ]]; then
  log "DRY RUN — validating config only"
  for project in "${PROJECTS[@]}"; do
    log "  Would benchmark: ${project}"
  done
  exit 0
fi

# ---------------------------------------------------------------------------
# Check API health before starting
# ---------------------------------------------------------------------------
log "Checking API health at ${API_BASE_URL}/health ..."
if ! curl -sf --max-time 10 "${API_BASE_URL}/health" > /dev/null; then
  log "ERROR: API is not reachable. Aborting benchmark run."
  send_alert "Quantum Benchmark FAILED" "API unreachable at ${API_BASE_URL}" || true
  exit 1
fi
log "API health OK."

# ---------------------------------------------------------------------------
# Run benchmarks
# ---------------------------------------------------------------------------
RESULTS_TMPDIR="$(mktemp -d)"
trap 'rm -rf "${RESULTS_TMPDIR}"' EXIT

benchmark_project() {
  local project_id="$1"
  local result_file="${RESULTS_TMPDIR}/${project_id}.json"
  local start_ts
  start_ts="$(date +%s%N)"

  log "  Starting: ${project_id}"

  # POST to the API benchmark endpoint — runs the project's registered benchmark
  local response
  response="$(curl -sf \
    --max-time "${TIMEOUT_SECONDS}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"project_id\": \"${project_id}\", \"shots\": 1024, \"backend\": \"aer_simulator\"}" \
    "${API_BASE_URL}/api/v1/benchmarks/run" 2>&1)" || {
    local exit_code=$?
    log "  FAILED: ${project_id} (curl exit code ${exit_code})"
    echo "{
      \"project_id\": \"${project_id}\",
      \"status\": \"failed\",
      \"error\": \"curl failed with exit code ${exit_code}\",
      \"run_timestamp\": \"${TIMESTAMP}\"
    }" > "${result_file}"
    return 0
  }

  local end_ts
  end_ts="$(date +%s%N)"
  local elapsed_ms=$(( (end_ts - start_ts) / 1000000 ))

  # Inject elapsed_ms into response
  echo "${response}" | python3 -c "
import json, sys
data = json.load(sys.stdin)
data['wall_time_ms'] = ${elapsed_ms}
print(json.dumps(data))
" > "${result_file}" 2>/dev/null || {
    echo "{
      \"project_id\": \"${project_id}\",
      \"status\": \"parse_error\",
      \"raw_response\": $(echo "${response}" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))"),
      \"wall_time_ms\": ${elapsed_ms},
      \"run_timestamp\": \"${TIMESTAMP}\"
    }" > "${result_file}"
  }

  local status
  status="$(python3 -c "import json; d=json.load(open('${result_file}')); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")"
  log "  Done: ${project_id} — status=${status}, elapsed=${elapsed_ms}ms"
}

export -f benchmark_project log
export RESULTS_TMPDIR TIMESTAMP API_BASE_URL TIMEOUT_SECONDS LOG_FILE

# Run up to MAX_PARALLEL projects simultaneously using GNU parallel or xargs
log "Running benchmarks (max_parallel=${MAX_PARALLEL}) ..."
printf '%s\n' "${PROJECTS[@]}" | \
  xargs -P "${MAX_PARALLEL}" -I {} bash -c 'benchmark_project "$@"' _ {}

# ---------------------------------------------------------------------------
# Aggregate results
# ---------------------------------------------------------------------------
log "Aggregating results ..."

python3 - <<'PYEOF'
import json
import os
import glob
from datetime import datetime, timezone

results_dir = os.environ.get("RESULTS_TMPDIR", "/tmp")
output_file = os.environ.get("OUTPUT_FILE")
timestamp = os.environ.get("TIMESTAMP")

results = []
for f in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
    try:
        with open(f) as fp:
            results.append(json.load(fp))
    except Exception as e:
        print(f"  Warning: could not parse {f}: {e}")

summary = {
    "benchmark_run": {
        "timestamp": timestamp,
        "total_projects": len(results),
        "passed": sum(1 for r in results if r.get("status") == "passed"),
        "failed": sum(1 for r in results if r.get("status") != "passed"),
        "avg_quantum_accuracy": None,
        "avg_classical_accuracy": None,
        "avg_fidelity": None,
    },
    "results": results,
}

# Compute aggregate stats
q_accs = [r["quantum_accuracy"] for r in results if r.get("quantum_accuracy") is not None]
c_accs = [r["classical_accuracy"] for r in results if r.get("classical_accuracy") is not None]
fids   = [r["fidelity"] for r in results if r.get("fidelity") is not None]

if q_accs:
    summary["benchmark_run"]["avg_quantum_accuracy"] = sum(q_accs) / len(q_accs)
if c_accs:
    summary["benchmark_run"]["avg_classical_accuracy"] = sum(c_accs) / len(c_accs)
if fids:
    summary["benchmark_run"]["avg_fidelity"] = sum(fids) / len(fids)

with open(output_file, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"Results written to {output_file}")
print(f"  Total: {summary['benchmark_run']['total_projects']}")
print(f"  Passed: {summary['benchmark_run']['passed']}")
print(f"  Failed: {summary['benchmark_run']['failed']}")
if q_accs:
    print(f"  Avg quantum accuracy: {summary['benchmark_run']['avg_quantum_accuracy']:.4f}")
if c_accs:
    print(f"  Avg classical accuracy: {summary['benchmark_run']['avg_classical_accuracy']:.4f}")
PYEOF

# ---------------------------------------------------------------------------
# Push results to BigQuery (if configured)
# ---------------------------------------------------------------------------
if [[ -n "${GCP_PROJECT:-}" ]]; then
  log "Pushing results to BigQuery ..."
  python3 - <<'PYEOF'
import json
import os
from google.cloud import bigquery

project = os.environ["GCP_PROJECT"]
output_file = os.environ["OUTPUT_FILE"]

with open(output_file) as f:
    data = json.load(f)

client = bigquery.Client(project=project)
table_id = f"{project}.quantum_analytics_prod.quantum_benchmarks"
rows = []
for r in data.get("results", []):
    rows.append({
        "benchmark_id": f"{r['project_id']}-{data['benchmark_run']['timestamp']}",
        "project_id": r.get("project_id"),
        "run_timestamp": data["benchmark_run"]["timestamp"],
        "backend": r.get("backend", "aer_simulator"),
        "circuit_depth": r.get("circuit_depth"),
        "num_qubits": r.get("num_qubits"),
        "fidelity": r.get("fidelity"),
        "execution_time_ms": r.get("execution_time_ms"),
        "classical_accuracy": r.get("classical_accuracy"),
        "quantum_accuracy": r.get("quantum_accuracy"),
        "noise_level": r.get("noise_level"),
        "error_mitigation": r.get("error_mitigation"),
        "model_version": r.get("model_version"),
        "cost_usd": r.get("cost_usd"),
    })

if rows:
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        print(f"BigQuery insert errors: {errors}")
    else:
        print(f"Inserted {len(rows)} benchmark rows to BigQuery")
PYEOF
fi

# ---------------------------------------------------------------------------
# Send summary email
# ---------------------------------------------------------------------------
send_summary_email() {
  local summary_file="$1"
  python3 - "${summary_file}" "${ALERT_EMAIL}" <<'PYEOF'
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

summary_file, to_email = sys.argv[1], sys.argv[2]
smtp_host = os.environ.get("SMTP_HOST", "")

with open(summary_file) as f:
    data = json.load(f)

run = data["benchmark_run"]
body = f"""Quantum Portal — Weekly Benchmark Summary
==========================================
Date:      {run['timestamp']}
Projects:  {run['total_projects']}
Passed:    {run['passed']}
Failed:    {run['failed']}

Averages:
  Quantum Accuracy:   {run.get('avg_quantum_accuracy') or 'N/A'}
  Classical Accuracy: {run.get('avg_classical_accuracy') or 'N/A'}
  Fidelity:           {run.get('avg_fidelity') or 'N/A'}

Failed projects:
"""
for r in data.get("results", []):
    if r.get("status") != "passed":
        body += f"  - {r['project_id']}: {r.get('error', r.get('status', 'unknown'))}\n"

body += f"\nFull results: {summary_file}\n"

if not smtp_host:
    print("SMTP_HOST not set — email not sent. Summary:")
    print(body)
    sys.exit(0)

import os
msg = MIMEMultipart()
msg["Subject"] = f"Quantum Benchmark {'PASSED' if run['failed'] == 0 else 'ATTENTION'} — {run['timestamp'][:10]}"
msg["From"] = "quantum-benchmarks@noreply.local"
msg["To"] = to_email
msg.attach(MIMEText(body, "plain"))

with smtplib.SMTP(smtp_host, int(os.environ.get("SMTP_PORT", 587))) as s:
    s.ehlo()
    s.starttls()
    s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASS", ""))
    s.sendmail(msg["From"], [to_email], msg.as_string())
    print(f"Summary email sent to {to_email}")
PYEOF
}

log "Sending summary email to ${ALERT_EMAIL} ..."
export OUTPUT_FILE
send_summary_email "${OUTPUT_FILE}" || log "Warning: email send failed (non-fatal)"

log "=== Benchmark run complete: ${OUTPUT_FILE} ==="

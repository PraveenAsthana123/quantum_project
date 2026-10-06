"""
Async SQLite database layer for Quantum Portal API.
All CRUD operations use aiosqlite; schema created from schema.sql on startup.
DB path: /mnt/deepa/quantum/api/quantum_portal.db
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — override via environment for container / CI use
# ---------------------------------------------------------------------------
_API_DIR = Path(__file__).parent
DB_PATH = os.environ.get(
    "QUANTUM_DB_PATH",
    str(_API_DIR / "quantum_portal.db"),
)
DB_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
SCHEMA_PATH = str(_API_DIR / "schema.sql")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())[:8]


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _connect() -> aiosqlite.Connection:
    """Return an aiosqlite context-manager connection (NOT awaited here)."""
    return aiosqlite.connect(DB_PATH)


async def init_db() -> None:
    """Create all tables from schema.sql."""
    schema_sql = Path(SCHEMA_PATH).read_text()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        for stmt in schema_sql.split(";"):
            # Strip SQL line comments before checking emptiness
            lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt:
                try:
                    await conn.execute(stmt)
                except Exception as e:
                    logger.warning("Schema stmt warning: %s | stmt: %.80s", e, stmt)
        await conn.commit()


# Keep get_db for any callers that use it directly
async def get_db() -> aiosqlite.Connection:
    """Async context-manager for a raw connection."""
    return _connect()


async def execute(sql: str, params: tuple = ()) -> None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(sql, params)
        await conn.commit()


async def execute_many_fast(statements: list) -> None:
    """Execute a list of (sql, params) tuples in ONE transaction — fast bulk insert."""
    async with _connect() as conn:
        await conn.execute("PRAGMA synchronous=OFF")
        await conn.execute("PRAGMA journal_mode=MEMORY")
        for sql, params in statements:
            try:
                await conn.execute(sql, params)
            except Exception as e:
                logger.debug("Bulk insert skip: %s", e)
        await conn.commit()
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA journal_mode=WAL")


async def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def insert_project(id: str, title: str, domain: str, status: str, description: str) -> None:
    await execute(
        "INSERT OR IGNORE INTO projects (id,title,domain,status,description,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
        (id, title, domain, status, description, _now(), _now()),
    )


async def get_projects() -> List[Dict[str, Any]]:
    return await fetch_all("SELECT * FROM projects ORDER BY title")


async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    return await fetch_one("SELECT * FROM projects WHERE id=?", (project_id,))


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

async def insert_experiment(
    project_id: str,
    name: str,
    exp_type: str,
    classical_model: str = "",
    quantum_backend: str = "aer_simulator",
    n_qubits: int = 4,
    compiler_passes: int = 3,
    qml_algorithm: str = "",
    error_correction: str = "none",
    optimization_method: str = "COBYLA",
    status: str = "pending",
    classical_accuracy: float = 0.0,
    quantum_accuracy: float = 0.0,
    hybrid_accuracy: float = 0.0,
    speedup_factor: float = 1.0,
    fidelity: float = 0.99,
    circuit_depth: int = 10,
    gate_count: int = 50,
    error_rate: float = 0.01,
    mitigation_method: str = "ZNE",
    notes: str = "",
) -> str:
    exp_id = _uid()
    await execute(
        """INSERT OR IGNORE INTO experiments
        (exp_id,project_id,name,type,classical_model,quantum_backend,n_qubits,
         compiler_passes,qml_algorithm,error_correction,optimization_method,status,
         started_at,classical_accuracy,quantum_accuracy,hybrid_accuracy,
         speedup_factor,fidelity,circuit_depth,gate_count,error_rate,
         mitigation_method,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (exp_id, project_id, name, exp_type, classical_model, quantum_backend,
         n_qubits, compiler_passes, qml_algorithm, error_correction, optimization_method,
         status, _now(), classical_accuracy, quantum_accuracy, hybrid_accuracy,
         speedup_factor, fidelity, circuit_depth, gate_count, error_rate,
         mitigation_method, notes),
    )
    return exp_id


async def get_experiments(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM experiments WHERE project_id=? ORDER BY started_at DESC",
        (project_id,),
    )


async def get_all_experiments() -> List[Dict[str, Any]]:
    return await fetch_all("SELECT * FROM experiments ORDER BY started_at DESC LIMIT 200")


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

async def insert_run(
    run_id: str,
    project_id: str,
    timestamp: str,
    status: str,
    accuracy: Optional[float] = None,
    duration_ms: Optional[int] = None,
    output: Optional[str] = None,
    error: Optional[str] = None,
    stage: str = "",
    metrics: Optional[str] = None,
    exp_id: str = "",
) -> None:
    await execute(
        """INSERT OR REPLACE INTO runs
        (run_id,exp_id,project_id,timestamp,status,accuracy,duration_ms,output,error,stage,metrics)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, exp_id, project_id, timestamp, status, accuracy, duration_ms,
         output, error, stage, metrics),
    )


async def get_runs(limit: int = 50) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
    )


async def get_runs_for_project(project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM runs WHERE project_id=? ORDER BY timestamp DESC LIMIT ?",
        (project_id, limit),
    )


async def update_run_status(run_id: str, status: str, output: str = "", metrics: str = "") -> None:
    """QP-19: Update run status, output, and metrics in place (used by background worker)."""
    await execute(
        "UPDATE runs SET status=?, output=?, metrics=? WHERE run_id=?",
        (status, output, metrics, run_id),
    )


# ---------------------------------------------------------------------------
# Hybrid Pipelines
# ---------------------------------------------------------------------------

async def insert_hybrid_pipeline(
    project_id: str,
    name: str,
    classical_preprocess: str = "",
    encoding_method: str = "angle",
    circuit_design: str = "",
    n_qubits: int = 4,
    circuit_depth: int = 10,
    error_mitigation: str = "ZNE",
    measurement: str = "expectation",
    classical_postprocess: str = "",
    accuracy: float = 0.0,
    throughput_qps: float = 0.0,
    latency_ms: float = 0.0,
) -> str:
    pid = _uid()
    await execute(
        """INSERT OR IGNORE INTO hybrid_pipelines
        (pipeline_id,project_id,name,classical_preprocess,encoding_method,
         circuit_design,n_qubits,circuit_depth,error_mitigation,measurement,
         classical_postprocess,accuracy,throughput_qps,latency_ms,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pid, project_id, name, classical_preprocess, encoding_method,
         circuit_design, n_qubits, circuit_depth, error_mitigation, measurement,
         classical_postprocess, accuracy, throughput_qps, latency_ms, _now()),
    )
    return pid


async def get_hybrid_pipeline(project_id: str) -> Optional[Dict[str, Any]]:
    return await fetch_one(
        "SELECT * FROM hybrid_pipelines WHERE project_id=? ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Compiler Stages
# ---------------------------------------------------------------------------

async def insert_compiler_stage(
    run_id: str,
    project_id: str,
    stage_name: str,
    input_gates: int,
    output_gates: int,
    reduction_pct: float,
    fidelity_before: float,
    fidelity_after: float,
    technique: str,
    tool: str,
    duration_ms: float,
) -> str:
    sid = _uid()
    await execute(
        """INSERT OR IGNORE INTO compiler_stages
        (stage_id,run_id,project_id,stage_name,input_gates,output_gates,
         reduction_pct,fidelity_before,fidelity_after,technique,tool,duration_ms,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (sid, run_id, project_id, stage_name, input_gates, output_gates,
         reduction_pct, fidelity_before, fidelity_after, technique, tool,
         duration_ms, _now()),
    )
    return sid


async def get_compiler_stages(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM compiler_stages WHERE project_id=? ORDER BY timestamp DESC LIMIT 20",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# QML Models
# ---------------------------------------------------------------------------

async def insert_qml_model(
    project_id: str,
    algorithm: str,
    n_qubits: int,
    n_layers: int,
    optimizer: str,
    learning_rate: float,
    epochs: int,
    train_accuracy: float,
    val_accuracy: float,
    test_accuracy: float,
    classical_baseline: float,
    quantum_advantage: float,
    feature_map: str,
    ansatz: str,
) -> str:
    mid = _uid()
    await execute(
        """INSERT OR IGNORE INTO qml_models
        (model_id,project_id,algorithm,n_qubits,n_layers,optimizer,learning_rate,
         epochs,train_accuracy,val_accuracy,test_accuracy,classical_baseline,
         quantum_advantage,feature_map,ansatz,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (mid, project_id, algorithm, n_qubits, n_layers, optimizer, learning_rate,
         epochs, train_accuracy, val_accuracy, test_accuracy, classical_baseline,
         quantum_advantage, feature_map, ansatz, _now()),
    )
    return mid


async def get_qml_models(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM qml_models WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Error Corrections
# ---------------------------------------------------------------------------

async def insert_error_correction(
    run_id: str,
    project_id: str,
    noise_model: str,
    error_rate: float,
    correction_code: str,
    code_distance: int,
    logical_error_rate: float,
    physical_qubits: int,
    logical_qubits: int,
    overhead_ratio: float,
    fidelity_before: float,
    fidelity_after: float,
    technique: str,
) -> str:
    eid = _uid()
    await execute(
        """INSERT OR IGNORE INTO error_corrections
        (ec_id,run_id,project_id,noise_model,error_rate,correction_code,
         code_distance,logical_error_rate,physical_qubits,logical_qubits,
         overhead_ratio,fidelity_before,fidelity_after,technique,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (eid, run_id, project_id, noise_model, error_rate, correction_code,
         code_distance, logical_error_rate, physical_qubits, logical_qubits,
         overhead_ratio, fidelity_before, fidelity_after, technique, _now()),
    )
    return eid


async def get_error_corrections(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM error_corrections WHERE project_id=? ORDER BY timestamp DESC LIMIT 20",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Optimizations
# ---------------------------------------------------------------------------

async def insert_optimization(
    run_id: str,
    project_id: str,
    problem_type: str,
    method: str,
    n_variables: int,
    classical_obj: float,
    quantum_obj: float,
    improvement_pct: float,
    optimizer: str,
    iterations: int,
    convergence_threshold: float,
    circuit_depth: int,
    n_qubits: int,
) -> str:
    oid = _uid()
    await execute(
        """INSERT OR IGNORE INTO optimizations
        (opt_id,run_id,project_id,problem_type,method,n_variables,
         classical_obj,quantum_obj,improvement_pct,optimizer,iterations,
         convergence_threshold,circuit_depth,n_qubits,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (oid, run_id, project_id, problem_type, method, n_variables,
         classical_obj, quantum_obj, improvement_pct, optimizer, iterations,
         convergence_threshold, circuit_depth, n_qubits, _now()),
    )
    return oid


async def get_optimizations(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM optimizations WHERE project_id=? ORDER BY timestamp DESC LIMIT 20",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Circuits
# ---------------------------------------------------------------------------

async def insert_circuit(
    project_id: str,
    name: str,
    n_qubits: int,
    depth: int,
    gate_count: int,
    t_count: int,
    cnot_count: int,
    qasm: str,
    description: str,
    fidelity: float,
    noise_model: str,
) -> str:
    cid = _uid()
    await execute(
        """INSERT OR IGNORE INTO circuits
        (circuit_id,project_id,name,n_qubits,depth,gate_count,t_count,
         cnot_count,qasm,description,fidelity,noise_model,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, project_id, name, n_qubits, depth, gate_count, t_count,
         cnot_count, qasm, description, fidelity, noise_model, _now()),
    )
    return cid


async def get_circuits(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM circuits WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

async def insert_dataset(
    project_id: str,
    name: str,
    source: str,
    n_samples: int,
    n_features: int,
    file_path: str,
    description: str,
    is_synthetic: bool = True,
) -> str:
    did = _uid()
    await execute(
        """INSERT OR IGNORE INTO datasets
        (ds_id,project_id,name,source,n_samples,n_features,file_path,
         created_at,description,is_synthetic)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (did, project_id, name, source, n_samples, n_features, file_path,
         _now(), description, int(is_synthetic)),
    )
    return did


async def get_datasets(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM datasets WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# User Stories
# ---------------------------------------------------------------------------

async def insert_user_story(
    project_id: str,
    role: str,
    goal: str,
    benefit: str,
    acceptance_criteria: str,
    priority: str = "medium",
    story_points: int = 3,
    status: str = "open",
) -> str:
    sid = _uid()
    await execute(
        """INSERT OR IGNORE INTO user_stories
        (story_id,project_id,role,goal,benefit,acceptance_criteria,
         priority,story_points,status,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (sid, project_id, role, goal, benefit, acceptance_criteria,
         priority, story_points, status, _now()),
    )
    return sid


async def get_user_stories(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM user_stories WHERE project_id=? ORDER BY priority DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Demo Stories
# ---------------------------------------------------------------------------

async def insert_demo_story(
    project_id: str,
    title: str,
    narrative: str,
    steps: str,
    expected_output: str,
    duration_min: int,
    audience: str,
) -> str:
    did = _uid()
    await execute(
        """INSERT OR IGNORE INTO demo_stories
        (demo_id,project_id,title,narrative,steps,expected_output,
         duration_min,audience,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (did, project_id, title, narrative, steps, expected_output,
         duration_min, audience, _now()),
    )
    return did


async def get_demo_stories(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM demo_stories WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Architecture Docs
# ---------------------------------------------------------------------------

async def insert_architecture_doc(
    project_id: str,
    doc_type: str,
    title: str,
    content: str,
    version: str = "1.0",
    author: str = "system",
) -> str:
    did = _uid()
    await execute(
        """INSERT OR IGNORE INTO architecture_docs
        (doc_id,project_id,doc_type,title,content,version,author,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (did, project_id, doc_type, title, content, version, author, _now(), _now()),
    )
    return did


async def get_architecture_docs(project_id: str, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    if doc_type:
        return await fetch_all(
            "SELECT * FROM architecture_docs WHERE project_id=? AND doc_type=? ORDER BY created_at DESC",
            (project_id, doc_type),
        )
    return await fetch_all(
        "SELECT * FROM architecture_docs WHERE project_id=? ORDER BY doc_type",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Test Results
# ---------------------------------------------------------------------------

async def insert_test_result(
    project_id: str,
    test_type: str,
    test_name: str,
    status: str,
    duration_ms: float,
    error_message: str = "",
    coverage_pct: float = 0.0,
    assertions: int = 0,
    run_id: str = "",
) -> str:
    tid = _uid()
    await execute(
        """INSERT OR IGNORE INTO test_results
        (test_id,project_id,run_id,test_type,test_name,status,
         duration_ms,error_message,timestamp,coverage_pct,assertions)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, project_id, run_id, test_type, test_name, status,
         duration_ms, error_message, _now(), coverage_pct, assertions),
    )
    return tid


async def get_test_results(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM test_results WHERE project_id=? ORDER BY timestamp DESC LIMIT 50",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

async def insert_api_test(
    project_id: str,
    endpoint: str,
    method: str,
    payload: str,
    response_status: int,
    response_body: str,
    latency_ms: float,
    passed: bool,
) -> str:
    tid = _uid()
    await execute(
        """INSERT OR IGNORE INTO api_tests
        (api_test_id,project_id,endpoint,method,payload,response_status,
         response_body,latency_ms,passed,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (tid, project_id, endpoint, method, payload, response_status,
         response_body, latency_ms, int(passed), _now()),
    )
    return tid


async def get_api_tests(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM api_tests WHERE project_id=? ORDER BY timestamp DESC LIMIT 30",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Security Scans
# ---------------------------------------------------------------------------

async def insert_security_scan(
    project_id: str,
    scan_type: str,
    severity: str,
    finding: str,
    remediation: str,
    status: str = "open",
) -> str:
    sid = _uid()
    await execute(
        """INSERT OR IGNORE INTO security_scans
        (scan_id,project_id,scan_type,severity,finding,remediation,status,timestamp)
        VALUES (?,?,?,?,?,?,?,?)""",
        (sid, project_id, scan_type, severity, finding, remediation, status, _now()),
    )
    return sid


async def get_security_scans(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM security_scans WHERE project_id=? ORDER BY timestamp DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Layer Tracking
# ---------------------------------------------------------------------------

async def insert_layer_tracking(
    project_id: str,
    layer_id: str,
    layer_name: str,
    status: str = "pending",
    quality_gate: str = "QG-01",
    qg_passed: bool = False,
    input_spec: str = "",
    output_spec: str = "",
    tool: str = "",
    metrics: str = "",
) -> str:
    tid = _uid()
    await execute(
        """INSERT OR IGNORE INTO layer_tracking
        (tracking_id,project_id,layer_id,layer_name,status,quality_gate,
         qg_passed,input_spec,output_spec,tool,last_run,metrics)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, project_id, layer_id, layer_name, status, quality_gate,
         int(qg_passed), input_spec, output_spec, tool, _now(), metrics),
    )
    return tid


async def get_layer_tracking(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM layer_tracking WHERE project_id=? ORDER BY layer_id",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------

async def insert_simulation(
    project_id: str,
    name: str,
    sim_type: str,
    n_qubits: int,
    shots: int,
    noise_model: str,
    result: str,
    statevector: str,
    probabilities: str,
    duration_ms: float,
) -> str:
    sid = _uid()
    await execute(
        """INSERT OR IGNORE INTO simulations
        (sim_id,project_id,name,type,n_qubits,shots,noise_model,
         result,statevector,probabilities,timestamp,duration_ms)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (sid, project_id, name, sim_type, n_qubits, shots, noise_model,
         result, statevector, probabilities, _now(), duration_ms),
    )
    return sid


async def get_simulations(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM simulations WHERE project_id=? ORDER BY timestamp DESC LIMIT 20",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# RAG Documents
# ---------------------------------------------------------------------------

async def insert_rag_document(
    project_id: str,
    title: str,
    content: str,
    doc_type: str,
    embedding_id: str = "",
    collection: str = "",
) -> str:
    did = _uid()
    await execute(
        """INSERT OR IGNORE INTO rag_documents
        (doc_id,project_id,title,content,doc_type,embedding_id,collection,created_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (did, project_id, title, content, doc_type, embedding_id, collection, _now()),
    )
    return did


async def get_rag_documents(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT doc_id,project_id,title,doc_type,collection,created_at FROM rag_documents WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Animations
# ---------------------------------------------------------------------------

async def insert_animation(
    project_id: str,
    name: str,
    anim_type: str,
    config: str,
) -> str:
    aid = _uid()
    await execute(
        """INSERT OR IGNORE INTO animations
        (anim_id,project_id,name,type,config,created_at)
        VALUES (?,?,?,?,?,?)""",
        (aid, project_id, name, anim_type, config, _now()),
    )
    return aid


async def get_animations(project_id: str) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM animations WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )


# ---------------------------------------------------------------------------
# Operation Logs
# ---------------------------------------------------------------------------

async def insert_operation_log(
    log_id: str,
    timestamp: str,
    method: str,
    endpoint: str,
    project_id: Optional[str],
    request_body: Optional[str],
    response_status: Optional[int],
    response_time_ms: Optional[float],
    error: Optional[str],
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> None:
    await execute(
        """INSERT OR IGNORE INTO operation_logs
        (log_id,timestamp,method,endpoint,project_id,request_body,
         response_status,response_time_ms,error,user_agent,ip_address)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (log_id, timestamp, method, endpoint, project_id, request_body,
         response_status, response_time_ms, error, user_agent, ip_address),
    )


async def get_operation_logs(limit: int = 100) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM operation_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )


async def get_operation_logs_for_project(project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    return await fetch_all(
        "SELECT * FROM operation_logs WHERE project_id=? ORDER BY timestamp DESC LIMIT ?",
        (project_id, limit),
    )


async def clear_operation_logs(older_than_days: int = 7) -> int:
    """Delete logs older than N days. Returns count deleted."""
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    import datetime as dt
    cutoff_str = (cutoff - dt.timedelta(days=older_than_days)).isoformat()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT COUNT(*) as cnt FROM operation_logs WHERE timestamp < ?", (cutoff_str,)
        ) as cur:
            row = await cur.fetchone()
            count = dict(row)["cnt"] if row else 0
        await conn.execute("DELETE FROM operation_logs WHERE timestamp < ?", (cutoff_str,))
        await conn.commit()
    return count


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------

async def insert_comparison(
    project_id: str,
    classical_accuracy: float,
    quantum_accuracy: float,
    classical_compiler_gates: int,
    quantum_compiler_gates: int,
    classical_error_rate: float,
    quantum_error_rate: float,
    classical_opt_score: float,
    quantum_opt_score: float,
    classical_latency_ms: float,
    quantum_latency_ms: float,
    classical_cost: float = 0.0,
    quantum_cost: float = 0.0,
) -> str:
    cid = _uid()
    await execute(
        """INSERT OR REPLACE INTO comparisons
        (comp_id,project_id,classical_accuracy,quantum_accuracy,
         classical_compiler_gates,quantum_compiler_gates,
         classical_error_rate,quantum_error_rate,
         classical_opt_score,quantum_opt_score,
         classical_latency_ms,quantum_latency_ms,
         classical_cost,quantum_cost,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, project_id, classical_accuracy, quantum_accuracy,
         classical_compiler_gates, quantum_compiler_gates,
         classical_error_rate, quantum_error_rate,
         classical_opt_score, quantum_opt_score,
         classical_latency_ms, quantum_latency_ms,
         classical_cost, quantum_cost, _now()),
    )
    return cid


async def get_comparison(project_id: str) -> Optional[Dict[str, Any]]:
    return await fetch_one(
        "SELECT * FROM comparisons WHERE project_id=? ORDER BY updated_at DESC LIMIT 1",
        (project_id,),
    )

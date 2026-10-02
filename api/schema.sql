-- Quantum Portal — complete schema
-- All tables use TEXT primary keys (UUID strings)

CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    domain      TEXT,
    status      TEXT DEFAULT 'active',
    description TEXT,
    created_at  TEXT,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    exp_id              TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    name                TEXT,
    type                TEXT,
    classical_model     TEXT,
    quantum_backend     TEXT,
    n_qubits            INTEGER,
    compiler_passes     INTEGER,
    qml_algorithm       TEXT,
    error_correction    TEXT,
    optimization_method TEXT,
    status              TEXT DEFAULT 'pending',
    started_at          TEXT,
    completed_at        TEXT,
    classical_accuracy  REAL,
    quantum_accuracy    REAL,
    hybrid_accuracy     REAL,
    speedup_factor      REAL,
    fidelity            REAL,
    circuit_depth       INTEGER,
    gate_count          INTEGER,
    error_rate          REAL,
    mitigation_method   TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    exp_id       TEXT,
    project_id   TEXT NOT NULL,
    timestamp    TEXT NOT NULL,
    status       TEXT NOT NULL,
    accuracy     REAL,
    duration_ms  INTEGER,
    output       TEXT,
    error        TEXT,
    stage        TEXT,
    metrics      TEXT
);

CREATE TABLE IF NOT EXISTS hybrid_pipelines (
    pipeline_id           TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL,
    name                  TEXT,
    classical_preprocess  TEXT,
    encoding_method       TEXT,
    circuit_design        TEXT,
    n_qubits              INTEGER,
    circuit_depth         INTEGER,
    error_mitigation      TEXT,
    measurement           TEXT,
    classical_postprocess TEXT,
    accuracy              REAL,
    throughput_qps        REAL,
    latency_ms            REAL,
    created_at            TEXT
);

CREATE TABLE IF NOT EXISTS compiler_stages (
    stage_id        TEXT PRIMARY KEY,
    run_id          TEXT,
    project_id      TEXT NOT NULL,
    stage_name      TEXT,
    input_gates     INTEGER,
    output_gates    INTEGER,
    reduction_pct   REAL,
    fidelity_before REAL,
    fidelity_after  REAL,
    technique       TEXT,
    tool            TEXT,
    duration_ms     REAL,
    timestamp       TEXT
);

CREATE TABLE IF NOT EXISTS qml_models (
    model_id          TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL,
    algorithm         TEXT,
    n_qubits          INTEGER,
    n_layers          INTEGER,
    optimizer         TEXT,
    learning_rate     REAL,
    epochs            INTEGER,
    train_accuracy    REAL,
    val_accuracy      REAL,
    test_accuracy     REAL,
    classical_baseline REAL,
    quantum_advantage REAL,
    feature_map       TEXT,
    ansatz            TEXT,
    created_at        TEXT
);

CREATE TABLE IF NOT EXISTS error_corrections (
    ec_id              TEXT PRIMARY KEY,
    run_id             TEXT,
    project_id         TEXT NOT NULL,
    noise_model        TEXT,
    error_rate         REAL,
    correction_code    TEXT,
    code_distance      INTEGER,
    logical_error_rate REAL,
    physical_qubits    INTEGER,
    logical_qubits     INTEGER,
    overhead_ratio     REAL,
    fidelity_before    REAL,
    fidelity_after     REAL,
    technique          TEXT,
    timestamp          TEXT
);

CREATE TABLE IF NOT EXISTS optimizations (
    opt_id               TEXT PRIMARY KEY,
    run_id               TEXT,
    project_id           TEXT NOT NULL,
    problem_type         TEXT,
    method               TEXT,
    n_variables          INTEGER,
    classical_obj        REAL,
    quantum_obj          REAL,
    improvement_pct      REAL,
    optimizer            TEXT,
    iterations           INTEGER,
    convergence_threshold REAL,
    circuit_depth        INTEGER,
    n_qubits             INTEGER,
    timestamp            TEXT
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id  TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    name        TEXT,
    n_qubits    INTEGER,
    depth       INTEGER,
    gate_count  INTEGER,
    t_count     INTEGER,
    cnot_count  INTEGER,
    qasm        TEXT,
    description TEXT,
    fidelity    REAL,
    noise_model TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
    ds_id        TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    name         TEXT,
    source       TEXT,
    n_samples    INTEGER,
    n_features   INTEGER,
    file_path    TEXT,
    created_at   TEXT,
    description  TEXT,
    is_synthetic INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS user_stories (
    story_id            TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    role                TEXT,
    goal                TEXT,
    benefit             TEXT,
    acceptance_criteria TEXT,
    priority            TEXT DEFAULT 'medium',
    story_points        INTEGER,
    status              TEXT DEFAULT 'open',
    created_at          TEXT
);

CREATE TABLE IF NOT EXISTS demo_stories (
    demo_id         TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    title           TEXT,
    narrative       TEXT,
    steps           TEXT,
    expected_output TEXT,
    duration_min    INTEGER,
    audience        TEXT,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS architecture_docs (
    doc_id     TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    doc_type   TEXT,
    title      TEXT,
    content    TEXT,
    version    TEXT DEFAULT '1.0',
    author     TEXT DEFAULT 'system',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS test_results (
    test_id      TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    run_id       TEXT,
    test_type    TEXT,
    test_name    TEXT,
    status       TEXT DEFAULT 'pending',
    duration_ms  REAL,
    error_message TEXT,
    timestamp    TEXT,
    coverage_pct REAL,
    assertions   INTEGER
);

CREATE TABLE IF NOT EXISTS api_tests (
    api_test_id     TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    endpoint        TEXT,
    method          TEXT DEFAULT 'GET',
    payload         TEXT,
    response_status INTEGER,
    response_body   TEXT,
    latency_ms      REAL,
    passed          INTEGER DEFAULT 0,
    timestamp       TEXT
);

CREATE TABLE IF NOT EXISTS security_scans (
    scan_id    TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    scan_type  TEXT,
    severity   TEXT,
    finding    TEXT,
    remediation TEXT,
    status     TEXT DEFAULT 'open',
    timestamp  TEXT
);

CREATE TABLE IF NOT EXISTS layer_tracking (
    tracking_id TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    layer_id    TEXT,
    layer_name  TEXT,
    status      TEXT DEFAULT 'pending',
    quality_gate TEXT,
    qg_passed   INTEGER DEFAULT 0,
    input_spec  TEXT,
    output_spec TEXT,
    tool        TEXT,
    last_run    TEXT,
    metrics     TEXT
);

CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id       TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    title        TEXT,
    content      TEXT,
    doc_type     TEXT,
    embedding_id TEXT,
    collection   TEXT,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS animations (
    anim_id    TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name       TEXT,
    type       TEXT,
    config     TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS simulations (
    sim_id        TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL,
    name          TEXT,
    type          TEXT,
    n_qubits      INTEGER,
    shots         INTEGER DEFAULT 1024,
    noise_model   TEXT,
    result        TEXT,
    statevector   TEXT,
    probabilities TEXT,
    timestamp     TEXT,
    duration_ms   REAL
);

CREATE TABLE IF NOT EXISTS operation_logs (
    log_id           TEXT PRIMARY KEY,
    timestamp        TEXT NOT NULL,
    method           TEXT,
    endpoint         TEXT,
    project_id       TEXT,
    request_body     TEXT,
    response_status  INTEGER,
    response_time_ms REAL,
    error            TEXT,
    user_agent       TEXT,
    ip_address       TEXT
);

CREATE TABLE IF NOT EXISTS comparisons (
    comp_id                    TEXT PRIMARY KEY,
    project_id                 TEXT NOT NULL,
    classical_accuracy         REAL,
    quantum_accuracy           REAL,
    classical_compiler_gates   INTEGER,
    quantum_compiler_gates     INTEGER,
    classical_error_rate       REAL,
    quantum_error_rate         REAL,
    classical_opt_score        REAL,
    quantum_opt_score          REAL,
    classical_latency_ms       REAL,
    quantum_latency_ms         REAL,
    classical_cost             REAL,
    quantum_cost               REAL,
    updated_at                 TEXT
);

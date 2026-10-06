# Quantum: demo and production implementation plan

Created: October 1, 2026. Status: PLANNED — no implementation or deployment implied.
Evidence: docs/audits/2026-10-01-review.md. Fresh crypto test result: 108 passed; frontend TypeScript check passed.

## Target outcomes and boundaries

Demo release: five reproducible, guided browser journeys backed by real executions or clearly identified historical artifacts. All other pages display their actual capability state. A simulator run is real computation, but is never presented as a hardware QPU run.

Production pilot: authenticated single-organization research/education portal with durable jobs, measured results, maintained cryptographic providers, reproducible releases and verified recovery. Healthcare predictions remain research demonstrations; enterprise multi-tenancy, clinical deployment, hardware control and broad cloud deployment require separate acceptance plans.

Do not add more pages before execution truth and deployment reliability are fixed. Existing educational cryptography remains available with explicit labels; production security paths use maintained implementations. Standards-compliance claims require specific conformance evidence.

## Release gates

| Gate | Required evidence | Blocks |
|---|---|---|
| G0: reproducible source | Clean-checkout build, tracked required code, dependency locks, build identifier | Any release |
| G1: trustworthy execution | Success/error/timeout/cancel/restart tests, metrics tied to immutable artifacts | Demo |
| G2: demo ready | Five browser journeys pass; replay visibly labeled; no fabricated measured values | Demo |
| G3: protected pilot | Access-control matrix, isolated workers, fail-closed configuration, security checks | Shared production |
| G4: operable pilot | Load results, restore drill, upgrade/rollback drill, alerts and runbooks | Production pilot |

Every task starts NOT_STARTED. A checkbox is complete only when its evidence exists. Blocked tasks record the prerequisite and next action. Page count and passing unit tests alone do not satisfy a release gate.

## Phase 0 — Preserve and reproduce the project (P0)

- [ ] QP-01: Inventory root and nested portal Git state. Back up current work; choose an explicitly versioned portal submodule or consolidate into the root repository. Preserve nested history. Track required source/workflows/configuration; exclude databases, caches, secrets, private datasets and generated runtime state. Scan staged contents before an initial commit. Do not publish without authorization.
- [ ] QP-02: Record current Python/Node/package state; pin tested dependencies and runtime versions. Local commands activate /home/praveen/venv-ardupilot in the same shell. Do not create environments or reinstall available packages. Container dependencies are locked separately.
- [ ] QP-03: Choose SQLite for the local single-worker demo and PostgreSQL for the concurrent production pilot. Introduce explicit database configuration, versioned migrations and migration parity tests; remove unused services from the demo profile. Replace embedded credentials with private runtime configuration.
- [ ] QP-04: Repair portal standalone output, image build context and Python package/script resolution. Use browser same-origin API routing through a server proxy; keep service hostnames server-side. Mount persistent database/artifact storage. Add health/readiness and build SHA/version endpoints.

Touchpoints: .gitignore, quantum-portal-web/next.config.ts, Dockerfiles, docker-compose.yml, api/database.py, api/main.py, api/requirements.txt.
Acceptance: clean checkout builds both images; local demo starts without host absolute paths; database/artifacts survive recreation; security route contract passes against the running image; source and running build identifiers agree. No restart of current services until a verified replacement exists.
Dependencies: QP-03/04 follow inventory; G0 follows QP-01–04.

## Phase 1 — Make execution and reporting truthful (P0)

- [ ] QP-05: Replace SCRIPT_MAP with a capability registry: project ID, supported action, runner, accepted input schema, backend and evidence state. Correct the VQE/portfolio mismatch. Unsupported actions return an explicit unsupported response, never a fabricated result.
- [ ] QP-06: Use one execution service for POST and SSE. State machine: queued → running → succeeded / failed / timed_out / cancelled. Persist one run ID throughout; terminal states cannot turn into success. Kill and reap timed-out subprocesses. Resume observation after browser reconnect; retry creates a linked new attempt.
- [ ] QP-07: Require runner-produced structured metrics and artifacts. Store dataset hash, split identifier, seed, parameters, dependency versions, source revision, backend/device, timestamps and artifact hashes. Reject missing/malformed output. Remove hash-derived accuracy, fabricated hybrid improvement and fixed fidelity/duration from measured reports.
- [ ] QP-08: Add provenance to every metric/result: measured simulator, measured hardware, historical measured artifact, estimate, educational simulation or unavailable. Show sample size, run date and source. Replace static security percentages/attack events/benchmark timings with real data where available; visibly label fixtures where retained. Production mode disables fixture fallback.

Acceptance: no-script, nonzero exit, timeout, malformed output and worker crash cannot create success; reconnect returns the same persisted run; actual duration is recorded; result hashes resolve; unavailable data displays unavailable. SSE stages reflect runner events rather than timed pretend progress.
Dependencies: QP-05 before QP-06/07; QP-08 consumes QP-07. G1 follows all four.

## Phase 2 — Repair scientific validity (P0/P1)

- [ ] QP-09: Split banking data before fitting PCA/scalers. Fit preprocessing on training data only; persist it with the model. Keep identical holdout IDs across classical and quantum experiments. Training balancing must not alter the representative evaluation holdout.
- [ ] QP-10: Separate small matched-compute simulator benchmarks from full-dataset classical baselines. Report actual training/test counts and prevalence. Use at least five seeds, confidence intervals and paired evaluation; report ROC-AUC, PR-AUC, precision/recall/F1, training/inference duration and compute configuration. Choose thresholds on validation data only.
- [ ] QP-11: Withdraw or qualify unsupported advantage claims until reruns are complete. Reconcile PORTFOLIO.md, API summaries and portal cards with signed-off artifacts. For crypto performance, report equivalent operations/security targets, machine/provider versions and repeated timing distributions; keygen speed alone is not an overall security advantage.

Acceptance: held-out records do not participate in preprocessing/training; comparison manifest proves matched evaluation; scripts reproduce metrics within declared tolerance; old unverified benchmark claims cannot appear as fresh results.
Dependencies: QP-07 before evidence capture; QP-09 before QP-10/11.

## Phase 3 — Build an engaging, honest demo (P1)

- [ ] QP-12: Add a guided Demo Hub using existing pages: choose story → inspect input → execute → inspect result/evidence → compare → explain limitation. Show capability badges, progress, actionable errors, cancel and reset. Provide a presenter script and downloadable evidence summary.
- [ ] QP-13: Deliver these journeys in order:
  1. PQC readiness: scan an isolated fixture, generate CBOM, inspect vulnerable assets, produce migration recommendations. Include a maintained-provider KEM roundtrip and sign/verify demonstration. Clearly distinguish recommendations from completed migration.
  2. QKD: run BB84 without/with simulated eavesdropping; show sifted key and QBER. Label the simulated channel and simplified protocol stages.
  3. Banking: run a bounded matched-data classical/VQC comparison with preprocessing and result provenance visible. Live quick mode may use a smaller subset; historical long-run replay shows original run date and configuration.
  4. Finance: wire quantum_options.py through the execution service; compare with an analytic/classical reference using the same inputs, confidence bounds and runtime.
  5. Healthcare ECG: wire quantum_ecg.py; show research dataset provenance, held-out comparison and error analysis without clinical claims.
- [ ] QP-14: Integrate real NSL-KDD records into IDS with train-only preprocessing and a repeatable evaluation manifest. Keep it an optional sixth demo until validated. Add banking/finance notebooks after the executable paths are stable.
- [ ] QP-15: Add Playwright checks for each journey, including API unavailable, authorization denied, runner failure, reconnect and empty-data behavior. Include keyboard navigation and readable error/result states.

Acceptance: five journeys pass on the release image; presenters can reset fixtures; live quick mode has a measured runtime budget; replay is never labeled live. Capture video/screenshots, browser traces, run IDs and artifact hashes. G2 requires QP-12/13/15 and G0/G1; banking comparison requires QP-09–11.

## Phase 4 — Protect the shared production pilot (P0 before exposure)

- [ ] QP-16: Integrate configured identity provider/OIDC; validate tokens/sessions server-side. Define viewer (read), operator (run own permitted jobs), admin (configuration/users) and service roles. Enforce access on APIs, SSE, downloads and artifacts. Define single-organization scope; do not imply tenant isolation.
- [ ] QP-17: Replace wildcard CORS with explicit allowed origins; add CSRF protection where cookie sessions authorize writes. Apply request, qubit, shot, dataset, timeout, output and concurrency bounds. Rate-limit execution and expensive inference; enforce per-user quotas and overload responses.
- [ ] QP-18: Remove raw sensitive request logging. Redact tokens, private data and key material; retain structured audit metadata with configured retention. Keep secrets outside images/source and fail startup when required production settings are absent.
- [ ] QP-19: Move blocking execution into isolated non-root workers with bounded CPU/memory/time, read-only source, scoped writable artifacts and restricted network. Accept allowlisted tasks only. Durable queue provides leases, heartbeat, idempotency, bounded retries and recovery without duplicate terminal results. API requests never run long synchronous subprocess jobs.
- [ ] QP-20: Route security operations to maintained cryptographic libraries/providers; keep handcrafted algorithms educational. Add known-answer/interoperability checks where available, tamper/invalid-input rejection and key lifecycle rules. Report provider and validation status accurately; do not claim FIPS validation from implementing named algorithms.

Acceptance: complete role/endpoint matrix passes; unauthorized/expired sessions cannot observe or trigger jobs; bounds reject oversized workloads; worker failures do not take down API; keys/secrets are absent from logs/artifacts; production starts without demo fallback. G3 follows QP-16–20 and G0/G1.

## Phase 5 — Establish operations and release discipline (P1)

- [ ] QP-21: Remove test/dependency/lint failure masking. CI checks backend units/contracts, meaningful crypto tests, capability smoke tests, frontend typecheck/lint/build, five browser journeys and container startup. Test algorithm invariants and failure paths; do not duplicate implementation with superficial tests. Unsupported architecture-only labs get honest status rather than token tests.
- [ ] QP-22: Add dependency/secret/image scanning, pinned build inputs, image SBOM, artifact retention and release manifests. Define vulnerability triage with time-bound documented exceptions rather than silently passing findings.
- [ ] QP-23: Instrument request errors/latency, queue depth/wait, run outcomes/timeouts, worker heartbeats, database and disk health. Correlate request → run → artifact. Verify an alert reaches the configured operator destination through an authorized test.
- [ ] QP-24: Automate encrypted database/artifact backup; perform actual restore into an isolated instance. Document upgrades, schema migration rollback constraints, image rollback, failed jobs and provider outages. Verify a rollback with compatible schema.
- [ ] QP-25: Load-test the agreed pilot envelope. Initial proposed target: 10 concurrent viewers, 2 concurrent bounded simulator jobs, p95 metadata API <500 ms, request failures <1%, and UI responsive under saturation. Exclude long-running job duration from metadata latency. Proposed recovery targets: RPO 24 hours, RTO 4 hours. Accept or revise targets from measured hardware capacity and operator requirements before declaring G4.

Acceptance: CI genuinely fails on an injected failure; clean release deployment passes smoke/browser checks; load, restore and rollback evidence retained; operators can diagnose a failed run without private request content. G4 requires QP-21–25 plus G3/G2.

## Delivery order and effort

| Milestone | Tasks | Rough engineering effort | Exit |
|---|---|---|---|
| Trustworthy local baseline | QP-01–08 | 5–8 working days | G0/G1 |
| Valid comparison and core security/banking demos | QP-09–13 partial, QP-15 | 5–8 working days | First three journeys verified |
| Expanded demo release | Finance/ECG portions of QP-13, QP-14 optional | 4–7 working days | G2 |
| Protected production pilot | QP-16–20 | 7–12 working days | G3 |
| Operable pilot release | QP-21–25 | 5–8 working days | G4 |

Estimates assume one engineer and existing compatible dependencies; they are not promises. Benchmark runtimes, identity-provider configuration and cryptographic provider compatibility may add time. Shared access stays disabled until G3; a local demo can ship at G2. Fold regression tests into each phase instead of postponing all testing to Phase 5.

## Evidence and automatic progress tracking

Use docs/plans/quantum-readiness-tasks.csv as the task register. Record status (NOT_STARTED, IN_PROGRESS, BLOCKED, DONE), evidence path, owner and blocker. CI should publish docs/readiness/latest.json and retained per-release results containing build ID, timestamp, test counts, journey outcomes and artifact links. Derive gate status from checks; never promote a gate from manually ticked boxes alone. Scheduled smoke checks detect route/source drift and create a local failure record; external notifications require a configured, authorized destination.

Each deliberate implementation change is logged immediately to Continuity; update session notes with current task, blocker and next action. Existing pending-page claims remain historical implementation claims until release evidence verifies them. No automatic tracker or scheduler is installed by this planning deliverable.

First implementation slice: QP-01 inventory, QP-04 running/source route check, QP-05/06 truthful runner, then QP-09 train-only preprocessing. Review the resulting measured artifacts before expanding the demo.
